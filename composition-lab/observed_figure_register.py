"""One explicit guitar figure's octave placement, using original observations.

This is a coordinated register choice, not inferred phrase identity or a ranking
of musical quality. Optional retained observations also support saving a plain
melody edit before a separate register adjustment. Original observations stay
fixed; current pitches and physical context determine the available choices.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import math
import random

import backing_motion_intervention as motion
import backing_pitch_ownership as backing
import backing_execution_constraints as execution
import figure_register_ownership as groups
from observed_note_register import _plain, _note
from source_observation_evidence import require, digest, operation_changes

POLICY = 'observed_guitar_figure_register'
STANDALONE = 'source_guitar_figure_register'
EXPRESSIVE = 'source_expressive_figure_register'
MUTED = 'source_muted_figure_register'
CURRENT_STRINGS = 'current_strings'
MINIMUM_STRING_CHANGES = 'minimum_string_changes'


def _current_context(current, refs, *, expressive_wrapper=None, muted_wrapper=None):
    """Shared existing target/execution qualification, without donor collection."""
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    from execution_dependencies import build as execution_graph
    from voicing_register import tie_relationships

    documents = project_documents(current)
    lower = extract_documents(documents)
    events = {event['id']: event for event in lower['events']}
    selected = [events[ref] for ref in refs]
    if len({(e['part_id'], e['voice']) for e in selected}) != 1:
        raise ValueError('ONE_FOCAL_GUITAR_VOICE_REQUIRED')
    part_id = selected[0]['part_id']
    part = documents[f'track-{part_id}.json']
    if type(part.get('instrumentId')) is not int or not 24 <= part['instrumentId'] <= 31:
        raise ValueError('OUTSIDE_DECLARED_GUITAR_PROGRAM_SCOPE')
    context = dict(documents=documents, events=events)
    dependencies = execution_graph(current)
    ties = tie_relationships(lower)
    pinned = set(dependencies['pinned_members'])
    pinned.update(ref for edge in ties['links'] for ref in (edge['origin'], edge['destination']))
    pinned.update(edge['destination'] for edge in ties['unresolved'])
    if expressive_wrapper is not None and muted_wrapper is not None:
        raise ValueError('ONE_EXPLICIT_FIGURE_EXECUTION_PROFILE_REQUIRED')
    if muted_wrapper is not None:
        if muted_wrapper.get('schema') != groups.MUTED_SCHEMA:
            raise ValueError('EXPLICIT_MUTED_REGISTER_OWNER_REQUIRED')
        groups.validate_execution(muted_wrapper, current)
        guard = None
    elif expressive_wrapper is not None:
        if expressive_wrapper.get('schema') != groups.EXPRESSIVE_SCHEMA:
            raise ValueError('EXPLICIT_EXPRESSIVE_REGISTER_OWNER_REQUIRED')
        groups.validate_execution(expressive_wrapper, current)
        guard = None
    else:
        guard = execution.build(current, refs)
        if pinned.intersection(refs) or any(set(row['member_refs']).intersection(refs) for row in guard['obligations']):
            raise ValueError('FIGURE_EXECUTION_DEPENDENCY')
        for event in selected:
            _plain(context, event)
    return dict(documents=documents, events=events, pinned=pinned, execution_constraints=guard)


def prepare_original(upper, refs, *, expressive=False, muted=False, observation_profile=None):
    from connected_tier2 import realize
    from figure_register_observations import WRITTEN_PROFILE
    if (muted and (expressive or observation_profile != WRITTEN_PROFILE)
            or not muted and observation_profile is not None):
        raise ValueError('EXPLICIT_ORIGINAL_REGISTER_OBSERVATION_PROFILE_REQUIRED')
    require(upper, dict(register=100))
    original = realize(upper)
    context = _current_context(original, refs,
        expressive_wrapper=upper['musical_relationships'] if expressive else None,
        muted_wrapper=upper['musical_relationships'] if muted else None)
    documents, events, pinned = context['documents'], context['events'], context['pinned']
    part_id = events[refs[0]]['part_id']
    donors = defaultdict(list)
    excluded = []
    for event in events.values():
        if event['part_id'] != part_id or event['id'] in refs or event['pitch'] is None:
            continue
        try:
            if not muted and event['id'] in pinned:
                raise ValueError('SOURCE_EXECUTION_DEPENDENCY')
            _plain(context, event)
        except ValueError as error:
            excluded.append(dict(ref=event['id'], reason=str(error)))
            continue
        donors[int(F(event['pitch']))].append(event['id'])
    result = dict(original=original, documents=documents, events=events,
                  source_origin=deepcopy(upper['source_origin']),
                  donors=dict(donors), excluded=excluded,
                  execution_constraints=context['execution_constraints'])
    if expressive:
        result['expressive_wrapper'] = deepcopy(upper['musical_relationships'])
    if muted:
        result['muted_wrapper'] = deepcopy(upper['musical_relationships'])
    return result


def _observed_pitches(prepared):
    return prepared['observed_counts'] if 'observed_counts' in prepared else prepared['donors']


def _support(prepared, pitches):
    if 'observed_counts' in prepared:
        return dict(observation_support={ref: dict(pitch_class=pitch % 12,
                    octave=pitch // 12 - 1, count=prepared['observed_counts'][pitch])
                    for ref, pitch in pitches.items()}, evidence_sha256=prepared['evidence_sha256'])
    return dict(donor_refs={ref: sorted(prepared['donors'][pitch]) for ref, pitch in pitches.items()})


def _contact_facts(current, events, contacts):
    replacements = {motion.pointer(events[ref]) + '/fret': contact['fret']
                    for ref, contact in contacts.items()}
    found = set()
    result = deepcopy(current)
    for row in result['facts']:
        if row['id'] in replacements:
            if row['type'] != 'integer':
                raise ValueError('EXISTING_INTEGER_CONTACT_REQUIRED')
            row['value'] = replacements[row['id']]
            found.add(row['id'])
    if found != set(replacements):
        raise ValueError('MISSING_REGISTER_CONTACT_OWNER')
    return result


def choices(prepared, current, refs, *, placement_policy=CURRENT_STRINGS):
    """Current pitches select relevant ORIGINAL evidence; they do not add votes."""
    if placement_policy == MINIMUM_STRING_CHANGES:
        return _placement_choices(prepared, current, refs)
    if placement_policy != CURRENT_STRINGS:
        raise ValueError('EXPLICIT_SUPPORTED_FIGURE_PLACEMENT_REQUIRED')
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents

    documents = project_documents(current)
    events = {event['id']: event for event in extract_documents(documents)['events']}
    selected = [events[ref] for ref in refs]
    context = dict(documents=documents, events=events)
    expressive = prepared.get('expressive_wrapper') or prepared.get('muted_wrapper')
    selected_note = _note if expressive else _plain
    shifts = None
    for event in selected:
        selected_note(context, event)
        pitch = int(F(event['pitch']))
        supported = {p - pitch for p in _observed_pitches(prepared) if (p - pitch) % 12 == 0}
        shifts = supported if shifts is None else shifts.intersection(supported)
    options, refused = [], []
    for shift in sorted(shifts or ()):
        contacts = {}
        supported_pitches = {}
        reason = None
        for event in selected:
            part, _, note = selected_note(context, event)
            pitch = int(F(event['pitch'])) + shift
            fret = note['fret'] + shift
            if fret < 0 or (part.get('frets') is not None and fret > part['frets']):
                reason = 'CURRENT_STRING_CONTACT_LIMIT'
            contacts[event['id']] = dict(string=note['string'], fret=fret)
            supported_pitches[event['id']] = pitch
        if reason is None:
            try:
                if expressive:
                    group = expressive['groups'][0]
                    moved = groups.shift(expressive, group['id'], group['octave'] + shift // 12)
                    groups.validate_execution(moved, _contact_facts(current, events, contacts))
                else:
                    execution.proposed(prepared['execution_constraints'], current, refs, contacts)
            except ValueError as error:
                reason = str(error)
        row = dict(shift_semitones=shift, contacts=contacts, **_support(prepared, supported_pitches))
        if reason is None:
            options.append(row)
        else:
            refused.append(dict(row, reason=reason))
    return options, refused


def _placement_choices(prepared, current, refs):
    """One vote per source-supported octave; contacts are a separate choice."""
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    from backing_motion_relations import minimum_string_changes

    if prepared.get('expressive_wrapper') is not None or prepared.get('execution_constraints') is None:
        raise ValueError('PLAIN_FIGURE_EXECUTION_SCOPE_REQUIRED')
    documents = project_documents(current)
    events = {e['id']: e for e in extract_documents(documents)['events']}
    selected = [events[r] for r in refs]
    context = dict(documents=documents, events=events)
    if len({(e['part_id'], e['voice']) for e in selected}) != 1:
        raise ValueError('ONE_FOCAL_GUITAR_VOICE_REQUIRED')
    notes = [_plain(context, event)[2] for event in selected]
    part = documents[f"track-{selected[0]['part_id']}.json"]
    shifts = None
    for event in selected:
        pitch = int(F(event['pitch']))
        supported = {p - pitch for p in prepared['donors'] if (p - pitch) % 12 == 0}
        shifts = supported if shifts is None else shifts.intersection(supported)
    options, refused = [], []
    for shift in sorted(shifts or ()):
        pitches = [int(F(e['pitch'])) + shift for e in selected]
        donor_refs = {e['id']: sorted(prepared['donors'][pitch]) for e, pitch in zip(selected, pitches)}
        physical = minimum_string_changes(pitches, [n['string'] for n in notes],
            part['tuning'], part.get('capo') or 0, max_fret=part.get('frets'))
        contacts = []
        for assignment in physical['assignments']:
            proposal = {ref: dict(contact) for ref, contact in zip(refs, assignment)}
            try:
                execution.proposed(prepared['execution_constraints'], current, refs, proposal)
            except ValueError as error:
                refused.append(dict(shift_semitones=shift, contacts=proposal,
                    donor_refs=donor_refs, reason=str(error)))
            else:
                contacts.append(proposal)
        if contacts:
            options.append(dict(shift_semitones=shift, contact_options=contacts,
                donor_refs=donor_refs, minimum_string_changes=physical['minimum_changes']))
        elif not physical['assignments']:
            refused.append(dict(shift_semitones=shift, donor_refs=donor_refs,
                reason='NO_NOMINAL_CONTACT_ASSIGNMENT'))
    return options, refused


def validate_controls(controls):
    if type(controls) is not dict or controls.get('context_policy') not in (POLICY, STANDALONE, EXPRESSIVE, MUTED):
        raise ValueError('EXPLICIT_FIGURE_REGISTER_CONTROLS_REQUIRED')
    compound = controls['context_policy'] == POLICY
    required = {'context_policy', 'register', 'seed'} | ({'melody_controls'} if compound else {'physical'})
    optional = {'placement_policy'} if controls['context_policy'] == STANDALONE else set()
    if not required <= set(controls) or set(controls) - required - optional:
        raise ValueError('EXPLICIT_FIGURE_REGISTER_CONTROLS_REQUIRED')
    if 'placement_policy' in controls and (type(controls['placement_policy']) is not str or controls['placement_policy'] not in (CURRENT_STRINGS, MINIMUM_STRING_CHANGES)):
        raise ValueError('EXPLICIT_SUPPORTED_FIGURE_PLACEMENT_REQUIRED')
    level = controls['register']
    if type(level) not in (int, float) or not math.isfinite(level) or not 0 <= level <= 100 or type(controls['seed']) is not int:
        raise ValueError('FINITE_REGISTER_RELEASE_AND_INTEGER_SEED_REQUIRED')
    if compound:
        motion.validate_controls(controls['melody_controls'])
    elif type(controls['physical']) is not int or controls['physical'] not in (0, 100):
        raise ValueError('EXPLICIT_PHYSICAL_CONTACT_PERMISSION_REQUIRED')


from source_observation_evidence import controlled_update as _controlled_update
@_controlled_update
def intervene(upper, controls):
    from connected_tier2 import realize

    validate_controls(controls)
    retained = 'figure_register_observations' in upper['owned_parameters']
    if controls['context_policy'] == MUTED:
        return _intervene_muted(upper, controls)
    if retained and controls['register'] != 0 and (controls['context_policy'] == EXPRESSIVE
            or controls.get('placement_policy') == MINIMUM_STRING_CHANGES):
        raise ValueError('REGISTER_OBSERVATIONS_UNSUPPORTED_POLICY_SCOPE')
    if controls['context_policy'] == EXPRESSIVE:
        return _intervene_expressive(upper, controls)
    if controls.get('placement_policy') == MINIMUM_STRING_CHANGES:
        return _intervene_placement(upper, controls)
    level = controls['register']
    melody_controls = controls.get('melody_controls')
    melody_level = melody_controls['melody'] if melody_controls else 0
    physical = melody_controls['physical'] if melody_controls else controls['physical']
    incoming_group = upper['musical_relationships']
    if incoming_group.get('schema') != groups.SCHEMA:
        raise ValueError('PREOWNED_FIGURE_GROUP_REQUIRED')
    refs = melody_controls['target_refs'] if melody_controls else incoming_group['groups'][0]['occurrence_refs']
    if len(incoming_group['groups']) != 1 or incoming_group['groups'][0]['occurrence_refs'] != refs:
        raise ValueError('EXACT_EXISTING_FIGURE_SCOPE_REQUIRED')
    before = realize(upper)
    if level == 0 and melody_level == 0:
        return deepcopy(upper), dict(status='EXACT_ZERO_LOCK', released=False,
            **operation_changes(before, before, before,
                initial_relationships=upper['musical_relationships'],
                final_relationships=upper['musical_relationships']))
    # Retained observations migrate only the plain standalone register request.
    # The melody operation itself still requires original input.
    require(upper, controls if retained and melody_controls is None
            else dict(register=level, melody=melody_level))
    if retained:
        from figure_register_observations import validate_current, prepare_current, SLOT
        validate_current(upper)
    prepared = prepare_original(upper, refs) if level and not retained else None
    melody_input = deepcopy(upper)
    melody_input['musical_relationships'] = groups.expand(incoming_group)
    if melody_controls is not None:
        edited, melody_decision = motion.intervene(melody_input, melody_controls)
    else:
        edited = melody_input
        melody_decision = dict(status='NO_MELODY_OPERATION', changed=False)
    current = realize(edited)
    # The group owns the CURRENT intervals, including an unchanged destination
    # when melody remained locked. No reference pattern is silently substituted.
    grouped = groups.lift(edited['musical_relationships'], refs)
    # Only this named group's shape may change with the melody operation.
    # Every unrelated owner, backing ID and dependency remains byte-for-byte.
    if digest(grouped['core']) != digest(incoming_group['core']):
        raise ValueError('FIGURE_MELODY_CHANGED_UNRELATED_RELATIONSHIPS')
    if current == before and grouped != incoming_group:
        raise ValueError('UNCHANGED_MELODY_CHANGED_FIGURE_PARAMETERS')
    result = deepcopy(edited)
    result['musical_relationships'] = grouped
    if realize(result) != current:
        raise ValueError('FIGURE_LIFT_CHANGED_SOURCE')
    if retained:
        validate_current(result)
        prepared = prepare_current(result, current, refs) if level else None
    rng = random.Random('figure-register:' + str(controls['seed']))
    released = rng.random() < level / 100
    options, refused = choices(prepared, current, refs) if prepared else ([], [])
    choice = deepcopy(rng.choice(options)) if released and options else None
    original_group = grouped['groups'][0]
    if choice is not None:
        if choice['shift_semitones'] != 0 and physical == 0:
            raise ValueError('FIGURE_REGISTER_PHYSICAL_CONTACT_LOCK')
        octave = original_group['octave'] + choice['shift_semitones'] // 12
        result['musical_relationships'] = groups.shift(grouped, original_group['id'], octave)
        groups.assert_preserved(grouped, result['musical_relationships'], mutable_groups=[original_group['id']])
    restored = realize(result)
    expected = deepcopy(current)
    if choice is not None:
        for row in expected['facts']:
            for ref, contact in choice['contacts'].items():
                if row['id'] == motion.pointer(prepared['events'][ref]) + '/fret':
                    row['value'] = contact['fret']
    if restored != expected:
        raise ValueError('FIGURE_REGISTER_CHANGED_LOCKED_FIELDS')
    expanded = groups.expand(result['musical_relationships'])
    backing.assert_preserved(melody_input['musical_relationships'], expanded, mutable_refs=refs)
    if result['source_origin'] != upper['source_origin']:
        raise ValueError('ORIGINAL_OBSERVATION_ORIGIN_CHANGED')
    if retained:
        if result['owned_parameters'][SLOT] != upper['owned_parameters'][SLOT]:
            raise ValueError('ORIGINAL_REGISTER_EVIDENCE_CHANGED')
        validate_current(result)
    elif prepared and digest(prepared['original']) != upper['source_origin']['facts_sha256']:
        raise ValueError('ORIGINAL_REGISTER_EVIDENCE_CHANGED')
    decision = dict(status='FIGURE_REGISTER_RESULT', released=released,
                    **operation_changes(before, current, restored,
                        initial_relationships=upper['musical_relationships'],
                        final_relationships=result['musical_relationships']),
                    melody=melody_decision, choice=choice, options=options, refused=refused,
                    source_origin=deepcopy(upper['source_origin']),
                    meaning='One explicit figure; same pitch classes and internal shape. Uniform choice among feasible original-register intersections, not a learned preference or phrase identification.',
                    restriction='Current strings retained for this experiment; physical refusals are not claims of musical impossibility.')
    return result, decision


def _intervene_placement(upper, controls):
    """Plain group: shared octave plus necessary existing string parameters."""
    from connected_tier2 import realize

    wrapper = upper['musical_relationships']
    if wrapper.get('schema') != groups.SCHEMA or wrapper.get('core', {}).get('schema') != backing.EXECUTION_SCHEMA:
        raise ValueError('PLAIN_FIGURE_WITH_SHARED_EXECUTION_REQUIRED')
    before = realize(upper)
    if controls['register'] == 0:
        return deepcopy(upper), dict(status='EXACT_ZERO_LOCK', released=False, changed=False)
    group = wrapper['groups'][0]
    refs = group['occurrence_refs']
    prepared = prepare_original(upper, refs)
    options, refused = choices(prepared, before, refs, placement_policy=MINIMUM_STRING_CHANGES)
    rng = random.Random('figure-register:' + str(controls['seed']))
    released = rng.random() < controls['register'] / 100
    octave_choice = deepcopy(rng.choice(options)) if released and options else None
    choice = None
    if octave_choice is not None:
        # Extra fingerings do not give this register extra probability.
        contacts = deepcopy(rng.choice(octave_choice['contact_options']))
        choice = dict(shift_semitones=octave_choice['shift_semitones'], contacts=contacts,
            donor_refs=octave_choice['donor_refs'], minimum_string_changes=octave_choice['minimum_string_changes'],
            contact_option_count=len(octave_choice['contact_options']))
    result = deepcopy(upper)
    expected = deepcopy(before)
    mutable_strings = {}
    if choice is not None:
        contact_changed = any(_note(dict(documents=prepared['documents'], events=prepared['events']),
            prepared['events'][ref])[2][key] != value
            for ref, contact in choice['contacts'].items() for key, value in contact.items())
        if contact_changed and controls['physical'] == 0:
            raise ValueError('FIGURE_REGISTER_PHYSICAL_CONTACT_LOCK')
        result['musical_relationships'] = groups.shift(wrapper, group['id'],
            group['octave'] + choice['shift_semitones'] // 12)
        parameters = result['owned_parameters']['source_choices']
        replacements = {}
        for ref, contact in choice['contacts'].items():
            pointer = motion.pointer(prepared['events'][ref])
            for key, value in contact.items():
                replacements[pointer + '/' + key] = value
            original = _note(dict(documents=prepared['documents'], events=prepared['events']), prepared['events'][ref])[2]
            if contact['string'] != original['string']:
                ident = pointer + '/string'
                matches = [p for p in parameters if p['fact_ref'] == ident]
                if len(matches) != 1:
                    raise ValueError('EXACTLY_ONE_EXISTING_STRING_OWNER_REQUIRED')
                mutable_strings[ident] = deepcopy(matches[0]['parameter'])
                matches[0]['parameter'] = dict(normalized=str(contact['string']), negative_zero=False)
        found = set()
        for row in expected['facts']:
            if row['id'] in replacements:
                if row['type'] != 'integer':
                    raise ValueError('EXISTING_INTEGER_CONTACT_REQUIRED')
                row['value'] = replacements[row['id']]
                found.add(row['id'])
        if found != set(replacements):
            raise ValueError('MISSING_REGISTER_CONTACT_OWNER')
    groups.assert_preserved(wrapper, result['musical_relationships'], mutable_groups=[group['id']])
    history = deepcopy(result)
    history['musical_relationships'] = wrapper
    for row in history['owned_parameters']['source_choices']:
        if row['fact_ref'] in mutable_strings:
            row['parameter'] = mutable_strings[row['fact_ref']]
    if digest(history) != digest(upper):
        raise ValueError('REGISTER_PLACEMENT_CHANGED_UNRELATED_OWNERS')
    if realize(result) != expected:
        raise ValueError('FIGURE_REGISTER_CHANGED_LOCKED_FIELDS')
    if result['source_origin'] != upper['source_origin'] or digest(prepared['original']) != upper['source_origin']['facts_sha256']:
        raise ValueError('ORIGINAL_REGISTER_EVIDENCE_CHANGED')
    return result, dict(status='PLAIN_FIGURE_REGISTER_PLACEMENT_RESULT', released=released,
        changed=choice is not None and choice['shift_semitones'] != 0,
        choice=choice, options=options, refused=refused, source_origin=deepcopy(upper['source_origin']),
        meaning='One source-supported common octave, then an equal choice among surviving minimum string-change contacts. Original pitch observations are not contact preferences.',
        restriction='Plain selected notes only. Minimum-count string changes are geometric; no reach, comfort, acoustic-equivalence or artistic preference is inferred. Additional string changes are not searched after minimum assignments fail execution checks.')


def _intervene_expressive(upper, controls):
    """Change only the shared octave of a pre-owned complete written figure."""
    from connected_tier2 import realize

    wrapper = upper['musical_relationships']
    if wrapper.get('schema') != groups.EXPRESSIVE_SCHEMA:
        raise ValueError('EXPLICIT_EXPRESSIVE_REGISTER_OWNER_REQUIRED')
    before = realize(upper)
    level = controls['register']
    if level == 0:
        return deepcopy(upper), dict(status='EXACT_ZERO_LOCK', released=False, changed=False)
    group = wrapper['groups'][0]
    refs = group['occurrence_refs']
    prepared = prepare_original(upper, refs, expressive=True)
    options, refused = choices(prepared, before, refs)
    rng = random.Random('figure-register:' + str(controls['seed']))
    released = rng.random() < level / 100
    choice = deepcopy(rng.choice(options)) if released and options else None
    result = deepcopy(upper)
    if choice is not None:
        if choice['shift_semitones'] != 0 and controls['physical'] == 0:
            raise ValueError('FIGURE_REGISTER_PHYSICAL_CONTACT_LOCK')
        result['musical_relationships'] = groups.shift(wrapper, group['id'],
            group['octave'] + choice['shift_semitones'] // 12)
    groups.assert_preserved(wrapper, result['musical_relationships'], mutable_groups=[group['id']])
    expected = before if choice is None else _contact_facts(before, prepared['events'], choice['contacts'])
    if realize(result) != expected:
        raise ValueError('FIGURE_REGISTER_CHANGED_LOCKED_FIELDS')
    if result['source_origin'] != upper['source_origin'] or digest(prepared['original']) != upper['source_origin']['facts_sha256']:
        raise ValueError('ORIGINAL_REGISTER_EVIDENCE_CHANGED')
    return result, dict(status='EXPRESSIVE_FIGURE_REGISTER_RESULT', released=released,
        changed=choice is not None and choice['shift_semitones'] != 0,
        choice=choice, options=options, refused=refused,
        source_origin=deepcopy(upper['source_origin']),
        meaning='One common octave for complete written ties and the same relative bend, vibrato and symbolic exit. Individual original pitches supply register choices, not a complete observed expressive figure or preference.',
        restriction='Current strings and every other field remain fixed. The source slide endpoint stays unknown; pinned rendering is not proof of identical physical execution.')


def _intervene_muted(upper, controls):
    """Saved muted-register adjustment: fixed observations, only common k moves."""
    from connected_tier2 import realize
    from figure_register_observations import SLOT, MUTED_SCHEMA, validate_current, prepare_current

    wrapper = upper['musical_relationships']
    if wrapper.get('schema') != groups.MUTED_SCHEMA:
        raise ValueError('EXPLICIT_MUTED_REGISTER_OWNER_REQUIRED')
    before = realize(upper)
    level = controls['register']
    if level == 0:
        return deepcopy(upper), dict(status='EXACT_ZERO_LOCK', released=False, changed=False)
    if SLOT not in upper['owned_parameters'] or upper['owned_parameters'][SLOT]['schema'] != MUTED_SCHEMA:
        raise ValueError('ORIGINAL_MUTED_REGISTER_OBSERVATIONS_REQUIRED')
    require(upper, controls)
    validate_current(upper)
    group = wrapper['groups'][0]; refs = group['occurrence_refs']
    prepared = prepare_current(upper, before, refs)
    options, refused = choices(prepared, before, refs)
    rng = random.Random('figure-register:' + str(controls['seed']))
    released = rng.random() < level / 100
    choice = deepcopy(rng.choice(options)) if released and options else None
    result = deepcopy(upper)
    if choice is not None:
        if choice['shift_semitones'] != 0 and controls['physical'] == 0:
            raise ValueError('FIGURE_REGISTER_PHYSICAL_CONTACT_LOCK')
        result['musical_relationships'] = groups.shift(wrapper, group['id'],
            group['octave'] + choice['shift_semitones'] // 12)
    groups.assert_preserved(wrapper, result['musical_relationships'], mutable_groups=[group['id']])
    expected = before if choice is None else _contact_facts(before, prepared['events'], choice['contacts'])
    if realize(result) != expected:
        raise ValueError('FIGURE_REGISTER_CHANGED_LOCKED_FIELDS')
    if result['owned_parameters'][SLOT] != upper['owned_parameters'][SLOT]:
        raise ValueError('ORIGINAL_REGISTER_EVIDENCE_CHANGED')
    validate_current(result)
    return result, dict(status='MUTED_FIGURE_REGISTER_RESULT', released=released,
        changed=choice is not None and choice['shift_semitones'] != 0,
        choice=choice, options=options, refused=refused,
        source_origin=deepcopy(upper['source_origin']),
        meaning='Same fixed figure, pitch classes, palm-mute declarations and timing; one common octave. Qualified original written occurrences supply register availability, not independent examples, a whole observed muted riff or learned preference.',
        restriction='Current strings and all other owners/fields stay fixed; no melody or placement migration. Written mute preservation does not establish acoustic muting authenticity.')
