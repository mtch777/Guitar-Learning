"""Release complete repeated-note rhythm choices observed in the same source."""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import json
import math
from source_rhythm_groups import inventory

POLICY='source_complete_group_rhythm'


def options(tier1,target_ref,prepared=None):
    view=inventory(tier1)if prepared is None else prepared
    target=next((g for g in view['groups']if g['id']==target_ref),None)
    if target is None:raise ValueError('Complete original source bracket required')
    donors=[g for g in view['groups']if not g['reasons']and g['context_key']==target['context_key']and not set(g['closure_refs'])&set(target['closure_refs'])]if not target['reasons']else[]
    grouped=defaultdict(list)
    for d in donors:grouped[tuple(d['shares'])].append(d)
    witness=None
    if len(grouped)>1:
        witness=next(([a['id'],b['id']]for i,a in enumerate(donors)for b in donors[i+1:]if a['shares']!=b['shares']and not set(a['closure_refs'])&set(b['closure_refs'])),None)
    observed=[dict(shares=list(shares),donor_refs=[d['id']for d in group],changed=list(shares)!=target['shares'])for shares,group in sorted(grouped.items())]
    return dict(target_ref=target_ref,target=deepcopy(target),observed_options=observed,options=deepcopy(observed)if witness else[],witness_pair=witness,
                status='UNSUPPORTED_GROUP'if target['reasons']else'SOURCE_SUPPORTED_GROUP_CHOICES'if witness else'NO_INDEPENDENT_MULTI_CHOICE')


def validate_controls(controls):
    if type(controls)is not dict or set(controls)!={'context_policy','rhythm','target_ref','seed'}or controls['context_policy']!=POLICY:raise ValueError('Explicit local rhythm controls required; all other dimensions locked')
    value=controls['rhythm']
    if type(value)not in(int,float)or not math.isfinite(value)or not 0<=value<=100:raise ValueError('Rhythm release must be0..100')
    if type(controls['seed'])is not int or type(controls['target_ref'])is not str or not controls['target_ref'].startswith('source-beam:'):raise ValueError('Source group identity and typed seed required')


def sample(evidence,controls):
    validate_controls(controls)
    from declared_degree_choices import sample as release
    return release(evidence,dict(voicing=controls['rhythm'],seed=controls['seed']))


def apply(upper,target_ref,shares):
    from group_rhythm_relations import SCHEMA,expand
    edited=deepcopy(upper);model=edited['musical_relationships']
    if model.get('schema')!=SCHEMA:raise ValueError('Sole complete-group time authority required')
    group=next((g for g in model['groups']if g['id']==target_ref),None)
    if group is None:raise ValueError('Group is not owned by the rhythm relation')
    group['shares']=deepcopy(shares);expand(model)
    return edited


def verify_effect(before,after,target,shares):
    """Independent source occurrence/time comparisons; no core-view trust."""
    from source_fact_tier1 import project_documents
    from run_reversible_tier_qa import extract_documents
    old={r['id']:r for r in before['facts']};new={r['id']:r for r in after['facts']}
    if before['documents']!=after['documents']or before['scope']!=after['scope']or list(old)!=list(new):raise ValueError('Rhythm edit changed source topology/order')
    allowed={ref+tail for ref in target['beat_refs']for tail in('/type','/duration/0','/duration/1')}
    for ref,row in old.items():
        if ref not in allowed and row!=new[ref]:raise ValueError('Rhythm edit changed a locked source fact')
        if ref in allowed and {k:v for k,v in row.items()if k!='value'}!={k:v for k,v in new[ref].items()if k!='value'}:raise ValueError('Rhythm edit changed notation structure')
    a=extract_documents(project_documents(before));b=extract_documents(project_documents(after));refs=set(target['occurrence_refs'])
    if {k:v for k,v in a.items()if k!='events'}!={k:v for k,v in b.items()if k!='events'}or len(a['events'])!=len(b['events']):raise ValueError('Rhythm changed score scope')
    start=F(target['start_q']);span=F(target['span_q']);expected={};pos=start
    for ref,share in zip(target['occurrence_refs'],shares):expected[ref]=(pos,span*F(share));pos+=span*F(share)
    if pos!=start+span:raise ValueError('Group span changed')
    for left,right in zip(a['events'],b['events']):
        if left['id']not in refs:
            if left!=right:raise ValueError('An outside note or clock moved')
        else:
            if {k:v for k,v in left.items()if k not in('onset_q','duration_q')}!={k:v for k,v in right.items()if k not in('onset_q','duration_q')}:raise ValueError('A locked note field changed')
            if (F(right['onset_q']),F(right['duration_q']))!=expected[left['id']]:raise ValueError('Source timing does not solve share relationship')
    # Consecutive identical pitches cover the identical interval at both settings.
    # This says nothing about real acoustic decay or expressive attack intent.
    selected=[e for e in a['events']if e['id']in refs]
    if len({(e['part_id'],e['pitch'])for e in selected})!=1:raise ValueError('Written pitch contribution is not invariant')
    return dict(status='EXACT_GROUP_TIMING_ONLY_CHANGE',changed_occurrence_refs=target['occurrence_refs'],
                fixed_start_q=target['start_q'],fixed_span_q=target['span_q'],nominal_pitch_contribution_preserved=True,
                attack_conditioned_harmonic_context='recomputed_not_claimed_unchanged')


def intervene(upper,controls):
    validate_controls(controls)
    from connected_tier2 import realize
    before=realize(upper)
    if controls['rhythm']==0:return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False)
    evidence=options(before,controls['target_ref']);choice,decision=sample(evidence,controls);decision['evidence']=evidence
    if choice is None:return deepcopy(upper),decision
    edited=apply(upper,controls['target_ref'],choice['shares'])
    decision['influence_check']=verify_effect(before,realize(edited),evidence['target'],choice['shares'])
    decision['status']='SOURCE_SUPPORTED_RHYTHM_CHANGE'if decision['changed']else'OBSERVED_COINCIDENCE'
    return edited,decision
