"""Intentional keyboard-note register release through existing pitch owners.

Original same-part, same-pitch-class attacks supply octave choices. This is not
a harmonic suitability predictor. A compound request prepares that evidence
BEFORE editing melody; generated notes never become additional observations.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import math
import random

import musical_tier2 as music
import backing_motion_intervention as motion
import backing_pitch_ownership as owners
import backing_execution_constraints as execution
from source_observation_evidence import require, digest, operation_changes

POLICY = 'source_keyboard_note_register'
COMPOUND = 'backing_motion_with_note_register'


def _body(upper):
    core = upper['musical_relationships']
    if core.get('schema') in owners.SCHEMAS:
        core = core['core']
    return owners._body(core)


def _note(context, event):
    part = context['documents'][f"track-{event['part_id']}.json"]
    beat = part['measures'][event['bar']-1]['voices'][event['voice']]['beats'][event['beat']]
    return part, beat, beat['notes'][event['note']]


def _plain(context, event):
    part, beat, note = _note(context, event)
    if event['pitch'] is None or F(event['pitch']).denominator != 1 or F(event['duration_q']) <= 0:
        raise ValueError('KNOWN_POSITIVE_DURATION_PITCH_REQUIRED')
    if set(note) - {'string', 'fret'} or set(beat) - (motion.PLAIN_BEAT | {'chord'}):
        raise ValueError('PLAIN_KEYBOARD_NOTATION_REQUIRED')
    chord = beat.get('chord')
    if chord is not None and (type(chord) is not dict or set(chord) - {'text', 'width'}):
        raise ValueError('UNINTERPRETED_CHORD_DIAGRAM')
    motion.original_contact(part, note, event['pitch'])
    return part, beat, note


def prepare(upper, target_ref):
    """Evidence comes from the unchanged supplied upper, never an external score."""
    from connected_tier2 import realize
    require(upper, dict(register=100))
    return _original_options(realize(upper), upper['source_origin'], target_ref)


def _original_options(before, origin, target_ref):
    """Canonical evidence from hash-bound original facts, also used to check it."""
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    if digest(before) != origin['facts_sha256']:
        raise ValueError('ORIGINAL_REGISTER_EVIDENCE_CHANGED')
    documents = project_documents(before)
    lower = extract_documents(documents)
    context = dict(documents=documents, events={e['id']: e for e in lower['events']})
    if target_ref not in context['events']:
        raise ValueError('UNKNOWN_REGISTER_OCCURRENCE')
    target = context['events'][target_ref]
    part, beat, note = _plain(context, target)
    if type(part.get('instrumentId')) is not int or not 0 <= part['instrumentId'] <= 23:
        raise ValueError('OUTSIDE_PLAIN_KEYBOARD_PROGRAM_SCOPE')
    from voicing_register import tie_relationships
    from execution_dependencies import build as dependency_graph
    written_ties = tie_relationships(lower)
    dependencies = dependency_graph(before)
    pinned = set(dependencies['pinned_members'])
    pinned.update(r for edge in written_ties['links'] for r in (edge['origin'], edge['destination']))
    pinned.update(edge['destination'] for edge in written_ties['unresolved'])
    # The accepted HP detector does not establish keyboard endpoints. Do not
    # invent a successor and call a plain-looking later note independent.
    for edge in dependencies['edges']:
        if edge['kind'] == 'hopo' and any(owners.address(r)[1] == target['part_id'] for r in edge['member_refs']):
            raise ValueError('UNKNOWN_KEYBOARD_HOPO_EXECUTION')
    if target_ref in pinned:
        raise ValueError('REGISTER_EXECUTION_DEPENDENCY')
    # Incoming/outgoing dependencies and invalid written clocks remain guarded.
    guard = execution.build(before, [target_ref])
    if any(target_ref in row['member_refs'] for row in guard['obligations']):
        raise ValueError('REGISTER_EXECUTION_DEPENDENCY')
    pitch = int(F(target['pitch'])); pc = pitch % 12
    populations = defaultdict(list); refused = []
    for event in context['events'].values():
        if event['id'] == target_ref or event['part_id'] != target['part_id'] or event['pitch'] is None:
            continue
        p = F(event['pitch'])
        if p.denominator != 1 or int(p) % 12 != pc:
            continue
        if event['id'] in pinned:
            refused.append(dict(ref=event['id'], reason='REGISTER_EXECUTION_DEPENDENCY'))
            continue
        try:
            _plain(context, event)
        except ValueError as error:
            refused.append(dict(ref=event['id'], reason=str(error)))
            continue
        populations[int(p)//12].append(event['id'])
    options = []; rejected = []
    for register, refs in sorted(populations.items()):
        # The SAME pitch = anchor + interval equation used by the inverse.
        proposed = int(F(music.relation(anchor=str(pc), interval=str(12*register))['pitch']))
        fret = proposed - part['tuning'][note['string']] - (part.get('capo') or 0)
        row = dict(register=register, pitch=proposed, fret=fret,
                   donor_refs=sorted(set(refs)))
        if fret < 0 or (part.get('frets') is not None and fret > part['frets']):
            rejected.append(dict(row, reason='FIXED_NOTATION_CONTACT_LIMIT')); continue
        try:
            execution.proposed(guard, before, [target_ref],
                               {target_ref: dict(string=note['string'], fret=fret)})
        except ValueError as error:
            rejected.append(dict(row, reason=str(error))); continue
        options.append(row)
    return dict(before=before, target=deepcopy(target), options=options,
                rejected=rejected, excluded_donors=refused, source_origin=deepcopy(origin),
                evidence_facts_sha256=digest(before), pitch_class=pc, string=note['string'],
                execution_constraints=guard,
                meaning='Original same-part same-PC registers; complete new voicing and musical suitability are NOT witnessed or inferred')


def sample(prepared, level, seed):
    if type(level) not in (int, float) or not math.isfinite(level) or not 0 <= level <= 100 or type(seed) is not int:
        raise ValueError('FINITE_REGISTER_RELEASE_AND_INTEGER_SEED_REQUIRED')
    rng = random.Random(seed); released = rng.random() < level/100
    decision = dict(released=released, changed=False, source_origin=deepcopy(prepared['source_origin']),
                    options=deepcopy(prepared['options']), meaning=prepared['meaning'])
    if not released:
        return None, dict(decision, status='REGISTER_LOCKED')
    population = [o for o in prepared['options'] for _ in o['donor_refs']]
    if not population:
        return None, dict(decision, status='NO_ORIGINAL_REGISTER_ALTERNATIVES')
    chosen = deepcopy(rng.choice(population))
    return chosen, dict(decision, chosen=chosen, changed=chosen['pitch'] != int(F(prepared['target']['pitch'])),
                        status='ORIGINAL_REGISTER_CHOICE')


def apply(upper, prepared, choice, *, allowed_prior_refs=()):
    """Update ONE allowed owner; preserve existing dependency links exactly."""
    from connected_tier2 import realize
    if choice not in prepared['options'] or upper['source_origin'] != prepared['source_origin']:
        raise ValueError('UNSUPPORTED_REGISTER_CHOICE_OR_ORIGIN')
    if digest(prepared['before']) != prepared['evidence_facts_sha256'] or prepared['evidence_facts_sha256'] != upper['source_origin']['facts_sha256']:
        raise ValueError('ORIGINAL_REGISTER_EVIDENCE_CHANGED')
    canonical = _original_options(prepared['before'], prepared['source_origin'], prepared['target']['id'])
    if canonical != prepared:
        raise ValueError('REGISTER_PREPARATION_NOT_ORIGINAL: target or observations changed')
    before = realize(upper); result = deepcopy(upper); ref = prepared['target']['id']
    # This stage accepts only the explicitly declared preceding melody edit.
    # It is not a public bypass for relearning or arbitrary edited inputs.
    allowed_facts = set()
    if type(allowed_prior_refs) not in (tuple, list) or len(set(allowed_prior_refs)) != len(allowed_prior_refs):
        raise ValueError('EXPLICIT_PRIOR_OCCURRENCES_REQUIRED')
    for prior in allowed_prior_refs:
        _, part, bar, voice, beat, note = owners.address(prior)
        base = f'track-{part}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}/notes/{note}'
        allowed_facts.update((base+'/string', base+'/fret'))
    original = {r['id']: r for r in prepared['before']['facts']}
    current = {r['id']: r for r in before['facts']}
    if set(original) != set(current) or any(current[k] != v for k, v in original.items() if k not in allowed_facts):
        raise ValueError('UNAUTHORIZED_PRIOR_REGISTER_INPUT')
    authorized = deepcopy(prepared['before'])
    for row in authorized['facts']:
        if row['id'] in allowed_facts and 'value' in current[row['id']]:
            row['value'] = deepcopy(current[row['id']]['value'])
    if before != authorized:
        raise ValueError('UNAUTHORIZED_PRIOR_REGISTER_STRUCTURE')
    execution.validate(prepared['execution_constraints'], before, [ref])
    core = result['musical_relationships']; body = _body(result)
    matches = [(g, m) for g in body['coattacks'] for m in g['members'] if m['id'] == ref]
    if len(matches) != 1:
        raise ValueError('UNIQUE_REGISTER_OWNER_REQUIRED')
    group, member = matches[0]
    if core.get('schema') in owners.SCHEMAS:
        linked = {r[k] for r in core['relationships'] for k in ('occurrence_ref', 'backing_ref')}
        if ref in linked:
            raise ValueError('REGISTER_BACKING_DEPENDENCY_LOCK: selected note owns or anchors another pitch relationship')
    if group['bass_register_anchor'] is None or any(m['voicing_interval'] is None for m in group['members']):
        raise ValueError('UNSUPPORTED_MIXED_REGISTER_OWNER')
    pitches = {m['id']: F(music.member_pitch(group, m)) for m in group['members']}
    if pitches[ref] != F(prepared['target']['pitch']):
        raise ValueError('REGISTER_TARGET_CHANGED_DURING_COMPOUND')
    pitches[ref] = F(choice['pitch']); anchor = min(pitches.values())
    group['bass_register_anchor'] = str(anchor)
    for m in group['members']:
        m['voicing_interval'] = music.relation(anchor=str(anchor), pitch=str(pitches[m['id']]))['interval']
    if 'ensemble_coattacks' in body:
        # Plain models store derived views; backing/rhythm wrappers rebuild
        # theirs on expansion. Refresh only views, never relift the owners.
        from group_rhythm_relations import refresh
        refresh(body)
    if core.get('schema') in owners.SCHEMAS:
        owners.assert_preserved(upper['musical_relationships'], core)
    after = realize(result)
    expected = deepcopy(before); fact = motion.pointer(prepared['target']) + '/fret'
    rows = [r for r in expected['facts'] if r['id'] == fact]
    if len(rows) != 1 or rows[0]['type'] != 'integer':
        raise ValueError('INTEGER_NOTATION_CONTACT_REQUIRED')
    rows[0]['value'] = choice['fret']
    if after != expected:
        raise ValueError('REGISTER_CHANGED_LOCKED_SCORE_FIELDS')
    execution.validate(prepared['execution_constraints'], after, [ref])
    return result


from source_observation_evidence import controlled_update as _controlled_update
@_controlled_update
def intervene(upper, controls):
    from connected_tier2 import realize
    if type(controls) is not dict or controls.get('context_policy') not in (POLICY, COMPOUND):
        raise ValueError('EXPLICIT_NOTE_REGISTER_POLICY_REQUIRED')
    compound = controls['context_policy'] == COMPOUND
    required = {'context_policy', 'register', 'target_ref', 'seed'} | ({'melody_controls'} if compound else set())
    if set(controls) != required:
        raise ValueError('EXPLICIT_NOTE_REGISTER_CONTROLS_REQUIRED')
    owners.address(controls['target_ref'])
    level = controls['register']; seed = controls['seed']
    if type(level) not in (int, float) or not math.isfinite(level) or not 0 <= level <= 100 or type(seed) is not int:
        raise ValueError('FINITE_REGISTER_RELEASE_AND_INTEGER_SEED_REQUIRED')
    before = realize(upper)
    if compound:
        motion.validate_controls(controls['melody_controls'])
    if level == 0 and (not compound or controls['melody_controls']['melody'] == 0):
        return deepcopy(upper), dict(status='EXACT_ZERO_LOCK', released=False,
            **operation_changes(before, before, before,
                initial_relationships=upper['musical_relationships'],
                final_relationships=upper['musical_relationships']))
    # Both option sets are derived from this untouched upper. Later preparation
    # inside the existing melody operation receives that SAME input as well.
    prepared = prepare(upper, controls['target_ref']) if level else None
    chosen, decision = sample(prepared, level, seed) if prepared else (None, dict(released=False, changed=False))
    if compound:
        edited, melody_decision = motion.intervene(upper, controls['melody_controls'])
        decision['melody'] = melody_decision
    else:
        edited = deepcopy(upper)
    after_melody = realize(edited)
    if chosen is not None and decision['changed']:
        edited = apply(edited, prepared, chosen,
                       allowed_prior_refs=controls['melody_controls']['target_refs'] if compound else ())
    if edited['source_origin'] != upper['source_origin']:
        raise ValueError('ORIGINAL_OBSERVATION_ORIGIN_CHANGED')
    decision['status'] = 'COMPOUND_REGISTER_RESULT' if compound else 'REGISTER_RESULT'
    decision.update(operation_changes(before, after_melody, realize(edited),
        initial_relationships=upper['musical_relationships'],
        final_relationships=edited['musical_relationships']))
    return edited, decision
