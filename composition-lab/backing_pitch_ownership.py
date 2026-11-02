"""Owned cross-part pitch intervals. No selector, score cache, or generation policy.

The owned equation is the existing musical_tier2 pitch=anchor+interval.
Backing references are caller-specified original independent occurrences. Only
written activity at the focal attack is asserted, not acoustic sustain or role.
"""
from copy import deepcopy
import re

import group_rhythm_relations as rhythm
import musical_tier2 as music
import backing_written_tie_constraints as ties
import backing_execution_constraints as execution

LEGACY_SCHEMA = 'backing-relative-pitches/1'
SCHEMA = 'backing-relative-pitches/2'
EXECUTION_SCHEMA = 'backing-relative-pitches/3'
MEMBER_SCHEMA = 'backing-relative-pitches/4'
SCHEMAS = (LEGACY_SCHEMA, SCHEMA, EXECUTION_SCHEMA, MEMBER_SCHEMA)
TIED_SCHEMAS = (SCHEMA, EXECUTION_SCHEMA, MEMBER_SCHEMA)
EXECUTED_SCHEMAS = (EXECUTION_SCHEMA, MEMBER_SCHEMA)
PLAIN = 'musical-context-relations/2'
RHYTHM = 'source-group-rhythm/2'
BASE_FIELDS = {'tier', 'schema', 'theory', 'coattacks', 'realization_order',
               'source_quality', 'lower_scope', 'measure_geometry', 'source_keys'}
LINK_FIELDS = {'occurrence_ref', 'backing_ref', 'interval_semitones'}


def address(ref):
    if type(ref) is not str or not re.fullmatch(r'event:(?:0|[1-9]\d*)(?::(?:0|[1-9]\d*)){5}', ref):
        raise ValueError('Canonical source occurrence address required')
    return tuple(map(int, ref.split(':')[1:]))


def _body(shared):
    if type(shared) is not dict:
        raise ValueError('Owned relationship object required')
    if shared.get('schema') == PLAIN:
        body = shared
    elif shared.get('schema') == RHYTHM and set(shared) == {'schema', 'pitch_relationships', 'groups'}:
        body = shared['pitch_relationships']
        if type(body) is not dict or body.get('schema') != PLAIN:
            raise ValueError('Plain independent pitch relationships required')
    else:
        raise ValueError('Unsupported ownership wrapper')
    if 'input' in body or 'written_ties' in body:
        raise ValueError('Cached lower or legacy physical-note payload forbidden')
    return body


def _normal(shared):
    _body(shared)
    normal = rhythm.expand(shared)[0] if shared['schema'] == RHYTHM else shared
    music.validate(normal)
    return normal


def _index(body):
    result = {}
    for group in body['coattacks']:
        for member in group['members']:
            ref = member['id']
            if ref in result:
                raise ValueError('Duplicate occurrence owner')
            parsed = address(ref)
            if parsed[1:] != (group['part_id'], member['bar'], member['voice'], member['beat'], member['note']):
                raise ValueError('Occurrence address contradicts owned location')
            result[ref] = (group, member)
    return result


def validate_contacts(tier1, wrapper, *, normal=None):
    """Check only this owner's physical consequences; never repair/clamp them."""
    from source_fact_tier1 import project_documents
    from backing_motion_intervention import original_contact
    normal = _normal(expand(wrapper)) if normal is None else normal
    index = _index(normal)
    documents = project_documents(tier1)
    for row in wrapper['relationships']:
        group, member = index[row['occurrence_ref']]
        _, part, bar, voice, beat, note = address(row['occurrence_ref'])
        doc = documents[f'track-{part}.json']
        raw = doc['measures'][bar-1]['voices'][voice]['beats'][beat]['notes'][note]
        original_contact(doc, raw, music.member_pitch(group, member))
    if wrapper['schema'] in TIED_SCHEMAS:
        ties.validate_tier1(wrapper['written_tie_constraints'], normal, tier1,
                            [r['occurrence_ref'] for r in wrapper['relationships']])
    if wrapper['schema'] in EXECUTED_SCHEMAS:
        execution.validate(wrapper['execution_constraints'], tier1,
                           [r['occurrence_ref'] for r in wrapper['relationships']])


def _links(rows, fields):
    if type(rows) is not list or not rows:
        raise ValueError('Nonempty explicit bindings required')
    if any(type(row) is not dict or set(row) != fields for row in rows):
        raise ValueError('Unexpected binding fields')
    targets = [row['occurrence_ref'] for row in rows]
    anchors = [row['backing_ref'] for row in rows]
    for ref in targets + anchors:
        address(ref)
    if len(set(targets)) != len(targets):
        raise ValueError('Duplicate target owner')
    if set(targets) & set(anchors):
        raise ValueError('Target cannot serve as an independent backing anchor')
    return sorted(rows, key=lambda row: address(row['occurrence_ref']))


def _bound(index, link, *, member_scope=False, stored=False):
    target = link['occurrence_ref']; anchor = link['backing_ref']
    if target not in index or anchor not in index:
        raise ValueError('Dangling occurrence reference')
    group, member = index[target]; backing, note = index[anchor]
    if address(target)[0] != address(anchor)[0] or group['part_id'] == backing['part_id']:
        raise ValueError('Backing must be a foreign part of the same source song')
    if len(group['members']) == 1:
        if member.get('voicing_interval') != '0':
            raise ValueError('Exactly one owned focal pitch is required')
    elif not member_scope:
        raise ValueError('Exactly one owned focal pitch is required')
    else:
        if 'bass_register_anchor' not in group:
            raise ValueError('Independent lower coattack anchor required')
        if not any(m is not member and m.get('voicing_interval') == '0' for m in group['members']):
            raise ValueError('Retained lower member required; lower-member ownership unsupported')
        if stored:
            if 'voicing_interval' in member:
                raise ValueError('Duplicate upper-member pitch owner')
        elif member.get('voicing_interval') is None or music.fraction(member['voicing_interval']) <= 0:
            raise ValueError('Known upper member above the retained lower note required')
    if 'bass_register_anchor' not in backing or music.member_pitch(backing, note) is None:
        raise ValueError('Backing pitch must have its own known independent owner')
    return group, member, backing, note


def _active(normal, links, *, member_scope=False):
    index = _index(normal)
    for link in links:
        group, member, backing, note = _bound(index, link, member_scope=member_scope)
        if group['timing_uncertain'] is not False or backing['timing_uncertain'] is not False:
            raise ValueError('Unknown written clock cannot establish activity')
        try:
            onset = music.fraction(group['onset_q']); start = music.fraction(backing['onset_q'])
            duration = music.fraction(note['duration_q']); focal_duration = music.fraction(member['duration_q'])
        except (KeyError, TypeError) as error:
            raise ValueError('Missing owned written clock') from error
        if duration <= 0 or focal_duration <= 0 or not start <= onset < start + duration:
            raise ValueError('Backing is not active at the focal attack')


def lift(shared, bindings, *, tier1, preserve_execution=False, member_scope=False):
    if type(preserve_execution) is not bool or type(member_scope) is not bool:
        raise ValueError('Explicit execution-scope choice required')
    if member_scope and not preserve_execution:
        raise ValueError('Upper-member ownership requires execution preservation')
    return _lift(shared, bindings, tier1=tier1, legacy=False,
                 preserve_execution=preserve_execution, member_scope=member_scope)


def legacy_relift(shared, bindings):
    """Canonical verification of sealed v1 artifacts, not new construction."""
    return _lift(shared, bindings, tier1=None, legacy=True)


def assert_preserved(before, after, *, mutable_refs=()):
    """Compare authoritative history, not merely today's reconstructed pitches.

    An explicitly edited target may change its interval, never its backing ID.
    Every other existing relationship and constraint record must survive exactly.
    """
    if before.get('schema') not in SCHEMAS or after.get('schema') not in SCHEMAS:
        raise ValueError('Backing owners required for relationship preservation')
    current = {r['occurrence_ref']: r for r in after['relationships']}
    allowed = set(mutable_refs)
    for previous in before['relationships']:
        ref = previous['occurrence_ref']; present = current.get(ref)
        if present is None:
            raise ValueError('BACKING_RELATIONSHIP_LOSS: existing dependency disappeared')
        expected = dict(previous)
        if ref in allowed:
            expected['interval_semitones'] = present['interval_semitones']
        if present != expected:
            raise ValueError('BACKING_RELATIONSHIP_CHANGED: unauthorized rebinding or interval change')

    def retained(old, new, key):
        rows = {r[key]: r for r in new}
        if any(rows.get(r[key]) != r for r in old):
            raise ValueError('BACKING_CONSTRAINT_LOSS: existing obligation changed or disappeared')

    if before['schema'] in TIED_SCHEMAS:
        if after['schema'] not in TIED_SCHEMAS:
            raise ValueError('BACKING_CONSTRAINT_LOSS: written-tie scope downgraded')
        a, b = before['written_tie_constraints'], after['written_tie_constraints']
        if a['schema'] != b['schema']:
            raise ValueError('BACKING_CONSTRAINT_LOSS: written-tie schema changed')
        retained(a['relations'], b['relations'], 'id')
        retained(a['incidence'], b['incidence'], 'occurrence_ref')
    if before['schema'] in EXECUTED_SCHEMAS:
        if after['schema'] not in EXECUTED_SCHEMAS or (before['schema'] == MEMBER_SCHEMA and after['schema'] != MEMBER_SCHEMA):
            raise ValueError('BACKING_CONSTRAINT_LOSS: execution scope downgraded')
        a, b = before['execution_constraints'], after['execution_constraints']
        if (a['schema'] != b['schema'] or
                a['written_string_occupancy'] != b['written_string_occupancy'] or
                not set(a['owned_refs']) <= set(b['owned_refs']) or
                not set(a['part_ids']) <= set(b['part_ids'])):
            raise ValueError('BACKING_CONSTRAINT_LOSS: execution scope narrowed')
        retained(a['obligations'], b['obligations'], 'id')
        retained(a['unresolved_outside_neighborhood'], b['unresolved_outside_neighborhood'], 'id')


def extend_bindings(wrapper, bindings, *, tier1, preserve_execution=False, member_scope=False):
    """Add compatible owners without flattening/replacing existing owners.

    Expanded values are a transient read view for computing NEW intervals only.
    Existing stored core, links and obligations are preserved or explicitly refused.
    """
    if type(preserve_execution) is not bool or type(member_scope) is not bool:
        raise ValueError('Explicit execution-scope choice required')
    if wrapper.get('schema') == LEGACY_SCHEMA:
        raise ValueError('LEGACY_BACKING_EXTENSION_UNSUPPORTED: explicit upgrade required before nonzero edits')
    if wrapper.get('schema') not in TIED_SCHEMAS:
        raise ValueError('Existing guarded backing owner required')
    normal = _normal(expand(wrapper))
    validate_contacts(tier1, wrapper, normal=normal)
    additions = _links(bindings, {'occurrence_ref', 'backing_ref'})
    previous = {r['occurrence_ref']: r for r in wrapper['relationships']}
    fresh = []
    for row in additions:
        old = previous.get(row['occurrence_ref'])
        if old is not None:
            if old['backing_ref'] != row['backing_ref']:
                raise ValueError('BACKING_REBIND_CONFLICT: existing owner has a different backing reference')
        else:
            fresh.append(row)
    union = [dict(occurrence_ref=r['occurrence_ref'], backing_ref=r['backing_ref'])
             for r in wrapper['relationships']] + fresh
    if {r['occurrence_ref'] for r in union} & {r['backing_ref'] for r in union}:
        raise ValueError('UNSUPPORTED_BACKING_DEPENDENCY_CHAIN: dependent notes cannot become independent anchors')
    union = _links(union, {'occurrence_ref', 'backing_ref'})
    member_required = member_scope or wrapper['schema'] == MEMBER_SCHEMA
    execution_required = preserve_execution or wrapper['schema'] in EXECUTED_SCHEMAS
    if member_required and not execution_required:
        raise ValueError('Upper-member ownership requires execution preservation')
    _active(normal, union, member_scope=member_required)
    if not fresh and execution_required == (wrapper['schema'] in EXECUTED_SCHEMAS) and member_required == (wrapper['schema'] == MEMBER_SCHEMA):
        return deepcopy(wrapper)

    result = deepcopy(wrapper)
    result['schema'] = MEMBER_SCHEMA if member_required else EXECUTION_SCHEMA if execution_required else SCHEMA
    index = _index(normal); stored = _index(_body(result['core']))
    for row in fresh:
        group, member, backing, note = _bound(index, row, member_scope=member_required)
        pitch = music.member_pitch(group, member)
        if pitch is None:
            raise ValueError('Known focal pitch required for interval extraction')
        solved = music.relation(anchor=music.member_pitch(backing, note), pitch=pitch)
        result['relationships'].append(dict(row, interval_semitones=solved['interval']))
        _remove_pitch_owner(stored[row['occurrence_ref']])
    result['relationships'].sort(key=lambda r: address(r['occurrence_ref']))
    refs = [r['occurrence_ref'] for r in result['relationships']]
    result['written_tie_constraints'] = ties.from_tier1(normal, tier1, refs)
    if execution_required:
        result['execution_constraints'] = execution.build(tier1, refs)
    assert_preserved(wrapper, result)
    expand(result)
    validate_contacts(tier1, result, normal=normal)
    return result


def _remove_pitch_owner(pair):
    group, member = pair
    if len(group['members']) == 1:
        del group['bass_register_anchor']
    else:
        del member['voicing_interval']


def _lift(shared, bindings, *, tier1, legacy, preserve_execution=False, member_scope=False):
    """Replace selected absolute anchors with interval ownership; input unchanged."""
    normal = _normal(shared)
    rows = _links(bindings, {'occurrence_ref', 'backing_ref'})
    _active(normal, rows, member_scope=member_scope)
    index = _index(normal); relationships = []
    for row in rows:
        group, member, backing, note = _bound(index, row, member_scope=member_scope)
        pitch = music.member_pitch(group, member)
        if pitch is None:
            raise ValueError('Known focal pitch required for interval extraction')
        solved = music.relation(anchor=music.member_pitch(backing, note), pitch=pitch)
        relationships.append(dict(row, interval_semitones=solved['interval']))
    core = deepcopy(shared); body = _body(core); stored = _index(body)
    for row in relationships:
        _remove_pitch_owner(stored[row['occurrence_ref']])
    for view in rhythm.VIEWS:
        body.pop(view, None)
    for group in body['coattacks']:
        group.pop('interpretation', None)
    wrapper = dict(schema=LEGACY_SCHEMA if legacy else MEMBER_SCHEMA if member_scope else EXECUTION_SCHEMA if preserve_execution else SCHEMA, core=core, relationships=relationships)
    if not legacy:
        wrapper['written_tie_constraints'] = ties.from_tier1(normal, tier1, [r['occurrence_ref'] for r in rows])
    if preserve_execution:
        wrapper['execution_constraints'] = execution.build(tier1, [r['occurrence_ref'] for r in rows])
    expand(wrapper)
    return wrapper


def expand(wrapper):
    """Solve the SAME equation into transient anchors and existing derived views."""
    if type(wrapper) is not dict or wrapper.get('schema') not in SCHEMAS:
        raise ValueError('Unsupported backing-relative ownership')
    fields = {'schema', 'core', 'relationships'}
    if wrapper['schema'] in TIED_SCHEMAS:
        fields.add('written_tie_constraints')
    if wrapper['schema'] in EXECUTED_SCHEMAS:
        fields.add('execution_constraints')
    if set(wrapper) != fields:
        raise ValueError('Unsupported backing-relative ownership or missing written-tie constraints')
    links = _links(wrapper['relationships'], LINK_FIELDS)
    if links != wrapper['relationships']:
        raise ValueError('Canonical occurrence order required')
    if wrapper['schema'] in TIED_SCHEMAS:
        ties.shape(wrapper['written_tie_constraints'], [r['occurrence_ref'] for r in links])
    if wrapper['schema'] in EXECUTED_SCHEMAS:
        execution.shape(wrapper['execution_constraints'], [r['occurrence_ref'] for r in links])
    body = _body(wrapper['core'])
    if set(body) != BASE_FIELDS or any('interpretation' in g for g in body['coattacks']):
        raise ValueError('Derived views, cached values or unregistered fields forbidden')
    index = _index(body)
    targets = {row['occurrence_ref'] for row in links}
    member_scope = wrapper['schema'] == MEMBER_SCHEMA
    for group in body['coattacks']:
        selected = any(member['id'] in targets for member in group['members'])
        owns_anchor = selected and len(group['members']) == 1
        if ('bass_register_anchor' in group) == owns_anchor:
            raise ValueError('Missing or duplicate independent pitch owner')
        for member in group['members']:
            owns_member = member_scope and len(group['members']) > 1 and member['id'] in targets
            if ('voicing_interval' in member) == owns_member:
                raise ValueError('Missing or duplicate member pitch owner')
    solved = []
    for row in links:
        group, member, backing, note = _bound(index, row, member_scope=member_scope, stored=member_scope)
        music.fraction(row['interval_semitones'])
        pitch = music.relation(anchor=music.member_pitch(backing, note), interval=row['interval_semitones'])['pitch']
        solved.append((row['occurrence_ref'], pitch))
    result = deepcopy(wrapper['core']); output = _body(result); output_index = _index(output)
    for ref, pitch in solved:
        group, member = output_index[ref]
        if len(group['members']) == 1:
            group['bass_register_anchor'] = pitch
        else:
            interval = music.relation(anchor=group['bass_register_anchor'], pitch=pitch)['interval']
            if music.fraction(interval) <= 0:
                raise ValueError('Dependent upper member crosses retained lower note')
            member['voicing_interval'] = interval
    if result['schema'] == PLAIN:
        _active(result, links, member_scope=member_scope)
        rhythm.refresh(result)
    normal = _normal(result)
    _active(normal, links, member_scope=member_scope)
    return result
