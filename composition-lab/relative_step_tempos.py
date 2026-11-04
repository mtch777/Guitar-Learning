"""Intentional pace changes through the existing exact step-clock relationship.

Ratios are choices, not inferred artist preferences or new source observations.
The immutable request baseline counts global tempo regions, never track aliases.
Written positions remain owned by the existing rhythm relationships.
"""
from copy import deepcopy
from fractions import Fraction as F

from step_tempo_relations import expand, set_bpm, speed_relation


def apply_ratios(model, *, baseline, ratios, percent):
    """Atomically realize explicit pace ratios and check FINAL output coverage.

0 locks the supplied CURRENT model. Positive percentages compare resulting BPMs
with the frozen original request, with nearest-integer/half-up unit rounding.
A ratio of 3/2 means 1.5 times the current pace, not 50% changed coverage.
"""
    expand(model)
    expand(baseline)
    if type(percent) not in (int, str):
        raise ValueError('Exact percentage required')
    amount = F(percent)
    if not 0 <= amount <= 100:
        raise ValueError('Percentage must be between 0 and 100')
    current = {g['id']: g for g in model['groups']}
    original = {g['id']: g for g in baseline['groups']}
    if current.keys() != original.keys() or any(
            current[key]['bpm_refs'] != original[key]['bpm_refs'] for key in current):
        raise ValueError('Frozen global tempo identities and aliases must survive')
    if type(ratios) is not dict or set(ratios) - current.keys():
        raise ValueError('Ratios must name existing global tempo regions')
    for ratio in ratios.values():
        if type(ratio) not in (int, str) or F(ratio) <= 0:
            raise ValueError('Positive exact pace ratios required')
    count = len(original)
    target = (amount * count / 100 + F(1, 2)).numerator // (amount * count / 100 + F(1, 2)).denominator
    candidate = deepcopy(model)
    if amount:
        for key, ratio in ratios.items():
            bpm = F(speed_relation(quarter_seconds=current[key]['quarter_seconds']))
            candidate = set_bpm(candidate, key, str(bpm * F(ratio)))
    rows = []
    for group in candidate['groups']:
        key = group['id']
        before, old = current[key], original[key]
        rows.append(dict(id=key, alias_count=len(group['bpm_refs']),
            baseline_bpm=speed_relation(quarter_seconds=old['quarter_seconds']),
            current_bpm=speed_relation(quarter_seconds=before['quarter_seconds']),
            result_bpm=speed_relation(quarter_seconds=group['quarter_seconds']),
            changed_from_baseline=group['quarter_seconds'] != old['quarter_seconds'],
            changed_from_current=group['quarter_seconds'] != before['quarter_seconds']))
    changed = sum(row['changed_from_baseline'] for row in rows)
    if amount and changed != target:
        raise ValueError(f'Final tempo target unmet: {changed}/{count}; required {target}')
    return candidate, dict(status='NOT_APPLICABLE' if not count else 'EXACT_CURRENT_LOCK' if not amount else 'OUTPUT_TARGET_MET',
        requested_percent=str(amount), original_units=count, target_units=target,
        changed_from_baseline=changed, changed_from_current=sum(r['changed_from_current'] for r in rows),
        rows=rows, written_positions_changed=False,
        claim='Intentional pace only; native elapsed time and musical preference require separate verification')
