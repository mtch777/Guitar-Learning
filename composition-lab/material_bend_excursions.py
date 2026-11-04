"""Resolve explicit untied bend strengths through the existing scalar owner.

The immutable definition remains the only stored curve. Each point's height is
its original normalized coefficient times the requested excursion. Pitch still
belongs to the material's existing pitch owner; this module does not select a
base, landing, key or physical force limit. Callers jointly validate those choices.

Nonempty choices require the complete parent tie membership, including origins,
tails and execution-specific tied members. A local material cannot infer whether
its final note has an outgoing tie outside its own scope.
"""
from copy import deepcopy
from fractions import Fraction as F

import backing_pitch_ownership as backing
import bend_choice_constraints as bends
import bend_gesture_ownership as gesture
import musical_support_material as material
import technique_observation_relations as technique


def parent_ties(definition, parent, event_map):
    """Read complete live sustain ownership, mapped to stable material members.

    Absence of a local tie declaration does not prove absence of an outgoing
    dependency. Unknown tie neighborhoods remain blocked, not treated as empty.
    """
    from written_tie_pitch_ownership import SCHEMA
    core = (parent or {}).get('musical_relationships', {})
    if core.get('schema') != SCHEMA:
        raise ValueError('Bend edits require complete shared written-tie ownership')
    blocked = {ref for row in core['relationships']
               for ref in (row['origin_ref'], row['destination_ref'])}
    for row in core['unresolved']:
        blocked.add(row['destination_ref'])
        blocked.update(row['neighborhood_refs'])
    return sorted(m['id'] for g in definition['lower_tier']['coattacks']
                  for m in g['members'] if event_map(m['id']) in blocked)


def check_targets(original, resolved, excursions):
    """Check changed curves against ALL already-declared path interpretations.

    The same degree owner supplies the current start; the same curve supplies
    arrival, plateau and turn offsets. No key is invented to admit a change.
    Continuous travel between stable targets need not be a scale note.
    """
    if not excursions:
        return
    from material_degree_paths import SCHEMA
    if original.get('schema') != SCHEMA:
        raise ValueError('Changed bends require explicit existing tonal interpretations')
    hypotheses = {p['path_ref']: p['hypotheses'] for p in original['degree_paths']['paths']}
    paths = {b['coattack_ref']: b['pitch_path_ref'] for b in original['bindings']}
    fragment = material.expand(resolved)
    groups = {m['id']: (g, m) for g in fragment['coattacks'] for m in g['members']}
    declarations = {g['source_fact_ref']: g for g in fragment['technique_declarations']}
    for ref in excursions:
        group, member = groups[ref]
        context = hypotheses.get(paths[group['id']])
        if context is None or member['voicing_interval'] is None:
            raise ValueError('Changed bend lacks a declared pitched tonal context')
        pointer = gesture.pointer(ref) + '/bend'
        constraint = dict(schema=bends.SCHEMA, occurrence_ref=ref, source_fact_ref=pointer,
            hypotheses=context, targets=bends._targets(declarations[pointer]))
        pitch = F(group['bass_register_anchor']) + F(member['voicing_interval'])
        if not bends.evaluate(constraint, pitch)['admissible']:
            raise ValueError('Changed bend target conflicts with retained tonal interpretations')


def _excursion(value):
    if type(value) is not str:
        raise ValueError('Canonical positive semitone excursion string required')
    try:
        number = F(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError('Canonical positive semitone excursion string required') from error
    if str(number) != value or number <= 0:
        raise ValueError('Canonical positive semitone excursion string required')
    return number


def _ties(tied_refs):
    if tied_refs is None:
        raise ValueError('Complete parent tie context required for bend choices')
    if type(tied_refs) not in (list, tuple, set, frozenset):
        raise ValueError('Explicit parent tied occurrence references required')
    for ref in tied_refs:
        if type(ref) is not str:
            raise ValueError('Explicit parent tied occurrence references required')
        backing.address(ref)
    if len(set(tied_refs)) != len(tied_refs):
        raise ValueError('Unique parent tied occurrence references required')
    return set(tied_refs)


def resolve(definition, excursions=None, *, tied_refs=None):
    """Return a transient definition with requested current excursions.

    ``excursions`` maps stable material note occurrences to positive canonical
    semitone strings. It contains values, not percentages: zero-percent behavior
    is retaining the supplied current use choices, not requesting excursion0.
    Missing/empty choices return an equal independent copy. No input is mutated.

    Plain or degree-owned definitions use the same technique scalar equation.
    Complete current key/target, contact and execution checks belong after the
    caller combines pitch and curve choices, never at an invalid intermediate.
    """
    if excursions is None:
        excursions = {}
    if type(excursions) is not dict:
        raise ValueError('Explicit stable occurrence excursion mapping required')
    # Validate the existing ownership interface without realizing source files.
    material.expand(definition)
    groups = definition['lower_tier']['technique_declarations']
    technique.realize(dict(schema='technique-observation-relations/1',
                           groups=groups, unsupported=[]))
    if not excursions:
        return deepcopy(definition)

    blocked = _ties(tied_refs)
    blocked.update(row['occurrence_ref'] for row in definition.get('external_pitch_refs', [])
                   if row['kind'] == 'tied_member')
    for record in definition['observed_execution']:
        blocked.update(record['tied_member_refs'])
    members = {m['id'] for group in definition['lower_tier']['coattacks']
               for m in group['members']}
    indexed = {group['source_fact_ref']: (i, group) for i, group in enumerate(groups)}
    if len(indexed) != len(groups):
        raise ValueError('Duplicate material technique ownership')

    plans = []
    for ref, requested in excursions.items():
        if type(ref) is not str:
            raise ValueError('Stable material note occurrence required')
        backing.address(ref)
        if ref not in members:
            raise ValueError('Bend occurrence is outside the material')
        if ref in blocked:
            raise ValueError('Tied bend requires its complete existing gesture owner')
        value = _excursion(requested)
        pointer = gesture.pointer(ref) + '/bend'
        if pointer not in indexed:
            raise ValueError('One existing explicit bend declaration required')
        index, group = indexed[pointer]
        if group['field'] != 'bend' or group['scope'] != 'note':
            raise ValueError('One existing explicit bend declaration required')
        # Reuse the target/curve contract: ordered full-duration nonnegative
        # points, declared maximum agreement, explicit vibrato uncertainty.
        bends._targets(group)
        parameters = {p['fact_ref']: p for p in group['parameters']}
        peak_ref = pointer + '/tone'
        if peak_ref not in parameters or 'normalized' not in parameters[peak_ref]['parameter']:
            raise ValueError('Explicit numerical source bend peak required')
        peak = _excursion(parameters[peak_ref]['parameter']['normalized'])
        shapes = {s['id']: s for s in group['structure']}
        updates = []
        for ordinal, parameter in enumerate(group['parameters']):
            if not parameter['fact_ref'].endswith('/tone'):
                continue
            shape = shapes[parameter['fact_ref']]
            if shape['type'] not in ('integer', 'float') or parameter['unit'] != '50':
                raise ValueError('Registered numerical bend amplitude unit required')
            old = parameter['parameter']
            coefficient = F(old['normalized']) / peak
            if not 0 <= coefficient <= 1:
                raise ValueError('Bend amplitude lies outside its declared peak')
            current = dict(normalized=str(coefficient * value),
                           negative_zero=old['negative_zero'])
            # The SAME codec checks exact integer/float realization, including
            # negative zero. No rounding or field-type replacement is allowed.
            technique.scalar_relation(shape['type'], parameter=current, unit=parameter['unit'])
            updates.append((ordinal, current))
        plans.append((index, updates))

    result = deepcopy(definition)
    for index, updates in plans:
        for ordinal, current in updates:
            result['lower_tier']['technique_declarations'][index]['parameters'][ordinal]['parameter'] = current
    # Prove the closed source-type interface still realizes; pitch may be
    # deliberately awaiting the caller's simultaneous degree choice.
    technique.realize(dict(schema='technique-observation-relations/1',
        groups=result['lower_tier']['technique_declarations'], unsupported=[]))
    material.expand(result)
    return result
