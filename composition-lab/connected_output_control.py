"""Joint final-output targets for disjoint movement and material timing owners.

The existing T2 movement and direct-T3 material inverses remain authoritative.
No score is copied into a parent, and no constructor is used as an updater.
Overlapping movement/material ownership is deliberately outside this boundary.
"""
from copy import deepcopy
import random

import connected_tier2 as connected
import halfstep_preference as halfsteps
import melodic_movement_ownership as movement
import movement_output_control as melodic
import musical_support_material as material
import rhythm_output_control as rhythmic
import support_material_uses as uses
from output_change_targets import freeze_targets, evaluate_targets
from source_observation_evidence import digest


def _direct(upper):
    if type(upper) is not dict or upper.get('schema') != uses.DIRECT_SCHEMA:
        raise ValueError('This combined boundary requires an existing direct material-use T3')


def _unique(rows, key):
    mapped = {row[key]: row for row in rows}
    if len(mapped) != len(rows):
        raise ValueError('Duplicate stable owner identity')
    return mapped


def pack_movement(upper, changed_t2):
    """Pack only permitted existing movement/contact leaves by stable IDs."""
    _direct(upper)
    current, before, _ = uses.realize_pair(upper)
    after = connected.realize(changed_t2)
    model, refs, _ = movement._shape(current)
    if model['schema'] != movement.SCHEMA_V2:
        raise ValueError('Existing version2 movement owner required')
    for slot in upper['slots']:
        if any(material._event(ref, slot['scope']) for ref in refs):
            raise ValueError('Overlapping movement and material owners are not supported by this boundary')
    # This protects full owners, observations, source facts and every field
    # outside the existing selected parameter/contact permission.
    movement._allowed_changes(current, changed_t2, before, after, version2=True)
    out = deepcopy(upper)
    parent = out['lower_tier']['owned_parameters']
    if parent.get(movement.SLOT) != current['owned_parameters'][movement.SLOT]:
        raise ValueError('Movement must remain owned completely by the retained lower T2')
    parent[movement.SLOT]['parameters'] = deepcopy(changed_t2['owned_parameters'][movement.SLOT]['parameters'])
    new_positions = _unique(changed_t2['owned_parameters']['physical_positions'], 'occurrence_ref')
    saved_positions = _unique(parent['physical_positions'], 'occurrence_ref')
    new_choices = _unique(changed_t2['owned_parameters']['source_choices'], 'fact_ref')
    saved_choices = _unique(parent['source_choices'], 'fact_ref')
    for ref in refs:
        if ref not in saved_positions or ref not in new_positions:
            raise ValueError('Selected movement contact is not retained outside material ownership')
        old, new = saved_positions[ref], new_positions[ref]
        if old.get('string_ref') != new.get('string_ref'):
            raise ValueError('Movement contact identity changed')
        string_ref = old['string_ref']
        if string_ref not in saved_choices or string_ref not in new_choices:
            raise ValueError('Selected string owner is not retained')
        old['negative_zero'] = new['negative_zero']
        for name in ('normalized', 'negative_zero'):
            saved_choices[string_ref]['parameter'][name] = new_choices[string_ref]['parameter'][name]
    if uses.expand(out) != changed_t2:
        raise ValueError('Movement packing changed or lost a retained material/relationship owner')
    return out


def intervene(upper, movement_controls, rhythm_requests, rhythm_percent, *, seed=0,
              max_candidates=64, max_rhythm_combinations=64):
    """Return one jointly satisfying saved T3, or the complete unchanged input.

    This searches the movement vocabulary and invokes the existing bounded
    rhythm selector for each. It does not exhaust every possible joint rhythm
    realization and never reports its failure as universal musical impossibility.
    """
    _direct(upper)
    if type(seed) is not int:
        raise ValueError('Integer combined selection seed required')
    before_t2, before, _ = uses.realize_pair(upper)
    initial_hash = digest(upper)
    # Zero obtains the complete structural onset denominator before any pitch
    # alternative can affect feasibility. The contract here uses the request.
    _, clock_zero = rhythmic.intervene(upper, rhythm_requests, 0, seed=seed,
                                       max_combinations=max_rhythm_combinations)
    baseline = dict(melodic.measurements(before_t2, lower=before),
                    **clock_zero['target_contract']['baseline'])
    requests = dict(melody=movement_controls['melody'], register=movement_controls['register'],
                    attack_onset_q=rhythm_percent)
    contract = freeze_targets(baseline, requests)
    initial = evaluate_targets(contract, baseline)
    candidates, movement_report = melodic.candidates(before_t2, movement_controls,
        max_candidates=max_candidates, defer_preference=True)
    report = dict(policy='connected_movement_rhythm_output/1', target_contract=contract,
        movement=movement_report, attempts=[], output=initial, satisfied=False, changed=False,
        scope='Disjoint existing movement and material timing owners in direct T3',
        joint_search_exhausted=False,
        search_limits='One deterministic bounded rhythm selection per admitted movement candidate; not all joint musical realizations')

    def refuse(status):
        if digest(upper) != initial_hash:
            raise ValueError('Combined candidate search mutated its input')
        return deepcopy(upper), dict(report, status=status)

    if not candidates:
        return refuse(movement_report['status'])
    model, _, _ = movement._shape(before_t2)
    context = halfsteps.freeze(before, model['attacks'], reference_attacks=model['reference_attacks'],
        original_reference_steps=model['observations']['reference_steps'], source_origin=before_t2['source_origin'])
    admitted = []
    for index, (candidate_t2, detail) in enumerate(candidates):
        attempt = dict(movement_candidate=index)
        try:
            packed = pack_movement(upper, candidate_t2)
            candidate, clock_report = rhythmic.intervene(packed, rhythm_requests, rhythm_percent,
                seed=seed, max_combinations=max_rhythm_combinations)
            attempt['rhythm'] = clock_report
            if not clock_report['output']['satisfied']:
                attempt['status'] = 'RHYTHM_TARGET_NOT_MET'
                report['attempts'].append(attempt)
                continue
            final_t2, final_lower, _ = uses.realize_pair(candidate)
            final = dict(melodic.measurements(final_t2, baseline_upper=before_t2, lower=final_lower),
                         **rhythmic.measurements(final_lower, rhythm_requests))
            checked = evaluate_targets(contract, final)
            if not checked['satisfied']:
                attempt.update(status='FINAL_OUTPUT_TARGET_NOT_MET', output=checked)
                report['attempts'].append(attempt)
                continue
            preference = halfsteps.evaluate(final_lower, context)
        except ValueError as error:
            attempt.update(status='UNSUPPORTED_COMPOSED_CANDIDATE', reason=str(error))
            report['attempts'].append(attempt)
            continue
        attempt.update(status='JOINT_OUTPUT_TARGETS_SATISFIED', output=checked,
                       halfstep_preference=preference)
        report['attempts'].append(attempt)
        admitted.append((candidate, checked, preference, final_lower != before))
    if not admitted:
        return refuse('JOINT_TARGET_UNSATISFIED_WITHIN_SEARCH')
    chosen = halfsteps.choose([a[2] for a in admitted], random.Random(f'connected-output:{seed}'))
    candidate, checked, _, changed = admitted[chosen]
    if digest(upper) != initial_hash:
        raise ValueError('Combined candidate search mutated its input')
    return candidate, dict(report, status='JOINT_OUTPUT_TARGETS_SATISFIED', satisfied=True,
        changed=changed, output=checked, admitted_candidates=len(admitted), selected_index=chosen)
