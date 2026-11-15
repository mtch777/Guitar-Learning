"""Explicit guitar-template preferences for the fifth optimization tier only.

This module recognizes coordinates, never changes pitches and never declares a
key. Its cost must remain subordinate to open strings, neck shifts, remaining
movement and picking. A pentatonic *fragment* means only that the observed
current/previous coordinates fit one transposition of a named box; it does not
mean a whole scale, phrase, or original guitarist's intention was recovered.

Scope: drop-power barres; adjacent-string power voicings; five major CAGED
chord templates; common E/A/D minor chord templates; E/A minor-pentatonic boxes.
Two frames do not establish a 2/3-notes-per-string phrase or an arpeggio, so
those labels are intentionally absent. Maximum-contact and reach admission
belong to the caller, not this preference helper.
"""
from functools import lru_cache


# String 1 is the highest string. Standard CAGED shapes use strings 1 through 6.
TUNING = (64, 59, 55, 50, 45, 40, 35, 28)
NO_MATCH_COST = 10

# Exact standard open-position shapes, written high string to low string.
# A common offset transposes every fretted/open coordinate together.
CHORD_TEMPLATES = (
    ('C', 'major', ((1, 0), (2, 1), (3, 0), (4, 2), (5, 3))),
    ('A', 'major', ((1, 0), (2, 2), (3, 2), (4, 2), (5, 0))),
    ('G', 'major', ((1, 3), (2, 0), (3, 0), (4, 0), (5, 2), (6, 3))),
    ('E', 'major', ((1, 0), (2, 0), (3, 1), (4, 2), (5, 2), (6, 0))),
    ('D', 'major', ((1, 2), (2, 3), (3, 2), (4, 0))),
    ('E', 'minor', ((1, 0), (2, 0), (3, 0), (4, 2), (5, 2), (6, 0))),
    ('A', 'minor', ((1, 0), (2, 1), (3, 2), (4, 2), (5, 0))),
    ('D', 'minor', ((1, 1), (2, 3), (3, 2), (4, 0))),
)

# Root at string 6, offset 0 (E box); string 5, offset 0 (A box).
# Every cell belongs to that root's minor pentatonic collection {0,3,5,7,10}.
PENTATONIC_TEMPLATES = (
    ('E', ((1, (0, 3)), (2, (0, 3)), (3, (0, 2)),
           (4, (0, 2)), (5, (0, 2)), (6, (0, 3)))),
    ('A', ((1, (0, 3)), (2, (1, 3)), (3, (0, 2)),
           (4, (0, 2)), (5, (0, 3)), (6, (0, 3)))),
)


def _canonical(placements, pitches):
    coords, ps = tuple(placements), tuple(pitches)
    if len(coords) != len(ps):
        raise ValueError('Placements and pitches must have the same length')
    rows = []
    strings = set()
    for coordinate, pitch in zip(coords, ps):
        if not isinstance(coordinate, (tuple, list)) or len(coordinate) != 2:
            raise ValueError('Each placement must be (string, fret)')
        string, fret = coordinate
        if (type(string) is not int or type(fret) is not int or
                not 1 <= string <= 8 or not 0 <= fret <= 24 or
                type(pitch) is not int or TUNING[string - 1] + fret != pitch):
            raise ValueError('Placement must preserve its exact Drop E pitch')
        if string in strings:
            raise ValueError('A simultaneous placement uses a string twice')
        strings.add(string)
        rows.append((string, fret, pitch))
    return tuple(sorted(rows))


@lru_cache(maxsize=8192)
def _current_patterns(rows):
    """Full chord/current-attack patterns, without any previous-frame inference."""
    if not rows:
        return ()
    coords = frozenset((s, f) for s, f, p in rows)
    pitches = sorted(p for s, f, p in rows)
    found = []
    strings = {s for s, f, p in rows}
    frets = {f for s, f, p in rows}
    if strings in ({7, 8}, {6, 7, 8}) and len(frets) == 1:
        intervals = [p - pitches[0] for p in pitches]
        if intervals in ([0, 7], [0, 7, 12]):
            label = 'Drop E open power chord' if next(iter(frets)) == 0 else 'Drop E power-chord barre'
            found.append((0, label))

    if len(rows) in (2, 3) and max(strings) - min(strings) + 1 == len(rows):
        # Explicit adjacent-string root/fifth(/octave) shape. Reversed or
        # compound intervals and octave-only dyads are not claimed here.
        low_to_high = sorted(rows, reverse=True)
        ps = [p for s, f, p in low_to_high]
        intervals = [p - ps[0] for p in ps]
        if intervals in ([0, 7], [0, 7, 12]):
            found.append((2, 'Adjacent-string power-chord shape'))

    if len(coords) >= 3 and len({p % 12 for p in pitches}) == 3:
        for name, quality, template in CHORD_TEMPLATES:
            # Matching the first observed coordinate uniquely determines an
            # offset for each template; every coordinate must then agree.
            template_dict = dict(template)
            string, fret, _ = rows[0]
            if string not in template_dict:
                continue
            offset = fret - template_dict[string]
            if offset < 0:
                continue
            translated = frozenset((s, f + offset) for s, f in template)
            if not coords <= translated:
                continue
            expected_pcs = {(TUNING[s - 1] + f) % 12 for s, f in translated}
            if {p % 12 for p in pitches} != expected_pcs:
                continue
            complete = coords == translated
            label = f'CAGED {name}-shape {quality} chord'
            if not complete:
                label += ' fragment'
            found.append((1 if complete else 4, label))
    return tuple(found)


@lru_cache(maxsize=32768)
def _pentatonic_patterns(rows):
    """A literal box subset; label fragments rather than claiming full shapes."""
    if len(rows) < 2 or len({p for s, f, p in rows}) < 2:
        return ()
    if any(s > 6 for s, f, p in rows):
        return ()
    coords = frozenset((s, f) for s, f, p in rows)
    found = []
    first_s, first_f, _ = rows[0]
    for name, template in PENTATONIC_TEMPLATES:
        cells = dict(template)
        for base_cell in cells[first_s]:
            offset = first_f - base_cell
            if offset < 0:
                continue
            translated = frozenset((s, f + offset) for s, fs in template for f in fs)
            if coords <= translated:
                found.append((6, f'{name}-shape minor-pentatonic fragment'))
                break
    return tuple(found)


def shape_cost(placements, pitches, previous_placements=(), previous_pitches=()) -> tuple[int, list[str]]:
    """Return ``(integer_cost, labels)``; smaller is preferred only at Tier 5.

    Inputs are never mutated. Invalid geometry raises ValueError, rather than
    receiving a plausible shape label. Same-pitch occurrences on different
    strings remain separate during chord recognition. The union used solely
    for fragment recognition merges identical prior/current coordinates.
    Labels are sorted and contain only patterns tied at the best current cost.
    Empty/current-rest frames return ``(0, [])``.
    """
    current = _canonical(placements, pitches)
    previous = _canonical(previous_placements, previous_pitches)
    if not current:
        return 0, []
    found = list(_current_patterns(current))
    fragment = tuple(sorted(set(previous) | set(current)))
    found.extend(_pentatonic_patterns(fragment))
    if not found:
        return NO_MATCH_COST, []
    best = min(cost for cost, label in found)
    return best, sorted({label for cost, label in found if cost == best})
