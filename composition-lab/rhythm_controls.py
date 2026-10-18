"""Empirical rhythm freedom with literal pitch/voicing/form locks.

Locked event slots constrain the rhythm vocabulary. The proposer receives meter,
role and event cardinalities, never the reference onsets or durations. This does
not independently change event density/rest topology or tempo.
"""
from copy import deepcopy
from collections import defaultdict
from fractions import Fraction as F
import random
from corpus_composer import choose_family
from generation_freedom import validate,facets
from technique_strength import released


def locked_context(score,roles):
    if len(roles)!=len(score['tracks']) or set(roles)-{'harmony','melody','bass'}:raise ValueError('Explicit supported role per track required')
    return [dict(role=roles[ti],bars=[dict(meter=m['time_signature'],voices=[[len(e['notes']) for e in v] for v in m['voices']])
        for m in t['measures']]) for ti,t in enumerate(score['tracks'])]


def propose(model,context,seed=17):
    rng=random.Random(seed);out=[];cache={}
    for track in context:
        if track['role'] not in model['parts']:raise ValueError('No trained role')
        bars=[]
        for bar in track['bars']:
            voices=[]
            for shape in bar['voices']:
                if not shape:voices.append([]);continue
                key=(track['role'],bar['meter'],tuple(shape))
                if key not in cache:
                    fs={}
                    for family,records in model['parts'][track['role']].items():
                        pool=[p for p in records if p['meter']==bar['meter'] and [len(e['intervals']) for e in p['events']]==shape]
                        if pool:fs[family]=pool
                    cache[key]=fs
                if not cache[key]:raise ValueError('No source rhythm compatible with locked event topology')
                pattern=choose_family(rng,cache[key]);voices.append([e['duration_q'] for e in pattern['events']])
            bars.append(voices)
        out.append(bars)
    return out


def apply(reference,model,roles,freedom,seed=17):
    if isinstance(freedom,bool) or not isinstance(freedom,int) or not 0<=freedom<=100:raise ValueError('Integer freedom0–100 required')
    validate(reference);context=locked_context(reference,roles)
    if freedom==0:return deepcopy(reference),dict(all_locked=True,freedom=0)
    proposal=propose(model,context,seed);out=deepcopy(reference);decisions=[]
    for ti,t in enumerate(out['tracks']):
        for mi,m in enumerate(t['measures']):
            for vi,v in enumerate(m['voices']):
                if not v:continue
                unlocked=released(('rhythm',f'{ti}:{mi}:{vi}'),freedom);cursor=F(0)
                for ei,e in enumerate(v):
                    if unlocked:e['duration_q']=str(F(proposal[ti][mi][vi][ei]))
                    e['local_onset_q']=str(cursor);e['onset_q']=str(F(m['onset_q'])+cursor);cursor+=F(e['duration_q'])
                decisions.append(dict(track=ti,bar=mi+1,voice=vi,released=unlocked,
                    changed=v!=reference['tracks'][ti]['measures'][mi]['voices'][vi]))
    validate(out);before=facets(reference,roles);after=facets(out,roles)
    for dimension in before:
        if dimension!='rhythm' and before[dimension]!=after[dimension]:raise AssertionError('Non-rhythm lock violated: '+dimension)
    return out,dict(freedom=freedom,seed=seed,units=decisions,forced_difference=False,
        limitations=['Event/rest/voicing topology, meter and tempo locked; incompatible training support fails closed.',
            'Event-indexed pitches stay fixed; changed timing can change intertrack simultaneous harmony.',
            'Release fraction, not required difference or perceptual strength.'])
