"""Independent, exact-lock controls for harmonic event transformations.

This module operates on symbolic events with explicit source/target chord windows.
It does not infer harmony or mutate GP archives. At strength 0 the selected
feature is an identity. Strengths above zero are stochastic transformation
probabilities, NOT calibrated perceptual distances. Unavailable variations and
conflicting locks are reported, never silently rewritten.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
import random
from harmonic_relative import Chord, analyze_note, map_note

@dataclass(frozen=True)
class Controls:
    chords: float = 0.0
    melody: float = 0.0
    rhythm: float = 0.0

    def __post_init__(self):
        for key in ('chords','melody','rhythm'):
            value=getattr(self,key)
            if not isinstance(value,(float,int)) or not 0 <= value <= 100:
                raise ValueError(f'{key} must be between 0 and 100')


def chord_identity(c):
    return (c.root % 12, c.degrees)


def _unique_chords(chords):
    return sorted(set(chords),key=lambda c:(c.root%12,c.degrees,c.root))


def _choose_harmony(windows, pool, strength, rng):
    result=[]; changed=0; unavailable=0
    for window in windows:
        source=window['chord']; target=source
        if rng.random() < strength/100:
            choices=[c for c in pool if chord_identity(c)!=chord_identity(source)]
            if choices:
                picked=rng.choice(choices)
                root=min((picked.root%12+12*k for k in range(-2,12)),key=lambda x:(abs(x-source.root),x))
                target=Chord(root,picked.degrees)
                changed+=1
            else:unavailable+=1
        result.append({**window,'target':target})
    return result,changed,unavailable


def _at(windows, onset):
    matching=[w for w in windows if Fraction(w['start'])<=onset<Fraction(w['end'])]
    if len(matching)>1:raise ValueError(f'Overlapping harmonic windows at {onset}')
    return matching[0] if matching else None


def transform(events, harmony, *, controls=Controls(), chord_pool=None, melody_offsets=None,
              rhythm_patterns=None, seed=17):
    """Transform note pitches and timed events without overwriting locked dimensions.

    Input events: {onset, duration, pitches, ...}; all times exact Fraction-able.
    harmony: {start, end, chord: Chord}. Arbitrary metadata passes through.
    melody_offsets: allowable nonzero signed semitone shifts relative to the
    resulting chord; a changed degree is deliberately a DIFFERENT melodic role.
    rhythm_patterns: alternative (onset_offset, duration) pairs, exact Fractions.
    Rejected incompatible changes are counted and source events are preserved.
    """
    rng=random.Random(seed)
    controls=controls if isinstance(controls,Controls) else Controls(**controls)
    ordered=sorted(harmony,key=lambda w:Fraction(w['start']))
    for i,w in enumerate(ordered):
        if Fraction(w['start'])>=Fraction(w['end']):raise ValueError('Invalid harmonic window')
        if i and Fraction(ordered[i-1]['end'])>Fraction(w['start']):raise ValueError('Overlapping harmony windows')
    pool=_unique_chords(chord_pool if chord_pool is not None else [w['chord'] for w in ordered])
    chosen,chord_changed,chord_unavailable=_choose_harmony(ordered,pool,controls.chords,rng)
    variants=tuple(s for s in (melody_offsets if melody_offsets is not None else (-2,-1,1,2)) if int(s)==s and s!=0)
    timing=tuple((Fraction(a),Fraction(b)) for a,b in (rhythm_patterns or ()))
    if any(duration<=0 for _,duration in timing):raise ValueError('Rhythm durations must be positive')
    output=[];melody_changed=0;rhythm_changed=0;conflicts=[];unsupported=0
    for index,ev in enumerate(events):
        item=dict(ev)
        source_onset=Fraction(ev['onset']);duration=Fraction(ev['duration'])
        if duration<=0:raise ValueError('Event durations must be positive')
        source=_at(chosen,source_onset)
        pitches=tuple(ev.get('pitches',()))
        new_pitches=pitches
        if source and pitches:
            new_pitches=tuple(map_note(analyze_note(p,source['chord']),source['target']) for p in pitches)
            if controls.melody==0:
                # Relative harmonic roles are locked; map_note preserves roles
                # even when underlying absolute pitches necessarily change.
                pass
            elif rng.random()<controls.melody/100 and variants:
                delta=rng.choice(variants)
                new_pitches=tuple(p+delta for p in new_pitches)
                melody_changed+=1
        elif pitches and controls.chords>0:
            unsupported+=1
        item['pitches']=new_pitches
        if controls.rhythm>0 and rng.random()<controls.rhythm/100 and timing:
            candidates=[(source_onset+shift,d) for shift,d in timing
                        if (shift!=0 or d!=duration) and source_onset+shift>=0]
            # Keep the original harmonic association: moving a note across a
            # chord boundary would otherwise silently change its context.
            candidates=[(start,d) for start,d in candidates
                        if _at(chosen,start) is source]
            if candidates:
                start,d=rng.choice(candidates)
                item['onset']=start;item['duration']=d;rhythm_changed+=1
            else:conflicts.append({'event':index,'reason':'no safe rhythm variation within harmonic window'})
        output.append(item)
    return {'events':output,'harmony':chosen,'report':{
        'changed_chord_windows':chord_changed,'unavailable_chord_variations':chord_unavailable,
        'changed_melody_events':melody_changed,'changed_rhythm_events':rhythm_changed,
        'events_without_harmonic_evidence':unsupported,'conflicts':conflicts,
        'strength_semantics':'stochastic variation probability; not calibrated musical distance',
        'zero_strength':'exact feature lock'}}