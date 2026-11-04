"""Resolve complete existing voice-lane proportions through the shared pulse clock.

The caller owns musical intention and saved share choices. This pure operation
does not choose notes, add attacks, learn observations or validate execution
consequences. The complete inverse must still check ties and gesture context.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import re

import musical_support_material as material
from group_rhythm_relations import relation as clock_relation, coordinate
from material_rhythm_displacement import _owners, _value, _set_integer, _add_dots
from source_rhythm_groups import TYPES

BEAT = re.compile(r'(track-(\d+)\.json#/measures/(\d+)/voices/(\d+)/beats)/(\d+)')
MAX_DOTS = 2


def _multiplier(ref, owners):
    """The captured Songsterr triplet declaration means three in two.

    Unknown declarations are not inferred from an otherwise inconsistent clock.
    Tuplet start/stop membership stays in its preceding owner without changes.
    """
    structure = owners[0]
    field = ref+'/tuplet'
    if field not in structure:
        return F(1)
    if structure[field]['type'] in ('array', 'object'):
        raise ValueError('Unsupported explicit tuplet declaration: '+field)
    value = _value(field, owners)
    if value is None or value is False or type(value) is int and value == 0:
        return F(1)
    if type(value) is int and value == 3:
        return F(2, 3)
    raise ValueError('Unsupported explicit tuplet declaration: '+field)


def _notation(duration, multiplier):
    choices = [(typ, dots) for typ in TYPES for dots in range(MAX_DOTS+1)
               if F(4, typ)*(2-F(1, 2**dots))*multiplier == duration]
    if len(choices) != 1:
        raise ValueError('No unique type/dots at the preserved tuplet ratio: '+str(duration))
    return choices[0]


def _layout(definition, expanded, ticks):
    owners = _owners(expanded)
    structure = owners[0]
    scope = definition['scope']
    spans = [coordinate(value) for value in definition['bar_spans_q']]
    if (len(spans) != scope['last_bar']-scope['first_bar']+1
            or any(value <= 0 for value in spans)):
        raise ValueError('Complete positive fixed bar frames required')
    frames = [F(0)]
    for span in spans:
        frames.append(frames[-1]+span)
    if frames[-1] != coordinate(definition['span_q']):
        raise ValueError('Bar frames differ from the material span')
    lanes = defaultdict(list)
    for slot in definition['slots']:
        ref = slot['beat_ref']
        match = BEAT.fullmatch(ref)
        if match is None:
            raise ValueError('Stable existing beat address required')
        lane, part, index, voice, ordinal = match.groups()
        part, bar, voice, ordinal = int(part), int(index)+1, int(voice), int(ordinal)
        if part not in scope['parts'] or not scope['first_bar'] <= bar <= scope['last_bar']:
            raise ValueError('Slot outside declared material scope')
        if ref not in structure or structure[ref]['type'] != 'object':
            raise ValueError('Resolved beat container authority required: '+ref)
        typ = _value(ref+'/type', owners, notation=True)
        dots = _value(ref+'/dots', owners, notation=True) if ref+'/dots' in structure else 0
        if type(typ) is not int or typ not in TYPES or type(dots) is not int or not 0 <= dots <= MAX_DOTS:
            raise ValueError('Supported integer type/dots required')
        multiplier = _multiplier(ref, owners)
        start, end = ticks[slot['from_pulse']], ticks[slot['to_pulse']]
        numerator = _value(ref+'/duration/0', owners, notation=True)
        denominator = _value(ref+'/duration/1', owners, notation=True)
        if (numerator <= 0 or denominator <= 0
                or F(4*numerator, denominator) != end-start
                or F(4, typ)*(2-F(1, 2**dots))*multiplier != end-start):
            raise ValueError('Declared notation, duration and pulse clock disagree: '+ref)
        for name in ('dotted', 'graceNote'):
            field = ref+'/'+name
            if field in structure and (structure[field]['type'] in ('object', 'array')
                    or _value(field, owners) not in (None, False, 0)):
                raise ValueError('Unresolved extra duration declaration: '+field)
        lanes[lane].append(dict(beat_ref=ref, part=part, bar=bar, voice=voice,
            ordinal=ordinal, start=start, end=end, type=typ, dots=dots,
            multiplier=multiplier, dots_present=ref+'/dots' in structure))
    present = {(rows[0]['part'], rows[0]['bar']) for rows in lanes.values()}
    expected = {(part, bar) for part in scope['parts']
                for bar in range(scope['first_bar'], scope['last_bar']+1)}
    if present != expected:
        raise ValueError('Material is missing complete part/bar clocks')
    for lane, rows in lanes.items():
        rows.sort(key=lambda row: row['ordinal'])
        left, right = frames[rows[0]['bar']-scope['first_bar']:rows[0]['bar']-scope['first_bar']+2]
        if (structure.get(lane, {}).get('type') != 'array'
                or structure[lane]['children'] != [r['beat_ref'] for r in rows]
                or [r['ordinal'] for r in rows] != list(range(len(rows)))
                or rows[0]['start'] != left or rows[-1]['end'] != right
                or any(a['end'] != b['start'] for a, b in zip(rows, rows[1:]))):
            raise ValueError('Complete contiguous existing beat lane required: '+lane)
    return lanes, frames


def _resolved_layout(definition):
    if type(definition) is not dict or definition.get('schema') != material.MATERIAL:
        raise ValueError('Resolved coordinated-support-material/1 required')
    expanded = material.expand(definition)
    clock = clock_relation(start_q='0', span_q=definition['span_q'], shares=definition['pulse_shares'])
    ticks = [F(value) for value in clock['onsets_q']]+[F(definition['span_q'])]
    return _layout(definition, expanded, ticks)


def current_lane_shares(definition):
    """Derive current choices from their sole existing pulse-clock authority."""
    lanes, _ = _resolved_layout(definition)
    return {lane: {r['beat_ref']: str((r['end']-r['start'])/(rows[-1]['end']-rows[0]['start']))
                   for r in rows} for lane, rows in lanes.items()}


def solve(definition, lane_shares):
    """Return ``(resolved_material, report)`` without mutating either input.

    ``lane_shares`` maps a beats-array source reference to a complete mapping of
    its existing beat references to canonical rational shares of that fixed bar.
    Omitted lanes retain their exact clock. Empty requests and supplied current
    shares preserve the complete definition, including optional notation fields.
    """
    if type(lane_shares) is not dict:
        raise ValueError('Explicit lane-to-complete-beat share mappings required')
    lanes, frames = _resolved_layout(definition)
    if any(type(lane) is not str or lane not in lanes for lane in lane_shares):
        raise ValueError('Unknown lane identity')
    changed_times = {}
    report = dict(changed=False, lanes=[], changed_clocks=[], notation_changes=[],
                  added_notation_refs=[], execution_validation='REQUIRED_IN_COMPLETE_INVERSE')
    for lane, rows in lanes.items():
        span = rows[-1]['end']-rows[0]['start']
        old = [str((r['end']-r['start'])/span) for r in rows]
        requested = lane_shares.get(lane)
        if lane in lane_shares:
            if type(requested) is not dict or set(requested) != {r['beat_ref'] for r in rows}:
                raise ValueError('Every existing beat in a selected lane needs exactly one share')
            shares = [requested[r['beat_ref']] for r in rows]
            if any(coordinate(value) <= 0 for value in shares) or sum(map(F, shares), F(0)) != 1:
                raise ValueError('Positive shares must sum exactly to one')
        else:
            shares = old
        report['lanes'].append(dict(lane_ref=lane, selected=lane in lane_shares,
            beat_refs=[r['beat_ref'] for r in rows], before_shares=old, after_shares=shares))
        if shares == old:
            for row in rows:
                changed_times[row['beat_ref']] = (row['start'], row['end'])
            continue
        solved = clock_relation(start_q=str(rows[0]['start']), span_q=str(span), shares=shares)
        for row, onset, duration in zip(rows, solved['onsets_q'], solved['durations_q']):
            start, length = F(onset), F(duration)
            changed_times[row['beat_ref']] = (start, start+length)
            if (start, start+length) != (row['start'], row['end']):
                report['changed_clocks'].append(dict(beat_ref=row['beat_ref'],
                    before=dict(onset_q=str(row['start']), duration_q=str(row['end']-row['start'])),
                    after=dict(onset_q=onset, duration_q=duration)))
    result = deepcopy(definition)
    if not report['changed_clocks']:
        return result, report
    boundaries = sorted(set(frames)|{time for pair in changed_times.values() for time in pair})
    solved = clock_relation(start_q='0', span_q=definition['span_q'],
                            durations_q=[str(b-a) for a, b in zip(boundaries, boundaries[1:])])
    result['pulse_shares'] = solved['shares']
    index = {time: i for i, time in enumerate(boundaries)}
    for slot in result['slots']:
        start, end = changed_times[slot['beat_ref']]
        slot['from_pulse'], slot['to_pulse'] = index[start], index[end]
    for rows in lanes.values():
        for row in rows:
            ref = row['beat_ref']
            start, end = changed_times[ref]
            if end-start == row['end']-row['start']:
                continue
            typ, dots = _notation(end-start, row['multiplier'])
            _set_integer(result['lower_tier'], ref+'/type', typ)
            if row['dots_present']:
                _set_integer(result['lower_tier'], ref+'/dots', dots)
            elif dots:
                report['added_notation_refs'].append(_add_dots(result['lower_tier'], ref, dots))
            report['notation_changes'].append(dict(beat_ref=ref,
                before=dict(type=row['type'], dots=row['dots'], dots_present=row['dots_present']),
                after=dict(type=typ, dots=dots, dots_present=row['dots_present'] or bool(dots)),
                tuplet_multiplier=str(row['multiplier'])))
    # Check the resulting notation and incidence using the existing inverse.
    _layout(result, material.expand(result), boundaries)
    report['changed'] = True
    return result, report
