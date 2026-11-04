"""Same-span repeated attacks, with symbolic inheritance from each current parent.

This module plans a typed-fragment expansion; it never rebuilds source data or
chooses pitches. The caller stores a subdivision factor and realizes each child
through its parent's current pitch/contact relationships. Existing evidence is
not changed or copied into a new observation pool.
"""
from collections import defaultdict
from fractions import Fraction as F
import re

from source_rhythm_groups import TYPES
from technique_observation_relations import scalar_relation


SCHEMA = 'same-span-material-subdivision/1'
BEAT = re.compile(r'track-(\d+)\.json#/measures/(\d+)/voices/(\d+)/beats/(\d+)')
EVENT = re.compile(r'event:([^:]+):(\d+):(\d+):(\d+):(\d+):(\d+)')
_SIMPLE_BEAT = {'palmMute', 'velocity', 'rest'}
_SIMPLE_NOTE = {'string', 'fret', 'dead', 'ghost', 'velocity', 'accentuated', 'staccato', 'rest'}
_NOTATION = {'duration', 'type', 'dots'}
_BOUNDARIES = {'beamStart': 'first', 'beamStop': 'last'}
_BEAT_EXECUTION = {'graceNote', 'tuplet', 'tupletStart', 'tupletStop', 'dotted',
                   'letRing', 'tapping', 'brushStroke', 'arpeggio', 'downStroke',
                   'upStroke', 'pickStroke', 'fadeIn', 'tremoloBar', 'vibrato',
                   'wideVibrato', 'leftHandVibrato', 'vibratoWithTremoloBar',
                   'tremolo', 'harmonic', 'gradualVelocity', 'wahwah', 'golpe',
                   'sustainPedal', 'slapping', 'popping', 'downArpeggio', 'upArpeggio'}
_NOTE_EXECUTION = {'tie', 'hp', 'slide', 'bend', 'harmonic', 'harmonicFret',
                   'tremolo', 'vibrato', 'wideVibrato', 'leftHandVibrato', 'pickScrape', 'trill'}


def _rational(value):
    if type(value) is not str or str(F(value)) != value:
        raise ValueError('Canonical rational string required')
    return F(value)


def _factor(value):
    if type(value) is not int or value < 1 or value & (value-1):
        raise ValueError('Positive power-of-two subdivision factor required')
    return value


def relation(*, start_q=None, span_q=None, children=None, factor=1):
    """Solve/recover equal subdivisions of a closed rational span.

    One direction needs start/span, the other needs contiguous equal children.
    Supplying both verifies the same equation. No rounding or duration floor.
    """
    factor = _factor(factor)
    if children is not None:
        if type(children) is not list or len(children) != factor:
            raise ValueError('One exact span per declared child required')
        pairs = []
        for child in children:
            if type(child) is not dict or set(child) != {'onset_q', 'duration_q'}:
                raise ValueError('Closed child onset/duration required')
            pairs.append((_rational(child['onset_q']), _rational(child['duration_q'])))
        if any(d <= 0 or d != pairs[0][1] for _, d in pairs):
            raise ValueError('Equal positive child spans required')
        if any(b[0] != a[0]+a[1] for a, b in zip(pairs, pairs[1:])):
            raise ValueError('Children must be contiguous and ordered')
        recovered_start, recovered_span = pairs[0][0], sum((d for _, d in pairs), F(0))
        if start_q is not None and _rational(start_q) != recovered_start:
            raise ValueError('Parent/child start conflict')
        if span_q is not None and _rational(span_q) != recovered_span:
            raise ValueError('Parent/child duration conflict')
        start_q, span_q = str(recovered_start), str(recovered_span)
    if start_q is None or span_q is None:
        raise ValueError('Parent span or complete children required')
    start, span = _rational(start_q), _rational(span_q)
    if start < 0 or span <= 0:
        raise ValueError('Nonnegative onset and positive span required')
    length = span/factor
    return dict(start_q=str(start), span_q=str(span), factor=factor,
                children=[dict(onset_q=str(start+i*length), duration_q=str(length)) for i in range(factor)])


def _index(rows, key):
    if type(rows) is not list:
        raise ValueError('Explicit fragment rows required')
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate fragment authority')
    return result


def _notation(span):
    matches = [(typ, dots) for typ in TYPES for dots in range(3)
               if F(4, typ)*(2-F(1, 2**dots)) == span]
    if len(matches) != 1:
        raise ValueError('No unique supported child notation')
    typ, dots = matches[0]
    return dict(type=typ, dots=dots)


def _field_values(fragment):
    structure = _index(fragment['source_structure'], 'id')
    choices = _index(fragment['source_choices'], 'fact_ref')
    for group in fragment['technique_declarations']:
        for row in group['structure']:
            if row['id'] in structure:
                raise ValueError('Duplicate source/technique field owner')
            structure[row['id']] = row
        for row in group['parameters']:
            if row['fact_ref'] in choices:
                raise ValueError('Duplicate source/technique value owner')
            choices[row['fact_ref']] = row
    def value(ref):
        row = structure.get(ref)
        if row is None:
            raise ValueError('Missing source field: '+ref)
        if row['type'] in ('array', 'object'):
            return True  # a structured execution declaration requires its own semantics
        if ref not in choices or 'parameter' not in choices[ref]:
            raise ValueError('Unresolved field ownership: '+ref)
        return scalar_relation(row['type'], parameter=choices[ref]['parameter'])
    return structure, value


def _fields(root, structure):
    row = structure[root]
    if row['type'] != 'object':
        raise ValueError('Explicit object owner required')
    children = row['children']
    if len(set(children)) != len(children):
        raise ValueError('Duplicate object membership')
    if any(c not in structure or structure[c]['parent'] != root for c in children):
        raise ValueError('Broken field membership')
    return {structure[c]['slot']: c for c in children}


def inventory(fragment, observed_execution=()):
    """Every beat stays in the inventory, including unsupported and silent units."""
    structure, value = _field_values(fragment)
    groups = _index(fragment['coattacks'], 'id')
    bybeat = {}
    for group in groups.values():
        members = group['members']
        if not members:
            raise ValueError('Empty coattack')
        locations = {(m['bar'], m['voice'], m['beat']) for m in members}
        if len(locations) != 1 or len({m['id'] for m in members}) != len(members):
            raise ValueError('Complete unique single-beat coattack required')
        bar, voice, beat = next(iter(locations))
        ref = f'track-{group["part_id"]}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}'
        if ref in bybeat:
            raise ValueError('Duplicate beat coattack')
        bybeat[ref] = group
    lanes = defaultdict(list)
    for ref in structure:
        match = BEAT.fullmatch(ref)
        if match:
            p, mi, vi, bi = map(int, match.groups())
            lanes[p, mi, vi].append((bi, ref))
    if set(bybeat)-set(ref for rows in lanes.values() for _, ref in rows):
        raise ValueError('Coattack without beat owner')
    units = []
    for lane, rows in sorted(lanes.items()):
        rows.sort()
        if [i for i, _ in rows] != list(range(len(rows))):
            raise ValueError('Complete bar beat addresses required')
        relative = F(0); lane_units = []; bar_start = None
        for ordinal, ref in rows:
            fields = _fields(ref, structure)
            duration = fields.get('duration')
            if duration is None or structure[duration]['type'] != 'array':
                raise ValueError('Explicit duration pair required')
            nums = structure[duration]['children']
            if nums != [duration+'/0', duration+'/1']:
                raise ValueError('Exact two-component duration required')
            numerator, denominator = value(nums[0]), value(nums[1])
            if type(numerator) is not int or type(denominator) is not int or numerator <= 0 or denominator <= 0:
                raise ValueError('Positive rational duration required')
            span = F(4*numerator, denominator)
            reasons = []; group = bybeat.get(ref); members = [] if group is None else group['members']
            if group is None:
                reasons.append('REST_OR_UNBOUND_BEAT')
            else:
                if group['timing_uncertain']:
                    reasons.append('UNCERTAIN_CLOCK')
                onset = _rational(group['onset_q'])
                if bar_start is None:
                    bar_start = onset-relative
                if onset != bar_start+relative or any(_rational(m['duration_q']) != span for m in members):
                    raise ValueError('Current coattack and source clock disagree')
            policies = {'duration': 'child_clock', 'type': 'child_notation', 'dots': 'child_notation'}
            for name, field in fields.items():
                if name == 'notes' or name in _NOTATION:
                    continue
                if name in _BOUNDARIES:
                    if type(value(field)) is not bool:
                        reasons.append('UNSUPPORTED_BEAM_BOUNDARY:'+name)
                    policies[name] = _BOUNDARIES[name]
                elif name in ('beam', 'beamMode'):
                    if value(field) not in (False, None, 0):
                        reasons.append('UNSUPPORTED_BEAM_DIRECTIVE:'+name)
                    policies[name] = 'each'
                elif name in _SIMPLE_BEAT:
                    if name == 'rest' and value(field):
                        reasons.append('REST_BEAT')
                    policies[name] = 'each'
                elif name in _BEAT_EXECUTION:
                    if value(field) not in (False, None, 0):
                        reasons.append('UNSUPPORTED_EXECUTION:'+name)
                    policies[name] = 'each'
                elif name in ('text', 'chord'):
                    policies[name] = 'first'
                else:
                    reasons.append('UNSUPPORTED_BEAT_FIELD:'+str(name))
            note_root = fields.get('notes')
            if note_root is None or structure[note_root]['type'] != 'array':
                raise ValueError('Explicit complete note membership required')
            note_fields = []
            for ni, note_ref in enumerate(structure[note_root]['children']):
                if note_ref != note_root+'/'+str(ni):
                    raise ValueError('Contiguous original note addresses required')
                own = _fields(note_ref, structure); note_fields.append(list(own))
                for name, field in own.items():
                    if name in _SIMPLE_NOTE:
                        if name == 'rest' and value(field):
                            reasons.append('REST_MEMBER')
                    elif name in _NOTE_EXECUTION:
                        if value(field) not in (False, None, 0):
                            reasons.append('UNSUPPORTED_EXECUTION:'+name)
                    else:
                        reasons.append('UNSUPPORTED_NOTE_FIELD:'+str(name))
            if group is not None:
                if len(members) != len(note_fields) or {m['note'] for m in members} != set(range(len(note_fields))):
                    reasons.append('INCOMPLETE_COATTACK')
                ids = {m['id'] for m in members}
                for record in observed_execution:
                    linked = set(record.get('member_refs', [])) | set(record.get('tied_member_refs', []))
                    linked.update(record[k] for k in ('origin_ref', 'destination_ref', 'candidate_destination_ref') if record.get(k) is not None)
                    if ids & linked or record.get('source_fact_ref', '').startswith(ref+'/'):
                        reasons.append('EXISTING_EXECUTION_DEPENDENCY')
            try:
                notation = _notation(span/2)
                if 'type' in fields:
                    typ = value(fields['type']); dots = value(fields['dots']) if 'dots' in fields else 0
                    if type(typ) is not int or type(dots) is not int or typ not in TYPES or dots not in (0, 1, 2):
                        reasons.append('UNSUPPORTED_PARENT_NOTATION')
                    elif F(4, typ)*(2-F(1, 2**dots)) != span:
                        reasons.append('CONFLICTING_PARENT_NOTATION')
            except ValueError:
                notation = None; reasons.append('UNREPRESENTABLE_CHILD_NOTATION')
            lane_units.append(dict(beat_ref=ref, coattack_ref=None if group is None else group['id'],
                part_id=lane[0], bar=lane[1]+1, voice=lane[2], beat=ordinal,
                relative_onset_q=str(relative), duration_q=str(span),
                member_refs=[m['id'] for m in members], member_note_ordinals=[m['note'] for m in members],
                beat_field_policy=policies, note_fields=note_fields,
                split_supported=not reasons, blocked_reasons=sorted(set(reasons)), half_notation=notation))
            relative += span
        for unit in lane_units:
            unit['onset_q'] = None if bar_start is None else str(bar_start+F(unit['relative_onset_q']))
            unit['bar_span_q'] = str(relative)
        units.extend(lane_units)
    return units


def _child_identity(parent, fraction):
    return parent if fraction == 0 else parent+'@subdivision:'+str(fraction)


def plan(fragment, counts, *, observed_execution=()):
    """Return an atomic symbolic plan; factors are 1,2,4,..., never percentages.

    A request may use a stable coattack ID or an exact beat reference (including
    an unsupported/rest beat, so failures cannot disappear from accounting).
    Factor1 preserves the current parent; a later factor4 retains factor2's
    0 and 1/2 logical children and inserts 1/4 and 3/4 children.
    """
    if type(counts) is not dict or any(type(k) is not str for k in counts):
        raise ValueError('Explicit subdivision factors by stable identity required')
    units = inventory(fragment, observed_execution)
    lookup = {}
    for unit in units:
        lookup[unit['beat_ref']] = unit
        if unit['coattack_ref'] is not None:
            if unit['coattack_ref'] in lookup:
                raise ValueError('Ambiguous beat/coattack identity')
            lookup[unit['coattack_ref']] = unit
    unknown = set(counts)-set(lookup)
    if unknown:
        raise ValueError('Unknown subdivision unit: '+','.join(sorted(unknown)))
    factors = {}; blocked = []
    for ref, factor in counts.items():
        factor = _factor(factor); unit = lookup[ref]; beat_ref = unit['beat_ref']
        if beat_ref in factors:
            raise ValueError('Same unit requested twice through different identities')
        factors[beat_ref] = factor
        reasons = list(unit['blocked_reasons']) if factor > 1 else []
        if factor > 1:
            try:
                _notation(F(unit['duration_q'])/factor)
            except ValueError:
                reasons.append('UNREPRESENTABLE_CHILD_NOTATION')
        if reasons:
            blocked.append(dict(request=ref, beat_ref=beat_ref, factor=factor, reasons=sorted(set(reasons))))
    if blocked:
        # The full inventory remains available independently. No partial plan
        # is returned and the caller's complete input is untouched.
        error = ValueError('SUBDIVISION_BLOCKED: '+repr(blocked))
        error.blocked_units = blocked
        error.inventory = units
        raise error
    next_beat = defaultdict(int); beats = []; events = []; groups = []
    for unit in units:
        parent = unit['beat_ref']; factor = factors.get(parent, 1)
        lane = (unit['part_id'], unit['bar'], unit['voice'])
        absolute = unit['onset_q']
        solved = relation(start_q=absolute or unit['relative_onset_q'], span_q=unit['duration_q'], factor=factor)
        children = []
        for i, timing in enumerate(solved['children']):
            fraction = F(i, factor); ordinal = next_beat[lane]; next_beat[lane] += 1
            address = parent.rsplit('/', 1)[0]+'/'+str(ordinal)
            child = dict(identity=_child_identity(parent, fraction), parent_beat_ref=parent,
                         beat_ref=address, relative_parent_offset=str(fraction),
                         onset_q=timing['onset_q'] if absolute is not None else None,
                         relative_onset_q=str(F(unit['relative_onset_q'])+fraction*F(unit['duration_q'])),
                         duration_q=timing['duration_q'], factor=factor,
                         notation=None if factor == 1 else _notation(F(timing['duration_q'])),
                         copy_beat_fields=[field for field, policy in unit['beat_field_policy'].items()
                                           if policy == 'each' or policy == 'first' and i == 0 or policy == 'last' and i == factor-1])
            if factor == 1:
                child['copy_beat_fields'] = None  # entire unchanged beat; no metadata filtering
            children.append(child)
            if unit['coattack_ref'] is not None:
                group_identity = _child_identity(unit['coattack_ref'], fraction)
                groups.append(dict(identity=group_identity, parent_coattack_ref=unit['coattack_ref'],
                                   beat_ref=address, relative_parent_offset=str(fraction),
                                   member_parent_refs=list(unit['member_refs']),
                                   inherit_pitch_contact_from=unit['coattack_ref']))
            for member, note in zip(unit['member_refs'], unit['member_note_ordinals']):
                match = EVENT.fullmatch(member)
                if match is None:
                    raise ValueError('Explicit original event address required')
                song, p, bar, voice, oldbeat, oldnote = match.groups()
                if tuple(map(int, (p, bar, voice, oldbeat, oldnote))) != (*lane, unit['beat'], note):
                    raise ValueError('Member address conflicts with parent coattack')
                events.append(dict(identity=_child_identity(member, fraction), parent_occurrence=member,
                                   current_address=f'event:{song}:{p}:{bar}:{voice}:{ordinal}:{note}',
                                   parent_coattack_ref=unit['coattack_ref'], coattack_identity=group_identity,
                                   relative_parent_offset=str(fraction), inherit_pitch_contact_from=member,
                                   inherited_note_fields=list(unit['note_fields'][note])))
        beats.append(dict(parent_beat_ref=parent, parent_coattack_ref=unit['coattack_ref'],
                          parent_duration_q=unit['duration_q'], factor=factor, children=children))
    if len({e['current_address'] for e in events}) != len(events):
        raise ValueError('Noninjective child occurrence mapping')
    return dict(schema=SCHEMA, requested_factors=dict(counts), units=units,
                beat_map=beats, event_map=events, coattack_map=groups,
                original_evidence_action='unchanged', child_pitch_policy='inherit_same_current_parent',
                unselected_beat_units=sum(b['factor'] == 1 for b in beats),
                changed_beat_units=sum(b['factor'] > 1 for b in beats))


def plan_maps(plans):
    """Flatten disjoint complete-bar plans for the existing typed projection."""
    if type(plans) is not list:
        raise ValueError('Explicit subdivision plan list required')
    beats = {}; events = {}; spans = {}; used_bars = set(); output_beats = set(); output_events = set()
    for item in plans:
        if type(item) is not dict or item.get('schema') != SCHEMA:
            raise ValueError('Same-span subdivision plan required')
        current_bars = set(); child_spans = {}
        for row in item['beat_map']:
            old = row['parent_beat_ref']; match = BEAT.fullmatch(old)
            if match is None or old in beats:
                raise ValueError('Duplicate or invalid original beat address')
            part, mi, voice, ordinal = map(int, match.groups()); current_bars.add((part, mi))
            factor = _factor(row['factor']); children = row['children']
            if len(children) != factor:
                raise ValueError('Incomplete declared child membership')
            local = relation(children=[dict(onset_q=c['relative_onset_q'], duration_q=c['duration_q'])
                                       for c in children], factor=factor)
            if local['span_q'] != row['parent_duration_q']:
                raise ValueError('Child spans do not recover parent duration')
            addresses = []
            for child in children:
                address = child['beat_ref']; newmatch = BEAT.fullmatch(address)
                if newmatch is None or tuple(map(int, newmatch.groups()[:3])) != (part, mi, voice):
                    raise ValueError('Subdivision child moved outside its original bar/voice')
                if address in output_beats:
                    raise ValueError('Noninjective child beat mapping')
                output_beats.add(address); addresses.append(address)
                child_spans[address] = dict(onset_q=child['onset_q'], duration_q=child['duration_q'])
            beats[old] = addresses
        if used_bars & current_bars:
            raise ValueError('Overlapping complete-bar subdivision plans')
        used_bars.update(current_bars)
        grouped = defaultdict(list)
        for row in item['event_map']:
            grouped[row['parent_occurrence']].append(row)
        for old, rows in grouped.items():
            if old in events or EVENT.fullmatch(old) is None:
                raise ValueError('Duplicate or invalid original event address')
            addresses = []; clocks = []
            for row in rows:
                address = row['current_address']; match = EVENT.fullmatch(address)
                if match is None or address in output_events:
                    raise ValueError('Noninjective child event mapping')
                song, part, bar, voice, beat, note = match.groups()
                beat_ref = f'track-{part}.json#/measures/{int(bar)-1}/voices/{voice}/beats/{beat}'
                if beat_ref not in child_spans or child_spans[beat_ref]['onset_q'] is None:
                    raise ValueError('Missing exact child event clock')
                output_events.add(address); addresses.append(address); clocks.append(dict(child_spans[beat_ref]))
            events[old] = addresses; spans[old] = clocks
    return dict(beats=beats, events=events, spans=spans)
