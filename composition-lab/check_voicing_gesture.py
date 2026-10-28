"""Independent simultaneous source-gesture verifier, never a proposal generator."""
from collections import defaultdict
from fractions import Fraction as F
from source_fact_tier1 import project_documents
from check_family_policy import normalized_units
from check_voicing_context import check_many,_nodes


def _run(units,groups):
    if type(groups)is not list or len(groups)<2:raise ValueError('At least two source groups required')
    chosen=[];seen=set()
    for refs in groups:
        if type(refs)is not list or not refs or any(type(x)is not str for x in refs)or len(set(refs))!=len(refs):raise ValueError('Exact unique group occurrence references required')
        if seen.intersection(refs):raise ValueError('Overlapping source groups')
        seen.update(refs)
        unit=next((u for u in units if set(u['member_refs'])==set(refs)),None)
        if unit is None or unit['refusal_reasons']:raise ValueError('Unadmitted or incomplete source group')
        chosen.append(unit)
    if len({u['part_id']for u in chosen})!=1:raise ValueError('One source part per gesture')
    sequence=[u['id']for u in units if u['part_id']==chosen[0]['part_id']]
    indices=[sequence.index(u['id'])for u in chosen]
    if indices!=list(range(indices[0],indices[0]+len(indices))):raise ValueError('Source groups must be consecutive and ordered; no refused events skipped')
    return chosen,seen


def _classifications(nodes):
    # Accepted detector primitive, independent mapping from actual source notes.
    from technique_analysis import classify_group
    groups=defaultdict(list)
    for n in nodes.values():
        if n['instrument']==1024:continue
        groups[n['part'],n['onset']].append(dict(midi=n['pitch'],string=n['string']))
    return {key:classify_group(rows)for key,rows in groups.items()}


def check(tier1_before,tier1_after,target_groups,donor_groups):
    try:
        if type(target_groups)is not list or type(donor_groups)is not list or len(target_groups)!=len(donor_groups):raise ValueError('Paired target/donor group sequences required')
        units,_,_,_=normalized_units(project_documents(tier1_before))
        targets,target_refs=_run(units,target_groups);donors,donor_refs=_run(units,donor_groups)
        if target_refs.intersection(donor_refs):raise ValueError('Target and source witness blocks overlap')
        if any(t['part_id']!=d['part_id']for t,d in zip(targets,donors)):raise ValueError('Donor must be same source part')
        target_clock=[F(t['onset_q'])-F(targets[0]['onset_q'])for t in targets]
        donor_clock=[F(d['onset_q'])-F(donors[0]['onset_q'])for d in donors]
        if target_clock!=donor_clock:raise ValueError('Exact source inter-onset timing differs')
        result=check_many(tier1_before,tier1_after,[t['member_refs']for t in targets],[[d['id']]for d in donors],True)
        _,_,old_nodes,_=_nodes(tier1_before);_,_,new_nodes,_=_nodes(tier1_after)
        if _classifications(old_nodes)!=_classifications(new_nodes):result['issues'].append('RETAINED_COATTACK_CLASSIFICATION_CHANGED')
        result['issues']=sorted(set(result['issues']))
        result['status']='PASS_INDEPENDENT_VOICING_GESTURE'if not result['issues']else'FAIL_INDEPENDENT_VOICING_GESTURE'
        result.update(target_group_refs=[t['id']for t in targets],donor_group_refs=[d['id']for d in donors],group_count=len(targets),scope='Complete simultaneous source-group gesture; original-neighborhood-excluded source paths, raw locks and retained coattack classes. Approved pedal verification is separate; no melody/artist/acoustic claim.')
        return result
    except Exception as error:
        return dict(status='FAIL_INDEPENDENT_VOICING_GESTURE',issues=[type(error).__name__+': '+str(error)],witness_count=0)
