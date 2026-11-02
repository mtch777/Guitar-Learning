"""One explicit melodic line: first pitch plus ordered signed movements.

Singleton pitches need no invented lower note. Independently owned upper members
use the same absolute line equation, then solve their existing vertical interval.
Tied written members share one attack pitch. This is intentional control, not a
donor selector, a phrase detector, or an assertion that a pitch is in key.
"""
from copy import deepcopy
from collections import Counter
from fractions import Fraction as F
import random

import backing_pitch_ownership as backing
import backing_written_tie_constraints as ties
import backing_execution_constraints as execution
import figure_execution_contract as closure
import figure_register_ownership as registers
import group_rhythm_relations as rhythm
import musical_tier2 as music
from source_observation_evidence import (
    digest, validate_origin, assert_only_parameter_changes, controlled_update,
)

SLOT = 'melodic_movement'
SCHEMA = 'source-melodic-movement/1'
SCHEMA_V2 = 'source-melodic-movement/2'
POLICY = 'source_melodic_movement'
REFERENCE_STEP = 'reference_step'
INTENTS = ('repeat_start', 'follow_reference_motion')


def _integer(value):
    if type(value) is not str:
        raise ValueError('Canonical integer pitch or signed-step string required')
    value_fraction = music.fraction(value)
    if value_fraction.denominator != 1 or str(value_fraction) != value:
        raise ValueError('Canonical integer pitch or signed-step string required')
    return value_fraction


def relation(*, pitches=None, pitch_class=None, octave=None, steps=None, reference_pitches=None):
    """The same additive equation in both directions.

    ``octave`` is the ordinary MIDI note-name octave: C4 is pitch60. The existing
    figure-register arithmetic uses coordinate k=octave+1 internally.
    """
    if pitches is not None:
        if any(v is not None for v in (pitch_class, octave, steps, reference_pitches)):
            raise ValueError('Choose extraction or realization, not both')
        if type(pitches) is not list or len(pitches) < 2:
            raise ValueError('At least two actual attack pitches required')
        values = [_integer(p) for p in pitches]
        start = registers.relation(intervals=[str(values[0]), str(values[0])])
        pitch_class, octave = start['interval_class'], start['octave'] - 1
        steps = [music.relation(anchor=str(a), pitch=str(b))['interval']
                 for a, b in zip(values, values[1:])]
    else:
        if type(octave) is not int or type(steps) is not list or not steps:
            raise ValueError('Integer first-note octave and ordered signed steps required')
        pc = _integer(pitch_class)
        if not 0 <= pc < 12:
            raise ValueError('First pitch class must be in [0,12)')
        start = registers.relation(interval_class=pitch_class,
            offsets_semitones=['0', '0'], octave=octave + 1)['intervals'][0]
        reference = None
        if reference_pitches is not None:
            if type(reference_pitches) is not list or len(reference_pitches) != len(steps) + 1:
                raise ValueError('One reference attack for every target attack required')
            reference = [_integer(p) for p in reference_pitches]
        values = [F(start)]
        for i, step in enumerate(steps):
            if step == REFERENCE_STEP:
                if reference is None:
                    raise ValueError('Live reference movement has no reference attacks')
                delta = music.relation(anchor=str(reference[i]), pitch=str(reference[i + 1]))['interval']
            else:
                delta = str(_integer(step))
            values.append(F(music.relation(anchor=str(values[-1]), interval=delta)['pitch']))
    return dict(pitch_class=pitch_class, octave=octave, steps=deepcopy(steps),
                pitches=list(map(str, values)))


def _body(shared):
    if shared.get('schema') in backing.SCHEMAS:
        return backing._body(shared['core'])
    return backing._body(shared)


def _roots(refs):
    if type(refs) is not list or len(refs) < 2:
        raise ValueError('At least two explicitly ordered attack roots required')
    addresses = [backing.address(r) for r in refs]
    if len(set(refs)) != len(refs) or addresses != sorted(addresses):
        raise ValueError('Unique chronological attack roots required')
    if len({(a[0], a[1], a[3]) for a in addresses}) != 1:
        raise ValueError('Attack roots must share a source song, part and voice')
    return refs


def _members(attacks):
    if type(attacks) is not list:
        raise ValueError('Explicit attack ownership rows required')
    _roots([r.get('attack_ref') for r in attacks if type(r) is dict])
    found = []
    for row in attacks:
        if type(row) is not dict or set(row) != {'attack_ref', 'member_refs'}:
            raise ValueError('Attack rows contain only root and complete written member identities')
        members = row['member_refs']
        if type(members) is not list or not members or members[0] != row['attack_ref']:
            raise ValueError('An attack must precede its tied continuations')
        addresses = [backing.address(ref) for ref in members]
        if addresses != sorted(addresses) or len({(a[0], a[1], a[3]) for a in addresses}) != 1:
            raise ValueError('One ordered written voice per complete attack required')
        found.extend(members)
    if len(set(found)) != len(found):
        raise ValueError('Duplicate/overlapping melodic pitch owners')
    return sorted(found, key=backing.address)


def _attack_rows(lower, roots):
    roots = _roots(roots)
    scope = closure.closure(lower, roots)
    if scope['attack_root_refs'] != roots:
        raise ValueError('A tied continuation is not a new attack root')
    data = closure._data(execution.encoded(lower))
    times = [F(data['events'][r]['onset_q']) for r in roots]
    if times != sorted(set(times)):
        raise ValueError('Attack roots require distinct known chronological onsets')
    rows = []
    for root in roots:
        connected = {root}
        while True:
            prior = set(connected)
            for edge in scope['tie_relations']:
                ends = {edge['origin_ref'], edge['destination_ref']}
                if connected & ends:
                    connected.update(ends)
            if connected == prior:
                break
        rows.append(dict(attack_ref=root, member_refs=sorted(connected, key=backing.address)))
    members = _members(rows)
    if members != scope['member_refs']:
        raise ValueError('Incomplete melodic tie closure')
    for ref in members:
        event = data['events'][ref]
        if event['pitch'] is None or F(event['pitch']).denominator != 1 or F(event['duration_q']) <= 0:
            raise ValueError('Known pitched attack/hold with positive written duration required')
        _, _, note, _ = closure._raw(data, event)
        if 'tie' in note and type(note['tie']) is not bool:
            raise ValueError('Unknown typed tie declaration')
    return rows, data


def _authority(index, ref, *, stored):
    if ref not in index:
        raise ValueError('Dangling melodic occurrence')
    group, member = index[ref]
    # Dead/unpitched occurrences keep their explicit None intervals and do not
    # create an imaginary lower pitch. A missing interval is different: another
    # owner may hold it, so it cannot establish this sole-pitched condition.
    sole_pitched = member.get('voicing_interval') == '0' and all(
        other is member or ('voicing_interval' in other and other['voicing_interval'] is None)
        for other in group['members'])
    if sole_pitched:
        if member.get('voicing_interval') != '0' or ('bass_register_anchor' in group) == stored:
            raise ValueError('Missing, duplicate or conflicting singleton pitch authority')
        return 'singleton', group, member
    if 'bass_register_anchor' not in group or not any(
            m is not member and m.get('voicing_interval') == '0' for m in group['members']):
        raise ValueError('Selected lowest coattack member is not an independent upper member')
    if stored:
        if 'voicing_interval' in member:
            raise ValueError('Duplicate upper-member pitch authority')
    elif member.get('voicing_interval') is None or _integer(member['voicing_interval']) <= 0:
        raise ValueError('Known independent upper member above a retained lower note required')
    return 'upper_member', group, member


def _pitch(shared, ref, seen=None):
    """Read an existing current authority, including unrelated backing links."""
    seen = set() if seen is None else set(seen)
    if ref in seen:
        raise ValueError('Cyclic melodic reference dependency')
    seen.add(ref)
    index = backing._index(_body(shared))
    if ref not in index:
        raise ValueError('Dangling live reference attack')
    links = shared.get('relationships', []) if shared.get('schema') in backing.SCHEMAS else []
    link = next((r for r in links if r['occurrence_ref'] == ref), None)
    if link is not None:
        if set(link) != backing.LINK_FIELDS:
            raise ValueError('Unsupported live-reference authority')
        return music.relation(anchor=_pitch(shared, link['backing_ref'], seen),
                              interval=str(_integer(link['interval_semitones'])))['pitch']
    group, member = index[ref]
    if 'bass_register_anchor' not in group or member.get('voicing_interval') is None:
        raise ValueError('Live reference depends on a selected or unsupported pitch owner')
    return music.relation(anchor=str(_integer(group['bass_register_anchor'])),
                          interval=str(_integer(member['voicing_interval'])))['pitch']


def _protected(lower, refs, *, flexible_strings=()):
    """Invariant selected notation/clock/contact context, without old pitches."""
    data = closure._data(execution.encoded(lower)); rows = []
    for ref in refs:
        event = data['events'][ref]
        part, beat, note, _ = closure._raw(data, event)
        rows.append(dict(ref=ref, onset_q=event['onset_q'], duration_q=event['duration_q'],
            instrument={k: part[k] for k in ('instrumentId', 'tuning', 'capo', 'frets') if k in part},
            note={k: v for k, v in note.items() if k != 'fret' and not(k == 'string' and ref in flexible_strings)},
            beat={k: v for k, v in beat.items() if k != 'notes'}))
    return digest(rows)


def _tie_scope(data, refs):
    # Both outputs of the existing tie predicate matter: do not reconstruct
    # its input from successful links alone and silently omit unknown ties.
    true_ids = {r['destination'] for r in data['links'] + data['unresolved']}
    return ties.build(data['nodes'], sorted(true_ids, key=backing.address), refs)


def _shape(upper):
    model = upper.get('owned_parameters', {}).get(SLOT)
    fields = {'schema', 'attacks', 'reference_attacks', 'parameters', 'observations',
              'written_ties', 'execution', 'protected_notation_sha256'}
    if type(model) is not dict or set(model) != fields or model['schema'] not in (SCHEMA, SCHEMA_V2):
        raise ValueError('Exact registered melodic movement ownership required')
    refs = _members(model['attacks']); reference = model['reference_attacks']
    reference_refs = [] if reference is None else _members(reference)
    if reference is not None and (len(reference) != len(model['attacks']) or set(refs) & set(reference_refs)):
        raise ValueError('Independent equal-length reference and target attack sequences required')
    if reference_refs and backing.address(reference_refs[0])[0] != backing.address(refs[0])[0]:
        raise ValueError('One original source song required')
    observations = model['observations']
    observation_fields = {'origin', 'reference_steps'} | ({'register_context'} if model['schema'] == SCHEMA_V2 else set())
    if type(observations) is not dict or set(observations) != observation_fields:
        raise ValueError('Original semantic observation provenance required')
    validate_origin(observations['origin'])
    if observations['origin'] != upper.get('source_origin'):
        raise ValueError('Original observation identity changed')
    if model['schema'] == SCHEMA_V2:
        _validate_register_context(observations['register_context'], observations['origin'], refs)
    old_steps = observations['reference_steps']
    if reference is None:
        if old_steps is not None:
            raise ValueError('Unbound original reference observations')
    elif type(old_steps) is not list or len(old_steps) != len(reference) - 1:
        raise ValueError('Original reference movement cardinality differs')
    else:
        for step in old_steps: _integer(step)
    parameters = model['parameters']
    if type(parameters) is not dict or set(parameters) != {'pitch_class', 'octave', 'steps'}:
        raise ValueError('One first pitch and ordered movement authority required')
    if type(parameters['steps']) is not list or len(parameters['steps']) != len(model['attacks']) - 1:
        raise ValueError('One signed movement between each attack pair required')
    if type(model['protected_notation_sha256']) is not str or len(model['protected_notation_sha256']) != 64:
        raise ValueError('Selected notation integrity commitment required')
    ties.shape(model['written_ties'], refs); execution.shape(model['execution'], refs)
    return model, refs, reference_refs


def expand(upper):
    """Restore current scalar pitches transiently; retain every foreign owner."""
    model, refs, _ = _shape(upper)
    result = deepcopy(upper); result['owned_parameters'].pop(SLOT)
    shared = result['musical_relationships']; index = backing._index(_body(shared))
    reference = None if model['reference_attacks'] is None else [
        _pitch(shared, r['attack_ref']) for r in model['reference_attacks']]
    solved = relation(**model['parameters'], reference_pitches=reference)
    for row, pitch in zip(model['attacks'], solved['pitches']):
        for ref in row['member_refs']:
            kind, group, member = _authority(index, ref, stored=True)
            if kind == 'singleton':
                group['bass_register_anchor'] = pitch
            else:
                interval = music.relation(anchor=group['bass_register_anchor'], pitch=pitch)['interval']
                if F(interval) <= 0:
                    raise ValueError('Selected upper member crossed its retained lower note')
                member['voicing_interval'] = interval
    # An unrelated bend slot can still own other missing scalars. Its registered
    # expansion runs afterward, so do not refresh/flatten that incomplete core.
    if 'bend_gesture' not in result['owned_parameters']:
        if shared['schema'] == backing.PLAIN:
            rhythm.refresh(shared); music.validate(shared)
        elif shared['schema'] in backing.SCHEMAS:
            backing.expand(shared)
        elif shared['schema'] == backing.RHYTHM:
            rhythm.expand(shared)
    return result


def validate_execution(upper, lower):
    model, refs, reference_refs = _shape(upper)
    roots = [r['attack_ref'] for r in model['attacks']]
    current, data = _attack_rows(lower, roots)
    if current != model['attacks']:
        raise ValueError('Complete melodic attack/tie membership changed')
    reference = None if model['reference_attacks'] is None else [
        _pitch(upper['musical_relationships'], r['attack_ref']) for r in model['reference_attacks']]
    solved = relation(**model['parameters'], reference_pitches=reference)
    for row, pitch in zip(model['attacks'], solved['pitches']):
        if any(data['events'][ref]['pitch'] != pitch for ref in row['member_refs']):
            raise ValueError('Reconstructed melodic pitches differ from their movement authority')
    if model['reference_attacks'] is not None:
        current_reference, _ = _attack_rows(lower, [r['attack_ref'] for r in model['reference_attacks']])
        if current_reference != model['reference_attacks']:
            raise ValueError('Complete live reference membership changed')
    if _protected(lower, refs + reference_refs, flexible_strings=refs if model['schema'] == SCHEMA_V2 else ()) != model['protected_notation_sha256']:
        raise ValueError('Selected/reference clock, expression or fixed contact context changed')
    if _tie_scope(data, refs) != model['written_ties']:
        raise ValueError('Complete saved written-tie incidence changed')
    execution.validate(model['execution'], lower, refs)
    from backing_motion_intervention import original_contact
    for ref in refs + reference_refs:
        event = data['events'][ref]; part, _, note, _ = closure._raw(data, event)
        original_contact(part, note, event['pitch'])
    if model['schema'] == SCHEMA_V2:
        span = F(model['observations']['register_context']['max_simultaneous_span'])
        for ref in refs:
            _, _, note, _ = closure._raw(data, data['events'][ref])
            if not _contact_span_ok(data, ref, note, span):
                raise ValueError('Selected contact exceeds the declared source-span experiment')


def _realize(upper):
    from connected_tier2 import realize
    lower = realize(expand(upper)); validate_execution(upper, lower)
    return lower


def lift(upper, attack_refs, *, reference_attack_refs=None, register_controls=False):
    from connected_tier2 import realize, strip_lower
    if SLOT in upper.get('owned_parameters', {}):
        raise ValueError('Existing movement owner must be updated, not rebuilt')
    if type(register_controls) is not bool:
        raise ValueError('Explicit Boolean register ownership opt-in required')
    result = strip_lower(upper); lower = realize(result)
    validate_origin(result.get('source_origin'))
    if digest(lower) != result['source_origin']['facts_sha256']:
        raise ValueError('Original observations required when establishing movement ownership')
    attacks, data = _attack_rows(lower, attack_refs); refs = _members(attacks)
    reference = None
    if reference_attack_refs is not None:
        reference, _ = _attack_rows(lower, reference_attack_refs)
        if len(reference) != len(attacks) or set(refs) & set(_members(reference)):
            raise ValueError('Independent equal-length reference and target attack sequences required')
    shared = result['musical_relationships']; body = _body(shared); index = backing._index(body)
    for ref in refs: _authority(index, ref, stored=False)
    source_pitches = None if reference is None else [_pitch(shared, r['attack_ref']) for r in reference]
    solved = relation(pitches=[data['events'][r['attack_ref']]['pitch'] for r in attacks])
    observations = dict(origin=deepcopy(result['source_origin']), reference_steps=None if reference is None else relation(pitches=source_pitches)['steps'])
    if register_controls:
        observations['register_context'] = _original_register_context(lower, observations['origin'], refs)
    model = dict(schema=SCHEMA_V2 if register_controls else SCHEMA, attacks=attacks, reference_attacks=reference,
        parameters={k: solved[k] for k in ('pitch_class', 'octave', 'steps')},
        observations=observations,
        written_ties=_tie_scope(data, refs),
        execution=execution.build(lower, refs),
        protected_notation_sha256=_protected(lower, refs + ([] if reference is None else _members(reference)), flexible_strings=refs if register_controls else ()))
    for ref in refs:
        kind, group, member = _authority(index, ref, stored=False)
        if kind == 'singleton': del group['bass_register_anchor']
        else: del member['voicing_interval']
    for field in rhythm.VIEWS: body.pop(field, None)
    for group in body['coattacks']: group.pop('interpretation', None)
    result['owned_parameters'][SLOT] = model
    if _realize(result) != lower:
        raise ValueError('Movement ownership changed the complete original source')
    return result


def validate_controls(controls):
    legacy = {'context_policy', 'melody', 'intent', 'seed'}
    if type(controls) is not dict or set(controls) not in (legacy, legacy | {'register', 'register_direction'}):
        raise ValueError('Exact melodic movement controls required')
    if controls['context_policy'] != POLICY or controls['intent'] not in INTENTS:
        raise ValueError('Explicit repeat/follow movement intention required')
    if type(controls['melody']) is not int or not 0 <= controls['melody'] <= 100 or type(controls['seed']) is not int:
        raise ValueError('Integer percentage and seed required')
    if 'register' in controls and (type(controls['register']) is not int or not 0 <= controls['register'] <= 100 or controls['register_direction'] not in ('up', 'down')):
        raise ValueError('Integer register release and explicit up/down direction required')


@controlled_update
def intervene(upper, controls):
    validate_controls(controls)
    before = _realize(upper); model, refs, _ = _shape(upper)
    if model['schema'] == SCHEMA_V2:
        if 'register' not in controls:
            raise ValueError('Version2 requires both explicit control percentages')
        return _intervene_v2(upper, controls, before)
    if 'register' in controls:
        raise ValueError('Version2 register ownership must be prepared on original input')
    result = deepcopy(upper)
    released = random.Random(f'melodic-movement:{controls["seed"]}').random() < controls['melody'] / 100
    if released:
        if controls['intent'] == 'follow_reference_motion' and model['reference_attacks'] is None:
            raise ValueError('Follow intention requires explicit original reference attacks')
        value = '0' if controls['intent'] == 'repeat_start' else REFERENCE_STEP
        result['owned_parameters'][SLOT]['parameters']['steps'] = [value] * (len(model['attacks']) - 1)
    paths = [('owned_parameters', SLOT, 'parameters', 'steps', i) for i in range(len(model['attacks']) - 1)]
    assert_only_parameter_changes(upper, result, paths)
    after = _realize(result)
    from backing_motion_intervention import pointer
    data = closure._data(execution.encoded(before))
    allowed = {pointer(data['events'][ref]) + '/fret' for ref in refs}
    if {k: v for k, v in before.items() if k != 'facts'} != {k: v for k, v in after.items() if k != 'facts'} or len(before['facts']) != len(after['facts']):
        raise ValueError('Movement changed the source envelope')
    changed = []
    for old, new in zip(before['facts'], after['facts']):
        if old == new: continue
        if old['id'] not in allowed or {k: v for k, v in old.items() if k != 'value'} != {k: v for k, v in new.items() if k != 'value'}:
            raise ValueError('Movement propagated outside its complete selected fret scope')
        changed.append(old['id'])
    return result, dict(context_policy=POLICY, intent=controls['intent'], released=released,
        changed=bool(changed), relationships_changed=digest(result) != digest(upper),
        attack_refs=[r['attack_ref'] for r in model['attacks']], member_refs=refs,
        changed_fact_refs=changed, original_observations_unchanged=True,
        scope='Explicit first-pitch-preserving movement; no key, preference or musical-fit claim')


REGISTER_PROFILE = 'original-written-register-support-and-source-span/1'


def _original_register_context(lower, origin, refs):
    """Aggregate original observations; never retain a source note stream.

    Counts describe support, not admission or sampling weight. The source span
    is a conservative experiment policy, not an anatomical or musical law.
    """
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    from observed_note_register import _plain
    from voicing_register import inventory
    docs = project_documents(lower); events = extract_documents(docs)['events']
    context = dict(documents=docs, events={e['id']: e for e in events})
    part_id = backing.address(refs[0])[1]; counts = Counter()
    part = docs[f'track-{part_id}.json']
    if type(part.get('instrumentId')) is not int or not 24 <= part['instrumentId'] <= 31:
        raise ValueError('Version2 placement requires an explicitly declared guitar')
    if type(part.get('frets')) is not int or part['frets'] <= 0:
        raise ValueError('Version2 register search requires declared finite fret bounds')
    for event in events:
        if event['part_id'] != part_id or event['id'] in refs or event['pitch'] is None:
            continue
        try: _plain(context, event)
        except ValueError: continue
        counts[int(F(event['pitch']))] += 1
    envelope = inventory(lower, 'joint_source_fingering')['physical_envelopes'][str(part_id)]
    result = dict(profile=REGISTER_PROFILE, part_id=part_id, excluded_member_refs=list(refs),
        counts=[dict(pitch_class=p % 12, octave=p // 12 - 1, count=n) for p, n in sorted(counts.items())],
        max_simultaneous_span=str(F(str(envelope['max_simultaneous_span']))))
    result['evidence_sha256'] = digest(dict(origin=origin, context=result))
    return result


def _validate_register_context(context, origin, refs):
    fields = {'profile', 'part_id', 'excluded_member_refs', 'counts', 'max_simultaneous_span', 'evidence_sha256'}
    if type(context) is not dict or set(context) != fields or context['profile'] != REGISTER_PROFILE:
        raise ValueError('Typed original movement/register context required')
    if type(context['part_id']) is not int or context['part_id'] != backing.address(refs[0])[1] or context['excluded_member_refs'] != refs:
        raise ValueError('Original register observation scope changed')
    if type(context['counts']) is not list:
        raise ValueError('Original aggregate register counts required')
    pitches = []
    for row in context['counts']:
        if type(row) is not dict or set(row) != {'pitch_class', 'octave', 'count'} or any(type(v) is not int for v in row.values()) or not 0 <= row['pitch_class'] < 12 or row['count'] <= 0:
            raise ValueError('Typed original register count required')
        pitches.append(12 * (row['octave'] + 1) + row['pitch_class'])
    if pitches != sorted(set(pitches)) or _integer(context['max_simultaneous_span']) < 0:
        raise ValueError('Canonical original register/physical observations required')
    evidence = {k: v for k, v in context.items() if k != 'evidence_sha256'}
    if context['evidence_sha256'] != digest(dict(origin=origin, context=evidence)):
        raise ValueError('Original movement/register observation integrity changed')


def _solve(upper):
    model, _, _ = _shape(upper)
    reference = None if model['reference_attacks'] is None else [
        _pitch(upper['musical_relationships'], r['attack_ref']) for r in model['reference_attacks']]
    return relation(**model['parameters'], reference_pitches=reference)


def _string_paths(upper, refs):
    positions = upper['owned_parameters']['physical_positions']
    choices = upper['owned_parameters']['source_choices']; result = {}
    for ref in refs:
        matches = [(i, row) for i, row in enumerate(positions) if row['occurrence_ref'] == ref]
        if len(matches) != 1 or 'tuning_array_ref' not in matches[0][1]:
            raise ValueError('Dynamic existing physical occurrence owner required')
        pi, position = matches[0]
        matches = [(i, row) for i, row in enumerate(choices) if row['fact_ref'] == position['string_ref']]
        if len(matches) != 1 or set(matches[0][1]['parameter']) != {'normalized', 'negative_zero'}:
            raise ValueError('Existing integer source string parameter required')
        result[ref] = (pi, matches[0][0])
    return result


def _allowed_changes(before_upper, after_upper, before, after, *, version2):
    model, refs, _ = _shape(before_upper)
    paths = [('owned_parameters', SLOT, 'parameters', 'steps', i) for i in range(len(model['attacks']) - 1)]
    if version2:
        paths.append(('owned_parameters', SLOT, 'parameters', 'octave'))
        for pi, ci in _string_paths(before_upper, refs).values():
            paths += [('owned_parameters', 'source_choices', ci, 'parameter', field) for field in ('normalized', 'negative_zero')]
            paths.append(('owned_parameters', 'physical_positions', pi, 'negative_zero'))
    assert_only_parameter_changes(before_upper, after_upper, paths)
    from backing_motion_intervention import pointer
    data = closure._data(execution.encoded(before))
    allowed = {pointer(data['events'][ref]) + '/' + field for ref in refs for field in (('fret', 'string') if version2 else ('fret',))}
    if {k: v for k, v in before.items() if k != 'facts'} != {k: v for k, v in after.items() if k != 'facts'} or len(before['facts']) != len(after['facts']):
        raise ValueError('Movement/register changed the source envelope')
    changed = []
    for old, new in zip(before['facts'], after['facts']):
        if old == new: continue
        if old['id'] not in allowed or {k: v for k, v in old.items() if k != 'value'} != {k: v for k, v in new.items() if k != 'value'}:
            raise ValueError('Movement/register propagated outside selected physical facts')
        changed.append(old['id'])
    return changed


def _contact_span_ok(data, ref, contact, maximum, excluded=()):
    """Check actual simultaneous cells throughout a selected written hold.

    An unknown/dead pitch still occupies its declared string. Notes occurring
    in different cells do not form an invented simultaneous fret span.
    """
    member = data['events'][ref]
    start = F(member['onset_q']); end = start + F(member['duration_q'])
    boundaries = {start, end}; overlaps = []
    for other in data['events'].values():
        if other['part_id'] != member['part_id'] or other['id'] == ref or other['id'] in excluded:
            continue
        left = max(start, F(other['onset_q'])); right = min(end, F(other['onset_q']) + F(other['duration_q']))
        if left >= right: continue
        _, _, note, _ = closure._raw(data, other)
        if note.get('string') == contact['string']: return False
        boundaries.update((left, right)); overlaps.append((left, right, note))
    cuts = sorted(boundaries)
    for left, right in zip(cuts, cuts[1:]):
        frets = [F(str(contact['fret']))] if contact['fret'] > 0 else []
        for begin, finish, note in overlaps:
            value = note.get('fret')
            if begin < right and left < finish and type(value) in (int, float) and value > 0:
                frets.append(F(str(value)))
        if frets and max(frets) - min(frets) > maximum: return False
    return True


def _placed_candidate(upper, parameters, before):
    """One deterministic nominal contact proposal; no Cartesian product.

    All tied members use one string. Full held-note overlaps are considered,
    then the unchanged execution and tie predicates validate the whole result.
    """
    from backing_motion_relations import physical_contacts
    model, refs, _ = _shape(upper); selected = set(refs)
    data = closure._data(execution.encoded(before)); result = deepcopy(upper)
    result['owned_parameters'][SLOT]['parameters'] = deepcopy(parameters)
    pitches = _solve(result)['pitches']; paths = _string_paths(result, refs)
    span = F(model['observations']['register_context']['max_simultaneous_span'])
    contacts = {}
    for attack, pitch in zip(model['attacks'], pitches):
        event = data['events'][attack['attack_ref']]
        part, _, original, _ = closure._raw(data, event)
        candidates = physical_contacts(int(F(pitch)), part['tuning'], part.get('capo', 0), max_fret=part.get('frets'))
        viable = []
        for contact in candidates:
            fits = all(_contact_span_ok(data, ref, contact, span, selected) for ref in attack['member_refs'])
            if fits: viable.append(contact)
        if not viable:
            raise ValueError('NO_CONTACT_WITHIN_DECLARED_BOUNDS_AND_SOURCE_SPAN')
        chosen = min(viable, key=lambda c: (c['string'] != original['string'], abs(c['string'] - original['string']), c['string']))
        for ref in attack['member_refs']:
            contacts[ref] = deepcopy(chosen); pi, ci = paths[ref]
            parameter = result['owned_parameters']['source_choices'][ci]['parameter']
            if int(_integer(parameter['normalized'])) != chosen['string']:
                parameter.update(normalized=str(chosen['string']), negative_zero=False)
            if chosen['fret'] != 0:
                result['owned_parameters']['physical_positions'][pi]['negative_zero'] = False
    after = _realize(result)
    _allowed_changes(upper, result, before, after, version2=True)
    if 'stable_pitch_preference' in upper:
        from stable_pitch_policy import enforce_transition
        enforce_transition(upper, before, after)
    return result, contacts


def _movement_candidates(upper, before, intent):
    model, _, _ = _shape(upper); current = deepcopy(model['parameters'])
    candidates = [(deepcopy(upper), dict(kind='current', parameters=current))]; refused = []
    wanted = deepcopy(current)
    wanted['steps'] = [('0' if intent == 'repeat_start' else REFERENCE_STEP)] * len(current['steps'])
    if wanted == current: return candidates, refused
    try:
        if intent == 'follow_reference_motion' and model['reference_attacks'] is None:
            raise ValueError('Follow intention requires explicit reference attacks')
        result, contacts = _placed_candidate(upper, wanted, before)
        candidates.append((result, dict(kind='requested_relation', parameters=wanted, contacts=contacts)))
    except ValueError as error: refused.append(dict(kind='requested_relation', reason=str(error)))
    return candidates, refused


def _register_candidates(upper, before, direction):
    model, refs, _ = _shape(upper); current = deepcopy(model['parameters'])
    candidates = [(deepcopy(upper), dict(kind='current', octave=current['octave']))]; refused = []
    data = closure._data(execution.encoded(before)); event = data['events'][refs[0]]
    part, _, _, _ = closure._raw(data, event)
    if type(part.get('frets')) is not int or part['frets'] <= 0:
        raise ValueError('Declared finite fret bounds required for directional octave search')
    pitches = list(map(F, _solve(upper)['pitches'])); capo = part.get('capo', 0)
    if direction == 'up':
        maximum = int((max(part['tuning']) + capo + part['frets'] - max(pitches)) // 12)
        shifts = range(1, maximum + 1)
    else:
        maximum = int((min(pitches) - min(part['tuning']) - capo) // 12)
        shifts = range(-1, -maximum - 1, -1)
    for shift in shifts:
        wanted = deepcopy(current); wanted['octave'] += shift
        try:
            result, contacts = _placed_candidate(upper, wanted, before)
            counts = {12 * (r['octave'] + 1) + r['pitch_class']: r['count'] for r in model['observations']['register_context']['counts']}
            candidates.append((result, dict(kind='next_feasible_directional_octave', octave=wanted['octave'],
                shift_semitones=12 * shift, contacts=contacts,
                original_written_support=[counts.get(int(F(p)), 0) for p in _solve(result)['pitches']])))
            break
        except ValueError as error:
            refused.append(dict(octave=wanted['octave'], shift_semitones=12 * shift, reason=str(error)))
    if len(candidates) == 1 and not refused:
        refused.append(dict(reason='NO_DIRECTIONAL_OCTAVE_WITHIN_DECLARED_GEOMETRY'))
    return candidates, refused


def options(upper, intent, register_direction):
    """Current-context choices without release, mutation or hidden lower data."""
    validate_controls(dict(context_policy=POLICY, melody=0, intent=intent, register=0, register_direction=register_direction, seed=0))
    model, _, _ = _shape(upper)
    if model['schema'] != SCHEMA_V2: raise ValueError('Version2 required')
    before = _realize(upper)
    movement, movement_refused = _movement_candidates(upper, before, intent)
    register, register_refused = _register_candidates(upper, before, register_direction)
    return dict(movement=[r for _, r in movement], movement_refused=movement_refused,
                register=[r for _, r in register], register_refused=register_refused)


def _intervene_v2(upper, controls, before):
    result = deepcopy(upper); decisions = {}
    for axis in ('melody', 'register'):
        released = random.Random(f'melodic-movement-v2:{axis}:release:{controls["seed"]}').random() < controls[axis] / 100
        decision = dict(released=released, selected_kind='current', alternatives_evaluated=False)
        if released:
            current = before if axis == 'melody' else _realize(result)
            candidates, refused = (_movement_candidates(result, current, controls['intent']) if axis == 'melody'
                else _register_candidates(result, current, controls['register_direction']))
            if len(candidates) == 1 and refused:
                raise ValueError(f'Requested {axis} alternative unsupported: {refused}')
            index = random.Random(f'melodic-movement-v2:{axis}:selection:{controls["seed"]}').randrange(len(candidates))
            result = candidates[index][0]
            decision.update(alternatives_evaluated=True, candidates=[r for _, r in candidates], refused=refused,
                selected_index=index, selected_kind=candidates[index][1]['kind'], has_alternative=len(candidates) > 1)
        decisions[axis] = decision
    after = _realize(result); changed = _allowed_changes(upper, result, before, after, version2=True)
    model, refs, _ = _shape(upper)
    return result, dict(context_policy=POLICY, intent=controls['intent'], register_direction=controls['register_direction'],
        released={axis: row['released'] for axis, row in decisions.items()}, decisions=decisions,
        changed=bool(changed), changed_fact_refs=changed, relationships_changed=digest(result) != digest(upper),
        attack_refs=[r['attack_ref'] for r in model['attacks']], member_refs=refs,
        original_observations_unchanged=True,
        scope='Independent signed movement and common octave; explicit direction and nominal contacts, not artist preference. Source span is a conservative experiment policy, not a universal musical law.')
