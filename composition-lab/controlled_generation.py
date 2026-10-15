"""Finite, measurable composition experiments from explicit relational plans.

Prototype, not a trained style model. Harmony and chord-relative degrees must be
provided with provenance; arbitrary GP notes are never silently assigned roles.
Difference is the share of changed plan units, not edit probability. Candidate
search reports achievable distances and rejects incompatible zero locks.
"""
import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import random
from gp_author import write_gp
from generation_validation import track_metrics, copying_ngrams
from musicxml_bridge import export_musicxml
from relational_graph import build_graph

DIMENSIONS=('harmony','rhythm','melody','structure')


def units(plan, dimension):
    if dimension=='harmony': return [(b['root'],tuple(b['quality'])) for b in plan['bars']]
    if dimension=='structure': return [b['phrase'] for b in plan['bars']]
    if dimension=='rhythm':
        return [tuple(str(Fraction(e['duration_q'])) for e in b['parts'][role])
                for b in plan['bars'] for role in sorted(plan['roles'])]
    return [tuple(tuple((n['degree'],n['octave'],n.get('alter',0)) for n in e['notes']) for e in b['parts'][role])
            for b in plan['bars'] for role in sorted(plan['roles'])]


def distance(a,b,dimension):
    left,right=units(a,dimension),units(b,dimension)
    if len(left)!=len(right): return 100.0
    return 100*sum(x!=y for x,y in zip(left,right))/max(1,len(left))


def position_chord(pitches,tuning,max_span=5,previous=()):
    """Joint fingering: unique strings, bounded fretted span, least movement."""
    choices=[[(s,p-open_pitch) for s,open_pitch in enumerate(tuning) if 0<=p-open_pitch<=24] for p in pitches]
    best=None
    for combination in itertools.product(*choices):
        if len({s for s,f in combination})!=len(combination): continue
        frets=[f for s,f in combination if f>0]
        if frets and max(frets)-min(frets)>max_span: continue
        motion=sum(abs(f-previous[i][1]) if i<len(previous) else f for i,(s,f) in enumerate(combination))
        key=(motion,sum(f for s,f in combination),combination)
        if best is None or key<best[0]: best=(key,combination)
    if best is None: raise ValueError('No playable simultaneous fingering for '+str(pitches))
    return best[1]


def realize(plan):
    score=dict(format='generated-relational-plan-v1',source_file='authored-plan',tracks=[])
    for ti,(role,info) in enumerate(plan['roles'].items()):
        track=dict(index=ti,name=role,tunings=[info['tuning']],program=info.get('program',25),measures=[])
        start=Fraction(0); previous=()
        for mi,bar in enumerate(plan['bars']):
            events=[]; offset=Fraction(0)
            for event in bar['parts'][role]:
                pitches=[12*n['octave']+bar['root']+bar['quality'][n['degree']]+n.get('alter',0) for n in event['notes']]
                fingering=position_chord(pitches,info['tuning'],previous=previous)
                notes=[dict(midi=p,string=s,fret=f,tie=None,technique_tags=[]) for p,(s,f) in zip(pitches,fingering)]
                duration=Fraction(event['duration_q'])
                if duration<=0: raise ValueError('Non-positive duration')
                events.append(dict(onset_q=str(start+offset),local_onset_q=str(offset),duration_q=str(duration),notes=notes))
                offset+=duration
                if fingering: previous=fingering
            num,den=map(int,bar['meter'].split('/'))
            if offset!=Fraction(4*num,den): raise ValueError('Role events do not fill meter')
            track['measures'].append(dict(number=mi+1,onset_q=str(start),time_signature=bar['meter'],
                                         section=bar['phrase'],voices=[events]))
            start+=offset
        score['tracks'].append(track)
    return score


def generate(plan, targets, seed=17, candidates=128):
    if set(targets)-set(DIMENSIONS): raise ValueError('Unknown dimension')
    targets={d:targets.get(d,0) for d in DIMENSIONS}
    if any(not 0<=v<=100 for v in targets.values()): raise ValueError('Targets must be 0..100')
    rng=random.Random(seed); feasible=[]
    for ci in range(candidates):
        candidate=deepcopy(plan)
        for bi,bar in enumerate(candidate['bars']):
            if targets['harmony'] and ci:
                # Whole-bar harmony changes keep chord-relative function exact.
                options=plan.get('harmony_options',[])
                if options and rng.randrange(2):
                    bar['root'],bar['quality']=deepcopy(rng.choice(options))
            for role,events in bar['parts'].items():
                if targets['rhythm'] and ci and len(events)>1 and rng.randrange(2):
                    durations=[e['duration_q'] for e in events]
                    shift=rng.randrange(len(events)); durations=durations[shift:]+durations[:shift]
                    for e,d in zip(events,durations): e['duration_q']=d
                if targets['melody'] and ci and candidate['roles'][role]['function']=='melody':
                    # Same transformation per named phrase creates recurring variants.
                    variant=(ci+sum(map(ord,bar['phrase'])))%3
                    for event in events:
                        for n in event['notes']:
                            n['degree']=(n['degree']+variant)%len(bar['quality'])
        if targets['structure'] and ci:
            # Move actual phrase blocks, including their musical content.
            blocks=[]
            for bar in candidate['bars']:
                if not blocks or blocks[-1][0]['phrase']!=bar['phrase']: blocks.append([])
                blocks[-1].append(bar)
            if len(blocks)>1:
                shift=ci%len(blocks)
                candidate['bars']=[bar for block in blocks[shift:]+blocks[:shift] for bar in block]
        try: score=realize(candidate)
        except ValueError: continue
        measured={d:distance(plan,candidate,d) for d in DIMENSIONS}
        if any(targets[d]==0 and measured[d]!=0 for d in DIMENSIONS): continue
        error=sum(abs(measured[d]-targets[d]) for d in DIMENSIONS)
        # Prefer smaller melodic jumps among equally close target matches.
        motion=0
        for track in score['tracks']:
            pitches=[e['notes'][0]['midi'] for m in track['measures'] for e in m['voices'][0] if e['notes']]
            motion+=sum(abs(a-b) for a,b in zip(pitches,pitches[1:]))
        feasible.append((error,motion,ci,candidate,score,measured))
    if not feasible: raise ValueError('No playable candidate satisfies the locked dimensions')
    _,_,_,chosen,score,measured=min(feasible,key=lambda c:c[:3])
    report=dict(targets=targets,measured=measured,seed=seed,candidates_evaluated=candidates,
                feasible_candidates=len(feasible),
                observed_ranges={d:[min(x[5][d] for x in feasible),max(x[5][d] for x in feasible)] for d in DIMENSIONS},
                target_reached=all(abs(targets[d]-measured[d])<1e-9 for d in DIMENSIONS),
                structure_metric='share of bars moved to a different named phrase block; not calibrated perceptual distance',
                melody_lock='explicit chord degree, octave, chromatic alteration; not literal MIDI',
                musical_quality_evaluated=False)
    return chosen,score,report


def demo_plan():
    """New authored engineering fixture, explicitly unrelated to Cloud V2."""
    roles=dict(lead=dict(function='melody',tuning=[40,45,50,55,59,64],program=25),
               harmony=dict(function='harmony',tuning=[40,45,50,55,59,64],program=24),
               bass=dict(function='bass',tuning=[28,33,38,43],program=33))
    bars=[]
    for i,root in enumerate([0,5,7,0,0,5,7,0]):
        melody=[dict(duration_q=d,notes=[dict(degree=g,octave=5)]) for d,g in zip(['1/2','1/2','1','2'],[0,1,2,(i%3)])]
        harmony=[dict(duration_q='4',notes=[dict(degree=g,octave=4) for g in range(3)])]
        bass=[dict(duration_q='2',notes=[dict(degree=g,octave=3)]) for g in [0,2]]
        bars.append(dict(root=root,quality=[0,4,7],meter='4/4',phrase='A' if i<4 else 'A2',parts=dict(lead=melody,harmony=harmony,bass=bass)))
    return dict(provenance='authored engineering fixture, not learned from commercial scores',roles=roles,bars=bars,
                harmony_options=[[0,[0,4,7]],[5,[0,4,7]],[7,[0,4,7]],[9,[0,3,7]]])


def copying_audit(reference, generated):
    def bars(score):
        return [tuple((e['local_onset_q'],e['duration_q'],tuple(n['midi'] for n in e['notes'])) for e in m['voices'][0])
                for t in score['tracks'] for m in t['measures']]
    originals=set(bars(reference)); output=bars(generated)
    return dict(exact_bar_copy_share=sum(b in originals for b in output)/max(1,len(output)),
                scope='exact absolute-pitch/rhythm bars against supplied reference; not proof of originality')


def main():
    p=argparse.ArgumentParser(); p.add_argument('--plan',type=Path); p.add_argument('--demo',action='store_true')
    p.add_argument('--out',type=Path,required=True); p.add_argument('--seed',type=int,default=17)
    args=p.parse_args()
    if bool(args.plan)==args.demo: p.error('Choose --plan or --demo')
    plan=demo_plan() if args.demo else json.loads(args.plan.read_text(encoding='utf-8'))
    args.out.mkdir(parents=True,exist_ok=True)
    reference=realize(plan); baseline=args.out/'engineering-reference.gp'
    if baseline.exists(): raise FileExistsError('Preserve previous artifacts: choose a fresh output directory')
    write_gp(reference,baseline)
    (args.out/'engineering-reference.expected.json').write_text(json.dumps(reference),encoding='utf-8')
    reports={}
    for name,targets in [('harmony',dict(harmony=75)),('rhythm',dict(harmony=75,rhythm=25)),
                         ('melody',dict(harmony=75,rhythm=25,melody=25)),
                         ('phrase-order',dict(harmony=75,rhythm=25,melody=25,structure=100))]:
        chosen,score,report=generate(plan,targets,args.seed)
        gp=args.out/(name+'.gp'); restored=write_gp(score,gp,title=name)
        (args.out/(name+'.expected.json')).write_text(json.dumps(restored),encoding='utf-8')
        report['gp_sha256']=hashlib.sha256(gp.read_bytes()).hexdigest()
        report['conversion']=export_musicxml(restored,args.out/(name+'.musicxml'))
        report['copying']=copying_audit(reference,score)
        report['relative_copying']=copying_ngrams(reference,score)
        report['track_metrics']=track_metrics(score)
        (args.out/(name+'.graph.json')).write_text(json.dumps(build_graph(restored)),encoding='utf-8')
        (args.out/(name+'.plan.json')).write_text(json.dumps(chosen),encoding='utf-8')
        reports[name]=report
    (args.out/'manifest.json').write_text(json.dumps(dict(provenance=plan['provenance'],reports=reports,
        baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),
        limitations=['Not a source-trained composition model','Roles are present in all stages; final stage reorders whole phrase blocks',
                     'Cloud V2 comparison unavailable','No listening judgments collected']),indent=2),encoding='utf-8')
    print(json.dumps({k:v['measured'] for k,v in reports.items()},indent=2))


if __name__=='__main__': main()
