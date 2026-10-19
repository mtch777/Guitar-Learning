"""Fixed-skeleton harmony intervention; experimental, not a live default.

Reference harmony pitch/fingering is removed before proposal construction.
Source-selected voicings and common uniforms are explicit experimental inputs.
Copied material is constrained recurrence, not a fresh conditional prediction.
"""
from bisect import bisect_right
from copy import deepcopy
from fractions import Fraction as F
from itertools import accumulate
import math
from conditional_harmony_steps import distribution, STEPS
from controlled_generation import position_chord


class PilotFitError(ValueError):
    def __init__(self, failure, decisions):
        self.failure=deepcopy(failure);self.decisions=deepcopy(decisions)
        super().__init__(f'No fit at bar {failure["bar"]}, {failure["local_q"]}; no reroll')


def draw(order, weights, uniform):
    if len(order)!=len(weights) or not order or len(set(order))!=len(order):
        raise ValueError('Unique categories and matching weights required')
    if not 0<=uniform<1 or any(not math.isfinite(w) or w<0 for w in weights):
        raise ValueError('Finite nonnegative weights and unit uniform required')
    cumulative=list(accumulate(weights))
    if cumulative[-1]<=0:raise ValueError('Positive mass required')
    return order[bisect_right(cumulative,uniform*cumulative[-1],0,len(order)-1)]


def redact(score):
    out=deepcopy(score)
    for bar in out['tracks'][0]['measures']:
        for voice in bar['voices']:
            for event in voice:
                for note in event['notes']:
                    for key in ('midi','string','fret'):note.pop(key)
    return out


def propose(skeleton, recurrence, records, initial_root, model, *, historical_null=False, mechanical_mask=False):
    """Accept only a redacted skeleton; abort on any unplayable sampled attack."""
    if historical_null and mechanical_mask:raise ValueError('Historical null must retain its original distribution')
    score=deepcopy(skeleton);track=score['tracks'][0];tuning=track['tunings'][0]
    if len(recurrence)!=len(track['measures']):raise ValueError('Recurrence coverage mismatch')
    if any(set(n)&{'midi','string','fret'} for b in track['measures'] for v in b['voices'] for e in v for n in e['notes']):
        raise ValueError('Reference target values must be removed')
    lookup={(r['bar']-1,F(r['local_q'])):r for r in records}
    if len(lookup)!=len(records):raise ValueError('Duplicate recorded decisions')
    root=round(initial_root);previous=();last_id=None;last_end=None;cache={};audit=[]
    for bi,bar in enumerate(track['measures']):
        if len(bar['voices'])!=1:raise ValueError('Main voice only')
        key=tuple(recurrence[bi]);start=F(bar['onset_q'])
        if key in cache:
            origin,local=cache[key];bar['voices'][0]=deepcopy(local)
            for e in bar['voices'][0]:
                e['onset_q']=str(start+F(e['local_onset_q']))
                if e['notes']:
                    root=min(n['midi'] for n in e['notes']);previous=tuple((n['string'],n['fret']) for n in e['notes'])
                    last_id=(origin,str(F(e['local_onset_q'])));last_end=F(e['onset_q'])+F(e['duration_q'])
            continue
        for e in bar['voices'][0]:
            if not e['notes']:continue
            q=F(e['onset_q']);r=lookup[bi,F(e['local_onset_q'])];shape=r['voicing_intervals']
            if len(shape)!=len(e['notes']) or min(shape)!=0:raise ValueError('Source voicing/cardinality mismatch')
            origin=root-min(tuning);span=max(shape)-min(shape)
            contiguous=last_end is not None and last_end==q
            probabilities,support=distribution(model,origin,span,conditional=contiguous)
            reason='initial' if last_id is None else 'gap' if not contiguous else 'missing_key' if support is None else None
            order=r['step_order']+[s for s in STEPS if s not in r['step_order']]
            removed_mass=0.0
            if mechanical_mask:
                from harmony_feasibility import mask,condition
                probabilities,retained=condition(probabilities,mask(root,shape,tuning,previous))
                removed_mass=1-retained
            weights=r['step_weights'] if historical_null else [probabilities[s+127] for s in order]
            step=draw(r['step_order'] if historical_null else order,weights,r['uniform'])
            target=root+step;positions=None
            for shift in sorted(range(-5,6),key=lambda x:(abs(x),x)):
                pitches=[target+d+12*shift for d in shape]
                try:positions=position_chord(pitches,tuning,max_span=4,previous=previous)
                except ValueError:continue
                break
            if positions is None:
                raise PilotFitError(dict(bar=bi+1,local_q=e['local_onset_q'],previous_root=root,
                    previous_id=last_id,origin_register=origin,voicing_span=span,voicing_intervals=shape,
                    sampled_step=step,target_before_fit=target,backoff_reason=reason,uniform=r['uniform'],
                    shifts_attempted=sorted(range(-5,6),key=lambda x:(abs(x),x))),audit)
            identity=(bi,str(F(e['local_onset_q'])))
            audit.append(dict(identity=identity,previous_id=last_id,previous_root=root,previous_fingering=previous,
                contiguous=contiguous,origin_register=origin,voicing_span=span,sampled_step=step,target_before_fit=target,
                octave_shift=shift,actual_root=min(pitches),backoff_reason=reason,mechanical_mask=mechanical_mask,removed_mass=removed_mass,
                raw_families=len(support['families']) if support else 0,
                raw_songs=len(support['songs']) if support else 0,weighted_mass=support['mass'] if support else 0))
            for note,pitch,(string,fret) in zip(e['notes'],pitches,positions):note.update(midi=pitch,string=string,fret=fret)
            root=min(pitches);previous=tuple(positions);last_id=identity;last_end=q+F(e['duration_q'])
        cache[key]=(bi,deepcopy(bar['voices'][0]))
    if len(audit)!=len(records):raise ValueError('Unconsumed or extra decisions')
    return score,audit
