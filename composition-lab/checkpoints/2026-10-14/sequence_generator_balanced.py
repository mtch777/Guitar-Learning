"""V8 alternative: context interpolation and corpus-calibrated event sampling.

Purely statistical controls: no genre/chug/root/chord-progressions. Learns event
class frequencies from observed sequence events, not manually supplied targets.
"""
from collections import Counter
from fractions import Fraction
import math, random
from sequence_generator_v6 import playable_positions, RHYTHMS, export_score


def _kind(token):
    shape=token[2]
    return 'rest' if not shape else ('single' if len(shape)==1 else 'polyphonic')


def generate(model,tuning,bars=16,meter='4/4',seed=17,max_fret=14):
    numerator,denominator=map(int,meter.split('/'))
    if denominator<=0 or numerator<1 or bars<1 or not tuning:
        raise ValueError('Expected positive meter, bars and pitched tuning')
    rng=random.Random(seed)
    anchor=rng.choices(list(model.pitch_starts),weights=list(model.pitch_starts.values()),k=1)[0]
    baseline=model.next_counts[0][()]
    categories=Counter()
    duration_totals=Counter()
    for token,n in baseline.items():
        categories[_kind(token)]+=n
        duration_totals[token[0]]+=n
    total=sum(categories.values())
    prior={kind:categories[kind]/total for kind in ('rest','single','polyphonic')}
    mean_units=sum(u*n for u,n in duration_totals.items())/sum(duration_totals.values())
    observed=Counter(); observed_units=0
    history=[];result=[];orders=Counter();rests=0
    # Generic prior smoothing and a soft penalty for drifting far from empirical
    # class/duration frequencies. Neither is a musical-style rule.
    for _ in range(bars):
        remaining=Fraction(16*numerator,denominator);measure=[]
        while remaining:
            candidates={};sources=Counter()
            for order in range(min(len(history),model.max_order),-1,-1):
                context=tuple(history[-order:]) if order else ()
                distribution=model.next_counts[order].get(context,{})
                if not distribution:continue
                possible={}
                for token,n in distribution.items():
                    units,delta,shape=token
                    if units>remaining:continue
                    if shape:
                        if delta is None and history:continue
                        fitted=playable_positions(anchor+(delta or 0),shape,tuning,max_fret)
                        if fitted is None:continue
                    else:fitted=[]
                    possible[token]=(n,fitted)
                if not possible:continue
                support=sum(n for n,_ in possible.values())
                # Longer contexts get greater weight only when supported by data.
                mass=(support/(support+6.0))*(1.7**order)
                for token,(n,placed) in possible.items():
                    if token not in candidates:candidates[token]=[0.,placed,Counter()]
                    candidates[token][0]+=mass*n/support
                    candidates[token][2][order]+=mass*n/support
            if not candidates:
                # Timing repair only; this is not a generated stylistic rest.
                unit=remaining
                measure.append({'units':unit,'positions':[]})
                remaining-=unit;rests+=1;history=[]
                continue
            weights=[];tokens=list(candidates)
            for tok in tokens:
                base=candidates[tok][0]
                kind=_kind(tok)
                generated_total=sum(observed.values())
                if generated_total:
                    empirical=(observed[kind]+prior[kind]*10)/(generated_total+10)
                    drift=prior[kind]-empirical
                    class_factor=math.exp(max(-2.,min(2.,7.*drift)))
                else:class_factor=1.
                if observed_units:
                    mean_generated=observed_units/max(1,generated_total)
                    duration_factor=math.exp(max(-1.5,min(1.5,0.8*(mean_units-mean_generated)*(tok[0]-mean_units)/max(1.,mean_units))))
                else:duration_factor=1.
                weights.append(base*class_factor*duration_factor)
            token=rng.choices(tokens,weights=weights,k=1)[0]
            units,delta,shape=token
            placed=candidates[token][1]
            measure.append({'units':units,'positions':placed})
            observed[_kind(token)]+=1;observed_units+=units
            if placed:anchor=placed[0][0]
            else:rests+=1
            order=max(candidates[token][2],key=candidates[token][2].get)
            orders[order]+=1
            history.append(token)
            history=history[-model.max_order:] if model.max_order else []
            remaining-=units
        result.append(measure)
    return result,{'context_uses':dict(orders),'rest_events':rests,'meter':meter,'bars':bars,
                   'learned_event_frequencies':prior,'generated_event_counts':dict(observed)}