"""Pitch-only factorial phrase experiment on frozen generated baselines.

No external model predictions or source-score labels are used. Unequal phrase
spans are authored test scaffolding, not inferred musical truth. Timing and
accompaniment stay exact; listening must determine whether either factor helps.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from source_ablations import fit_pitches
from gp_author import write_gp
from generation_validation import copying_ngrams

SPANS=(3,5,3,5)


def attacks(measures):
    return [e for m in measures for v in m['voices'] for e in v if e['notes']]


def harmony_pcs(score,bar):
    return sorted({n['midi']%12 for v in score['tracks'][0]['measures'][bar]['voices'] for e in v for n in e['notes']})


def nearest(pitch,pcs,low,high):
    candidates=[p for p in range(low,high+1) if p%12 in pcs]
    return min(candidates,key=lambda p:(abs(p-pitch),p)) if candidates else pitch


def develop(baseline,linked=False,endings=False):
    score=deepcopy(baseline)
    melody=score['tracks'][1]
    if len(melody['measures'])!=sum(SPANS):raise ValueError('Expected frozen 16-bar baseline')
    tuning=melody['tunings'][0];low=min(tuning);high=max(tuning)+24
    seed=attacks(baseline['tracks'][1]['measures'][:2])
    motif=[e['notes'][0]['midi']-seed[0]['notes'][0]['midi'] for e in seed]
    if not motif:raise ValueError('No melodic seed')
    previous=();last=None;start=0;boundaries=[]
    for phrase,length in enumerate(SPANS):
        events=attacks(melody['measures'][start:start+length]);end=events[-1] if events else None
        origin=events[0]['notes'][0]['midi'] if events else low
        anchor=nearest(last if last is not None else origin,harmony_pcs(score,start),low,high)
        for i,e in enumerate(events):
            original=[n['midi'] for n in e['notes']];pitch=original[0]
            if linked:
                # Shared contour; answer contracts it, development reverses it,
                # return restores it. This is explicit authored transformation.
                contour=motif[::-1] if phrase==2 else motif
                offset=contour[i%len(contour)]
                if phrase==1:offset=round(offset/2)
                pitch=anchor+offset
                pitch=min(max(pitch,low),high)
                if last is not None:
                    octaves=[pitch+12*k for k in range(-5,6) if low<=pitch+12*k<=high]
                    pitch=min(octaves,key=lambda p:(abs(p-last),abs(p-origin)))
            if endings and e is end:
                pitch=nearest(last if last is not None else pitch,harmony_pcs(score,start+length-1),low,high)
            if linked or (endings and e is end):
                positions=fit_pitches([pitch+p-original[0] for p in original],tuning,previous)
                for n,(p,s,f) in zip(e['notes'],positions):n.update(midi=p,string=s,fret=f)
                previous=[(s,f) for p,s,f in positions]
            last=e['notes'][0]['midi']
        boundaries.append(start+length);start+=length
    return score,dict(linked=linked,endings=endings,phrase_end_bars=boundaries)


def audit(baseline,score):
    assert baseline['tracks'][0]==score['tracks'][0] and baseline['tracks'][2:]==score['tracks'][2:]
    a,b=baseline['tracks'][1],score['tracks'][1]
    assert a['tunings']==b['tunings'] and a['program']==b['program']
    changed=0;total=0
    for ma,mb in zip(a['measures'],b['measures']):
        assert {k:v for k,v in ma.items() if k!='voices'}=={k:v for k,v in mb.items() if k!='voices'}
        assert len(ma['voices'])==len(mb['voices'])
        for va,vb in zip(ma['voices'],mb['voices']):
            assert len(va)==len(vb)
            for ea,eb in zip(va,vb):
                assert {k:v for k,v in ea.items() if k!='notes'}=={k:v for k,v in eb.items() if k!='notes'}
                assert len(ea['notes'])==len(eb['notes'])
                for na,nb in zip(ea['notes'],eb['notes']):
                    total+=1;changed+=na['midi']!=nb['midi']
                    assert nb['midi']==b['tunings'][0][nb['string']]+nb['fret']
    events=attacks(b['measures']);pitches=[e['notes'][0]['midi'] for e in events]
    ends=[];start=0
    for length in SPANS:
        phrase=attacks(b['measures'][start:start+length])
        if phrase:ends.append(phrase[-1]['notes'][0]['midi']%12 in harmony_pcs(score,start+length-1))
        start+=length
    return dict(changed_melody_notes=changed,melody_notes=total,
                mean_attack_leap=sum(abs(x-y) for x,y in zip(pitches,pitches[1:]))/max(1,len(pitches)-1),
                phrase_ends_in_accompaniment_pcs=sum(ends),phrase_ends=len(ends),
                accompaniment_exact=True,timing_and_note_counts_exact=True)


def main():
    import argparse
    from exact_score import extract_score
    parser=argparse.ArgumentParser()
    parser.add_argument('--reference',type=Path,action='append',default=[],help='Optional private source for exact-window copying audit; never copied to public output')
    args=parser.parse_args()
    references={p.stem:extract_score(p) for p in args.reference}
    root=Path(__file__).resolve().parent
    for family in ('cloud','sweet'):
        base=root/f'local-artifacts/{family}-native-ablations'
        baseline=json.loads((base/'roles-phrases.expected.json').read_text())
        out=root/f'local-artifacts/{family}-phrase-experiments'
        out.mkdir(exist_ok=False)
        report=dict(baseline_sha256=hashlib.sha256((base/'roles-phrases.gp').read_bytes()).hexdigest(),
                    factors=['linked contour','phrase-end accompaniment pitch-class targeting'],
                    limitations=['authored 3/5/3/5 spans; not learned phrase boundaries','pitch-only: no rhythmic breathing or harmonic progression improvement','end targeting is not proof of tonal resolution','one seed, two generated baselines; listening pending'],cases={})
        for name,linked,endings in [('baseline',False,False),('linked',True,False),('endings',False,True),('combined',True,True)]:
            score,plan=develop(baseline,linked,endings)
            metrics=audit(baseline,score)
            if name=='baseline':
                import shutil
                shutil.copy2(base/'roles-phrases.gp',out/(name+'.gp'))
            else:write_gp(score,out/(name+'.gp'),title=name)
            (out/(name+'.expected.json')).write_text(json.dumps(score),encoding='utf-8')
            report['cases'][name]=dict(plan=plan,metrics=metrics,baseline_copying=copying_ngrams(baseline,score),
                source_copying={key:copying_ngrams(source,score) for key,source in references.items()})
        (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(family,json.dumps({k:v['metrics'] for k,v in report['cases'].items()}))


if __name__=='__main__':main()
