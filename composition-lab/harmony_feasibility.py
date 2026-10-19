"""Mechanical action support only; no style claims or generator defaults."""
import math
from conditional_harmony_steps import STEPS
from conditional_harmony_pilot import draw
from controlled_generation import position_chord

SHIFTS=tuple(sorted(range(-5,6),key=lambda x:(abs(x),x)))


def realization(root,step,shape,tuning,previous=()):
    for shift in SHIFTS:
        pitches=[root+step+d+12*shift for d in shape]
        try:positions=position_chord(pitches,tuning,max_span=4,previous=previous)
        except ValueError:continue
        return dict(pitches=pitches,positions=positions,shift=shift)
    return None


def mask(root,shape,tuning,previous=()):
    if not shape or min(shape)!=0:raise ValueError('Source root-normalized voicing required')
    return [realization(root,s,shape,tuning,previous) is not None for s in STEPS]


def condition(probabilities,allowed):
    if len(probabilities)!=len(STEPS) or len(allowed)!=len(STEPS):raise ValueError('Complete fixed vocabulary required')
    if any(type(v)is not bool for v in allowed):raise ValueError('Boolean feasibility mask required')
    if any(not math.isfinite(p) or p<0 for p in probabilities):raise ValueError('Finite nonnegative mass required')
    if not math.isclose(sum(probabilities),1,abs_tol=1e-9):raise ValueError('Normalized input distribution required')
    mass=sum(p for p,a in zip(probabilities,allowed) if a)
    if mass<=0:raise ValueError('No feasible probability mass; refuse without reroll')
    return [p/mass if a else 0 for p,a in zip(probabilities,allowed)],mass


def choose(probabilities,allowed,order,uniform):
    if set(order)!=set(STEPS) or len(order)!=len(STEPS):raise ValueError('Every category exactly once required')
    ps,mass=condition(probabilities,allowed)
    step=draw(order,[ps[s+127] for s in order],uniform)
    if not allowed[step+127]:raise AssertionError('Selected excluded action')
    return step,dict(retained_mass=mass,removed_mass=1-mass,distribution_changed=mass<1)
