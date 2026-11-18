"""Pure, lossless recording-time review packaging. No classification or I/O.

Input segments require id, start_seconds, end_seconds, candidate_weights.
Empty weights are permitted only with status='unknown'. Gaps are explicit;
no winner is inferred and no adjacent segments are merged.
"""
from copy import deepcopy
from math import isfinite, fsum


def _number(value):
    return type(value) in (int, float) and isfinite(value)


def export_recording_review(segments, *, recording_duration):
    """Preserve every source boundary, alternative and extra metadata field.

    IDs must be unique nonempty strings. Distribution mass is validated, never
    normalized. Generated gaps have no source segment ID or candidate weights.
    Returned objects do not alias caller objects. No probability calibration is
    asserted, including when a caller supplies a one-hot distribution.
    """
    if not _number(recording_duration) or recording_duration <= 0:
        raise ValueError('positive finite recording duration required')
    timeline = []
    original = []
    seen = set()
    cursor = 0
    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError('segment must be a mapping')
        sid = segment.get('id')
        a, b = segment.get('start_seconds'), segment.get('end_seconds')
        weights = segment.get('candidate_weights')
        if not isinstance(sid, str) or not sid.strip() or sid in seen:
            raise ValueError('unique nonempty segment IDs required')
        if not _number(a) or not _number(b) or a < cursor or b <= a or b > recording_duration:
            raise ValueError('segments must be finite, sorted, nonoverlapping and within recording')
        if not isinstance(weights, dict):
            raise ValueError('candidate_weights mapping required')
        if weights:
            if any(not isinstance(k, str) or not k.strip() or not _number(v) or not 0 <= v <= 1
                   for k, v in weights.items()) or abs(fsum(weights.values()) - 1) > 1e-8:
                raise ValueError('finite nonnegative distribution with full unit mass required')
        elif segment.get('status') != 'unknown':
            raise ValueError('empty distribution requires explicit unknown status')
        if a > cursor:
            timeline.append({'kind': 'gap', 'start_seconds': cursor, 'end_seconds': a,
                             'status': 'unknown', 'candidate_weights': {}})
        original.append(deepcopy(segment))
        timeline.append({'kind': 'detected_segment', 'segment': deepcopy(segment)})
        seen.add(sid)
        cursor = b
    if cursor < recording_duration:
        timeline.append({'kind': 'gap', 'start_seconds': cursor, 'end_seconds': recording_duration,
                         'status': 'unknown', 'candidate_weights': {}})
    return {'schema': 'recording-review-export/1', 'recording_duration': recording_duration,
            'segments': original, 'timeline': timeline,
            'weight_semantics': 'caller_supplied_uncalibrated_distribution',
            'limitations': ['Weights are not calibrated confidence or measured accuracy.',
                            'Source segment boundaries are retained, not musically verified.',
                            'Unknown intervals and uncovered gaps are not assigned a role.']}
