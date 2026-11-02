"""Exact held-pitch membership in explicitly selected tonal contexts.

Selected contexts are composition intent, not an inferred key or authenticated
human approval. The source origin binds that intent to a score without changing
its original observations. This module does not select/admit hypotheses, infer
stable spans, edit notes, or impose a constraint on unchanged source notes.
"""
from copy import deepcopy
from fractions import Fraction

from source_observation_evidence import validate_origin


SCHEMA = 'stable-pitch-membership-context/1'
ASSESSMENT_SCHEMA = 'stable-pitch-membership-assessment/1'
BASIS = 'explicit_selected_context'
PITCH_FRAME = 'nominal_sounding_midi'
IN_COLLECTION = 'IN_COLLECTION'
OUT_OF_COLLECTION = 'OUT_OF_COLLECTION'
NOT_KEY_VERIFIED = 'NOT_KEY_VERIFIED'


def _fields(value, expected, description):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f'Exact {description} fields required')


def _text(value, description):
    if type(value) is not str or not value.strip():
        raise ValueError(f'Nonempty {description} required')


def _rational(value, description):
    if type(value) not in (str, int):
        raise ValueError(f'Exact rational {description} required')
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f'Exact rational {description} required') from exc


def _interval(row, description):
    start = _rational(row['start_q'], f'{description} start')
    end = _rational(row['end_q'], f'{description} end')
    if start >= end:
        raise ValueError(f'Positive {description} duration required')
    row.update(start_q=str(start), end_q=str(end))
    return start, end


def validate_context(packet, origin):
    """Validate strict selected-intent schema and match an external source origin.

    Return a deep copy with canonical rational times. Origin identity is not a
    tonal inference or proof of who selected the context. Gaps and empty candidate
    lists remain representable; assessment must report them as unresolved.
    """
    validate_origin(origin)
    _fields(packet, ('schema', 'origin', 'basis', 'pitch_frame',
                     'selection_reason', 'selection_reference', 'contexts'),
            'selected tonal context')
    validate_origin(packet['origin'])
    if packet['origin'] != origin:
        raise ValueError('Selected tonal context source origin mismatch')
    if (packet['schema'] != SCHEMA or packet['basis'] != BASIS
            or packet['pitch_frame'] != PITCH_FRAME):
        raise ValueError('Typed explicit selected nominal-sounding-pitch context required')
    for field in ('selection_reason', 'selection_reference'):
        _text(packet[field], field)
    if type(packet['contexts']) is not list or not packet['contexts']:
        raise ValueError('Nonempty selected context segments required')
    result = deepcopy(packet)
    ids = set()
    previous_end = None
    for row in result['contexts']:
        _fields(row, ('id', 'start_q', 'end_q', 'candidates'), 'context segment')
        _text(row['id'], 'context segment id')
        if row['id'] in ids:
            raise ValueError('Unique context segment ids required')
        ids.add(row['id'])
        start, end = _interval(row, 'context segment')
        if previous_end is not None and start < previous_end:
            raise ValueError('Ordered nonoverlapping context segments required')
        previous_end = end
        if type(row['candidates']) is not list:
            raise ValueError('Explicit candidate list required')
        candidate_ids = set()
        for candidate in row['candidates']:
            _fields(candidate, ('id', 'tonic_pc', 'intervals'), 'tonal hypothesis')
            _text(candidate['id'], 'tonal hypothesis id')
            if candidate['id'] in candidate_ids:
                raise ValueError('Unique tonal hypothesis ids per segment required')
            candidate_ids.add(candidate['id'])
            if type(candidate['tonic_pc']) is not int or not 0 <= candidate['tonic_pc'] < 12:
                raise ValueError('Integer tonic pitch class from 0 through 11 required')
            intervals = candidate['intervals']
            if (type(intervals) is not list or not intervals
                    or any(type(value) is not int or not 0 <= value < 12 for value in intervals)
                    or intervals != sorted(set(intervals)) or intervals[0] != 0):
                raise ValueError('Sorted unique integer collection intervals including zero required')
    return result


def _validated_spans(spans):
    if type(spans) is not list:
        raise ValueError('Explicit stable span list required')
    result = deepcopy(spans)
    for span in result:
        _fields(span, ('occurrence_refs', 'start_q', 'end_q', 'pitch'), 'stable span')
        refs = span['occurrence_refs']
        if type(refs) is not list or not refs:
            raise ValueError('Nonempty stable occurrence refs required')
        for ref in refs:
            _text(ref, 'stable occurrence ref')
        if len(set(refs)) != len(refs):
            raise ValueError('Unique stable occurrence refs required')
        _interval(span, 'stable span')
        span['pitch'] = str(_rational(span['pitch'], 'stable pitch'))
    return result


def _combined_status(statuses):
    if not statuses or NOT_KEY_VERIFIED in statuses:
        return NOT_KEY_VERIFIED
    if OUT_OF_COLLECTION in statuses:
        return OUT_OF_COLLECTION
    return IN_COLLECTION


def _cell(context, start, end, pitch):
    row = dict(start_q=str(start), end_q=str(end),
               context_id=None if context is None else context['id'],
               memberships=[], status=NOT_KEY_VERIFIED, reasons=[])
    if context is None:
        row['reasons'].append('UNCOVERED_STABLE_SPAN')
        return row
    if not context['candidates']:
        row['reasons'].append('NO_SELECTED_HYPOTHESES')
        return row
    if pitch.denominator != 1:
        row['reasons'].append('NONINTEGER_STABLE_PITCH_NOT_SUPPORTED')
        return row
    pc = int(pitch) % 12
    for candidate in context['candidates']:
        collection = sorted((candidate['tonic_pc'] + value) % 12
                            for value in candidate['intervals'])
        row['memberships'].append(dict(candidate_id=candidate['id'],
                                       collection_pitch_classes=collection,
                                       pitch_class=pc, inside=pc in collection))
    values = [member['inside'] for member in row['memberships']]
    if all(values):
        row['status'] = IN_COLLECTION
    elif not any(values):
        row['status'] = OUT_OF_COLLECTION
        row['reasons'].append('PITCH_OUTSIDE_ALL_SELECTED_COLLECTIONS')
    else:
        row['reasons'].append('SELECTED_COLLECTIONS_DISAGREE')
    return row


def assess_spans(packet, spans):
    """Assess every half-open stable interval against every selected hypothesis.

    Membership is conditional on selected intent, never a claim of inferred key.
    Full coverage and unanimous inclusion are required for IN_COLLECTION. Any
    unresolved cell makes the overall result NOT_KEY_VERIFIED; otherwise any
    unanimous exclusion makes it OUT_OF_COLLECTION. Per-cell findings remain
    available when exclusions and missing evidence coexist. Validate against the
    enclosing score's origin at its boundary with validate_context(packet, origin).
    """
    if type(packet) is not dict:
        raise ValueError('Typed selected tonal context required')
    selected = validate_context(packet, packet.get('origin'))
    normalized = _validated_spans(spans)
    contexts = [(Fraction(row['start_q']), Fraction(row['end_q']), row)
                for row in selected['contexts']]
    reports = []
    for span in normalized:
        start, end = Fraction(span['start_q']), Fraction(span['end_q'])
        relevant = [(a, b, row) for a, b, row in contexts if a < end and b > start]
        boundaries = sorted({start, end} | {max(start, a) for a, _, _ in relevant}
                            | {min(end, b) for _, b, _ in relevant})
        cells = []
        for a, b in zip(boundaries, boundaries[1:]):
            context = next((row for left, right, row in relevant
                            if left <= a and b <= right), None)
            cells.append(_cell(context, a, b, Fraction(span['pitch'])))
        reports.append(dict(span, cells=cells,
                            status=_combined_status([row['status'] for row in cells]),
                            reasons=sorted({reason for row in cells for reason in row['reasons']})))
    reasons = sorted({reason for span in reports for reason in span['reasons']})
    if not reports:
        reasons.append('NO_STABLE_SPANS')
    return dict(schema=ASSESSMENT_SCHEMA, origin=deepcopy(selected['origin']),
                basis=selected['basis'], pitch_frame=selected['pitch_frame'],
                selection_reason=selected['selection_reason'],
                selection_reference=selected['selection_reference'],
                status=_combined_status([span['status'] for span in reports]),
                reasons=reasons, spans=reports)
