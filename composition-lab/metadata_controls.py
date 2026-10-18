"""Source-fitted global tempo and MIDI-program controls for new scores.

Pitch/timing in quarter notes, tuning, fingering, track layout and all expression
stay locked. MIDI program is a preview instrument choice, not an RSE tone model.
"""
from copy import deepcopy
from fractions import Fraction as F
import random
from corpus_composer import choose_family
from generation_freedom import validate
from technique_strength import released


def proposals(model,roles,seed=17):
    if set(roles)-{'harmony','melody','bass'}:raise ValueError('Explicit supported roles required')
    programs=[]
    for ti,role in enumerate(roles):
        rng=random.Random(f'{seed}:program:{ti}')
        if not model['parts'].get(role):raise ValueError('No source role/program support')
        program=choose_family(rng,model['parts'][role])['program']
        if isinstance(program,bool) or not isinstance(program,int) or not 0<=program<=127:raise ValueError('Invalid source program')
        programs.append(program)
    tempo=F(choose_family(random.Random(f'{seed}:tempo'),model['parts']['harmony'])['tempo_bpm'])
    if not 0<tempo<=600:raise ValueError('Unsupported source tempo')
    return dict(programs=programs,tempo=str(tempo))


def apply(reference,roles,model,freedom,seed=17):
    if set(freedom)-{'programs','tempo'}:raise ValueError('Unknown metadata control')
    amounts={d:freedom.get(d,0) for d in ('programs','tempo')}
    for value in amounts.values():
        if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=100:raise ValueError('Integer freedom0–100 required')
    validate(reference)
    if len(roles)!=len(reference['tracks']) or set(roles)-{'harmony','melody','bass'}:raise ValueError('Explicit role per track required')
    if not any(amounts.values()):return deepcopy(reference),dict(all_locked=True,freedom=amounts)
    proposal=proposals(model,roles,seed);out=deepcopy(reference);decisions=[]
    for ti,t in enumerate(out['tracks']):
        unlocked=released(('programs',ti),amounts['programs'])
        if unlocked:t['program']=proposal['programs'][ti]
        decisions.append(dict(dimension='programs',track=ti,released=unlocked,changed=t.get('program')!=reference['tracks'][ti].get('program')))
    unlocked=released(('tempo',),amounts['tempo'])
    if unlocked:out['tempo_bpm']=proposal['tempo']
    decisions.append(dict(dimension='tempo',released=unlocked,changed=F(out.get('tempo_bpm',120))!=F(reference.get('tempo_bpm',120))))
    # Strip only permitted metadata; all remaining canonical data must be exact.
    def locked(score):
        s=deepcopy(score)
        if amounts['tempo']:s.pop('tempo_bpm',None)
        if amounts['programs']:
            for t in s['tracks']:t.pop('program',None)
        return s
    if locked(out)!=locked(reference):raise AssertionError('Non-metadata lock violated')
    validate(out)
    return out,dict(freedom=amounts,seed=seed,decisions=decisions,forced_difference=False,
        limitations=['Initial global tempo only; no inferred expressive timing or tempo map.',
            'MIDI programs only; tuning, fingering and track/role arrangement stay locked.',
            'Tempo changes real-time duration while preserving exact quarter-note timing.'])
