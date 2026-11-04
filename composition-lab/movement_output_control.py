"""Actual signed-step/register quotas through the existing movement inverse.

This is a new request API. Historical release-probability controls are unchanged.
The finite vocabulary retains each current symbolic step or adopts the explicit
repeat/reference relationship. Placement is checked only after both coordinates
are chosen. A bounded search failure is not a claim of musical impossibility.
"""
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations
from math import comb, ceil
import random

import melodic_movement_ownership as movement
import halfstep_preference as halfsteps
from output_change_targets import freeze_targets, evaluate_targets
from source_observation_evidence import digest

POLICY = 'movement_actual_output/1'
MAX_CANDIDATES = 256
FIELDS = {'melody', 'register', 'intent', 'register_direction', 'seed'}


def _controls(controls, max_candidates):
    if (type(controls) is not dict or set(controls) != FIELDS
            or any(type(controls[k]) is not int or not 0 <= controls[k] <= 100
                   for k in ('melody', 'register'))
            or controls['intent'] not in movement.INTENTS
            or controls['register_direction'] not in ('up', 'down')
            or type(controls['seed']) is not int):
        raise ValueError('Explicit movement/register output percentages, intention, direction and seed required')
    if type(max_candidates) is not int or max_candidates < 1:
        raise ValueError('Positive finite candidate-search bound required')


def _pitches(lower, attacks):
    """Observe the reconstructed score, not the proposed parameter values."""
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    events = {e['id']: e for e in extract_documents(project_documents(lower))['events']}
    values = []
    for attack in attacks:
        pitches = {events[ref]['pitch'] for ref in attack['member_refs']}
        if len(pitches) != 1 or None in pitches:
            raise ValueError('Complete tied attack must have one known realized pitch')
        pitch = F(pitches.pop())
        if pitch.denominator != 1:
            raise ValueError('Integer written attack pitch required')
        values.append(pitch)
    return values


def _values(attacks, pitches):
    roots = [a['attack_ref'] for a in attacks]
    if len(pitches) != len(attacks):
        raise ValueError('Every frozen attack needs a realized pitch')
    return dict(melody={left + '->' + right: str(b-a)
                        for left, right, a, b in zip(roots, roots[1:], pitches, pitches[1:])},
                register={ref: int(pitch // 12)-1 for ref, pitch in zip(roots, pitches)})


def _movement_only(parameters, original_octave, reference_pitches):
    pars = deepcopy(parameters)
    pars['octave'] = original_octave
    return list(map(F, movement.relation(**pars, reference_pitches=reference_pitches)['pitches']))


def _shifts(part, pitches):
    if type(part.get('frets')) is not int or part['frets'] <= 0:
        raise ValueError('Declared finite fret bounds required for joint register search')
    capo = part.get('capo', 0)
    minimum = ceil((min(part['tuning']) + capo - min(pitches)) / 12)
    maximum = int((max(part['tuning']) + capo + part['frets'] - max(pitches)) // 12)
    return range(minimum, maximum + 1)


def measurements(upper, *, baseline_upper=None, lower=None):
    """Measure a complete current T2 against the frozen line/register frame.

    A caller composing other controls can reuse its already reconstructed T1.
    The same stable attacks and first pitch class remain mandatory. Register is
    each FINAL letter-octave coordinate, including crossings caused by movement.
    """
    model, _, _ = movement._shape(upper)
    baseline, _, _ = movement._shape(upper if baseline_upper is None else baseline_upper)
    if (model['schema'] != movement.SCHEMA_V2 or baseline['schema'] != movement.SCHEMA_V2
            or model['attacks'] != baseline['attacks']
            or model['reference_attacks'] != baseline['reference_attacks']
            or model['parameters']['pitch_class'] != baseline['parameters']['pitch_class']):
        raise ValueError('Final movement measurement changed its frozen identity or pitch-class anchor')
    lower = movement._realize(upper) if lower is None else lower
    return _values(model['attacks'], _pitches(lower, model['attacks']))


def candidates(upper, controls, *, max_candidates=MAX_CANDIDATES, defer_preference=False):
    """Return ``[(complete_model, detail), ...], report`` without mutation.

    All identities/denominators precede admission. Search order is seeded before
    outcomes; each mask is visited at most once. At the bound, admitted results
    remain valid but exhaustion/preference optimality are not claimed.
    """
    _controls(controls, max_candidates)
    if type(defer_preference) is not bool:
        raise ValueError('Explicit Boolean preference deferral required')
    before = movement._realize(upper)
    model, _, _ = movement._shape(upper)
    if model['schema'] != movement.SCHEMA_V2:
        raise ValueError('Existing version2 movement/register ownership required')
    input_hash = digest(upper)
    attacks = model['attacks']; current = deepcopy(model['parameters'])
    original_pitches = _pitches(before, attacks)
    baseline = _values(attacks, original_pitches)
    contract = freeze_targets(baseline, {k: controls[k] for k in ('melody', 'register')})
    initial = evaluate_targets(contract, baseline)
    target_m = initial['features']['melody']['target_count']
    target_r = initial['features']['register']['target_count']
    report = dict(policy=POLICY, controls=deepcopy(controls), contract=contract,
        baseline=initial, candidates=[], refused=[], search_exhausted=True,
        search_limit=max_candidates, attempted_candidates=0, attempted_masks=0,
        original_input_sha256=input_hash,
        vocabulary='Retain each current symbolic step or adopt requested repeat/reference step; finite common-octave placements',
        register_definition='Actual final letter_octave coordinate floor(pitch/12)-1 per stable attack; common shift is a separate realization parameter',
        original_observations_unchanged=True)

    def finish(admitted, reason=None):
        if digest(upper) != input_hash:
            raise ValueError('Candidate search mutated its input')
        report['status'] = ('SATISFYING_CANDIDATES' if admitted else
                            'SEARCH_LIMIT' if not report['search_exhausted'] else 'TARGET_UNSATISFIED')
        if reason is not None: report['reason'] = reason
        report['admitted_candidates'] = len(admitted)
        return admitted, report

    if target_m == 0 and target_r not in (0, len(attacks)):
        report['algebraic_register_counts'] = [0, len(attacks)]
        return finish([], 'With movement locked, a common octave changes all attacks or none; requested count is unavailable')

    reference_pitches = None
    if model['reference_attacks'] is not None:
        reference_pitches = list(map(str, _pitches(before, model['reference_attacks'])))
    desired = '0' if controls['intent'] == 'repeat_start' else movement.REFERENCE_STEP
    if target_m and desired == movement.REFERENCE_STEP and reference_pitches is None:
        return finish([], 'Follow intention requires existing explicit reference attacks')
    current_steps = list(baseline['melody'].values())
    desired_steps = (['0'] * len(current_steps) if desired == '0' else
                     [str(F(b)-F(a)) for a,b in zip(reference_pitches,reference_pitches[1:])]
                     if reference_pitches is not None else current_steps)
    different = [i for i, (a,b) in enumerate(zip(current_steps, desired_steps)) if a != b]
    report['same_step_indices'] = [i for i in range(len(current_steps)) if i not in different]
    report['algebraic_melody_max_changed'] = len(different)
    if target_m > len(different):
        return finish([], 'Requested relationship leaves too many current signed steps unchanged')

    if target_m == target_r == 0:
        detail = dict(parameters=current, output=initial, changed=False,
                      changed_attack_refs=[], pitch_class_changed_attack_refs=[], contacts={})
        report['candidates'] = [deepcopy(detail)]
        return finish([(deepcopy(upper), detail)])

    context = halfsteps.freeze(before, attacks, reference_attacks=model['reference_attacks'],
        original_reference_steps=model['observations']['reference_steps'], source_origin=upper['source_origin'])
    report['halfstep_context'] = context
    order = list(different)
    random.Random(f'movement-output:mask-order:{controls["seed"]}').shuffle(order)
    report['total_step_masks'] = comb(len(order), target_m)
    from source_fact_tier1 import project_documents
    part_id = movement.backing.address(attacks[0]['attack_ref'])[1]
    part = project_documents(before)[f'track-{part_id}.json']
    admitted = []
    for mask in combinations(order, target_m):
        if report['attempted_masks'] >= max_candidates:
            report['search_exhausted'] = False
            break
        report['attempted_masks'] += 1
        pars = deepcopy(current)
        for index in mask: pars['steps'][index] = desired
        movement_only = _movement_only(pars, current['octave'], reference_pitches)
        shifts = _shifts(part, movement_only)
        if not shifts:
            report['refused'].append(dict(step_indices=sorted(mask), reason='No common octave placement within declared geometry'))
        for shift in shifts:
            projected = [p+12*shift for p in movement_only]
            projected_values = _values(attacks, projected)
            sign = 1 if controls['register_direction'] == 'up' else -1
            if any((projected_values['register'][ref]-value)*sign < 0
                   for ref,value in baseline['register'].items()):
                continue
            if not evaluate_targets(contract, projected_values)['satisfied']:
                continue
            if report['attempted_candidates'] >= max_candidates:
                report['search_exhausted'] = False
                break
            report['attempted_candidates'] += 1
            parameters = deepcopy(pars); parameters['octave'] += shift
            try:
                # No movement-only or register-only placement gate: this is
                # the complete candidate, checked by the existing inverse.
                candidate, contacts = movement._placed_candidate(upper, parameters, before)
                after = movement._realize(candidate)
                final_pitches = _pitches(after, attacks)
                final = _values(attacks, final_pitches)
                measured = evaluate_targets(contract, final)
                if not measured['satisfied']:
                    raise ValueError('Complete realized output does not meet every frozen feature target')
            except ValueError as error:
                report['refused'].append(dict(step_indices=sorted(mask), octave_shift=shift, reason=str(error)))
                continue
            preference = None if defer_preference else halfsteps.evaluate(after, context)
            detail = dict(parameters=parameters, output=measured, changed=after != before,
                step_indices=sorted(mask), octave_shift=shift, contacts=contacts,
                changed_attack_refs=[a['attack_ref'] for a,b,c in zip(attacks, original_pitches, final_pitches) if b != c],
                pitch_class_changed_attack_refs=[a['attack_ref'] for a,b,c in zip(attacks, original_pitches, final_pitches) if b % 12 != c % 12],
                halfstep_preference=preference)
            admitted.append((candidate, detail)); report['candidates'].append(deepcopy(detail))
        if not report['search_exhausted']: break
    return finish(admitted)


def intervene(upper, controls, *, max_candidates=MAX_CANDIDATES):
    """Commit only a complete satisfying result; otherwise return exact input."""
    admitted, report = candidates(upper, controls, max_candidates=max_candidates)
    if not admitted:
        return deepcopy(upper), dict(report, changed=False, satisfied=False,
                                     final_output=report['baseline'])
    if len(admitted) == 1:
        index = 0
    else:
        index = halfsteps.choose([detail['halfstep_preference'] for _, detail in admitted],
                                 random.Random(f'movement-output:selection:{controls["seed"]}'))
    chosen, detail = admitted[index]
    return chosen, dict(report, status='OUTPUT_TARGETS_SATISFIED', satisfied=True,
                        changed=detail['changed'], selected_index=index, final_output=detail['output'],
                        changed_attack_refs=detail['changed_attack_refs'],
                        pitch_class_changed_attack_refs=detail['pitch_class_changed_attack_refs'])
