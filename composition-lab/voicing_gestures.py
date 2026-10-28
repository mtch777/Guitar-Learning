"""Atomic source-observed voicing sequences, not inferred musical phrases.

Maximal matching consecutive coattack runs supply choices. All physical and
incident-path requirements remain those of the existing single-group policy.
Only the scope of the explicitly released operation changes.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
import random

POLICY='source_gesture_context'
MAX_MATCHED_PAIRS=100000


def token(v):return json.dumps(v,sort_keys=True,separators=(',',':'))


def discover(units,*,max_pairs=MAX_MATCHED_PAIRS):
    """All maximal matches; no arbitrary excerpt length or eligible-row skipping."""
    from voicing_context_relations import BASE_FIELDS
    parts=defaultdict(list);pairs=0;links=[]
    for row in units:parts[row['part_id']].append(row)
    for part,rows in sorted(parts.items()):
        rows.sort(key=lambda r:(F(r['onset_q']),r['id']))
        keys=[None if r['refusal_reasons'] else token([json.loads(r['family_context_key'])[k] for k in BASE_FIELDS]) for r in rows]
        index=defaultdict(list)
        for i,k in enumerate(keys):
            if k is not None:index[k].append(i)
        count=sum(len(v)*(len(v)-1) for v in index.values());pairs+=count
        if pairs>max_pairs:return dict(status='RESOURCE_BOUND_REFUSAL',matched_pairs=pairs,limit=max_pairs,links=[])
        def equal(i,j):return 0<=i<len(rows) and 0<=j<len(rows) and keys[i] is not None and keys[i]==keys[j]
        def gap(i):return F(rows[i]['onset_q'])-F(rows[i-1]['onset_q'])
        for i,key in enumerate(keys):
            if key is None:continue
            for j in index[key]:
                if i==j:continue
                if equal(i-1,j-1) and gap(i)==gap(j):continue
                n=1
                while equal(i+n,j+n) and gap(i+n)==gap(j+n):n+=1
                if n<2:continue
                target=[r['id'] for r in rows[i:i+n]];donor=[r['id'] for r in rows[j:j+n]]
                links.append(dict(target_refs=target,donor_refs=donor,
                    refusal='OVERLAPPING_SOURCE_RUNS' if set(target)&set(donor) else None))
    return dict(status='COMPLETE_MAXIMAL_SOURCE_MATCHES',matched_pairs=pairs,limit=max_pairs,links=links)


def catalog(tier1):
    from voicing_register import inventory
    from voicing_context_relations import catalog as lane_catalog
    base=lane_catalog(inventory(tier1,'transposed_voicing_family'),tier1,joint=True)
    matches=discover(base['units']);groups={}
    for link in matches['links']:
        key=token(link['target_refs'])
        if key not in groups:
            ident=link['target_refs'][0]+'|gesture:'+hashlib.sha256(key.encode()).hexdigest()
            groups[key]=dict(id=ident,target_refs=link['target_refs'],donors=[],refusal_reasons=[])
        groups[key]['donors'].append(link)
    return dict(base=base,units=list(groups.values()),discovery=matches,
        meaning='Exact recurrence of pitch-class/rhythm context; not an inferred phrase or artist intent')


def assignments(cat,target_id):
    block=next(r for r in cat['units'] if r['id']==target_id)
    rows={r['id']:r for r in cat['base']['units']}
    return block,rows,[rows[r] for r in block['target_refs']]


def labels(target,value):
    from technique_analysis import classify_group
    return classify_group([dict(midi=F(value['anchor'])+F(i),string=s) for i,s in zip(value['intervals'],value['strings'])])


def options(cat,target_id):
    from family_policy import admissible
    from voicing_context_relations import check_many
    block,rows,targets=assignments(cat,target_id);choices={};rejected=[];cache={}
    base=cat['base'];g=base['lane_relationships']
    source=({(p['kind'],p['center']):{k:v for k,v in p.items() if k not in ('kind','center')} for p in base['source_path_relations']},base['source_path_index'])
    original=[dict(t['realization'],strings=t['fixed_output_strings']) for t in targets]
    for link in block['donors']:
        reasons=[link['refusal']] if link['refusal'] else [];values=[]
        for target,ref in zip(targets,link['donor_refs']):
            value,reason=admissible(target,rows[ref]);values.append(value)
            if reason:reasons.append(reason)
            old=dict(target['realization'],strings=target['fixed_output_strings'])
            if labels(target,old)!=labels(target,value):reasons.append('LOCKED_COATTACK_TECHNIQUE_CLASS')
            if value!=old and json.loads(target['family_context_key'])['execution_uncertainty']:reasons.append('UNKNOWN_TARGET_OVERLAP_EXECUTION')
        relation=None
        if not reasons:
            key=token(values)
            if key not in cache:
                cache[key]=dict(status='PASS_UNCHANGED_PITCH_RELATIONSHIPS',reasons=[],witnesses=[]) if values==original else check_many(g,list(zip(targets,values)),source,allow_string_changes=True)
            relation=cache[key]
            if relation['status']=='REFUSED':reasons.extend(relation['reasons'])
        if reasons:
            rejected.append(dict(donor_refs=link['donor_refs'],reasons=sorted(set(reasons))));continue
        key=token(values);choices.setdefault(key,dict(realizations=values,donor_sequences=[],relationship_witnesses=relation))['donor_sequences'].append(link['donor_refs'])
    values=[choices[k] for k in sorted(choices)];alternative=any(v['realizations']!=original for v in values)
    return dict(status='SUPPORTED_EMPIRICAL_ALTERNATIVES' if alternative else 'OBSERVED_SINGLE_REALIZATION' if values else 'NO_ELIGIBLE_ALTERNATIVE',
        target_ref=target_id,original=original,options=values,rejected=rejected,levels=[dict(level='maximal_source_sequence',source_runs=len(block['donors']),distinct_realizations=len(values))])


def sample_choice(cat,controls):
    from voicing_register import validate_controls
    validate_controls(controls)
    if controls['register']!=0:raise ValueError('Gesture bass registers are locked')
    if not controls['voicing'] and not controls['physical']:
        return None,dict(status='EXACT_ZERO_LOCK',changed=False,released=dict(voicing=False,register=False,physical=False))
    evidence=options(cat,controls['target_ref']);rng=random.Random(controls['seed'])
    released={k:rng.random()<controls[k]/100 for k in ('voicing','register','physical')}
    allowed=[o for o in evidence['options'] if all(
        (released['voicing'] or a['intervals']==b['intervals']) and
        (released['physical'] or a['strings']==b['strings']) and a['anchor']==b['anchor']
        for a,b in zip(o['realizations'],evidence['original']))]
    population=[(o,d) for o in allowed for d in o['donor_sequences']]
    if not population:return None,dict(status='NO_OBSERVED_CHOICE_SATISFIES_LOCKS',changed=False,released=released)
    choice,donor=rng.choice(population);changed=choice['realizations']!=evidence['original']
    return deepcopy(choice['realizations']),dict(status='SOURCE_SUPPORTED_GESTURE' if changed else 'OBSERVED_COINCIDENCE',changed=changed,
        released=released,target_ref=controls['target_ref'],donor_refs=donor,chosen=deepcopy(choice),
        opportunities='One joint source-run choice, not one independent chance per note')


def validate_actual(before,after,targets,values,cat):
    from voicing_context_relations import graph,check_many
    from voicing_register import tie_relationships
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    from execution_dependencies import build
    a,b=graph(before),graph(after);expected=deepcopy(a)
    for target,value in zip(targets,values):
        for ref,interval,string in zip(target['member_refs'],value['intervals'],value['strings']):
            expected['nodes'][ref].update(pitch=str(F(value['anchor'])+F(interval)),string=string)
    if expected!=b:raise ValueError('Actual joint inverse changed locked notes/time/declarations')
    if tie_relationships(extract_documents(project_documents(after)))!=cat['base']['written_tie_relationships']:raise ValueError('Written tie relationships changed')
    if build(after)['signature']!=cat['base']['execution_dependencies']['signature']:raise ValueError('Execution dependencies changed')
    relation=check_many(a,list(zip(targets,values)),allow_string_changes=True)
    if relation['status']=='REFUSED':raise ValueError('Actual combined motion lacks source support')
    # Re-run the approved detector unchanged; voicing permission cannot silently
    # introduce/remove/relabel approved pedal calls and responses.
    from freeze_technique_baseline import retained
    def pedals(tier):return [t['approved_pedal_phrases'] for t in retained(project_documents(tier))['tracks']]
    if pedals(before)!=pedals(after):raise ValueError('Locked approved pedal analysis changed')
    return relation


def intervene(upper,controls):
    from connected_tier2 import realize
    from voicing_register import apply_family_choices,validate_controls
    validate_controls(controls);before=realize(upper)
    if not controls['voicing'] and not controls['physical']:
        return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',changed=False)
    cat=catalog(before)
    if cat['discovery']['status']=='RESOURCE_BOUND_REFUSAL':return deepcopy(upper),dict(status='RESOURCE_BOUND_REFUSAL',changed=False)
    values,decision=sample_choice(cat,controls)
    if values is None:return deepcopy(upper),decision
    block,rows,targets=assignments(cat,controls['target_ref'])
    edited=apply_family_choices(upper,list(zip(targets,values)))
    if 'contextual_constraints' in edited:
        from contextual_note_roles import evaluate
        requests=[r['request'] for r in edited.pop('contextual_constraints')['results']]
        edited['contextual_constraints']=evaluate(realize(edited),requests)
    validate_actual(before,realize(edited),targets,values,cat)
    return edited,decision
