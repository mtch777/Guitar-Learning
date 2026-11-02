"""Original register counts for explicit, versioned guitar-figure scopes.

The table contains aggregate counts, never an original score or an occurrence
pitch stream. Pitch = 12 * (octave + 1) + pitch_class. Current pitches and
contacts select from these fixed observations. Counts are qualified original
written occurrences, not independent examples or sampling weights. Schema1
supports the existing plain melody/register sequence; schema2 supports only
the common octave of the fixed palm-mute-only group.
Checksums bind integrity and supported scope; they do not prove authenticity.
"""
from copy import deepcopy
import math
import re

import backing_pitch_ownership as backing
import figure_register_ownership as groups
from source_observation_evidence import digest, validate_origin

SLOT = 'figure_register_observations'
SCHEMA = 'source-figure-register-observations/1'
MUTED_SCHEMA = 'source-figure-register-observations/2'
PROFILE = 'same-part-plain-original-registers/1'
WRITTEN_PROFILE = 'same-part-plain-written-registers/1'
POLICY = 'source_guitar_figure_register'
MUTED_POLICY = 'source_muted_figure_register'
FIELDS = {'schema', 'source_origin', 'scope', 'qualification', 'counts',
          'protected_state_sha256', 'evidence_sha256'}


def evidence(model):
    return {key: deepcopy(value) for key, value in model.items() if key != 'evidence_sha256'}


def validate(model, source_origin):
    """Typed table validation only: no inverse, source query or current rebuild."""
    if type(model) is not dict or set(model) != FIELDS or model['schema'] not in (SCHEMA, MUTED_SCHEMA):
        raise ValueError('REGISTER_OBSERVATIONS_SCHEMA_REQUIRED')
    validate_origin(source_origin)
    validate_origin(model['source_origin'])
    profile = PROFILE if model['schema'] == SCHEMA else WRITTEN_PROFILE
    if model['source_origin'] != source_origin or model['qualification'] != profile:
        raise ValueError('REGISTER_OBSERVATIONS_ORIGIN_OR_QUALIFICATION_CONFLICT')
    scope = model['scope']
    if type(scope) is not dict or set(scope) != {'group_id', 'part_id', 'excluded_member_refs'}:
        raise ValueError('REGISTER_OBSERVATIONS_SCOPE_REQUIRED')
    refs = scope['excluded_member_refs']
    if (type(scope['part_id']) is not int or scope['part_id'] < 0
            or groups.identifier(refs) != scope['group_id']
            or any(backing.address(ref)[1] != scope['part_id'] for ref in refs)):
        raise ValueError('REGISTER_OBSERVATIONS_SCOPE_CONFLICT')
    if type(model['counts']) is not list:
        raise ValueError('REGISTER_OBSERVATIONS_TYPED_COUNTS_REQUIRED')
    keys = []
    for row in model['counts']:
        if (type(row) is not dict or set(row) != {'pitch_class', 'octave', 'count'}
                or any(type(row[key]) is not int for key in row)
                or not 0 <= row['pitch_class'] < 12 or row['count'] <= 0):
            raise ValueError('REGISTER_OBSERVATIONS_TYPED_COUNTS_REQUIRED')
        keys.append((row['pitch_class'], row['octave']))
    if keys != sorted(set(keys)):
        raise ValueError('REGISTER_OBSERVATIONS_CANONICAL_COUNTS_REQUIRED')
    for name in ('protected_state_sha256', 'evidence_sha256'):
        if type(model[name]) is not str or re.fullmatch('[0-9a-f]{64}', model[name]) is None:
            raise ValueError('REGISTER_OBSERVATIONS_CHECKSUM_REQUIRED')
    if digest(evidence(model)) != model['evidence_sha256']:
        raise ValueError('REGISTER_OBSERVATIONS_CHECKSUM_CONFLICT')


def protected_state(upper, scope):
    """Protect the exact state, allowing only each version's declared changes.

    Legacy plain scope normalizes group/backing and redacts selected interval
    and string values for its melody/register sequence. Muted schema2 redacts
    ONLY the common octave; its entire shape, strings and execution contract
    remain fixed. Both protect group IDs, backing links and all unrelated data.
    Bare backing is a legacy melody intermediate, not a muted entry route.
    """
    result = deepcopy(upper)
    result.pop('input', None)
    result.pop('derived_views', None)
    result['owned_parameters'].pop(SLOT, None)
    model = result['musical_relationships']
    refs = scope['excluded_member_refs']
    if model.get('schema') == groups.MUTED_SCHEMA:
        groups.expand(model)
        if (model['groups'][0]['id'] != scope['group_id'] or
                model['groups'][0]['occurrence_refs'] != refs):
            raise ValueError('REGISTER_OBSERVATIONS_GROUP_CONFLICT')
        # This route does not migrate melody or physical placement. Retain the
        # whole group/contract/backing/core; erase ONLY its common octave.
        model['groups'][0]['octave'] = '<selected-common-octave>'
        return dict(upper=result, group_scope=deepcopy(scope))
    if model.get('schema') == groups.SCHEMA:
        if (len(model['groups']) != 1 or model['groups'][0]['id'] != scope['group_id']
                or model['groups'][0]['occurrence_refs'] != refs):
            raise ValueError('REGISTER_OBSERVATIONS_GROUP_CONFLICT')
        model = groups.expand(model)
    elif model.get('schema') == backing.EXECUTION_SCHEMA:
        backing.expand(model)
    else:
        raise ValueError('REGISTER_OBSERVATIONS_PLAIN_EXECUTION_SCOPE_REQUIRED')
    if model.get('schema') != backing.EXECUTION_SCHEMA:
        raise ValueError('REGISTER_OBSERVATIONS_PLAIN_EXECUTION_SCOPE_REQUIRED')
    selected = set(refs)
    found = set()
    for row in model['relationships']:
        if row['occurrence_ref'] in selected:
            row['interval_semitones'] = '<selected-current-interval>'
            found.add(row['occurrence_ref'])
    if found != selected:
        raise ValueError('REGISTER_OBSERVATIONS_MISSING_RELATIONSHIP')
    positions = upper['owned_parameters']['physical_positions']
    string_refs = []
    for ref in refs:
        rows = [row for row in positions if row['occurrence_ref'] == ref]
        if len(rows) != 1:
            raise ValueError('REGISTER_OBSERVATIONS_PHYSICAL_SCOPE_CONFLICT')
        string_refs.append(rows[0]['string_ref'])
    if len(set(string_refs)) != len(refs):
        raise ValueError('REGISTER_OBSERVATIONS_PHYSICAL_SCOPE_CONFLICT')
    for ident in string_refs:
        rows = [row for row in result['owned_parameters']['source_choices'] if row['fact_ref'] == ident]
        if (len(rows) != 1 or set(rows[0]['parameter']) != {'normalized', 'negative_zero'}
                or rows[0]['parameter']['negative_zero'] is not False):
            raise ValueError('REGISTER_OBSERVATIONS_INTEGER_STRING_OWNER_REQUIRED')
        rows[0]['parameter']['normalized'] = '<selected-current-string>'
    result['musical_relationships'] = model
    return dict(upper=result, group_scope=deepcopy(scope))


def lift(upper, *, profile=None):
    """Forward preparation on original input; aggregate ALL qualified pitches."""
    if SLOT in upper['owned_parameters']:
        raise ValueError('REGISTER_OBSERVATIONS_ALREADY_PREPARED')
    wrapper = upper['musical_relationships']
    muted = wrapper.get('schema') == groups.MUTED_SCHEMA
    if muted and profile != WRITTEN_PROFILE:
        raise ValueError('EXPLICIT_PLAIN_WRITTEN_OBSERVATION_PROFILE_REQUIRED')
    if not muted and (wrapper.get('schema') != groups.SCHEMA or profile is not None):
        raise ValueError('REGISTER_OBSERVATIONS_PLAIN_GROUP_REQUIRED')
    group = wrapper['groups'][0]
    refs = group['occurrence_refs']
    # Reuse the approved existing qualification, without retaining its transient
    # original facts, per-note events, donor identities or source documents.
    from observed_figure_register import prepare_original
    prepared = prepare_original(upper, refs, muted=muted, observation_profile=profile)
    scope = dict(group_id=group['id'], part_id=backing.address(refs[0])[1],
                 excluded_member_refs=list(refs))
    counts = [dict(pitch_class=pitch % 12, octave=pitch // 12 - 1, count=len(donors))
              for pitch, donors in prepared['donors'].items()]
    counts.sort(key=lambda row: (row['pitch_class'], row['octave']))
    model = dict(schema=MUTED_SCHEMA if muted else SCHEMA, source_origin=deepcopy(upper['source_origin']),
                 scope=scope, qualification=WRITTEN_PROFILE if muted else PROFILE, counts=counts,
                 protected_state_sha256=digest(protected_state(upper, scope)))
    model['evidence_sha256'] = digest(model)
    validate(model, upper['source_origin'])
    return model


def validate_current(upper):
    """Policy history boundary, deliberately separate from structural realize."""
    model = upper['owned_parameters'][SLOT]
    validate(model, upper.get('source_origin'))
    muted = upper['musical_relationships'].get('schema') == groups.MUTED_SCHEMA
    if muted != (model['schema'] == MUTED_SCHEMA):
        raise ValueError('REGISTER_OBSERVATIONS_PROFILE_SCOPE_CONFLICT')
    if digest(protected_state(upper, model['scope'])) != model['protected_state_sha256']:
        raise ValueError('REGISTER_OBSERVATIONS_PROTECTED_STATE_CHANGED')
    return model


def supported_controls(controls):
    required = {'context_policy', 'register', 'physical', 'seed'}
    muted = type(controls) is dict and controls.get('context_policy') == MUTED_POLICY
    return (type(controls) is dict and required <= set(controls)
            and not set(controls) - required - (set() if muted else {'placement_policy'})
            and controls['context_policy'] in (POLICY, MUTED_POLICY)
            and controls.get('placement_policy', 'current_strings') == 'current_strings'
            and type(controls['register']) in (int, float)
            and math.isfinite(controls['register']) and 0 <= controls['register'] <= 100
            and type(controls['physical']) is int and controls['physical'] in (0, 100)
            and type(controls['seed']) is int)


def prepare_current(upper, current, refs):
    """Frozen original bins; CURRENT target geometry and execution qualification."""
    model = validate_current(upper)
    if refs != model['scope']['excluded_member_refs']:
        raise ValueError('REGISTER_OBSERVATIONS_GROUP_CONFLICT')
    from observed_figure_register import _current_context
    muted = model['schema'] == MUTED_SCHEMA
    result = _current_context(current, refs,
        muted_wrapper=upper['musical_relationships'] if muted else None)
    result.pop('pinned')
    if muted:
        result['muted_wrapper'] = deepcopy(upper['musical_relationships'])
    result['observed_counts'] = {
        12 * (row['octave'] + 1) + row['pitch_class']: row['count']
        for row in model['counts']}
    result['source_origin'] = deepcopy(model['source_origin'])
    result['evidence_sha256'] = model['evidence_sha256']
    return result
