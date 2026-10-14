"""Key/genre-independent mapping of musical notes relative to supplied harmony.

Chord identity is explicit evidence (or supplied by a separate analyzer), never
inferred from a guitar note's register. No chord/progression is prescribed.
This is a semantic transformation layer, NOT a chord detector.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Chord:
    """Absolute MIDI root plus named chord degrees and semitone offsets.

    Example: Chord(50, ((1,0),(3,3),(5,7))) describes D minor.
    Extensions distinguish 2 from 9, 4 from 11, etc.
    """
    root: int
    degrees: tuple[tuple[int, int], ...]

    def __post_init__(self):
        if not self.degrees:
            raise ValueError("Chord requires at least one degree")
        if len({degree for degree, _ in self.degrees}) != len(self.degrees):
            raise ValueError("Duplicate chord degrees")
        if any(not isinstance(d, int) or not isinstance(semi, int) for d,semi in self.degrees):
            raise TypeError("Chord degrees and offsets must be integers")

    def offset(self, degree: int) -> int | None:
        return next((semi for d,semi in self.degrees if d == degree), None)


@dataclass(frozen=True)
class RelativeNote:
    """Retains actual pitch and chord-relative evidence, including ambiguity.

    degree is a chord-tone function ONLY when pitch class agrees with that
    degree in the reference chord. Chromatic/nonchord notes have degree=None.
    """
    original_pitch: int
    interval_from_root: int
    degree: int | None
    octave_displacement: int | None


def analyze_note(pitch: int, chord: Chord) -> RelativeNote:
    """Find an exact matching chord degree, without inventing a scale degree.

    The octave is measured from the chord-root reference, allowing the resulting
    melody to preserve register relative to the new chord root.
    """
    interval = pitch - chord.root
    matching = []
    for degree, offset in chord.degrees:
        if (interval-offset) % 12 == 0:
            matching.append((degree, (interval-offset)//12))
    if len(matching) == 1:
        degree, octaves = matching[0]
        return RelativeNote(pitch,interval,degree,octaves)
    # Multiple enharmonically equivalent named functions are ambiguous.
    return RelativeNote(pitch,interval,None,None)


def map_note(note: RelativeNote, target: Chord, *, missing: str = "preserve_interval") -> int:
    """Transform to target harmony while preserving verified chord function.

    Nonchord/ambiguous source notes retain the same semitone offset from root.
    Missing target degrees can preserve that offset or raise. No nearest-note
    quantization and no implicit jazz/metal rules.
    """
    if note.degree is not None:
        offset = target.offset(note.degree)
        if offset is not None:
            return target.root + offset + 12*note.octave_displacement
        if missing == 'error':
            raise ValueError(f"Target chord has no degree {note.degree}")
    if missing not in ('preserve_interval','error'):
        raise ValueError('Unknown missing-degree policy')
    return target.root + note.interval_from_root


def transform_melody(pitches: Iterable[int], source: Chord, target: Chord,
                     *, missing: str = 'preserve_interval') -> list[int]:
    return [map_note(analyze_note(p,source),target,missing=missing) for p in pitches]


def analyze_timed_melody(events: Iterable[dict], harmony: Iterable[dict]) -> list[dict]:
    """Attach harmonic relation at the event's exact onset (quarter-note beats).

    `harmony` entries: {start, end, chord: Chord}; end is exclusive.
    Overlap, gaps and missing harmony remain explicit; do not guess.
    """
    from fractions import Fraction
    spans = [(Fraction(h['start']),Fraction(h['end']),h['chord']) for h in harmony]
    if any(start>=end for start,end,_ in spans):
        raise ValueError('Invalid harmony window')
    result=[]
    for event in events:
        onset=Fraction(event['onset'])
        applicable=[ch for start,end,ch in spans if start<=onset<end]
        if len(applicable)>1:
            raise ValueError(f'Ambiguous overlapping harmony at onset {onset}')
        item=dict(event)
        item['chord']=applicable[0] if applicable else None
        item['relative_notes']=(tuple(analyze_note(p,applicable[0]) for p in event.get('pitches',()))
                                if applicable else None)
        result.append(item)
    return result


def transform_timed_melody(annotated_events: Iterable[dict], target_harmony: Iterable[dict]) -> list[dict]:
    """Reharmonize notes by exact onset; preserve event timing/rests.

    For source events with unknown harmony, preserve their absolute pitches.
    For target events without a matching chord window, raise rather than invent.
    """
    from fractions import Fraction
    spans=[(Fraction(h['start']),Fraction(h['end']),h['chord']) for h in target_harmony]
    out=[]
    for e in annotated_events:
        item={k:v for k,v in e.items() if k not in ('chord','relative_notes')}
        source=e.get('chord')
        if source is None:
            out.append(item);continue
        matches=[c for a,b,c in spans if a<=Fraction(e['onset'])<b]
        if len(matches)!=1:raise ValueError(f'Expected one target chord at {e["onset"]}')
        item['pitches']=transform_melody(e.get('pitches',()),source,matches[0])
        out.append(item)
    return out