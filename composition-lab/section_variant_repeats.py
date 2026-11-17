"""Experimental duration-invariant ordered note evidence. Not a role classifier."""
from collections import defaultdict
from difflib import SequenceMatcher
from fractions import Fraction
import section_repeats as B

def sequence(f,c):
    times=defaultdict(set)
    for key in f['pitch'].get(c,{}):
        onset,duration,pitch=key.split('|');times[Fraction(onset)].add(float(pitch))
    out=[]
    for t in sorted(times):
        group=tuple(sorted(times[t]))
        if not out or out[-1]!=group:out.append(group)
    return out

def similarity(a,b):
    return SequenceMatcher(None,a,b,autojunk=False).ratio() if a and b else None

def compare(a,b,weights=None):
    original=B.compare_bars(a,b,weights)
    p={};c={}
    for part in sorted(set(a['pitch'])&set(b['pitch'])):
        x=sequence(a,part);y=sequence(b,part)
        if not x or not y:continue
        p[part]=similarity(x,y)
        lo=min(n for g in x for n in g);ly=min(n for g in y for n in g)
        c[part]=similarity([tuple(n-lo for n in g) for g in x],[tuple(n-ly for n in g) for g in y])
    if not p:return original
    # A separate view: explicit attack order but invariant to articulation length.
    ps=sum(p.values())/len(p);cs=sum(c.values())/len(c)
    components={'pitch':ps,'contour':cs,'harmony':original['features']['harmony'],'arrangement':original['features']['arrangement']}
    w={'pitch':.5,'contour':.25,'harmony':.15,'arrangement':.10};den=sum(w[k] for k,v in components.items() if v is not None)
    score=sum(w[k]*v for k,v in components.items() if v is not None)/den*original['meter_similarity']
    if not a['observed'] or not b['observed']:score=None
    result=dict(original);result['score']=score
    result['features']={**components,'rhythm':None};result['channels']={**original['channels'],'pitch':p,'contour':c};result['exact_observed_match']=False
    return result

def analyze(features):
    result=B.analyze_repeats(features,comparison=compare)
    result['experimental_view']='duration_invariant_ordered_pitch_and_contour; condensed consecutive same groups'
    result['limitations'].append('May merge repetitions with different rhythms; separate candidate view, never exact repeats or automatic functional labels.')
    return result
