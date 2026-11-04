"""Measure requested change in the final output, without making musical choices.

This is a request/verification record, never an inverse input or a tier owner.
Callers supply canonical, meaningfully defined measurements and stable unit IDs.
Candidate availability must not change the baseline population. Unknown values
stay in its denominator and cannot establish a changed/unchanged feature.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json

SCHEMA = 'final-output-change-targets/v1'


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _hash(value):
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


def _values(values):
    if type(values) is not dict or not values:
        raise ValueError('Explicit nonempty feature measurements required')
    for name, units in values.items():
        if type(name) is not str or not name or type(units) is not dict:
            raise ValueError('Named features with stable unit mappings required')
        if any(type(key) is not str or not key for key in units):
            raise ValueError('Nonempty stable unit identities required')
    _json(values)


def target_count(total, percent):
    if type(total) is not int or total < 0:
        raise ValueError('Nonnegative integer unit count required')
    if type(percent) is not int or not 0 <= percent <= 100:
        raise ValueError('Integer output change percentage from 0 to 100 required')
    return int((Decimal(total) * Decimal(percent) / 100).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP))


def freeze_targets(values, requests):
    """Freeze every requested unit before testing alternatives."""
    _values(values)
    if type(requests) is not dict or set(requests) != set(values):
        raise ValueError('Every measured feature needs an explicit target, including zero locks')
    for name, percent in requests.items():
        target_count(len(values[name]), percent)
    payload = dict(schema=SCHEMA, baseline=deepcopy(values), requests=deepcopy(requests))
    return dict(**payload, request_sha256=_hash(payload))


def evaluate_targets(contract, values):
    """Check all targets on one final realization; no intermediate edit credit."""
    if (type(contract) is not dict or
            set(contract) != {'schema', 'baseline', 'requests', 'request_sha256'} or
            contract['schema'] != SCHEMA):
        raise ValueError('Frozen output target contract required')
    fresh = freeze_targets(contract['baseline'], contract['requests'])
    if contract != fresh:
        raise ValueError('Frozen output request was modified')
    _values(values)
    if set(values) != set(contract['baseline']):
        raise ValueError('Final feature set differs from the frozen request')
    rows = {}
    for name, baseline in contract['baseline'].items():
        final = values[name]
        if set(final) != set(baseline):
            raise ValueError(f'Final unit identities differ from frozen {name} scope')
        changed, unchanged, unknown = [], [], []
        for identity in sorted(baseline):
            if baseline[identity] is None or final[identity] is None:
                unknown.append(identity)
            elif _json(baseline[identity]) == _json(final[identity]):
                unchanged.append(identity)
            else:
                changed.append(identity)
        total = len(baseline)
        requested = contract['requests'][name]
        target = target_count(total, requested)
        satisfied = bool(total) and not unknown and len(changed) == target
        rows[name] = dict(requested_percent=requested, target_count=target,
            total_count=total, changed_count=len(changed), changed_ids=changed,
            unchanged_ids=unchanged, unknown_ids=unknown,
            achieved_percent=(100 * len(changed) / total if total else None),
            achieved_fraction=(f'{len(changed)}/{total}' if total else None),
            satisfied=satisfied,
            status=('NOT_APPLICABLE' if not total else 'UNKNOWN_MEASUREMENTS' if unknown
                    else 'SATISFIED' if satisfied else 'TARGET_NOT_MET'))
    return dict(request_sha256=contract['request_sha256'],
                satisfied=all(row['satisfied'] for row in rows.values()), features=rows)
