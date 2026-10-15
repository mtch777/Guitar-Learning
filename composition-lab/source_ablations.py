"""Source-conditioned multi-role statistical ablations, with explicit limits.

Role indices are explicit. Model observations stay separate by source track;
generated outputs use native source tuning/programs and fresh GPIF tables.
This is a testable baseline, not a validated phrase-aware composition model.
"""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
import importlib
import json
from pathlib import Path
import sys
from exact_score import extract_score, meter_length
from controlled_generation import position_chord
from generation_validation import track_metrics, copying_ngrams
from gp_author import write_gp
from musicxml_bridge import export_musicxml
from relational_graph import build_graph


def checkpoint_models():
    # Legacy checkpoint imports are absolute. Isolate resolution during import;
    # canonical extraction above remains explicitly namespaced.
    directory=str(Path(__file__).parent/'checkpoints/2026-10-14')
    sys.path.insert(0,directory)
    try:
        importlib.import_module('music_events')
        model=importlib.import_module('sequence_model').SequenceModel
        generate=importlib.import_module('sequence_generator_balanced').generate
    finally: sys.path.remove(directory)
    return model,generate


def fit_pitches(pitches,tuning,previous=()):
    for shift in sorted(range(-5,6),key=lambda x:(abs(x),x)):
        shifted=[p+12*shift for p in pitches]
        try: return [(p,s,f) for p,(s,f) in zip(shifted,position_chord(shifted,tuning,previous=previous))]
        except ValueError: pass
    raise ValueError('No playable exact chord shape')


def learn_parts(score,indices,bars,seed):
    Model,sample=checkpoint_models(); generated={}; evidence={}
    meter=Counter(m['time_signature'] for m in score['tracks'][indices['harmony']]['measures']).most_common(1)[0][0]
    for role,ti in indices.items():
        source=score['tracks'][ti]; view=deepcopy(source); excluded=0
        for m in view['measures']:
            for vi,v in enumerate(m['voices']):
                excluded+=sum(bool(e.get('grace_type')) for e in v)
                m['voices'][vi]=[e for e in v if not e.get('grace_type')]
        # The full canonical source retains ornaments; this training view does
        # not yet model grace performance timing or tied-note attack semantics.
        model=Model.from_scores([dict(tracks=[view])])
        measures,report=sample(model,source['tunings'][0],bars=bars,meter=meter,seed=seed+ti,max_fret=24)
        # Validate joint fingering, rather than trusting the older greedy fitter.
        previous=()
        for measure in measures:
            for e in measure:
                if e['positions']:
                    e['positions']=fit_pitches([p for p,s,f in e['positions']],source['tunings'][0],previous)
                    previous=[(s,f) for p,s,f in e['positions']]
        generated[role]=measures
        evidence[role]=dict(source_track=ti,source_name=source['name'],training_events=model.event_count,
            source_grace_events_excluded_from_training_view=excluded,statistics=report,
            tie_policy='written continuations are training events; no claim of attack/sustain learning')
    return generated,evidence,meter


def source_period(track,bars):
    seen={}; distances=Counter()
    for mi,m in enumerate(track['measures']):
        if not m['voices']:continue
        events=m['voices'][0]; pitches=[n['midi'] for e in events for n in e['notes'] if n['midi'] is not None]
        if not pitches:continue
        signature=tuple((e['duration_q'],tuple(n['midi']-pitches[0] for n in e['notes'])) for e in events)
        if signature in seen and 0<mi-seen[signature]<=bars: distances[mi-seen[signature]]+=1
        seen[signature]=mi
    # No fixed 4/8-bar assumption: use actual repeated-bar distance as a weak cue.
    return (distances.most_common(1)[0][0] if distances else bars),dict(distances)


def make_score(source,indices,parts,meter,stage,period):
    count=len(parts['harmony']); length=meter_length(meter)
    plan=[]
    for bar in parts['harmony']:
        sounding=[e['positions'] for e in bar if e['positions']]
        if not sounding: plan.append([])
        else:
            # Observed generated voicing, not a claimed harmonic root/quality.
            plan.append(Counter(tuple(p for p,s,f in x) for x in sounding).most_common(1)[0][0])
    roles=['harmony']+(['melody'] if stage>=3 else [])+(['bass'] if stage>=4 else [])
    score=dict(source_file='generated-from-'+source['source_file'],tracks=[])
    for index,role in enumerate(roles):
        original=source['tracks'][indices[role]]; tuning=original['tunings'][0]
        program=original.get('program')
        if program is None:raise ValueError('Source instrument program is unknown; choose an explicit target')
        track=dict(index=index,name=original['name'],tunings=[tuning],program=program,measures=[])
        previous=()
        for mi in range(count):
            material=deepcopy(parts[role][mi if role!='melody' or stage<4 else mi%period])
            if stage==1: material=[dict(units=length*4,positions=[])]
            events=[]; local=Fraction(0)
            anchor=next((e['positions'][0][0] for e in material if e['positions']),None)
            for ei,e in enumerate(material):
                pitches=[p for p,s,f in e['positions']]
                if role=='harmony' and (pitches or stage==1): pitches=list(plan[mi])
                if role in ('melody','bass') and pitches and plan[mi] and anchor is not None:
                    # A reproducible coordination ablation using a voicing anchor.
                    # It is not root inference or NCT functional interpretation.
                    shift=min(range(-6,7),key=lambda d:((anchor+d-min(plan[mi]))%12!=0,abs(d)))
                    pitches=[p+shift for p in pitches]
                positions=fit_pitches(pitches,tuning,previous) if pitches else []
                if positions: previous=[(s,f) for p,s,f in positions]
                duration=Fraction(e['units'])/4
                events.append(dict(onset_q=str(mi*length+local),local_onset_q=str(local),duration_q=str(duration),
                    notes=[dict(midi=p,string=s,fret=f,tie=None,technique_tags=[]) for p,s,f in positions]))
                local+=duration
            if local!=length: raise ValueError('Generated role does not fill meter')
            track['measures'].append(dict(number=mi+1,onset_q=str(mi*length),time_signature=meter,
                section=f'motif-{mi//period+1}' if stage>=4 else None,voices=[events]))
        score['tracks'].append(track)
    return score


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--lead',type=int,required=True)
    p.add_argument('--harmony',type=int,required=True);p.add_argument('--bass',type=int,required=True)
    p.add_argument('--bars',type=int,default=16);p.add_argument('--seed',type=int,default=17);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();source=extract_score(args.source);indices=dict(harmony=args.harmony,melody=args.lead,bass=args.bass)
    if args.out.exists(): raise FileExistsError('Choose fresh artifact directory')
    args.out.mkdir(parents=True);parts,evidence,meter=learn_parts(source,indices,args.bars,args.seed)
    period,periods=source_period(source['tracks'][args.lead],args.bars)
    report=dict(source_sha256=source['source_sha256'],seed=args.seed,meter=meter,roles=evidence,
        motif_period=period,motif_period_evidence=periods,stages={},
        limitations=['Statistical role baseline, not validated musical quality','Voicing-anchor coordination is not harmonic function inference',
          'Exact 0% controls are in controlled_generation; these feature ablations are not target-control claims',
          'No learned drums/vocals/ornaments/ties; selected source pitched roles only',
          'Motif repetition cue is not an adjudicated phrase boundary','No held-out source used for fitting'])
    for stage,name in enumerate(['harmony','harmony-rhythm','harmony-rhythm-melody','roles-phrases'],1):
        score=make_score(source,indices,parts,meter,stage,period);path=args.out/(name+'.gp');write_gp(score,path,title=name)
        (args.out/(name+'.expected.json')).write_text(json.dumps(score),encoding='utf-8')
        export_musicxml(score,args.out/(name+'.musicxml'))
        (args.out/(name+'.graph.json')).write_text(json.dumps(build_graph(score)),encoding='utf-8')
        report['stages'][name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),metrics=track_metrics(score),copying=copying_ngrams(source,score))
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(source=args.source.name,motif_period=period,stages={k:[t['notes'] for t in r['metrics']] for k,r in report['stages'].items()})))


if __name__=='__main__':main()
