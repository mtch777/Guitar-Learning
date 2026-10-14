"""Evidence-gated completion of incomplete/rootless chord observations.

A partial sonority is assigned only when matching independently observed
chord anchors occur on both sides and its sounded pitch classes agree with
that chord. No chord is inferred from register, genre, or tonic preference.
"""
from fractions import Fraction


def chord_identity(chord):
    return (chord.root % 12, tuple(chord.degrees))


def chord_pitch_classes(chord):
    return {(chord.root + semitones) % 12 for _, semitones in chord.degrees}


def supplement_anchors(score, track_index, anchors, max_gap=4):
    """Add safe partial-chord anchors using observed neighbors, not a guessed root.

    Only between NONOVERLAPPING observed anchors of identical identity.
    Partial observations must contain 2+ distinct pitch classes, be a strict
    subset of the chord and overlap neither existing anchors nor other voices
    with contradictory pitches. Source-note timing and IDs are not modified.
    """
    if max_gap is not None and Fraction(max_gap) < 0:
        raise ValueError('max_gap cannot be negative')
    ordered = sorted(anchors, key=lambda a: (a['start'], a['end']))
    additions = []
    candidates = 0
    rejected = 0
    events = [e for m in score['tracks'][track_index]['measures']
              for voice in m['voices'] for e in voice]
    for event in events:
        pitches = [n['midi'] for n in event['notes'] if n['midi'] is not None]
        pcs = set(p % 12 for p in pitches)
        if len(pcs) < 2:
            continue
        start = Fraction(event['onset_q'])
        end = start + Fraction(event['duration_q'])
        if any(start < a['end'] and a['start'] < end for a in ordered):
            continue
        if any(start == a['start'] and event['beat_id'] == a.get('beat_id') for a in additions):
            continue
        left = [a for a in ordered if a['end'] <= start]
        right = [a for a in ordered if a['start'] >= end]
        if not left or not right:
            continue
        l = max(left, key=lambda a: a['end'])
        r = min(right, key=lambda a: a['start'])
        if l['end'] > r['start']:
            continue
        if max_gap is not None and r['start'] - l['end'] > Fraction(max_gap):
            continue
        candidates += 1
        if chord_identity(l['chord']) != chord_identity(r['chord']):
            rejected += 1
            continue
        known = chord_pitch_classes(l['chord'])
        # A strict subset can be rootless; do not require root to be sounded.
        if not (pcs < known):
            rejected += 1
            continue
        # All voices sounding during the candidate must be compatible.
        contradictory = False
        for other in events:
            a = Fraction(other['onset_q'])
            b = a + Fraction(other['duration_q'])
            if a < end and start < b:
                other_pcs = {n['midi'] % 12 for n in other['notes'] if n['midi'] is not None}
                if other_pcs - known:
                    contradictory = True
                    break
        if contradictory:
            rejected += 1
            continue
        additions.append({'start': start, 'end': end,
                          'chord': l['chord'], 'beat_id': event['beat_id'],
                          'voice': event['voice_index'], 'contextual': True})
    return sorted(ordered + additions, key=lambda a: (a['start'], a['end'])), {
        'partial_chord_candidates': candidates,
        'contextually_completed_chords': len(additions),
        'contextual_candidates_rejected': rejected,
    }