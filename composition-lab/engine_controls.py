"""Measured discrete controls on generated scores; locks are invariants.

This layer is coupled to generated neural pitches, not calibrated perceptual
similarity. Structure movement conflicts with framewise dimension locks and is
rejected explicitly. Musical role-reassignment control remains unsupported.
"""
from copy import deepcopy
from fractions import Fraction as F
import math,random
from source_ablations import fit_pitches


def units(score,dimension):
    if dimension=='structure':return [m['number'] for m in score['tracks'][0]['measures']]
    if dimension=='rhythm':return [tuple((e['local_onset_q'],e['duration_q'],bool(e['notes'])) for v in m['voices'] for e in v) for t in score['tracks'] for m in t['measures']]
    ti=0 if dimension=='harmony' else 1
    return [tuple(n['midi'] for n in e['notes']) for m in score['tracks'][ti]['measures'] for v in m['voices'] for e in v if e['notes']]


def distance(a,b,dimension):
    x,y=units(a,dimension),units(b,dimension)
    if len(x)!=len(y):return 100.0
    return 100*sum(p!=q for p,q in zip(x,y))/max(1,len(x))


def vary(base,targets,pool,seed=17):
    for dimension,value in targets.items():
        if dimension not in ('harmony','melody','rhythm','structure'):raise ValueError('Unsupported independent role control')
        if not 0<=value<=100:raise ValueError('Target outside 0-100')
    if targets.get('structure',0)>0:raise ValueError('Structure movement incompatible with independent framewise locks; use explicit form regeneration experiment')
    out=deepcopy(base);rng=random.Random(seed);pitches=sorted({n['pitch'] for p in pool for n in p['notes']})
    for dimension,ti in [('harmony',0),('melody',1)]:
        events=[e for m in out['tracks'][ti]['measures'] for v in m['voices'] for e in v if e['notes']]
        count=round(len(events)*targets.get(dimension,0)/100);order=list(range(len(events)));rng.shuffle(order)
        tuning=out['tracks'][ti]['tunings'][0]
        for index in order[:count]:
            e=events[index];original=[n['midi'] for n in e['notes']];candidate=None
            # Melody candidates are actual sampled neural pitches; harmony uses
            # chromatic transpositions of its learned voicing, reported as such.
            options=[p-original[0] for p in pitches if p!=original[0]] if ti==1 else list(range(-5,0))+list(range(1,6))
            rng.shuffle(options)
            for shift in options:
                try:
                    fitted=fit_pitches([p+shift for p in original],tuning)
                    if [p for p,s,f in fitted]!=original:candidate=fitted;break
                except ValueError:pass
            if candidate:
                for n,(p,s,f) in zip(e['notes'],candidate):n.update(midi=p,string=s,fret=f)
    measures=[(t,m) for t in out['tracks'] for m in t['measures']]
    order=list(range(len(measures)));rng.shuffle(order)
    for index in order[:round(len(measures)*targets.get('rhythm',0)/100)]:
        t,m=measures[index]
        for voice in m['voices']:
            durations=[e['duration_q'] for e in voice]
            if len(set(durations))<2:
                candidates=[]
                for phrase in pool:
                    for bar in (0,1):
                        pattern=[];cursor=F(0)
                        for n in [n for n in phrase['notes'] if n['bar']==bar]:
                            pos,d=F(n['position']),F(n['duration'])
                            if pos>cursor:pattern.append(str(pos-cursor))
                            pattern.append(str(d));cursor=pos+d
                        if cursor<4:pattern.append(str(4-cursor))
                        if len(pattern)==len(voice) and len(set(pattern))>1:candidates.append(pattern)
                if not candidates:continue
                shifted=rng.choice(candidates)
            else:shifted=durations[1:]+durations[:1]
            local=F(0)
            for e,d in zip(voice,shifted):e.update(duration_q=d,local_onset_q=str(local),onset_q=str(F(m['onset_q'])+local));local+=F(d)
    actual={d:distance(base,out,d) for d in ('harmony','melody','rhythm','structure')}
    for d in actual:
        if targets.get(d,0)==0 and actual[d]!=0:raise AssertionError('Exact lock violated: '+d)
    return out,dict(requested=targets,actual=actual,attained={d:abs(actual[d]-targets.get(d,0))<=5 for d in actual},
        limitations=['discrete engineering distances, not perceptual similarity','harmony variation currently transposes learned voicings','rhythm needs a nonuniform sampled profile with matching event count','structure/role independent controls incomplete'])
