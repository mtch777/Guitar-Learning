"""Typed written slots; explicit dead notation is not a missing pitched note.

This is contextual evidence, not a pitch owner or inferred musical voice.
Unresolved execution remains refused; no event is deleted or assigned a pitch.
"""
from fractions import Fraction as F

DEAD_REASONS={'UNKNOWN_PITCH','unresolved_sounding_pitch_dead'}


def unpitched(node):
    return node is not None and node['pitch'] is None and node.get('nominal_dead_declaration',{}).get('eligible')is True


def spans(rows):
    """Every maximal dead run WITH both neighbors/boundaries retained."""
    result=[];i=0
    while i<len(rows):
        if not unpitched(rows[i]):i+=1;continue
        start=i
        while i<len(rows) and unpitched(rows[i]):i+=1
        result.append(('unpitched_span',rows[start]['id'],[rows[start-1] if start else None]+rows[start:i]+[rows[i] if i<len(rows) else None]))
    return result


def describe(window):
    kinds=[];reasons=[];pairs=[];dead_frets=[]
    for n in window:
        if n is None:kinds.append('BOUNDARY');dead_frets.append(None);continue
        if unpitched(n):
            kinds.append('UNPITCHED_NOMINAL_SLOT');dead_frets.append(n['nominal_dead_declaration']['fret'])
            reasons.extend(set(n['reasons'])-DEAD_REASONS);continue
        unknown=n['pitch']is None or F(n['pitch']).denominator!=1 or n['articulation']['note'].get('dead')is True
        kinds.append('UNKNOWN_PITCH' if unknown else 'PITCHED_WRITTEN_SLOT');dead_frets.append(None)
        reasons.extend(n['reasons'])
        if unknown:reasons.append('UNKNOWN_NOMINAL_SLOT')
    known=[i for i,k in enumerate(kinds) if k=='PITCHED_WRITTEN_SLOT']
    for position,i in enumerate(known):
        for j in known[position+1:]:
            pairs.append([i,j,str(F(window[j]['pitch'])-F(window[i]['pitch'])),'adjacent_string_events' if j==i+1 else 'bracketing_known_pitches'])
    return dict(slot_kinds=kinds,dead_fret_declarations=dead_frets,known_pitch_pairs=pairs,reasons=sorted(set(reasons)),has_unpitched=any(k=='UNPITCHED_NOMINAL_SLOT' for k in kinds))
