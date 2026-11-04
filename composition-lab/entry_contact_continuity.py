"""Existing written contact equalities that a delayed entry must preserve.

The guard supplies contact identities; this module does not detect gestures or
infer a performed ringing endpoint. Numeric times come only from current T1.
"""
import material_execution_locks as locks
from backing_execution_constraints import ordered,address


def required_pairs(guard,tier1,observed_execution,owned_refs,*,selected_next_refs=None,
                   identity_map=None,fact_identity_map=None,origin_q='0'):
    """Return CURRENT predecessor/destination refs for validated equalities.

    Only explicit v3 declaration-only contact fences qualify. A gap or overlap
    is not converted into a continuity requirement. The returned pairs contain
    identities only, and must be revalidated by the operation that uses them.
    """
    if type(guard)is not dict or guard.get('schema')!=locks.CLOCK_SCHEMA:
        raise ValueError('Entry contact continuity requires a validated v3 clock guard')
    locks.validate(guard,tier1,observed_execution,owned_refs,identity_map=identity_map,
                   fact_identity_map=fact_identity_map,origin_q=origin_q)
    data,records,identities,inverse,origin=locks._context(
        tier1,observed_execution,owned_refs,identity_map,fact_identity_map,origin_q)
    nodes=data['nodes']
    if selected_next_refs is not None:
        if (type(selected_next_refs)is not list or any(type(ref)is not str for ref in selected_next_refs)
                or len(set(selected_next_refs))!=len(selected_next_refs)or set(selected_next_refs)-set(nodes)):
            raise ValueError('Unique current selected contact destinations required')
        selected=set(selected_next_refs)
    else:selected=None
    result=set()
    for lock in guard['locks']:
        record=records[lock['record_identity']]
        if (not locks._numeric_successor_choices(record)or
                lock['policy']!='next_written_contact_context'):continue
        for boundary in lock['context_boundaries']:
            previous_ref=inverse[boundary['anchor']];previous=nodes[previous_ref]
            for stable_next in boundary['next_contact_ids']:
                next_ref=inverse[stable_next];following=nodes[next_ref]
                if selected is not None and next_ref not in selected:continue
                # Validation already protects the lane, kinds and identities;
                # keep the decision explicitly tied to the written equality.
                if (previous['part']==following['part']and previous['string']==following['string']
                        and previous['onset']+previous['duration']==following['onset']):
                    result.add((previous_ref,next_ref))
    return [dict(previous_ref=previous,next_ref=following)for previous,following in sorted(result)]


def required_groups(guard,tier1,observed_execution,owned_refs,*,selected_next_refs=None,
                    identity_map=None,fact_identity_map=None,origin_q='0'):
    """Retain a protected declaration's existing complete coending group.

    This uses the observed record's members and their current source coattack,
    not a chord interpretation. The selected next contact is a timing anchor
    for companion strings, not a claim that every member has that destination.
    """
    pairs=required_pairs(guard,tier1,observed_execution,owned_refs,selected_next_refs=selected_next_refs,
        identity_map=identity_map,fact_identity_map=fact_identity_map,origin_q=origin_q)
    data,records,identities,inverse,origin=locks._context(
        tier1,observed_execution,owned_refs,identity_map,fact_identity_map,origin_q)
    nodes=data['nodes'];result=set()
    for pair in pairs:
        previous=nodes[pair['previous_ref']]
        for record in records.values():
            if pair['previous_ref']not in record['member_refs']:continue
            members=record['member_refs']
            if len(members)<2:continue
            if all((nodes[r]['part'],nodes[r]['voice'],nodes[r]['bar'],nodes[r]['beat'],
                    nodes[r]['onset'],nodes[r]['duration'])==
                   (previous['part'],previous['voice'],previous['bar'],previous['beat'],
                    previous['onset'],previous['duration'])for r in members):
                result.add((tuple(ordered(members)),pair['next_ref']))
    return [dict(member_refs=list(members),next_ref=following)for members,following in
        sorted(result,key=lambda item:(address(item[0][0]),address(item[1])))]
