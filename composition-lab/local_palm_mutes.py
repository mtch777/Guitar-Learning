"""Source-observed complete-coattack palm muting through its existing inverse."""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import math,re
from palm_mute_opportunity_census import inventory,independent,encoded

POLICY='source_local_palm_mute'


def states(row):return[deepcopy(d['state'])for d in row['declarations']]


def options(tier1,target_ref,prepared=None):
    view=inventory(tier1)if prepared is None else prepared
    target=next((r for r in view['coattacks']if r['coattack_ref']==target_ref),None)
    if target is None:raise ValueError('Original complete coattack required')
    donors=[r for r in view['coattacks']if target['context_key']is not None and r['context_key']==target['context_key']and independent(target,r)]
    witness=next(([a['coattack_ref'],b['coattack_ref']]for a in donors if a['mute_mode']=='on'for b in donors if b['mute_mode']=='off'and independent(a,b)),None)
    grouped=defaultdict(list)
    for row in donors:grouped[encoded(states(row))].append(row)
    observed=[]
    for key,rows in sorted(grouped.items()):
        state=states(rows[0]);mode=rows[0]['mute_mode']
        observed.append(dict(states=state,mute_mode=mode,donor_refs=sorted(r['coattack_ref']for r in rows),
            changed=state!=states(target),mute_changed=mode!=target['mute_mode']))
    return dict(target_ref=target_ref,target=deepcopy(target),observed_options=observed,
        options=deepcopy(observed)if witness else[],witness_pair=witness,
        status='REFUSED_PALM_MUTE_CONTEXT'if target['reasons']else'SOURCE_SUPPORTED_PALM_MUTE_CHOICES'if witness else'NO_INDEPENDENT_PALM_MUTE_ALTERNATIVES')


def validate_controls(controls):
    if type(controls)is not dict or set(controls)!={'context_policy','palm_mute','target_ref','seed'}or controls['context_policy']!=POLICY:raise ValueError('Explicit palm-mute controls required; all other dimensions locked')
    amount=controls['palm_mute']
    if type(amount)not in(int,float)or not math.isfinite(amount)or not 0<=amount<=100:raise ValueError('Palm-mute release must be0..100')
    if type(controls['seed'])is not int or type(controls['target_ref'])is not str or re.fullmatch(r'coattack:(?:0|[1-9][0-9]*):(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?',controls['target_ref'])is None:raise ValueError('Typed original coattack identity and seed required')


def sample(evidence,controls):
    validate_controls(controls)
    from declared_degree_choices import sample as release
    chosen,decision=release(evidence,dict(voicing=controls['palm_mute'],seed=controls['seed']))
    decision['mute_changed']=bool(chosen and chosen['mute_changed'])
    if chosen is not None:decision['status']='SOURCE_SUPPORTED_PALM_MUTE_STATE'if decision['changed']else'OBSERVED_COINCIDENCE'
    return chosen,decision


def apply(upper,beat_refs,new_states):
    from optional_palm_mute_slots import expand
    if upper.get('schema')!='connected-source-musical-relations/3':raise ValueError('Optional palm-mute ownership required')
    if type(beat_refs)is not list or not beat_refs or any(type(r)is not str for r in beat_refs)or beat_refs!=sorted(set(beat_refs))or type(new_states)is not list or len(beat_refs)!=len(new_states):raise ValueError('Complete ordered beat/state correspondence required')
    edited=deepcopy(upper);index={g['beat_structure']['id']:g for g in edited['owned_parameters']['optional_beat_palm_mutes']['groups']}
    for ref,state in zip(beat_refs,new_states):
        if type(state)is not dict or not(state=={'kind':'absent'}or set(state)=={'kind','value'}and state['kind']=='explicit'and type(state['value'])is bool):raise ValueError('Known exact optional Boolean required')
        if ref not in index:raise ValueError('Sole optional beat owner required')
        group=index[ref];previous=group['state'];group['state']=deepcopy(state)
        if state['kind']=='explicit':group['state']['child_index']=previous['child_index']if previous['kind']=='explicit'else len(group['beat_structure']['children'])
        expand(group)
    return edited


def verify_effect(before,after,beat_refs,new_states):
    """Only selected flag facts and necessary child membership may differ."""
    if {k:v for k,v in before.items()if k!='facts'}!={k:v for k,v in after.items()if k!='facts'}:raise ValueError('Source document envelope changed')
    old={r['id']:deepcopy(r)for r in before['facts']};new={r['id']:r for r in after['facts']}
    for ref,state in zip(beat_refs,new_states):
        beat=old[ref];flag=ref+'/palmMute'
        if state['kind']=='absent':
            if flag in old:del old[flag];beat['children'].remove(flag)
        elif flag in old:old[flag]['value']=state['value']
        else:
            beat['children'].append(flag)
            old[flag]=dict(id=flag,document=beat['document'],pointer=beat['pointer']+'/palmMute',parent=ref,slot='palmMute',type='boolean',value=state['value'])
    if old!=new:raise ValueError('Palm-mute edit changed a locked source fact')
    return dict(status='EXACT_COMPLETE_COATTACK_PALM_MUTE_SCOPE',beat_refs=deepcopy(beat_refs),states=deepcopy(new_states),
        scope='Written flags only; performed duration is evaluated separately by native playback')


def intervene(upper,controls):
    validate_controls(controls)
    from connected_tier2 import realize
    before=realize(upper)
    if controls['palm_mute']==0:return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False,mute_changed=False)
    evidence=options(before,controls['target_ref']);chosen,decision=sample(evidence,controls);decision['evidence']=evidence
    if chosen is None:return deepcopy(upper),decision
    edited=apply(upper,evidence['target']['beat_refs'],chosen['states'])
    decision['influence_check']=verify_effect(before,realize(edited),evidence['target']['beat_refs'],chosen['states'])
    return edited,decision
