"""Bounded grow/turn degree preflight, measured on the existing material inverse.

This starts from an explicitly supplied original definition. It is not a saved
composition updater, a physical-feasibility solver, or a musical preference
model. Search bounds and line identities are supplied before seeing outcomes.
"""
from collections import defaultdict
from fractions import Fraction as F
from itertools import product

import material_degree_paths as degree
import musical_support_material as material
import musical_tier2 as music


def _percent(value, name):
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError(f'{name} must be an integer from 0 to 100')
    return value


def _count(total, percent):
    return (total * percent + 50) // 100


def _pitches(fragment):
    values = {}
    groups = {}
    for group in fragment['coattacks']:
        for member in group['members']:
            ref = member['id']
            if ref in values:
                raise ValueError('Unique stable member occurrences required')
            interval = member['voicing_interval']
            pitch = None if interval is None else F(music.relation(
                anchor=group['bass_register_anchor'], interval=interval)['pitch'])
            if pitch is not None and pitch.denominator != 1:
                raise ValueError('Integral written pitches required for octave measurement')
            values[ref] = None if pitch is None else int(pitch)
            groups[ref] = group
    return values, groups


def _context(original, owned, lines):
    before = material.expand(original)
    if degree.expand(owned) != original:
        raise ValueError('Original-definition preflight requires exact original ownership; not a current-state updater')
    if (type(lines) is not dict or not lines
            or any(type(part) is not int for part in lines)):
        raise ValueError('Distinct integer part IDs with frozen source line occurrences required')
    selected = set(degree.selected_refs(owned))
    selected_groups = [g for g in before['coattacks'] if g['id'] in selected]
    parts = {g['part_id'] for g in selected_groups}
    if set(lines) != parts:
        raise ValueError('Every selected part must retain its declared melodic line')
    values, groups = _pitches(before)
    seen = set()
    for part, refs in lines.items():
        if type(refs) is not list or len(refs) < 2 or any(type(ref) is not str for ref in refs):
            raise ValueError('At least two stable pitched occurrences per declared line required')
        if len(set(refs)) != len(refs) or seen.intersection(refs):
            raise ValueError('Duplicate line occurrence or part identity')
        seen.update(refs)
        if any(ref not in groups or groups[ref]['id'] not in selected
               or groups[ref]['part_id'] != part or values[ref] is None for ref in refs):
            raise ValueError('Unknown, unselected, unpitched or wrong-part line occurrence')
        expected = [g['id'] for g in selected_groups if g['part_id'] == part]
        actual = [groups[ref]['id'] for ref in refs]
        if len(actual) != len(set(actual)) or set(actual) != set(expected):
            raise ValueError('One frozen line member in every selected coattack required; no reduced denominator')
        onsets = [F(groups[ref]['onset_q']) for ref in refs]
        if any(left >= right for left, right in zip(onsets, onsets[1:])):
            raise ValueError('Frozen line must follow strictly chronological source coattacks')
    bindings = {b['coattack_ref']: b for b in original['bindings']}
    by_role = defaultdict(list)
    for group in selected_groups:
        binding = bindings[group['id']]
        by_role[(binding['pitch_path_ref'], binding['voicing_ref'])].append(binding)
    roles = []
    for (path, voicing), rows in sorted(by_role.items()):
        attacks = sorted({row['attack'] for row in rows})
        positions = {attack: i for i, attack in enumerate(attacks)}
        roles.append(dict(path_ref=path, voicing_ref=voicing, source_attacks=attacks,
            factors={row['coattack_ref']: min(positions[row['attack']],
                         len(attacks)-positions[row['attack']]) for row in rows}))
    return before, values, selected_groups, roles


def _measure(before, after, groups, lines):
    parts = []
    all_steps = []
    all_register = []
    for part in sorted(lines):
        refs = lines[part]
        roots = [dict(occurrence_ref=ref, before_pitch=before[ref],
                      after_pitch=after[ref], before_octave=before[ref]//12-1,
                      after_octave=after[ref]//12-1) for ref in refs]
        steps = [dict(from_ref=a, to_ref=b, before=before[b]-before[a],
                      after=after[b]-after[a], changed=before[b]-before[a] != after[b]-after[a])
                 for a,b in zip(refs, refs[1:])]
        register = []
        unpitched = []
        for group in groups:
            if group['part_id'] != part:
                continue
            for member in group['members']:
                ref = member['id']
                if before[ref] is None:
                    if after[ref] is not None:
                        raise ValueError('Unpitched member became a pitch choice')
                    unpitched.append(ref)
                else:
                    if after[ref] is None:
                        raise ValueError('Selected pitched member disappeared')
                    register.append(dict(occurrence_ref=ref, before=before[ref]//12-1,
                        after=after[ref]//12-1,
                        changed=before[ref]//12 != after[ref]//12))
        parts.append(dict(part_id=part, line_roots=roots, steps=steps,
            changed_steps=sum(row['changed'] for row in steps), total_steps=len(steps),
            register=register, changed_register=sum(row['changed'] for row in register),
            total_register=len(register), retained_unpitched_refs=unpitched))
        all_steps.extend(steps)
        all_register.extend(register)
    return dict(by_part=parts, movement=dict(total=len(all_steps),
        changed=sum(row['changed'] for row in all_steps)),
        register=dict(total=len(all_register), changed=sum(row['changed'] for row in all_register)))


def plans(original_plain_material, degree_owned_material, original_line_refs_by_part,
          *, movement_percent, octave=1, max_degree_stride, register_percent=100):
    """Enumerate a caller-frozen positive per-role stride product without mutation.

    For each original (path, voicing) role, chronological distinct attacks have
    displacement ``stride * min(i, n-i)``. Paired bindings of one attack share
    that value. Movement zero instead retains zero degree displacements.
    Percentages measure actual signed-step and note-name-octave differences
    against this supplied original, with half-up rounding over complete scopes.
    Octave is a separate explicit relationship parameter, never a percentage.
    """
    _percent(movement_percent, 'Movement percentage')
    _percent(register_percent, 'Register percentage')
    if type(octave) is not int:
        raise ValueError('Explicit integral octave displacement required')
    if type(max_degree_stride) is not int or max_degree_stride < 1:
        raise ValueError('Caller-frozen positive finite degree-stride bound required')
    _, before, groups, roles = _context(original_plain_material, degree_owned_material,
                                         original_line_refs_by_part)
    totals = _measure(before, before, groups, original_line_refs_by_part)
    targets = dict(movement=_count(totals['movement']['total'], movement_percent),
                   register=_count(totals['register']['total'], register_percent))
    choices = [0] if movement_percent == 0 else range(1, max_degree_stride+1)
    candidates = []
    rejections = []
    for index, strides in enumerate(product(choices, repeat=len(roles))):
        displacements = {ref: stride*factor for role,stride in zip(roles,strides)
                         for ref,factor in role['factors'].items()}
        octaves = {ref: octave for ref in displacements}
        trial = dict(trial_index=index, strides=list(strides), displacements=displacements,
            octaves=octaves, absolute_degree_displacement=sum(map(abs,displacements.values())))
        try:
            current = degree.expand(degree_owned_material, displacements, octaves)
            after, _ = _pitches(material.expand(current))
            if set(after) != set(before):
                raise ValueError('Material occurrence inventory changed')
            metrics = _measure(before, after, groups, original_line_refs_by_part)
            trial['measurements'] = metrics
            failed = [feature for feature in targets
                      if metrics[feature]['changed'] != targets[feature]]
            if failed:
                trial.update(reason='FINAL_OUTPUT_TARGET_NOT_MET', failed_features=failed)
                rejections.append(trial)
            else:
                candidates.append(trial)
        except ValueError as error:
            trial.update(reason='RELATIONSHIP_REALIZATION_REFUSED', error=str(error))
            rejections.append(trial)
    candidates.sort(key=lambda row:(row['absolute_degree_displacement'],row['strides']))
    for rank, row in enumerate(candidates):
        row['rank'] = rank
    return dict(schema='material-degree-intention-preflight/1',
        comparison='explicit_original_definition_only',
        requests=dict(movement_percent=movement_percent, register_percent=register_percent,
                      octave_displacement=octave),
        totals=dict(movement=totals['movement']['total'], register=totals['register']['total'],
                    line_roots=sum(len(refs) for refs in original_line_refs_by_part.values())),
        targets=targets, roles=roles, candidates=candidates, rejections=rejections,
        search=dict(max_degree_stride=max_degree_stride, trials=len(candidates)+len(rejections),
            frozen_trial_count=len(choices)**len(roles), exhausted_declared_product=True,
            interpretation='No claim outside this bounded intention family'),
        ranking='Minimum summed absolute degree displacement, then lexical strides; not musical preference',
        pending=['physical execution', 'complete inverse', 'all other output controls', 'listening'])
