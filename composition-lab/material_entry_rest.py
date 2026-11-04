"""A generated prefix rest followed by the same current written occurrences.

Run AFTER subdivision. Current attack identity maps one-to-one; the generated
rest has no original observation or attack lineage. Requests, not a saved note
stream, own this relationship. Full inverse execution checks remain mandatory.
"""
from copy import deepcopy
from fractions import Fraction as F
from math import gcd
import re

import musical_support_material as material
from group_rhythm_relations import coordinate, relation as clock_relation
from material_slot_clock import _notation, MAX_DOTS
from source_rhythm_groups import TYPES
from source_observation_evidence import digest
from technique_observation_relations import scalar_relation, realize as realize_techniques

SCHEMA = 'material-entry-rest-plan/1'
POLICY = 'existing_beat_marks_follow_their_beat;track_automation_clock_fixed'
LANE = re.compile(r'track-(\d+)\.json#/measures/(\d+)/voices/(\d+)/beats')


def _facts(fragment):
    structure = {r['id']: r for r in fragment['source_structure']}
    choices = {r['fact_ref']: r for r in fragment['source_choices']}
    if len(structure) != len(fragment['source_structure']) or len(choices) != len(fragment['source_choices']):
        raise ValueError('Duplicate current authority')
    values = {ref: scalar_relation(structure[ref]['type'], parameter=r['parameter'])
              for ref, r in choices.items()}
    for row in realize_techniques(dict(schema='technique-observation-relations/1',
                                     groups=fragment['technique_declarations'], unsupported=[])):
        if row['id'] in structure:
            raise ValueError('Duplicate technique authority')
        structure[row['id']] = row
        if 'value' in row:
            values[row['id']] = row['value']
    return structure, values


def _layout(fragment, lane, *, facts=None):
    match = LANE.fullmatch(lane)
    if match is None:
        raise ValueError('Exact current lane reference required')
    part, index, voice = map(int, match.groups())
    structure, values = _facts(fragment) if facts is None else facts
    row = structure.get(lane)
    if row is None or row['type'] != 'array' or not row['children']:
        raise ValueError('Complete nonempty current lane required')
    refs = row['children']
    if refs != [lane+'/'+str(i) for i in range(len(refs))]:
        raise ValueError('Complete contiguous current beat identities required')
    groups = {}
    for group in fragment['coattacks']:
        if group['part_id'] == part and group['bar'] == index+1:
            members = group['members']
            if members[0]['voice'] != voice:
                continue
            beat = lane+'/'+str(members[0]['beat'])
            if beat in groups or any(m['beat'] != members[0]['beat'] or m['voice'] != voice for m in members):
                raise ValueError('One complete current coattack per beat required')
            groups[beat] = group
    # A rest is a timed member of the same lane. Recover its bar origin from
    # the first subsequent coattack and the preceding written durations.
    first = next((ref for ref in refs if ref in groups), None)
    if first is None:
        raise ValueError('Changed all-rest lane needs an explicit bar clock')
    prefix = sum((F(4*values[ref+'/duration/0'], values[ref+'/duration/1'])
                  for ref in refs[:refs.index(first)]), F(0))
    start = coordinate(groups[first]['onset_q'])-prefix
    pos = start
    rows = []
    for ref in refs:
        for field in ('duration/0', 'duration/1', 'type'):
            if type(values.get(ref+'/'+field)) is not int:
                raise ValueError('Explicit current integer notation required')
        n, d, typ = (values[ref+'/'+field] for field in ('duration/0', 'duration/1', 'type'))
        dots = values.get(ref+'/dots', 0)
        if n <= 0 or d <= 0 or typ not in TYPES or type(dots) is not int or not 0 <= dots <= MAX_DOTS:
            raise ValueError('Valid current duration/type/dots required')
        tuplet = values.get(ref+'/tuplet')
        if tuplet is None or tuplet is False or type(tuplet) is int and tuplet == 0:
            multiplier = F(1)
        elif type(tuplet) is int and tuplet == 3:
            multiplier = F(2, 3)
        else:
            raise ValueError('Unknown current tuplet declaration')
        duration = F(4*n, d)
        if F(4, typ)*(2-F(1, 2**dots))*multiplier != duration:
            raise ValueError('Current notation and duration disagree')
        if any(values.get(ref+'/'+f) not in (None, False, 0) for f in ('graceNote', 'dotted')):
            raise ValueError('Unresolved extra duration declaration')
        if any(key.startswith(ref+'/') and ('tempo' in key.split('/') or 'automation' in key.split('/')) for key in structure):
            raise ValueError('ENTRY_REST_BEAT_TEMPO_POLICY_REQUIRED')
        group = groups.get(ref)
        if group is not None and (coordinate(group['onset_q']) != pos or any(
                coordinate(m['duration_q']) != duration for m in group['members'])):
            raise ValueError('Current coattack and complete lane clock disagree')
        rows.append(dict(beat_ref=ref, duration=duration, onset=pos, multiplier=multiplier,
                         fraction_scale=gcd(n, d),
                         incoming_tie=ref == refs[0] and group is not None and any(values.get(ref+'/notes/'+str(m['note'])+'/tie') not in (None, False, 0)
                                                            for m in group['members']),
                         group=group))
        pos += duration
    return rows, start, pos-start


def current_lane_shares(fragment, lane_refs, *, facts=None):
    """Current descendant shares, derived without storing them in an upper use."""
    structure, values = _facts(fragment) if facts is None else facts
    result = {}
    for lane in lane_refs:
        if type(lane) is not str or LANE.fullmatch(lane) is None or lane not in structure:
            raise ValueError('Exact current lane reference required')
        refs = structure[lane].get('children', [])
        if not refs or refs != [lane+'/'+str(i) for i in range(len(refs))]:
            raise ValueError('Complete contiguous current lane required')
        durations = []
        for ref in refs:
            n, d = values.get(ref+'/duration/0'), values.get(ref+'/duration/1')
            if type(n) is not int or type(d) is not int or n <= 0 or d <= 0:
                raise ValueError('Positive resolved current duration required')
            durations.append(F(n, d))
        span = sum(durations, F(0))
        result[lane] = {ref: str(duration/span) for ref, duration in zip(refs, durations)}
    return result


def plan(fragment, lane_requests):
    """Plan from current resolved typed owners, after any existing subdivision.

    Each lane request has entry_share and complete content_shares keyed by its
    current beat references. Existing content keeps its order and membership.
    """
    if type(lane_requests) is not dict:
        raise ValueError('Explicit lane requests required')
    beats, events, spans, notation, rests, clocks = {}, {}, {}, {}, [], []
    clock_evidence = []
    facts = _facts(fragment)
    for lane, request in lane_requests.items():
        if type(lane) is not str or type(request) is not dict or set(request) != {'entry_share', 'content_shares'}:
            raise ValueError('Closed lane entry/content request required')
        entry = coordinate(request['entry_share'])
        shares = request['content_shares']
        current = current_lane_shares(fragment, [lane], facts=facts)[lane]
        if type(shares) is not dict or set(shares) != set(current):
            raise ValueError('Complete current content shares required')
        weights = [coordinate(shares[ref]) for ref in current]
        if any(s <= 0 for s in weights) or sum(weights, F(0)) != 1 or not 0 <= entry < 1:
            raise ValueError('Positive content shares and entry in [0,1) required')
        if not entry and shares == current:
            continue
        rows, start, span = _layout(fragment, lane, facts=facts)
        if entry and rows[0]['group'] is None:
            raise ValueError('Existing entry rest must be retimed through its own content share')
        if entry and rows[0]['incoming_tie']:
            raise ValueError('ENTRY_REST_SEPARATES_INCOMING_TIE')
        solved = clock_relation(start_q=str(start), span_q=str(span),
            shares=([str(entry)] if entry else [])+[str((1-entry)*w) for w in weights])
        offset = 1 if entry else 0
        if entry:
            rest_type, rest_dots = _notation(F(solved['durations_q'][0]), F(1))
            rest_duration = F(solved['durations_q'][0])/4
            rests.append(dict(identity='entry-rest:'+lane, beat_ref=lane+'/0', onset_q=str(start),
                duration_q=solved['durations_q'][0], duration=[rest_duration.numerator, rest_duration.denominator],
                type=rest_type, dots=rest_dots))
        clock_evidence.append(dict(lane_ref=lane, start_q=str(start), span_q=str(span),
            durations=[str(r['duration']) for r in rows],
            occurrences=[[m['id'] for m in r['group']['members']] if r['group'] else [] for r in rows]))
        for i, row in enumerate(rows, offset):
            old = row['beat_ref']; new = lane+'/'+str(i)
            beats[old] = [new]
            duration = F(solved['durations_q'][i])
            typ, dots = _notation(duration, row['multiplier'])
            fraction = duration/4
            notation[new] = dict(type=typ, dots=dots,
                duration=[fraction.numerator*row['fraction_scale'], fraction.denominator*row['fraction_scale']])
            clocks.append(dict(before_beat_ref=old, after_beat_ref=new,
                before=dict(onset_q=str(row['onset']), duration_q=str(row['duration'])),
                after=dict(onset_q=solved['onsets_q'][i], duration_q=solved['durations_q'][i])))
            if row['group'] is not None:
                for member in row['group']['members']:
                    old_event = member['id']; address = old_event.split(':'); address[5] = str(i)
                    events[old_event] = [':'.join(address)]
                    spans[old_event] = [dict(onset_q=solved['onsets_q'][i], duration_q=solved['durations_q'][i])]
    return dict(schema=SCHEMA, lane_requests=deepcopy(lane_requests),
                maps=dict(beats=beats, events=events, spans=spans), notation=notation, generated_rests=rests,
                clock_changes=clocks, input_clock_sha256=digest(clock_evidence), beat_mark_policy=POLICY)


def _current_fragment(t2):
    fragment = deepcopy(material._arrays(t2))
    seen = {r['id'] for r in fragment['source_structure']}
    for row in material.expression_rows(t2):
        if row['id'] in seen:
            raise ValueError('Duplicate current expression authority')
        fragment['source_structure'].append({k:deepcopy(v) for k,v in row.items() if k != 'value'})
        if 'value' in row:
            fragment['source_choices'].append(dict(fact_ref=row['id'], owner='transient_expression',
                parameter=scalar_relation(row['type'], source=row['value'])))
        seen.add(row['id'])
    return fragment


def _append_rest(t2, rest):
    """Realize the generated rest's typed grammar, with no pitched event owner."""
    from connected_tier2 import owner_kind
    fragment = material._arrays(t2)
    ref = rest['beat_ref']; document, pointer = ref.split('#', 1)
    lane = ref.rsplit('/', 1)[0]
    parent = next(r for r in fragment['source_structure'] if r['id'] == lane)
    if ref in parent['children']:
        raise ValueError('Generated rest aliases an existing beat')
    parent['children'].insert(0, ref)
    def add(suffix, typ, value=None, children=None):
        ident = ref+suffix
        row = dict(id=ident, document=document, pointer=pointer+suffix,
                   parent=ident.rsplit('/', 1)[0], slot=ident.rsplit('/', 1)[1], type=typ)
        if suffix in ('', '/duration/0', '/duration/1', '/notes/0'):
            row['slot'] = int(row['slot'])
        if children is not None:
            row['children'] = [ref+c for c in children]
        fragment['source_structure'].append(row)
        owner = 'source_structure' if children is not None else owner_kind(row)
        fragment['coverage'].append(dict(fact_ref=ident, owner=owner))
        if children is None:
            fragment['source_choices'].append(dict(fact_ref=ident, owner=owner,
                parameter=scalar_relation(typ, source=value)))
    fields = ['/duration', '/type', '/rest', '/notes']+(['/dots'] if rest['dots'] else [])
    add('', 'object', children=fields)
    add('/duration', 'array', children=['/duration/0', '/duration/1'])
    for i, value in enumerate(rest['duration']):add('/duration/'+str(i), 'integer', value)
    add('/type', 'integer', rest['type']); add('/rest', 'boolean', True)
    add('/notes', 'array', children=['/notes/0']); add('/notes/0', 'object', children=['/notes/0/rest'])
    add('/notes/0/rest', 'boolean', True)
    if rest['dots']:add('/dots', 'integer', rest['dots'])


def _write_notation(t2, notation):
    from material_rhythm_displacement import _set_integer, _add_dots
    fragment = material._arrays(t2)
    for ref, values in notation.items():
        for field, value in (('type', values['type']), ('duration/0', values['duration'][0]), ('duration/1', values['duration'][1])):
            _set_integer(fragment, ref+'/'+field, value)
        if any(r['id'] == ref+'/dots' for r in fragment['source_structure']):
            _set_integer(fragment, ref+'/dots', values['dots'])
        elif values['dots']:
            # Optional beat expression owns its container; temporarily supply
            # that same object to the established dots insertion helper.
            container = next((g['beat_structure'] for g in t2['owned_parameters'].get('optional_beat_palm_mutes', {}).get('groups', [])
                              if g['beat_structure']['id'] == ref), None)
            if container is not None:fragment['source_structure'].append(container)
            _add_dots(fragment, ref, values['dots'])
            if container is not None:fragment['source_structure'].remove(container)


def project(t2, plans, *, execution_records=None, carry_plan=None, required_pairs=None, coherent_group_refs=None):
    """Validate plans against CURRENT owners, then project and insert atomically."""
    from material_subdivision_projection import _project_owners
    if type(plans) is not list:
        raise ValueError('Explicit entry-rest plan list required')
    if (required_pairs or coherent_group_refs) and carry_plan is None:
        raise ValueError('Required contact pairs need their explicit carry plan')
    fragment = _current_fragment(t2)
    maps = dict(beats={}, events={}, spans={}); notation = {}; rests = []; clocks = []; lanes = set()
    for item in plans:
        if type(item) is not dict or item.get('schema') != SCHEMA or 'lane_requests' not in item:
            raise ValueError('Closed entry-rest relationship plan required')
        if item != plan(fragment, item['lane_requests']):
            raise ValueError('Entry plan differs from current owners or its declared equation')
        if lanes & set(item['lane_requests']):
            raise ValueError('Overlapping entry-rest lane owners')
        lanes.update(item['lane_requests'])
        for key in maps:maps[key].update(deepcopy(item['maps'][key]))
        notation.update(deepcopy(item['notation'])); rests.extend(deepcopy(item['generated_rests']))
        clocks.extend(deepcopy(item['clock_changes']))
    if not maps['beats']:
        if carry_plan is not None:
            from material_entry_carry import plan as plan_carry
            if carry_plan != plan_carry(t2, dict(maps=maps, generated_rests=rests), execution_records,
                    required_pairs=required_pairs, coherent_group_refs=coherent_group_refs):
                raise ValueError('Carry plan differs from current owners')
        return deepcopy(t2), dict(changed=False, maps=maps, generated_rests=[], clock_changes=[], beat_mark_policy=POLICY)
    carried = set()
    if carry_plan is not None:
        from material_entry_carry import plan as plan_carry
        if carry_plan != plan_carry(t2, dict(maps=maps, generated_rests=rests), execution_records,
                required_pairs=required_pairs, coherent_group_refs=coherent_group_refs):
            raise ValueError('Carry plan differs from current owners')
        carried = {m['before_destination_ref'] for c in carry_plan['carries'] for m in c['members']}
    # A new gap cannot silently sever an existing held-note dependency.
    rest_lanes = {r['beat_ref'].rsplit('/', 1)[0] for r in rests}
    first = set()
    for old in maps['events']:
        _, song, part, bar, voice, beat, member = old.split(':')
        lane = f'track-{part}.json#/measures/{int(bar)-1}/voices/{voice}/beats'
        if beat == '0' and lane in rest_lanes:first.add(old)
    # Reuse the caller's existing current execution snapshot. Do not invent a
    # successor search or permit a missing snapshot to certify a continuous
    # gesture merely because its source flag survives the address projection.
    touched_parts = {int(ref.split(':')[2]) for ref in first}
    _, values = _facts(fragment)
    relevant_gestures = any(key.endswith(('/slide', '/hp')) and value not in (None, False, 0)
        and int(key.split('.json#', 1)[0].split('-')[1]) in touched_parts for key, value in values.items())
    if relevant_gestures and execution_records is None:
        raise ValueError('ENTRY_REST_CURRENT_EXECUTION_CONTEXT_REQUIRED')
    if execution_records is not None:
        from backing_execution_constraints import FIELDS, identity
        if type(execution_records) is not list or any(type(r) is not dict or set(r) != FIELDS
                or r['id'] != identity(r) for r in execution_records):
            raise ValueError('Complete typed current execution records required')
        for record in execution_records:
            if record['kind'] in ('slide', 'hopo') and (
                    record['destination_ref'] in first-carried or record['candidate_destination_ref'] in first-carried):
                raise ValueError('ENTRY_REST_SEPARATES_CONTINUOUS_GESTURE')
    core = t2['musical_relationships']
    for edge in core.get('relationships', []):
        if edge.get('destination_ref') in first:
            raise ValueError('ENTRY_REST_SEPARATES_INCOMING_TIE')
    out = _project_owners(t2, maps, update_clock=True)
    _write_notation(out, notation)
    for rest in rests:_append_rest(out, rest)
    carry_report = dict(carries=[], added_attacks=0)
    if carry_plan is not None:
        from material_entry_carry import apply as apply_carry
        out, carry_report = apply_carry(out, carry_plan)
    out = material.restore_fragments(out, [])
    if out['source_origin'] != t2['source_origin']:
        raise ValueError('Entry rest changed original observations')
    return out, dict(changed=True, maps=maps, generated_rests=rests, clock_changes=clocks, beat_mark_policy=POLICY,
                     execution_validation='REQUIRED_IN_COMPLETE_INVERSE', **carry_report)
