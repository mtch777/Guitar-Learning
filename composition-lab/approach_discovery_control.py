"""Prepare the first applicable discovered approach through existing owners.

Chronological selection is a reproducible demonstration policy, not musical
preference. Discovery describes the current composition, never new source votes.
Unsupported candidates are retained; no smaller replacement passage is tried.
"""
from copy import deepcopy

import connected_tier2 as connected
import material_approaches as approaches
import musical_support_material as material
import support_material_uses as uses
from source_observation_evidence import digest


def _overlap(left, right):
    return (bool(set(left['parts']) & set(right['parts'])) and
            max(left['first_bar'], right['first_bar']) <= min(left['last_bar'], right['last_bar']))


def _plan(upper, t2, lower, row):
    if row['voice'] != 0:
        raise ValueError('Current material placement supports voice zero only')
    scope = dict(parts=[row['part_id']], first_bar=row['bars'][0], last_bar=row['bars'][1])
    matches = [] if upper['tier'] == 2 else [u for u in upper['uses']
        if _overlap(scope, upper['slots'][u['slot_ref']]['scope'])]
    if not matches:
        definition = material.fit(t2, lower=lower, **scope)
        use_id = None
    else:
        if len(matches) != 1:
            raise ValueError('Discovered approach crosses existing material-use owners')
        use = matches[0]; slot = upper['slots'][use['slot_ref']]
        owned = slot['scope']
        if not (set(scope['parts']) <= set(owned['parts']) and
                owned['first_bar'] <= scope['first_bar'] <= scope['last_bar'] <= owned['last_bar']):
            raise ValueError('Discovered approach only partly overlaps existing material ownership')
        definition = upper['materials'][use['material_ref']]
        if sum(u['material_ref'] == use['material_ref'] for u in upper['uses']) != 1:
            raise ValueError('Shared material refinement needs an explicit shared decision')
        if definition['scope'] != owned:
            raise ValueError('Refinement of a displaced material is not implemented')
        use_id = use['id']
    evidence = 'current-context:' + digest(dict(input_sha256=row['input_sha256'],
                                                interpretations=row['interpretations']))
    # Cheap bounded fit before whole-composition updates: same fit and inverse,
    # including complete ties and path-suffix ownership. No new musical rule.
    refined = approaches.fit(definition, lower, row['attack_refs'], row['interpretations'], evidence)
    if refined['approach']['relation'] != row['relation']:
        raise ValueError('Discovered relationship and fitted ownership disagree')
    approaches.expand(refined, mode='flip')
    return scope, use_id, evidence


def prepare_first(upper):
    """Return original/changed material-use models and the full selection record.

    Input is either a complete stripped T2 or the current supported material-use
    T3. No caller-provided song, part, bar, note, pitch, or preferred direction.
    The explicit experiment intention is the existing opposite-approach choice.
    """
    from melodic_approach_discovery import discover, backing_context
    before = deepcopy(upper); seal = digest(upper)
    if upper.get('tier') == 2:
        if connected.strip_lower(upper) != upper:
            raise ValueError('Remove non-authoritative input/derived views before discovery')
        t2 = upper
    elif upper.get('tier') == 3:
        t2 = uses.expand(upper)
    else:
        raise ValueError('A complete current T2 or supported material-use T3 is required')
    report = discover(t2)
    if report['input_sha256'] != digest(t2):
        raise ValueError('Discovery input identity mismatch')
    lower = connected.realize(t2)
    attempts = []
    for row in report['runs']:
        if row['status'] != 'RELATION_AND_FLIP_ADMITTED':
            continue
        try:
            scope, use_id, evidence = _plan(upper, t2, lower, row)
            if upper['tier'] == 2:
                prepared = uses.from_tier2(upper, [scope])
                use_id = prepared['uses'][-1]['id']
            elif use_id is None:
                prepared = uses.extend_materials(upper, [scope])
                use_id = prepared['uses'][-1]['id']
            else:
                prepared = deepcopy(upper)
            prepared = uses.lift_approach(prepared, use_id, row['attack_refs'], row['interpretations'], evidence)
            changed = uses.approach_candidate(prepared, use_id, 'flip')
        except ValueError as error:
            attempts.append(dict(id=row['id'], status='BINDING_OR_EXECUTION_REFUSED', reason=str(error)))
            if upper != before:
                raise AssertionError('A refused update mutated its input') from error
            continue
        if upper != before or digest(upper) != seal:
            raise AssertionError('Discovery or preparation mutated its input')
        attempts.append(dict(id=row['id'], status='PREPARED'))
        return dict(status='PREPARED', original=prepared, changed=changed,
                    discovery=report, attempts=attempts, selected=row, use_id=use_id,
                    context=backing_context(t2, row), selection='first_applicable_chronological_not_preferred')
    if upper != before:
        raise AssertionError('An unsupported request mutated its input')
    return dict(status='NO_APPLICABLE_APPROACH', discovery=report, attempts=attempts,
                selection='first_applicable_chronological_not_preferred')
