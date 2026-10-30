"""Opt-in component-conditioned global speed experiment, with partial evidence.

No tempo is invented. A whole written interval changes speed because an exact
source rhythmic component has independent observations at those speeds. This
does not establish band consensus, transition suitability or artist preference.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import math,re

POLICY='source_rhythmic_component_tempo'


def component_id(part,voice):return f'part:{part}:voice:{voice}'


def inventory(tier1):
    from source_fact_tier1 import project_documents
    from tempo_source_census import global_inventory_documents,component_inventory_documents,tempo_opportunities
    docs=project_documents(tier1);clock=global_inventory_documents(docs)
    view=component_inventory_documents(docs,clock);choices=tempo_opportunities(view)
    native_reasons=[]
    if clock['unlocated']:native_reasons.append('UNLOCATED_TEMPO_DECLARATION')
    if clock['unsupported_temporal_records']:native_reasons.append('UNSUPPORTED_TEMPORAL_RECORD')
    if clock['extra_tempo_fields']:native_reasons.append('EXTRA_TEMPO_DECLARATION_REQUIRES_EXECUTION_PROOF')
    if any(e['native_reasons']for e in clock['global_events']):native_reasons.append('COMPLETE_NATIVE_STEP_MAP_NOT_QUALIFIED')
    return dict(schema='source-rhythmic-component-tempo-options/1',clock=clock,components=view,choices=choices,
        native_reasons=native_reasons,scope='Opt-in partial component-conditioned whole-band written interval speed. No full-band or full-lifetime artistic acceptance.')


def options(tier1,target_ref,component_ref,prepared=None):
    view=inventory(tier1)if prepared is None else prepared
    event=next((r for r in view['clock']['global_events']if r['id']==target_ref),None)
    temporal=next((r for r in view['components']['events']if r['event_id']==target_ref),None)
    if event is None or temporal is None:raise ValueError('Original global tempo event required')
    rows=[r for r in view['choices']['A_passage_speed']['components']if r['event_id']==target_ref]
    selected=next((r for r in rows if component_id(r['part_id'],r['voice'])==component_ref),None)
    if selected is None:raise ValueError('Original part and voice component required')
    original_component=next(r for r in temporal['components']if component_id(r['part_id'],r['voice'])==component_ref)
    full=next(r for r in view['choices']['A_passage_speed']['ensembles']if r['event_id']==target_ref)
    target=dict(event_id=event['id'],alias_refs=deepcopy(event['alias_refs']),bpm_refs=[r+'/bpm'for r in event['alias_refs']],
        **{k:deepcopy(event[k])for k in('quarter_bpm','onset_q','end_q','bar','position_q','incoming_bpm','outgoing_bpm','source_lifetime_q')},
        component_ref=component_ref,evidence_label='PARTIAL',component_evidence=deepcopy(selected),
        component_context=deepcopy(original_component),all_component_evidence=deepcopy(rows),full_ensemble_evidence=deepcopy(full),
        closure={k:deepcopy(temporal[k])for k in('closure_start_q','closure_end_q','closure_refs')},
        full_influence_musical_suitability=temporal['full_influence_musical_suitability'])
    index={e['event_id']:e for e in view['components']['events']};grouped=defaultdict(list)
    for ref in selected['donor_event_ids']:grouped[index[ref]['bpm']].append(ref)
    observed=[dict(quarter_bpm=bpm,donor_refs=sorted(refs),changed=bpm!=event['quarter_bpm'])for bpm,refs in sorted(grouped.items(),key=lambda item:F(item[0]))]
    eligible=bool(selected['independent_contrast'])and not view['native_reasons']
    return dict(target_ref=target_ref,component_ref=component_ref,target=target,observed_options=observed,
        options=deepcopy(observed)if eligible else[],witness_pair=deepcopy(selected['independent_contrast']),
        native_reasons=deepcopy(view['native_reasons']),evidence_label='PARTIAL',
        status='REFUSED_NATIVE_TEMPO_MAP'if view['native_reasons']else'PARTIAL_SOURCE_COMPONENT_SPEED_CHOICES'if eligible else selected['status'],
        donor_closures=[{k:deepcopy(index[ref][k])for k in('event_id','onset_q','end_q','incoming_bpm','outgoing_bpm','closure_start_q','closure_end_q','closure_refs')}for ref in selected['donor_event_ids']])


def validate_controls(controls):
    if type(controls)is not dict or set(controls)!={'context_policy','tempo','target_ref','component_ref','seed'}or controls['context_policy']!=POLICY:
        raise ValueError('Explicit opt-in component-conditioned speed controls required; other written dimensions locked')
    value=controls['tempo']
    if type(value)not in(int,float)or not math.isfinite(value)or not 0<=value<=100:raise ValueError('Tempo release must be 0..100')
    if type(controls['seed'])is not int:raise ValueError('Integer seed required')
    if type(controls['target_ref'])is not str or re.fullmatch(r'global-tempo:(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?',controls['target_ref'])is None:raise ValueError('Original global tempo identity required')
    if type(controls['component_ref'])is not str or re.fullmatch(r'part:(?:0|[1-9][0-9]*):voice:(?:0|[1-9][0-9]*)',controls['component_ref'])is None:raise ValueError('Original part/voice component identity required')


def sample(evidence,controls):
    validate_controls(controls)
    from declared_degree_choices import sample as release
    chosen,decision=release(evidence,dict(voicing=controls['tempo'],seed=controls['seed']))
    decision['evidence_label']='PARTIAL'
    if chosen is not None:decision['status']='PARTIAL_COMPONENT_CONDITIONED_SPEED'if decision['changed']else'OBSERVED_COINCIDENCE'
    return chosen,decision


def verify_effect(before,after,target,bpm):
    """Every original alias changes together; every other typed source fact locks."""
    value=F(bpm)
    if value.denominator!=1 or value<=0:raise ValueError('Observed positive integer quarter BPM required')
    if {k:v for k,v in before.items()if k!='facts'}!={k:v for k,v in after.items()if k!='facts'}:raise ValueError('Source document envelope changed')
    if [r['id']for r in before['facts']]!=[r['id']for r in after['facts']]:raise ValueError('Source fact occurrence order changed')
    expected={r['id']:deepcopy(r)for r in before['facts']};actual={r['id']:r for r in after['facts']}
    if len(expected)!=len(before['facts'])or len(actual)!=len(after['facts']):raise ValueError('Duplicate source fact ownership')
    refs=target['bpm_refs']
    if not refs or refs!=sorted(set(refs)):raise ValueError('Complete unique ordered source BPM aliases required')
    for ref in refs:
        if ref not in expected or expected[ref]['type']!='integer' or F(expected[ref]['value'])!=F(target['quarter_bpm']):raise ValueError('Target aliases no longer agree')
        expected[ref]['value']=value.numerator
    if expected!=actual:raise ValueError('Tempo edit changed a locked source fact or omitted an alias')
    return dict(status='EXACT_GLOBAL_BPM_ALIAS_SCOPE',bpm_refs=deepcopy(refs),quarter_bpm=str(value),
        written_interval=[target['onset_q'],target['end_q']],scope='Written dimensions locked. Native seconds, expression and audio require separate verification.')


def intervene(upper,controls):
    validate_controls(controls)
    from connected_tier2 import realize
    from step_tempo_relations import set_bpm
    before=realize(upper)
    if controls['tempo']==0:return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False,evidence_label='PARTIAL')
    evidence=options(before,controls['target_ref'],controls['component_ref']);chosen,decision=sample(evidence,controls);decision['evidence']=evidence
    if chosen is None:return deepcopy(upper),decision
    edited=deepcopy(upper)
    model=edited['owned_parameters']['global_step_tempos']
    edited['owned_parameters']['global_step_tempos']=set_bpm(model,controls['target_ref'],chosen['quarter_bpm'])
    decision['influence_check']=verify_effect(before,realize(edited),evidence['target'],chosen['quarter_bpm'])
    return edited,decision
