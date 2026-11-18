"""Provisional verse/chorus evidence over bar-level repeat candidates.

Not a trained classifier or final segmentation. Never treat these normalized
support weights as probability/accuracy. Original observations are not changed.
"""
from math import isfinite
from statistics import mean
from section_repeats import analyze_repeats, compare_bars

DEFAULT_WEIGHTS = {
    'return_stability': .20, 'boundary_support': .20,
    'arrangement_lift': .15, 'lead_return': .25, 'lead_variation': .20,
}


def _mean(values):
    values = [v for v in values if v is not None]
    return mean(values) if values else None


def _unit(value):
    return max(0., min(1., value))


def analyze_functions(features, repeats=None, lead_channels=(), weights=None, lyric_evidence=None):
    """Return hypotheses for existing repeated groups, plus one row per bar.

    lead_channels are caller-confirmed vocal/melodic foreground channel IDs, not
    guessed from pitch height. Without those observations the corresponding
    evidence stays unavailable, not zero. Bar indexes are zero-based half-open.
    Results retain overlapping alternatives; no greedy forced partition.
    """
    weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if (set(weights) != set(DEFAULT_WEIGHTS) or
            any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                not isfinite(v) or v < 0 for v in weights.values()) or
            not sum(weights.values())):
        raise ValueError('invalid function weights')
    repeats = analyze_repeats(features) if repeats is None else repeats
    if repeats.get('bar_count') != len(features):
        raise ValueError('repeat analysis does not match bar count')
    leads = set(map(str, lead_channels))
    total_weight = sum(weights.values())
    hypotheses = []
    n = len(features)
    for group_index, group in enumerate(repeats['groups']):
        occurrences = group['occurrences']
        ranges = [(o['start_index'], o['end_index']) for o in occurrences]
        if (len(ranges) < 2 or any(type(a) is not int or type(z) is not int or
                not 0 <= a < z <= n for a, z in ranges) or
                len(set(z-a for a, z in ranges)) != 1):
            raise ValueError('invalid repeat occurrence ranges')
        # Do not elevate an endlessly repeating one-bar accompaniment into a
        # functional section; retain it for inspection, but expose ambiguity.
        loop = group['interpretation'] == 'repeating_motif_or_loop'
        changes = []
        for a, z in ranges:
            for x, y in ((a-1, a), (z-1, z)):
                if 0 <= x < y < n:
                    s = compare_bars(features[x], features[y])['score']
                    if s is not None:
                        changes.append(1-s)
        boundary = _mean(changes)
        active = set(i for a, z in ranges for i in range(a, z))
        # Activity is arrangement fullness, never claimed to be acoustic loudness.
        inside = [len(features[i]['arrangement']) for i in active if features[i]['observed']]
        outside = [len(f['arrangement']) for i, f in enumerate(features)
                   if i not in active and f['observed']]
        lift = None
        if inside and outside and max(inside + outside):
            lift = (mean(inside)-mean(outside))/max(inside + outside)
        melody = []
        for j, (a, z) in enumerate(ranges):
            for b, _ in ranges[j+1:]:
                for offset in range(z-a):
                    x, y = features[a+offset], features[b+offset]
                    # Both passages must actually contain known observations.
                    # Missing lead notes cannot be interpreted as changing lyrics.
                    c = compare_bars(x, y)
                    melody.extend(v for k, v in c['channels']['pitch'].items() if k in leads)
        lead_return = _mean(melody)
        evidence = {
            'return_stability': group['minimum_pair_similarity'],
            'boundary_support': boundary,
            'arrangement_lift': lift,
            'lead_return': lead_return,
            'lead_variation': None if lead_return is None else 1-lead_return,
        }
        # Shared cues support sectionhood, not a verse/chorus distinction.
        # Lead repeat/variation is a soft cue only: solos and breakdowns remain
        # possible. Relative fullness is subordinate and never decisive alone.
        role_values = {
            'verse': {'return_stability': evidence['return_stability'],
                      'boundary_support': boundary,
                      'arrangement_lift': None if lift is None else max(0., -lift),
                      'lead_return': None if lead_return is None else .5*lead_return,
                      'lead_variation': evidence['lead_variation']},
            'chorus': {'return_stability': evidence['return_stability'],
                       'boundary_support': boundary,
                       'arrangement_lift': None if lift is None else max(0., lift),
                       'lead_return': lead_return,
                       'lead_variation': None if lead_return is None else .25*(1-lead_return)},
        }
        scores = {role: sum(weights[k]*v for k, v in vals.items() if v is not None)/total_weight
                  for role, vals in role_values.items()}
        # Unknown absorbs missing evidence and unresolved function. Absence of
        # foreground evidence OR loop status cannot yield an automatic role label.
        available = sum(weights[k] for k, v in evidence.items() if v is not None)/total_weight
        ambiguity = 1-abs(scores['verse']-scores['chorus'])
        scores['unknown'] = max(1-available, ambiguity, 1. if loop or lead_return is None else 0.)
        denominator = sum(scores.values())
        shares = {k: v/denominator for k, v in scores.items()}
        hypotheses.append(dict(
            id=group_index, occurrences=occurrences, evidence=evidence,
            contributions={role: {k: weights[k]*v/total_weight for k, v in vals.items() if v is not None}
                           for role, vals in role_values.items()},
            available_weight=available, support_weights=shares,
            label='unknown', status='provisional_hypotheses_not_validated',
            interpretation=group['interpretation'],
            warnings=(['internal_loop_not_proof_of_section'] if loop else []) +
                     (['no_confirmed_foreground_evidence'] if lead_return is None else []) +
                     ['verse_chorus_cues_also_possible_in_other_song_functions'],
            confidence=None))
    bars = []
    for i, feature in enumerate(features):
        ids = [h['id'] for h in hypotheses
               if any(o['start_index'] <= i < o['end_index'] for o in h['occurrences'])]
        bars.append(dict(bar=feature['bar'],start_q=feature['start_q'],end_q=feature['end_q'],
                         candidate_group_ids=ids, label='unknown',
                         reason='ambiguous_function' if ids else 'no_repeat_candidate',
                         observed=feature['observed']))
    result = dict(schema='bar-section-functions/1', bar_count=n,
                parameters={'weights': weights, 'confirmed_lead_channels': sorted(leads)},
                hypotheses=hypotheses, bars=bars,
                limitations=[
                    'Support weights are uncalibrated evidence shares, not confidence probabilities.',
                    'All role labels remain unknown until real-song validation supports automatic decisions.',
                    'Foreground recurrence is not lyric repetition or proof of chorus.',
                    'Repeated group proposals can overlap; not a final song partition.',
                    'Nonrepeating verse/chorus is not proposed by this repeat-anchored pilot.',
                    'No intro/outro, bridge, breakdown or solo classification in this pass.'])

    from lyric_refrain_evidence import attach_lyric_evidence, feature_fingerprint
    return attach_lyric_evidence(result, lyric_evidence, feature_fingerprint(features) if lyric_evidence is not None else None)
