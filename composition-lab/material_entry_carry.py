"""Derive a held prefix from an existing continuous written gesture.

The saved entry allocation contains no notes. This transient plan names CURRENT
owners; its pitch equation is the existing written-tie equality. A carrier is a
continuation, never another attack or another original observation.
"""
from copy import deepcopy
from fractions import Fraction as F

import backing_pitch_ownership as backing
import backing_written_tie_constraints as tie_relations
import material_entry_rest as entry
import musical_support_material as material
import musical_tier2 as music
import written_tie_pitch_ownership as ties
from group_rhythm_relations import VIEWS
from source_observation_evidence import digest
from technique_observation_relations import scalar_relation

SCHEMA = 'material-entry-carry-plan/1'


def _pointer(ref):
    _, song, part, bar, voice, beat, note = ref.split(':')
    return f'track-{part}.json#/measures/{int(bar)-1}/voices/{voice}/beats/{beat}/notes/{note}'


def _mapped(ref, maps):
    result = maps['events'].get(ref, [ref])
    if len(result) != 1:
        raise ValueError('Carry follows the current post-subdivision identity only')
    return result[0]


def _clock(ref, index, maps):
    if ref in maps['spans']:
        span = maps['spans'][ref]
        if len(span) != 1:
            raise ValueError('One current carried occurrence required')
        return F(span[0]['onset_q']), F(span[0]['duration_q'])
    group, member = index[ref]
    return F(group['onset_q']), F(member['duration_q'])


def plan(current_t2, entry_change, execution_records, *, required_pairs=None, coherent_group_refs=None):
    """Reference-only plan from the unchanged current owners and entry clock.

    entry_change contains maps and generated_rests from the entry-rest plan.
    Existing accepted execution records identify HP/legato obligations. Unknown
    endpoints cannot be replaced by a guessed continuation.
    """
    from backing_execution_constraints import FIELDS, identity
    if type(execution_records) is not list or any(type(r) is not dict or set(r) != FIELDS
            or r['id'] != identity(r) for r in execution_records):
        raise ValueError('Complete typed current execution records required')
    required_pairs = [] if required_pairs is None else required_pairs
    if type(required_pairs) is not list or any(type(p) is not dict or set(p) != {'previous_ref','next_ref'}
            or any(type(ref) is not str for ref in p.values()) for p in required_pairs):
        raise ValueError('Explicit validated written-contact pairs required')
    if len({(p['previous_ref'],p['next_ref']) for p in required_pairs}) != len(required_pairs):
        raise ValueError('Duplicate required written-contact pair')
    coherent_group_refs = [] if coherent_group_refs is None else coherent_group_refs
    if type(coherent_group_refs) is not list or any(type(g) is not dict or set(g) != {'member_refs','next_ref'}
            or type(g['member_refs']) is not list or not g['member_refs']
            or type(g['next_ref']) is not str or any(type(ref) is not str for ref in g['member_refs'])
            or len(set(g['member_refs'])) != len(g['member_refs']) for g in coherent_group_refs):
        raise ValueError('Explicit complete guarded coending groups required')
    maps = entry_change['maps']; rests = entry_change['generated_rests']
    if set(maps) != {'beats', 'events', 'spans'}:
        raise ValueError('Complete typed entry maps required')
    core = current_t2['musical_relationships']
    body = material._body(core)
    index = backing._index(body)
    _, values = entry._facts(entry._current_fragment(current_t2))
    outgoing = {r['origin_ref']: r['destination_ref'] for r in core.get('relationships', [])
                if r.get('kind') == 'written_pitched_tie'}
    result = []; plain_index = None
    for rest in rests:
        lane = rest['beat_ref'].rsplit('/', 1)[0]
        first = [ref for ref in index if _pointer(ref).rsplit('/notes/', 1)[0] == lane+'/0']
        obligations = [(r,r['origin_ref'],r['destination_ref'],'continuous_gesture')
            for r in execution_records if r['kind'] in ('hopo', 'slide') and
            (r['destination_ref'] in first or r['candidate_destination_ref'] in first)]
        for pair in required_pairs:
            if pair['next_ref'] not in first:continue
            prior, target = pair['previous_ref'],pair['next_ref']
            observed = [r for r in execution_records if r['kind'] == 'letRing' and
                r['status'] == 'declaration_only_unknown_end' and prior in r['member_refs']]
            if (len(observed) != 1 or prior not in index or
                    values.get(observed[0]['source_fact_ref']) is not True):
                raise ValueError('CARRY_REQUIRES_EXISTING_LETRING_CONTACT_OBLIGATION')
            pg, pm = index[prior]; ng, _ = index[target]
            if F(pg['onset_q'])+F(pm['duration_q']) != F(ng['onset_q']):
                raise ValueError('CARRY_MUST_PRESERVE_EXISTING_WRITTEN_CONTIGUITY')
            if values.get(_pointer(prior)+'/string') != values.get(_pointer(target)+'/string'):
                raise ValueError('CARRY_REQUIRED_CONTACT_MUST_RETAIN_ITS_STRING')
            obligations.append((observed[0],prior,target,'guarded_written_contact'))
        for coherent in coherent_group_refs:
            target = coherent['next_ref']
            if target not in first:continue
            refs = coherent['member_refs']
            if any(ref not in index for ref in refs):
                raise ValueError('CARRY_COENDING_MEMBER_MISSING')
            group = index[refs[0]][0]
            if (refs != [m['id'] for m in group['members']] or
                    len({F(index[ref][1]['duration_q']) for ref in refs}) != 1 or
                    F(group['onset_q'])+F(index[refs[0]][1]['duration_q']) != F(index[target][0]['onset_q']) or
                    not any(pair['previous_ref'] in refs and pair['next_ref'] == target for pair in required_pairs)):
                raise ValueError('CARRY_REQUIRES_COMPLETE_EXISTING_COENDING_GROUP')
            observed = [r for r in execution_records if r['kind'] == 'letRing' and
                r['status'] == 'declaration_only_unknown_end' and set(refs) <= set(r['member_refs'])]
            if len(observed) != 1 or values.get(observed[0]['source_fact_ref']) is not True:
                raise ValueError('CARRY_REQUIRES_EXISTING_COENDING_DECLARATION')
            for ref in refs:
                obligations.append((observed[0],ref,target,'guarded_coending_member'))
        if not obligations:
            continue
        if core.get('schema') not in (ties.SCHEMA, ties.PLAIN):
            raise ValueError('CARRY_REQUIRES_EXISTING_TIE_OR_PLAIN_PITCH_OWNER')
        if core.get('schema') == ties.PLAIN and any(key.endswith('/tie') and val not in (None, False, 0)
                                                  for key, val in values.items()):
            raise ValueError('CARRY_REQUIRES_EXISTING_WRITTEN_TIE_OWNERSHIP')
        start, duration = F(rest['onset_q']), F(rest['duration_q'])
        members = []; strings = set()
        seen_pairs = {}
        for record, origin, destination, reason in sorted(obligations,
                key=lambda r: (tie_relations.address(r[2] or r[0]['candidate_destination_ref']),r[3])):
            if (origin not in index or destination not in first or record['candidate_destination_ref'] not in (None, destination)
                    or record['reason'] is not None
                    or record['kind'] == 'hopo' and record['status'] != 'source_transition_candidate'
                    or record['kind'] == 'slide' and (record['slide_type'] != 'legato'
                        or record['status'] != 'resolved_written_target' or record['timing_eligible'] is not True)):
                raise ValueError('CARRY_REQUIRES_KNOWN_CONTINUOUS_GESTURE')
            tail = origin; visited = set()
            while tail in outgoing:
                if tail in visited:
                    raise ValueError('Cyclic carry predecessor')
                visited.add(tail); tail = outgoing[tail]
            if (tail,destination) in seen_pairs:
                previous = seen_pairs[tail,destination]
                previous['support_record_ids'] = sorted(set(previous['support_record_ids'])|{record['id']})
                previous['relationship_kinds'] = sorted(set(previous['relationship_kinds'])|{reason})
                continue
            go, mo = index[tail]; gd, md = index[destination]
            address = tie_relations.address(tail); target_address = tie_relations.address(destination)
            if address[:2] != target_address[:2] or address[3] != target_address[3]:
                raise ValueError('Carry requires the same part and voice')
            origin_start, origin_duration = _clock(tail, index, maps)
            destination_start, _ = _clock(destination, index, maps)
            if origin_start+origin_duration != start or start+duration != destination_start:
                raise ValueError('CARRY_REQUIRES_EXACT_CONTIGUOUS_WRITTEN_SPANS')
            string = values.get(_pointer(tail)+'/string')
            if (type(string) is not int or string < 0 or string in strings or
                    reason != 'guarded_coending_member' and values.get(_pointer(destination)+'/string') != string):
                raise ValueError('CARRY_CONTACT_CONFLICT')
            strings.add(string)
            # No guessed pitch, dead member, grace or competing physical voice.
            if plain_index is None:
                plain_index = backing._index(ties.expand(core) if core.get('schema') == ties.SCHEMA else core)
            if music.member_pitch(*plain_index[tail]) is None or origin_duration <= 0:
                raise ValueError('CARRY_REQUIRES_KNOWN_WRITTEN_PITCH')
            for other, (group, member) in index.items():
                if other == tail or group['part_id'] != go['part_id']:
                    continue
                a, d = _clock(other, index, maps)
                if a < start+duration and a+d > start and values.get(_pointer(other)+'/string') == string:
                    raise ValueError('CARRY_COMPETING_STRING_OCCUPANCY')
            note_index = len(members)
            pieces = destination.split(':'); pieces[5] = '0'; pieces[6] = str(note_index)
            member = dict(identity='entry-carry-member:'+tail+'->'+destination,
                occurrence_ref=':'.join(pieces), origin_ref=_mapped(origin, maps),
                predecessor_ref=_mapped(tail, maps), destination_ref=_mapped(destination, maps),
                before_destination_ref=destination, execution_record_id=record['id'],
                support_record_ids=[record['id']],relationship_kinds=[reason])
            members.append(member);seen_pairs[tail,destination] = member
        members.sort(key=lambda row:tie_relations.address(row['predecessor_ref']))
        for note_index, member in enumerate(members):
            pieces=member['occurrence_ref'].split(':');pieces[-1]=str(note_index)
            member['occurrence_ref']=':'.join(pieces)
        result.append(dict(identity='entry-carry:'+lane, beat_ref=rest['beat_ref'],
                           onset_q=str(start), duration_q=str(duration), members=members))
    return dict(schema=SCHEMA, input_sha256=digest(current_t2),
                entry_change_sha256=digest(dict(maps=maps, generated_rests=rests)), carries=result)


def _row(ref, typ, *, children=None):
    document, pointer = ref.split('#', 1); parent, slot = ref.rsplit('/', 1)
    row = dict(id=ref, document=document, pointer=pointer, parent=parent,
               slot=int(slot) if slot.isdecimal() else slot, type=typ)
    if children is not None:row['children'] = children
    return row


def _add(t2, ref, typ, *, value=None, children=None, owner=None):
    from connected_tier2 import owner_kind
    arrays = material._arrays(t2); row = _row(ref, typ, children=children)
    if any(r['id'] == ref for r in arrays['source_structure']):
        raise ValueError('Duplicate generated carry authority')
    arrays['source_structure'].append(row)
    actual_owner = owner or ('source_structure' if children is not None else owner_kind(row))
    arrays['coverage'].append(dict(fact_ref=ref, owner=actual_owner))
    if children is None and owner != 'written_pitch_relationship':
        arrays['source_choices'].append(dict(fact_ref=ref, owner=actual_owner,
                                            parameter=scalar_relation(typ, source=value)))


def _mute(t2, beat_ref, value):
    """Current mute state derives from the preceding held segment, not evidence."""
    ref = beat_ref+'/palmMute'; row = _row(ref, 'boolean')
    arrays = material._arrays(t2)
    beat = next(r for r in arrays['source_structure'] if r['id'] == beat_ref)
    beat['children'].append(ref)
    arrays['technique_declarations'].append(dict(id='technique:'+ref, source_fact_ref=ref,
        scope='beat', field='palmMute', owner_ref=beat_ref, structure=[row],
        parameters=[dict(fact_ref=ref, unit='1', parameter=scalar_relation('boolean', source=value))],
        meaning='Source technique declaration; numerical units normalized, unspecified execution remains unknown'))
    arrays['coverage'].append(dict(fact_ref=ref, owner='technique_declaration'))


def apply(projected_t2, definition):
    """Replace only verified generated rests before final grammar restoration.

    The caller must recompute plan against its current pre-projection input.
    Every generated pitch has one existing tie equation, with no absolute pitch
    payload. Contact and mute are derived anew from the mapped current parent.
    """
    if type(definition) is not dict or set(definition) != {'schema','input_sha256','entry_change_sha256','carries'} or definition['schema'] != SCHEMA:
        raise ValueError('Closed entry-carry plan required')
    out = deepcopy(projected_t2)
    if not definition['carries']:return out, dict(carries=[], added_attacks=0)
    core = out['musical_relationships']
    if core.get('schema') == ties.PLAIN:
        stripped = deepcopy(core)
        for g in stripped['coattacks']:g.pop('interpretation', None)
        for name in VIEWS:stripped.pop(name, None)
        out['musical_relationships'] = dict(schema=ties.SCHEMA, core=stripped,
                                             relationships=[], groups=[], unresolved=[])
    elif core.get('schema') != ties.SCHEMA:
        raise ValueError('CARRY_REQUIRES_EXISTING_TIE_OR_PLAIN_PITCH_OWNER')
    owner = out['musical_relationships']; body = owner['core']
    arrays = material._arrays(out); index = backing._index(body)
    _, values = entry._facts(entry._current_fragment(out))
    positions = {r['occurrence_ref']:r for r in arrays['physical_positions']}
    event_map = {}; carry_rows = []
    for carrier in definition['carries']:
        ref = carrier['beat_ref']; prefix = ref+'/notes'
        beat = next((r for r in arrays['source_structure'] if r['id'] == ref), None)
        if beat is None or values.get(ref+'/rest') is not True or values.get(prefix+'/0/rest') is not True:
            raise ValueError('CARRY_REQUIRES_ITS_GENERATED_REST')
        n, d = values.get(ref+'/duration/0'), values.get(ref+'/duration/1')
        if F(4*n,d) != F(carrier['duration_q']):
            raise ValueError('Carry duration differs from its entry allocation')
        removed = {r['id'] for r in arrays['source_structure'] if r['id'] == ref+'/rest' or r['id'] == prefix or r['id'].startswith(prefix+'/')}
        arrays['source_structure'][:] = [r for r in arrays['source_structure'] if r['id'] not in removed]
        for field in ('source_choices','coverage'):
            arrays[field][:] = [r for r in arrays[field] if r['fact_ref'] not in removed]
        beat['children'][:] = [r for r in beat['children'] if r != ref+'/rest']
        members = []; mute_values = []
        _add(out, prefix, 'array', children=[prefix+'/'+str(i) for i in range(len(carrier['members']))])
        for i, row in enumerate(carrier['members']):
            predecessor = row['predecessor_ref']; target = row['occurrence_ref']
            if predecessor not in index or predecessor not in positions or target in index:
                raise ValueError('Carry predecessor authority or identity missing')
            old_group, old_member = index[predecessor]
            if F(old_group['onset_q'])+F(old_member['duration_q']) != F(carrier['onset_q']):
                raise ValueError('Carry predecessor clock changed')
            source_note = _pointer(predecessor); note = prefix+'/'+str(i)
            contact = deepcopy(positions[predecessor]); string = values[source_note+'/string']
            _add(out, note, 'object', children=[note+'/string', note+'/fret', note+'/tie'])
            _add(out, note+'/string', 'integer', value=string)
            old_fret_row = next(r for r in arrays['source_structure'] if r['id'] == source_note+'/fret')
            _add(out, note+'/fret', old_fret_row['type'], owner='written_pitch_relationship')
            _add(out, note+'/tie', 'boolean', value=True)
            contact.update(fact_ref=note+'/fret', occurrence_ref=target, string_ref=note+'/string')
            arrays['physical_positions'].append(contact)
            _, _, part, bar, voice, beat_index, member_index = target.split(':')
            members.append(dict(id=target, bar=int(bar), voice=int(voice), beat=int(beat_index),
                                note=int(member_index), duration_q=carrier['duration_q']))
            owner['relationships'].append(tie_relations.relation(dict(origin=predecessor,
                destination=target, kind='written_pitched_tie')))
            arrays['realization_order'].append(target)
            event_map.setdefault(predecessor, [predecessor]).append(target)
            parent_beat = source_note.rsplit('/notes/', 1)[0]
            mute_values.append(values.get(parent_beat+'/palmMute'))
            carry_rows.append(dict(**deepcopy(row), beat_ref=ref, onset_q=carrier['onset_q'],
                                   duration_q=carrier['duration_q'], added_attacks=0))
        if len(set(mute_values)) != 1:
            raise ValueError('CARRY_MIXED_BEAT_MUTE_STATE')
        if mute_values[0] is not None:
            if type(mute_values[0]) is not bool:raise ValueError('CARRY_UNKNOWN_MUTE_DECLARATION')
            _mute(out, ref, mute_values[0])
        match = next((g for g in arrays['coattacks'] if g['part_id'] == int(part) and
                      g['bar'] == int(bar) and F(g['onset_q']) == F(carrier['onset_q'])), None)
        if match is not None:
            raise ValueError('CARRY_EXISTING_SIMULTANEOUS_VOICE_OWNER_REQUIRED')
        arrays['coattacks'].append(dict(id=carrier['identity'], part_id=int(part), bar=int(bar),
            onset_q=carrier['onset_q'], timing_uncertain=False, scope_type='coincident_written_note_starts', members=members))
        owner['groups'].append(dict(member_refs=[m['id'] for m in members], basis_ref=None))
    owner['relationships'].sort(key=lambda r:(tie_relations.address(r['destination_ref']),tie_relations.address(r['origin_ref'])))
    if 'observed_dynamics' in out['owned_parameters']:
        from observed_dynamics import project
        out['owned_parameters']['observed_dynamics'] = project(out['owned_parameters']['observed_dynamics'], {}, event_map)
    # Expression observations describe attacks; generated held tails are not
    # additional accent/mute observations. Their current state derives above.
    return out, dict(carries=carry_rows, added_attacks=0)
