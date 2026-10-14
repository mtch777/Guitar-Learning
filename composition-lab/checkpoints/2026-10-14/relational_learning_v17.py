"""Chord-independent melodic relationship learning over all voices and measures.

A first layer of a multi-view music model: observed interval contours are
learned without chord labels. It is NOT joint probabilistic inference yet.
"""
from collections import Counter
from fractions import Fraction
import random

F = Fraction


def voice_streams(score, track):
    """Combine same-index voices across measures, preserving global ordering."""
    streams = {}
    for measure in score['tracks'][track]['measures']:
        for vi, voice in enumerate(measure['voices']):
            streams.setdefault(vi, []).extend(voice)
    return [sorted(stream, key=lambda e: F(e['onset_q'])) for stream in streams.values()]


def observed_windows(score, track, sizes=(4, 3, 2)):
    """Return contiguous, single-note windows even across bar/chord boundaries."""
    for stream in voice_streams(score, track):
        for size in sizes:
            for i in range(len(stream) - size + 1):
                group = stream[i:i + size]
                if any(len([n for n in e['notes'] if n['midi'] is not None]) != 1 for e in group):
                    continue
                if any(n.get('tie') for e in group for n in e['notes']):
                    continue
                if any(F(a['onset_q']) + F(a['duration_q']) != F(b['onset_q'])
                       for a, b in zip(group, group[1:])):
                    continue
                yield group


def _pitches(group):
    return tuple(next(n['midi'] for n in e['notes'] if n['midi'] is not None) for e in group)


def _intervals(group):
    p = _pitches(group)
    return tuple(b - a for a, b in zip(p, p[1:]))


def learn_relations(score, track):
    """Learn observed interval sequences, without making a harmony guess."""
    patterns = Counter()
    for group in observed_windows(score, track):
        patterns[(len(group), _intervals(group))] += 1
    return patterns


def plan_intervals(score, track, strength, seed=17, exclude_events=(), max_pitch_jump=24):
    """Generate pitch-only replacements from whole observed interval patterns.

    Preserves first note and exact note onsets/durations. Does not claim to
    preserve chord functions when melody change is requested. Can propose
    unplayable notes; GP exporter must reject them.
    """
    if not 0 <= strength <= 100:
        raise ValueError('strength must be between 0 and 100')
    if strength == 0:
        return {}, {'relation_phrases': 0, 'relation_candidates_unavailable': 0, 'relation_vocabulary': 0}
    vocab = learn_relations(score, track)
    pool = {}
    for (size, intervals), count in vocab.items():
        pool.setdefault(size, []).append((intervals, count))
    rng = random.Random(seed + 1707)
    occupied = set(exclude_events)
    planned = {}
    changed = unavailable = 0
    for group in observed_windows(score, track):
        ids = tuple(id(e) for e in group)
        if any(i in occupied for i in ids):
            continue
        if rng.random() >= strength / 100:
            continue
        current = _intervals(group)
        original = _pitches(group)
        choices = []
        for intervals, count in pool.get(len(group), ()): 
            if intervals == current:
                continue
            pitches = [original[0]]
            for delta in intervals:
                pitches.append(pitches[-1] + delta)
            if max(abs(b - a) for a, b in zip(pitches, pitches[1:])) > max_pitch_jump:
                continue
            if any(p < 0 or p > 127 for p in pitches):
                continue
            choices.append((tuple(pitches), count))
        if not choices:
            unavailable += 1
            continue
        candidate = rng.choices([p for p, _ in choices], weights=[w for _, w in choices])[0]
        for event, pitch in zip(group, candidate):
            planned[id(event)] = (pitch,)
        occupied.update(ids)
        changed += 1
    return planned, {'relation_phrases': changed, 'relation_candidates_unavailable': unavailable,
                     'relation_vocabulary': len(vocab),
                     'relation_training_windows': sum(vocab.values())}