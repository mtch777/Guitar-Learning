"""Joint entry/content timing inside the existing material-use inverse.

Saved choices address original material beats. Subdivision and entry insertion
derive current addresses; neither changes the selected line's stable identity.
"""
from copy import deepcopy
from fractions import Fraction as F

import backing_execution_constraints as execution
import material_entry_rest as entry
import musical_support_material as material
from material_subdivision_projection import BEAT, _rewrite


def compose(before, after):
    """Compose occurrence/beat projections without losing untouched members."""
    out = dict(beats={}, events={}, spans={})
    for kind in ('beats', 'events'):
        produced = {child for children in before[kind].values() for child in children}
        for old, children in before[kind].items():
            out[kind][old] = [new for child in children for new in after[kind].get(child, [child])]
        for old, children in after[kind].items():
            if old not in produced and old not in before[kind]:out[kind][old] = deepcopy(children)
    return out


def _fact_map(maps, ref):
    match = BEAT.fullmatch(ref)
    base = match[1]+match[2] if match else None
    return maps['beats'][base][0]+ref[len(base):] if base in maps['beats'] else ref


def requests(upper, subdivision_maps):
    """Resolve stable material choices to current complete descendant lanes."""
    import support_material_uses as uses
    result = {}
    for use in upper['uses']:
        if 'entry_shares' not in use:continue
        definition = upper['materials'][use['material_ref']]
        fact, _, _ = uses._maps(definition, upper['slots'][use['slot_ref']])
        for lane, weights in use['rhythm_lane_shares'].items():
            current_lane = fact(lane)
            if current_lane in result:raise ValueError('Two entry owners for one current lane')
            if type(weights) is not dict or not weights:raise ValueError('Complete stable beat shares required')
            shares = {}
            for original, weight in weights.items():
                if type(original) is not str or original.rsplit('/', 1)[0] != lane:
                    raise ValueError('Content share names a different stable lane')
                current = fact(original)
                children = subdivision_maps['beats'].get(current, [current])
                value = F(weight)
                if type(weight) is not str or str(value) != weight or value <= 0:
                    raise ValueError('Positive canonical content proportions required')
                for child in children:
                    if child in shares:raise ValueError('Duplicated current content occurrence')
                    shares[child] = str(value/len(children))
            result[current_lane] = dict(entry_share=use['entry_shares'][lane], content_shares=shares)
    return result


def validate_execution(upper, pieces, contracts, lower, maps, *, derived_sustains=None):
    """Check saved obligations against final clocks and stable identities."""
    nodes = execution._snapshot(execution.encoded(lower))['nodes']
    event = lambda ref:maps['events'].get(ref, [ref])[0]
    fact = lambda ref:_fact_map(maps, ref)
    identities = {child:(old if i == 0 else old+'@subdivision:'+str(i)+'/'+str(len(children)))
        for old, children in maps['events'].items() for i, child in enumerate(children) if child in nodes}
    for use, piece, records in zip(upper['uses'], pieces, contracts):
        definition = upper['materials'][use['material_ref']]
        projected = dict(realization_order=[child for old in piece['realization_order']
            for child in maps['events'].get(old, [old])],
            physical_positions=[dict(occurrence_ref=child) for p in piece['physical_positions']
                for child in maps['events'].get(p['occurrence_ref'], [p['occurrence_ref']])])
        expected = []
        for record in records:
            row = _rewrite(record, fact, event);row['id'] = execution.identity(row);expected.append(row)
        facts = {fact(r['source_fact_ref']):r['source_fact_ref'] for r in records if r['source_fact_ref'] is not None}
        material.validate_fragment_execution(projected, expected, lower,
            execution_locks=definition.get('unresolved_execution_locks'), identity_map=identities,
            fact_identity_map=facts, origin_q=definition['source_start_q'],derived_sustains=derived_sustains)


def required_continuity(upper, pieces, contracts, lower, maps):
    """Read protected written adjacencies from their existing current guards."""
    from entry_contact_continuity import required_pairs,required_groups
    from material_execution_locks import CLOCK_SCHEMA
    nodes=execution._snapshot(execution.encoded(lower))['nodes']
    event=lambda ref:maps['events'].get(ref,[ref])[0]
    fact=lambda ref:_fact_map(maps,ref)
    identities={child:(old if i==0 else old+'@subdivision:'+str(i)+'/'+str(len(children)))
        for old,children in maps['events'].items()for i,child in enumerate(children)if child in nodes}
    pairs={};groups={}
    for use,piece,records in zip(upper['uses'],pieces,contracts):
        definition=upper['materials'][use['material_ref']];guard=definition.get('unresolved_execution_locks')
        if guard is None or guard['schema']!=CLOCK_SCHEMA:continue
        expected=[]
        for record in records:
            row=_rewrite(record,fact,event);row['id']=execution.identity(row);expected.append(row)
        refs=[child for old in piece['realization_order']for child in maps['events'].get(old,[old])]
        facts={fact(r['source_fact_ref']):r['source_fact_ref']for r in records if r['source_fact_ref']is not None}
        for pair in required_pairs(guard,lower,expected,refs,identity_map=identities,
                fact_identity_map=facts,origin_q=definition['source_start_q']):
            pairs[(pair['previous_ref'],pair['next_ref'])]=pair
        for group in required_groups(guard,lower,expected,refs,identity_map=identities,
                fact_identity_map=facts,origin_q=definition['source_start_q']):
            groups[(tuple(group['member_refs']),group['next_ref'])]=group
    return [pairs[key]for key in sorted(pairs)],[groups[key]for key in sorted(groups)]


def realize(upper, current, lower, pieces, contracts, ledger, subdivision_maps):
    from connected_tier2 import realize as realize_lower
    lane_requests = requests(upper, subdivision_maps)
    proposal = entry.plan(entry._current_fragment(current), lane_requests)
    current_records = execution._snapshot(execution.encoded(lower))['records']
    from material_entry_carry import plan as carry_plan
    pairs,groups=required_continuity(upper,pieces,contracts,lower,subdivision_maps)
    carries = carry_plan(current, proposal, current_records,required_pairs=pairs,coherent_group_refs=groups)
    changed, report = entry.project(current, [proposal], execution_records=current_records,
        carry_plan=carries,required_pairs=pairs,coherent_group_refs=groups)
    final = realize_lower(changed)
    maps = compose(subdivision_maps, report['maps'])
    validate_execution(upper, pieces, contracts, final, maps,derived_sustains=report.get('carries',[]))
    projected = deepcopy(ledger)
    for row in projected:
        row['current_address'] = report['maps']['events'].get(row['current_address'], [row['current_address']])[0]
    by_address={r['current_address']:r for r in projected}
    for carried in report.get('carries',[]):
        parent=by_address[carried['predecessor_ref']]
        row=deepcopy(parent)
        row.update(identity=parent['identity']+'@entry-carry:'+carried['identity'],
            current_address=carried['occurrence_ref'],parent_identity=parent['identity'],
            derived_kind='sustain_continuation')
        projected.append(row);by_address[row['current_address']]=row
    if len({r['identity'] for r in projected}) != len(projected) or len({r['current_address'] for r in projected}) != len(projected):
        raise ValueError('Entry projection lost stable identity or aliased current addresses')
    # An approach still names the same complete tie closures after projection.
    import support_material_uses as uses
    from material_approaches import SCHEMA, validate_membership
    for use in upper['uses']:
        definition = upper['materials'][use['material_ref']]
        if definition['schema'] == SCHEMA:
            _, event, _ = uses._maps(definition, upper['slots'][use['slot_ref']])
            validate_membership(definition, final,
                event_map=lambda ref:maps['events'].get(event(ref), [event(ref)])[0])
    return changed, final, projected, maps
