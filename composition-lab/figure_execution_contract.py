"""Written execution locks for one explicit common-octave figure.

The existing interval/class/offset/octave equation owns pitches. This module
only validates its consequences, in either direction, using accepted tie and
execution primitives. Digests protect invariant values without a note backup.
No slide endpoint, vibrato depth/rate, ringing end or comfort is inferred.
"""
from copy import deepcopy
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import json
import math

import backing_execution_constraints as execution
import backing_written_tie_constraints as ties

SCHEMA = 'figure-octave-execution/1'
MUTED_SCHEMA = 'figure-palm-mute-octave-execution/1'
CLOSURE_SCHEMA = 'figure-written-closure/1'
GROUP_FIELDS = {'id', 'occurrence_refs', 'interval_class', 'offsets_semitones', 'octave'}
TOP = {'schema', 'id', 'group_ref', 'closure', 'effects', 'fingerprints',
       'written_string_occupancy', 'source_exit_endpoint'}
HASHES = {'relative_geometry', 'contact_clock', 'expression', 'binding_shape', 'execution_context'}
MUTED_TOP = {'schema', 'id', 'group_ref', 'member_refs', 'palm_mute_declarations',
             'fingerprints', 'written_string_occupancy'}


def _typed(value):
    """Keep bool/int/float, absent/null and signed numeric distinctions."""
    if value is None:
        return ['null']
    if type(value) is bool:
        return ['bool', value]
    if type(value) is int:
        return ['int', str(value)]
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError('Nonfinite protected source value')
        return ['float', value.hex()]
    if type(value) is str:
        return ['str', value]
    if type(value) is list:
        return ['list', [_typed(x) for x in value]]
    if type(value) is dict and all(type(k) is str for k in value):
        return ['dict', [[k, _typed(value[k])] for k in sorted(value)]]
    raise ValueError('Plain typed JSON required by figure contract')


def fingerprint(value):
    return hashlib.sha256(json.dumps(_typed(value), separators=(',', ':'),
                                     ensure_ascii=True).encode()).hexdigest()


def _refs(refs):
    if type(refs) is not list or len(refs) < 2 or any(type(r) is not str for r in refs):
        raise ValueError('Explicit ordered figure references required')
    addresses = [execution.address(r) for r in refs]
    if len(set(refs)) != len(refs) or addresses != sorted(addresses):
        raise ValueError('Unique canonical figure reference order required')
    if len({(a[0], a[1], a[3]) for a in addresses}) != 1:
        raise ValueError('One source song, guitar part and voice required')
    return list(refs)


@lru_cache(maxsize=2)
def _data(encoded):
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    import musical_tier2 as music
    tier1 = json.loads(encoded)
    documents = project_documents(tier1)
    lower = extract_documents(documents)
    events = {e['id']: e for e in lower['events']}
    # Ephemeral adapter into the EXISTING written-tie predicate. There is no
    # harmonic analysis, new tie detector or saved duplicate event stream here.
    normal = dict(source_quality=dict(tracks=lower['source_coverage']['tracks']),
                  coattacks=[dict(part_id=e['part_id'], onset_q=e['onset_q'],
                                  bass_register_anchor=e['pitch'], members=[dict(
                                      id=e['id'], voice=e['voice'], duration_q=e['duration_q'],
                                      voicing_interval='0' if e['pitch'] is not None else None)])
                             for e in lower['events']])
    nodes, true_ids = music.written_tie_context(lower['tie_notation'], normal)
    links, unresolved = music.written_tie_edges(nodes, true_ids)
    return dict(documents=documents, events=events, nodes=nodes, links=links,
                unresolved=unresolved, execution=execution._snapshot(encoded))


def _closed(data, seed_refs):
    seeds = _refs(seed_refs)
    if not set(seeds) <= set(data['events']):
        raise ValueError('Unknown figure seed occurrence')
    members = set(seeds)
    while True:
        previous = set(members)
        for edge in data['links']:
            if members.intersection((edge['origin'], edge['destination'])):
                if edge['kind'] != 'written_pitched_tie':
                    raise ValueError('Only verified pitched ties belong to this scope')
                members.update((edge['origin'], edge['destination']))
        if members == previous:
            break
    refs = _refs(sorted(members, key=execution.address))
    if ties._affected_unknown(data['nodes'], data['unresolved'], refs):
        raise ValueError('UNRESOLVED_FIGURE_WRITTEN_TIE')
    incident = [e for e in data['links'] if members.intersection((e['origin'], e['destination']))]
    destinations = {e['destination'] for e in incident}
    relations = sorted((ties.relation(e) for e in incident),
                       key=lambda r: (execution.address(r['destination_ref']), execution.address(r['origin_ref'])))
    return dict(schema=CLOSURE_SCHEMA, seed_refs=seeds, member_refs=refs,
                attack_root_refs=[r for r in refs if r not in destinations], tie_relations=relations)


def closure(tier1, seed_refs):
    """Complete both directions of accepted written ties; do not pick new notes."""
    return _closed(_data(execution.encoded(tier1)), seed_refs)


def _raw(data, event):
    part = data['documents'][f"track-{event['part_id']}.json"]
    beat = part['measures'][event['bar'] - 1]['voices'][event['voice']]['beats'][event['beat']]
    note = beat['notes'][event['note']]
    pointer = f"track-{event['part_id']}.json#/measures/{event['bar'] - 1}/voices/{event['voice']}/beats/{event['beat']}/notes/{event['note']}"
    return part, beat, note, pointer


def _curve(bend, duration):
    from source_semantics import curve
    if type(bend) is not dict or set(bend) - {'tone', 'points'} or type(bend.get('points')) is not list or len(bend['points']) < 2:
        raise ValueError('Explicit supported relative bend curve required')
    for point in bend['points']:
        if type(point) is not dict or set(point) - {'tone', 'position', 'precisePosition'}:
            raise ValueError('Unsupported bend point execution')
        if type(point.get('tone')) not in (int, float) or not math.isfinite(point['tone']):
            raise ValueError('Known numeric bend point required')
        for key, maximum in [('position', 60), ('precisePosition', 100)]:
            if point.get(key) is not None and (type(point[key]) not in (int, float) or
                                             not math.isfinite(point[key]) or not 0 <= point[key] <= maximum):
                raise ValueError('Unknown bend coordinate')
    if bend.get('tone') is not None and (type(bend['tone']) not in (int, float) or not math.isfinite(bend['tone'])):
        raise ValueError('Unknown declared bend peak')
    try:
        parsed = curve(bend, F(duration))
    except (TypeError, KeyError, ValueError, ZeroDivisionError) as error:
        raise ValueError('Unsupported bend curve') from error
    if not parsed['valid']:
        raise ValueError('Invalid relative bend curve')


def build(tier1, seed_refs, group, bindings):
    """Capture only invariants; the existing group octave remains mutable."""
    from figure_register_ownership import identifier, relation
    from backing_motion_intervention import PLAIN_BEAT, original_contact
    data = _data(execution.encoded(tier1))
    closed = _closed(data, seed_refs)
    refs = closed['member_refs']
    if type(group) is not dict or set(group) != GROUP_FIELDS or group['occurrence_refs'] != refs or group['id'] != identifier(refs):
        raise ValueError('Exact pre-owned complete figure group required')
    solved = relation(interval_class=group['interval_class'], offsets_semitones=group['offsets_semitones'], octave=group['octave'])
    if len(solved['intervals']) != len(refs):
        raise ValueError('Complete figure interval ownership required')
    if type(bindings) is not list or len(bindings) != len(refs) or any(
            type(b) is not dict or set(b) != {'occurrence_ref', 'backing_ref'} for b in bindings):
        raise ValueError('Exact selected backing bindings required')
    if [b['occurrence_ref'] for b in bindings] != refs:
        raise ValueError('Complete canonical backing binding order required')
    events = data['events']; selected = [events[r] for r in refs]
    part_id = selected[0]['part_id']; part = data['documents'][f'track-{part_id}.json']
    if type(part.get('instrumentId')) is not int or not 24 <= part['instrumentId'] <= 31:
        raise ValueError('EXPRESSIVE_FIGURE_GUITAR_PROGRAM_REQUIRED')
    catalog = data['documents']['metadata.json'].get('tracks')
    if type(catalog) is not list or part_id >= len(catalog) or type(catalog[part_id]) is not dict:
        raise ValueError('Captured guitar catalog identity required')
    flags = catalog[part_id]
    if flags.get('isVocalTrack') or flags.get('isEmpty'):
        raise ValueError('Known nonempty guitar part required')
    if part_id in data['execution']['uncertain_parts']:
        raise ValueError('UNVERIFIED_FIGURE_WRITTEN_CLOCK')
    for a, b in zip(selected, selected[1:]):
        if F(a['onset_q']) + F(a['duration_q']) != F(b['onset_q']):
            raise ValueError('Contiguous complete written figure required')
    execution._occupancy(data['execution']['nodes'], refs)
    tied = {r for link in closed['tie_relations'] for r in (link['origin_ref'], link['destination_ref'])}
    geometry = []; clocks = []; expression = []; effects = []
    for ref, event, binding, interval in zip(refs, selected, bindings, solved['intervals']):
        if event['pitch'] is None or F(event['pitch']).denominator != 1 or F(event['duration_q']) <= 0:
            raise ValueError('Known positive-duration written pitch required')
        document, beat, note, pointer = _raw(data, event)
        original_contact(document, note, event['pitch'])
        if set(note) - {'string', 'fret', 'tie', 'leftHandVibrato', 'slide', 'bend'} or set(beat) - (PLAIN_BEAT | {'chord'}):
            raise ValueError('OUTSIDE_DECLARED_FIGURE_EXPRESSION_SCOPE')
        chord = beat.get('chord')
        if chord is not None and (type(chord) is not dict or set(chord) - {'text', 'width'}):
            raise ValueError('Uninterpreted chord diagram outside figure scope')
        if len([n for n in beat.get('notes', []) if not n.get('rest')]) != 1:
            raise ValueError('One written focal note per beat required')
        if 'tie' in note and note['tie'] is not None and type(note['tie']) is not bool:
            raise ValueError('Typed literal tie declaration required')
        if 'leftHandVibrato' in note and note['leftHandVibrato'] is not None and note['leftHandVibrato'] is not False:
            if note['leftHandVibrato'] != 'slight':
                raise ValueError('Only declared slight left-hand vibrato is in scope')
            effects.append(dict(kind='symbolic_slight_left_hand_vibrato', occurrence_ref=ref,
                                fact_ref=pointer + '/leftHandVibrato', depth=None, rate=None))
        if 'slide' in note and note['slide'] is not None and note['slide'] is not False:
            if note['slide'] != 'downwards':
                raise ValueError('Only symbolic downward exit is in scope')
            effects.append(dict(kind='symbolic_downward_exit', occurrence_ref=ref,
                                fact_ref=pointer + '/slide', endpoint=None, extent=None))
        if 'bend' in note and note['bend'] is not None and note['bend'] is not False:
            if ref in tied:
                raise ValueError('TIED_BEND_EXECUTION_NOT_IN_SCOPE')
            _curve(note['bend'], event['duration_q'])
            effects.append(dict(kind='untied_relative_bend_curve', occurrence_ref=ref,
                                fact_ref=pointer + '/bend'))
        anchor_ref = binding['backing_ref']; execution.address(anchor_ref)
        anchor = events.get(anchor_ref)
        if anchor is None or anchor_ref in refs or anchor['part_id'] == part_id or anchor['pitch'] is None:
            raise ValueError('Independent foreign-part backing pitch required')
        if anchor['part_id'] in data['execution']['uncertain_parts']:
            raise ValueError('UNVERIFIED_BACKING_WRITTEN_CLOCK')
        if not F(anchor['onset_q']) <= F(event['onset_q']) < F(anchor['onset_q']) + F(anchor['duration_q']):
            raise ValueError('Backing occurrence is not active')
        if F(event['pitch']) != F(anchor['pitch']) + F(interval):
            raise ValueError('Current source conflicts with the SAME backing interval equation')
        geometry.append([ref, str(F(event['pitch']) - 12 * group['octave']), str(F(note['fret']) - 12 * group['octave'])])
        clocks.append([ref, note['string'], event['onset_q'], event['duration_q'],
                       {k: v for k, v in beat.items() if k != 'notes'}])
        expression.append([ref, {k: v for k, v in note.items() if k not in ('fret', 'string')}])
    records = []
    for row in data['execution']['records']:
        if part_id not in execution._parts(row):
            continue
        affected = set(refs) & execution._neighborhood(row, data['execution']['nodes'])
        if affected and not (row['kind'] == 'slide' and row['status'] == 'exit_target_unspecified' and
                             row['slide_type'] == 'downwards' and row['origin_ref'] in refs and
                             row['destination_ref'] is None and row['candidate_destination_ref'] is None and
                             row['timing_eligible'] is True):
            raise ValueError('UNSUPPORTED_AFFECTED_FIGURE_EXECUTION: ' + row['kind'] + '/' + row['status'])
        records.append(row)
    protected_group = {k: v for k, v in group.items() if k != 'octave'}
    geometry_settings = {k: v for k, v in part.items() if k in ('instrumentId', 'tuning', 'capo', 'frets')}
    hashes = dict(relative_geometry=fingerprint(geometry),
                  contact_clock=fingerprint(dict(settings=geometry_settings, clocks=clocks)),
                  expression=fingerprint(expression),
                  binding_shape=fingerprint(dict(group=protected_group, bindings=bindings)),
                  execution_context=fingerprint(sorted(records, key=lambda r: r['id'])))
    return dict(schema=SCHEMA, id='figure-execution:' + fingerprint([group['id'], closed['seed_refs']]),
                group_ref=group['id'], closure=closed, effects=effects, fingerprints=hashes,
                written_string_occupancy=deepcopy(execution.OCCUPANCY), source_exit_endpoint='unknown')


def validate(contract, tier1, group, bindings):
    """SAME predicate for candidates and source-denied reconstructed facts."""
    if type(contract) is not dict or set(contract) != TOP or contract.get('schema') != SCHEMA:
        raise ValueError('Complete versioned figure execution contract required')
    if type(contract.get('closure')) is not dict or 'seed_refs' not in contract['closure']:
        raise ValueError('Saved explicit figure closure required')
    hashes = contract['fingerprints']
    if type(hashes) is not dict or set(hashes) != HASHES or any(
            type(h) is not str or len(h) != 64 or any(c not in '0123456789abcdef' for c in h) for h in hashes.values()):
        raise ValueError('Complete canonical figure invariant digests required')
    expected = build(tier1, contract['closure']['seed_refs'], group, bindings)
    if _typed(expected) != _typed(contract):
        raise ValueError('FIGURE_EXECUTION_CONTRACT_CONFLICT: closure, geometry, contact, expression or endpoint changed')


def build_muted(tier1, group, bindings):
    """Explicit PM-only register scope; do not weaken legacy expression rules.

    A written observation may have a protected incoming execution relationship.
    The selected notes being EDITED here must still have no such dependency.
    """
    from figure_register_ownership import identifier, relation
    from backing_motion_intervention import PLAIN_BEAT, original_contact
    from execution_dependencies import build as dependency_graph
    if type(group) is not dict or set(group) != GROUP_FIELDS:
        raise ValueError('Exact muted figure group required')
    refs = _refs(group['occurrence_refs'])
    if group['id'] != identifier(refs):
        raise ValueError('Stale muted figure group')
    solved = relation(interval_class=group['interval_class'],
                      offsets_semitones=group['offsets_semitones'], octave=group['octave'])
    if len(solved['intervals']) != len(refs) or type(bindings) is not list or len(bindings) != len(refs) or any(
            type(b) is not dict or set(b) != {'occurrence_ref', 'backing_ref'} for b in bindings):
        raise ValueError('Complete muted figure bindings required')
    if [b['occurrence_ref'] for b in bindings] != refs:
        raise ValueError('Complete canonical muted binding order required')
    data = _data(execution.encoded(tier1)); events = data['events']
    closed = _closed(data, refs)
    if closed['member_refs'] != refs or closed['tie_relations']:
        raise ValueError('MUTED_FIGURE_LINKED_EXECUTION_OUTSIDE_SCOPE')
    guard = execution.build(tier1, refs)
    if set(refs) & set(dependency_graph(tier1)['pinned_members']) or any(
            set(refs) & set(row['member_refs']) for row in guard['obligations']):
        raise ValueError('MUTED_FIGURE_LINKED_EXECUTION_OUTSIDE_SCOPE')
    selected = [events[r] for r in refs]; part_id = selected[0]['part_id']
    part = data['documents'][f'track-{part_id}.json']
    if type(part.get('instrumentId')) is not int or not 24 <= part['instrumentId'] <= 31:
        raise ValueError('MUTED_FIGURE_GUITAR_PROGRAM_REQUIRED')
    catalog = data['documents']['metadata.json'].get('tracks')
    if type(catalog) is not list or part_id >= len(catalog) or type(catalog[part_id]) is not dict:
        raise ValueError('Captured guitar catalog identity required')
    if catalog[part_id].get('isVocalTrack') or catalog[part_id].get('isEmpty'):
        raise ValueError('Known nonempty guitar part required')
    for a, b in zip(selected, selected[1:]):
        if F(a['onset_q']) + F(a['duration_q']) != F(b['onset_q']):
            raise ValueError('Contiguous complete written figure required')
    geometry = []; clocks = []; declarations = []
    for ref, event, binding, interval in zip(refs, selected, bindings, solved['intervals']):
        if event['pitch'] is None or F(event['pitch']).denominator != 1 or F(event['duration_q']) <= 0:
            raise ValueError('Known positive-duration written pitch required')
        document, beat, note, pointer = _raw(data, event)
        original_contact(document, note, event['pitch'])
        if set(note) != {'string', 'fret'} or set(beat) - (PLAIN_BEAT | {'chord', 'palmMute'}):
            raise ValueError('OUTSIDE_PALM_MUTE_ONLY_FIGURE_SCOPE')
        if 'palmMute' in beat and type(beat['palmMute']) is not bool:
            raise ValueError('EXPLICIT_BOOLEAN_PALM_MUTE_REQUIRED')
        chord = beat.get('chord')
        if chord is not None and (type(chord) is not dict or set(chord) - {'text', 'width'}):
            raise ValueError('Uninterpreted chord diagram outside figure scope')
        if len(beat['notes']) != 1:
            raise ValueError('One written focal note per beat required')
        anchor_ref = binding['backing_ref']; execution.address(anchor_ref)
        anchor = events.get(anchor_ref)
        if anchor is None or anchor_ref in refs or anchor['part_id'] == part_id or anchor['pitch'] is None:
            raise ValueError('Independent foreign-part backing pitch required')
        if anchor['part_id'] in data['execution']['uncertain_parts'] or not (
                F(anchor['onset_q']) <= F(event['onset_q']) < F(anchor['onset_q']) + F(anchor['duration_q'])):
            raise ValueError('Known active backing clock required')
        if F(event['pitch']) != F(anchor['pitch']) + F(interval):
            raise ValueError('Current source conflicts with the SAME backing interval equation')
        geometry.append([ref, str(F(event['pitch']) - 12 * group['octave']),
                         str(F(note['fret']) - 12 * group['octave'])])
        clocks.append([ref, note['string'], event['onset_q'], event['duration_q'],
                       {k: v for k, v in beat.items() if k != 'notes'}])
        state = dict(occurrence_ref=ref, fact_ref=pointer.rsplit('/notes/', 1)[0] + '/palmMute',
                     present='palmMute' in beat)
        if 'palmMute' in beat:
            state['value'] = beat['palmMute']
        declarations.append(state)
    protected_group = {k: v for k, v in group.items() if k != 'octave'}
    settings = {k: v for k, v in part.items() if k in ('instrumentId', 'tuning', 'capo', 'frets')}
    hashes = dict(relative_geometry=fingerprint(geometry),
                  contact_clock=fingerprint(dict(settings=settings, clocks=clocks)),
                  expression=fingerprint(declarations),
                  binding_shape=fingerprint(dict(group=protected_group, bindings=bindings)),
                  execution_context=fingerprint(guard))
    return dict(schema=MUTED_SCHEMA, id='muted-figure-execution:' + fingerprint(refs),
                group_ref=group['id'], member_refs=refs, palm_mute_declarations=declarations,
                fingerprints=hashes, written_string_occupancy=deepcopy(execution.OCCUPANCY))


def validate_muted(contract, tier1, group, bindings):
    """Same typed source geometry/PM/execution contract before and after."""
    if type(contract) is not dict or set(contract) != MUTED_TOP or contract.get('schema') != MUTED_SCHEMA:
        raise ValueError('Complete versioned palm-mute figure contract required')
    if _typed(build_muted(tier1, group, bindings)) != _typed(contract):
        raise ValueError('MUTED_FIGURE_CONTRACT_CONFLICT')
