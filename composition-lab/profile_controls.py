"""Independent pitch proposals from a fitted empirical corpus vocabulary.

Only locked timing, note-slot counts and instrumentation reach the proposer.
Reference pitches/frets/strings are removed before proposal. This permits direct
perturbation tests, with unchanged and coincident proposals allowed at100.
"""
from copy import deepcopy
from fractions import Fraction as F
import random
from controlled_generation import position_chord
from corpus_composer import choose_family
from generation_freedom import validate


def locked_context(score):
    validate(score);out={k:deepcopy(score[k]) for k in ('tracks','tempo_bpm') if k in score}
    for t in out['tracks']:
        for key in list(t):
            if key not in ('index','name','program','tunings','measures'):del t[key]
        for m in t['measures']:
            for voice in m['voices']:
                for e in voice:e['notes']=[{} for n in e['notes']]
    return out


def propose(model,context,roles,seed=17):
    rng=random.Random(seed);out=deepcopy(context)
    if len(roles)!=len(out['tracks']) or any(r not in ('harmony','melody','bass') for r in roles):raise ValueError('Explicit supported role per track required')
    cache={}
    for ti,t in enumerate(out['tracks']):
        role=roles[ti];tuning=t['tunings'][0];previous=();root=None
        for m in t['measures']:
            meter=m['time_signature'];pool={f:[p for p in ps if p['meter']==meter] for f,ps in model['parts'][role].items() if any(p['meter']==meter for p in ps)}
            if not pool:raise ValueError('No training meter support')
            for voice in m['voices']:
                for e in voice:
                    size=len(e['notes'])
                    if not size:continue
                    key=(role,meter,size)
                    if key not in cache:
                        cache[key]={f:[p for p in ps if any(len(x['intervals'])==size for x in p['events'])] for f,ps in pool.items()}
                        cache[key]={f:ps for f,ps in cache[key].items() if ps}
                    candidates=cache[key]
                    if not candidates:raise ValueError('No observed voicing cardinality compatible with locked event slots')
                    fitted=None
                    for attempt in range(50):
                        pattern=choose_family(rng,candidates)
                        intervals=rng.choice([x['intervals'] for x in pattern['events'] if len(x['intervals'])==size])
                        initial=rng.choice(pattern.get('root_events') or [dict(root=round(pattern['root_center']))])['root']
                        steps=pattern['root_steps'] or {'0':1}
                        target=initial if root is None else root+int(rng.choices(list(steps),weights=list(steps.values()),k=1)[0])
                        for shift in sorted(range(-5,6),key=lambda n:(abs(n),n)):
                            pitches=[target+x+12*shift for x in intervals]
                            if any(not 0<=p<=127 for p in pitches):continue
                            try:
                                positions=position_chord(pitches,tuning,max_span=4,previous=previous)
                                fitted=[dict(midi=p,string=s,fret=f,tie=None,technique_tags=[]) for p,(s,f) in zip(pitches,positions)];break
                            except ValueError:pass
                        if fitted is not None:break
                    if fitted is None:raise ValueError('No bounded fingering for independent proposal')
                    e['notes']=fitted;root=min(n['midi'] for n in fitted);previous=[(n['string'],n['fret']) for n in fitted]
    validate(out)
    return out
