"""Observed attack emphasis in matching local source contexts.

The optional owner supplies exact absence/presence. This policy selects only
source-observed states; it does not invent phrase intent or accent strength.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import math
from source_fact_tier1 import project_documents
from local_dynamics import inventory as dynamic_inventory

POLICY='source_local_note_accent'
NOTE_EXPR=('hp','ghost','dead','tie','slide','bend','harmonic','harmonicFret','staccato','tremolo','vibrato','wideVibrato','leftHandVibrato','pickScrape','trill')
BEAT_EXPR=('brushStroke','arpeggio','downArpeggio','letRing','tremoloBar','fadeIn','tapping','gradualVelocity','sustainPedal')


def inventory(tier1):
    from source_tie_tier1 import extract_documents
    try:from source_semantics import whole_measure_rest
    except ModuleNotFoundError as exc:
        if exc.name!='source_semantics':raise
        from songsterr_automation.songsterr_api.source_semantics import whole_measure_rest
    docs=project_documents(tier1);lower=extract_documents(docs)
    states={s['occurrence_ref']:s for s in dynamic_inventory(tier1)['states']}
    events={e['id']:e for e in lower['events']};frames={f['ordinal']:f for f in lower['measure_geometry']['frames']}
    warnings=lower['source_coverage']['layout_warnings']+lower['source_coverage']['timing_warnings'];rows=[]
    for name,part in sorted(docs.items()):
        if not name.startswith('track-'):continue
        for bar,measure in enumerate(part.get('measures',[]),1):
            frame=frames.get(bar)
            for voice,v in enumerate(measure.get('voices',[])):
                pos=F(0);known_clock=True
                for beat,b in enumerate(v.get('beats',[])):
                    raw_duration=b.get('duration');valid=type(raw_duration)is list and len(raw_duration)==2 and all(type(x)is int for x in raw_duration)and raw_duration[0]>=0 and raw_duration[1]>0
                    duration=F(*raw_duration)*4 if valid else None
                    if duration is None:known_clock=False
                    beat_ref=f'{name}#/measures/{bar-1}/voices/{voice}/beats/{beat}'
                    for ni,n in enumerate(b.get('notes',[])):
                        ref=f"event:{part['songId']}:{part['partId']}:{bar}:{voice}:{beat}:{ni}";note_ref=beat_ref+f'/notes/{ni}'
                        state={'kind':'absent'}if'accentuated'not in n else dict(kind='explicit',value=deepcopy(n['accentuated']))
                        sound=0 if state['kind']=='absent'else state['value']if type(state['value'])is int and state['value']in(0,1,2)else None
                        dynamic=states.get(ref);reasons=[]
                        if n.get('rest'):reasons.append('SOURCE_REST')
                        if ref not in events:reasons.append('NO_NORMALIZED_SOURCE_EVENT')
                        elif events[ref]['pitch']is None or F(events[ref]['pitch']).denominator!=1:reasons.append('UNKNOWN_OR_FRACTIONAL_WRITTEN_PITCH')
                        if type(part.get('instrumentId'))is not int or not 0<=part['instrumentId']<128:reasons.append('NONPITCHED_OR_UNKNOWN_INSTRUMENT')
                        if not dynamic or not dynamic['known']:reasons.append('UNKNOWN_WRITTEN_DYNAMIC')
                        if sound is None:reasons.append('UNKNOWN_ACCENT_DECLARATION')
                        if b.get('graceNote')or duration is None or duration<=0:reasons.append('NONPOSITIVE_OR_UNKNOWN_REGULAR_DURATION')
                        if frame is None or F(frame['span_q'])!=F(frame['signature'][0])*4/F(frame['signature'][1]):reasons.append('NONNOMINAL_FRAME')
                        if not known_clock:reasons.append('UNKNOWN_BAR_OFFSET')
                        if frame and known_clock and not F(0)<=pos<F(frame['span_q']):reasons.append('OUTSIDE_SOURCE_FRAME')
                        if frame and duration is not None and pos+duration>F(frame['span_q']):reasons.append('SOURCE_FRAME_CROSSING')
                        if any(w.get('bar')==bar and(w.get('part_id')is None or w['part_id']==part['partId'])for w in warnings):reasons.append('SOURCE_CLOCK_QUALIFICATION')
                        expression=[k for k in NOTE_EXPR if n.get(k)]+['beat:'+k for k in BEAT_EXPR if b.get(k)]
                        if expression:reasons.append('OTHER_EXECUTION_OR_ARTICULATION')
                        meter=deepcopy(frame['signature'])if frame else None;mark=dynamic['marking']if dynamic else None
                        key=None if reasons else[part['partId'],voice,mark,meter,str(pos),str(duration)]
                        rows.append(dict(occurrence_ref=ref,note_ref=note_ref,beat_ref=beat_ref,part_id=part['partId'],bar=bar,voice=voice,beat=beat,note=ni,
                            state=state,sound_level=sound,dynamic_marking=mark,dynamic_origin_ref=dynamic['origin_fact_ref']if dynamic else None,
                            source_meter=meter,position_q=str(pos),duration_q=str(duration)if duration is not None else None,
                            context_key=key,reasons=sorted(set(reasons)),expression_fields=expression))
                    if valid and not b.get('graceNote'):
                        pos+=F(frame['span_q'])if frame and whole_measure_rest(measure,v)else duration
    return dict(schema='source-local-accents/1',occurrences=sorted(rows,key=lambda r:(r['part_id'],r['bar'],r['voice'],r['beat'],r['note'])))


def options(tier1,target_ref,prepared=None):
    view=inventory(tier1)if prepared is None else prepared
    target=next((r for r in view['occurrences']if r['occurrence_ref']==target_ref),None)
    if target is None:raise ValueError('Original note occurrence required')
    donors=[r for r in view['occurrences']if target['context_key']is not None and r['context_key']==target['context_key']and r['beat_ref']!=target['beat_ref']]
    witness=None
    for i,a in enumerate(donors):
        for b in donors[i+1:]:
            if a['beat_ref']!=b['beat_ref']and a['sound_level']!=b['sound_level']:
                witness=[a['occurrence_ref'],b['occurrence_ref']];break
        if witness:break
    groups=defaultdict(list)
    for row in donors:groups[row['sound_level'],row['state']['kind']].append(row)
    observed=[]
    for (level,kind),rows in sorted(groups.items()):
        state=deepcopy(rows[0]['state'])
        observed.append(dict(state=state,sound_level=level,donor_refs=sorted(r['occurrence_ref']for r in rows),changed=state!=target['state']))
    status='NO_SUPPORTED_ACCENT_CONTEXT'if target['reasons']else'SOURCE_SUPPORTED_LOCAL_ACCENT_CHOICES'if witness else'NO_INDEPENDENT_ACCENT_MULTI_CHOICE'
    return dict(target_ref=target_ref,target=deepcopy(target),observed_options=observed,options=deepcopy(observed)if witness else[],witness_pair=witness,status=status)


def validate_controls(controls):
    if type(controls)is not dict or set(controls)!={'context_policy','accents','target_ref','seed'}or controls['context_policy']!=POLICY:raise ValueError('Explicit local accent controls required; all other dimensions locked')
    value=controls['accents']
    if type(value)not in(int,float)or not math.isfinite(value)or not 0<=value<=100:raise ValueError('Accent release must be0..100')
    if type(controls['seed'])is not int or type(controls['target_ref'])is not str or not controls['target_ref'].startswith('event:'):raise ValueError('Original note identity and typed seed required')


def sample(evidence,controls):
    validate_controls(controls)
    from declared_degree_choices import sample as release
    chosen,decision=release(evidence,dict(voicing=controls['accents'],seed=controls['seed']))
    if chosen is not None:decision['status']='SOURCE_SUPPORTED_ACCENT_STATE'if decision['changed']else'OBSERVED_COINCIDENCE'
    return chosen,decision


def apply(upper,note_ref,state):
    from optional_accent_slots import expand
    if upper.get('schema')!='connected-source-musical-relations/2':raise ValueError('Optional source-accent ownership required')
    if type(state)is not dict or not(state=={'kind':'absent'}or set(state)=={'kind','value'}and state['kind']=='explicit'and type(state['value'])is int and state['value']in(0,1,2)):raise ValueError('Known optional accent state required')
    edited=deepcopy(upper)
    group=next((g for g in edited['owned_parameters']['optional_note_accents']['groups']if g['note_structure']['id']==note_ref),None)
    if group is None:raise ValueError('Sole optional note owner required')
    previous=group['state'];group['state']=deepcopy(state)
    if state['kind']=='explicit':group['state']['child_index']=previous['child_index']if previous['kind']=='explicit'else len(group['note_structure']['children'])
    expand(group)
    return edited


def verify_effect(before,after,note_ref,state):
    """Only this note's optional accent and necessary child membership may vary."""
    if before['documents']!=after['documents']or before['scope']!=after['scope']:raise ValueError('Accent edit changed document scope')
    old={r['id']:deepcopy(r)for r in before['facts']};new={r['id']:r for r in after['facts']};ref=note_ref+'/accentuated';note=old[note_ref]
    if state['kind']=='absent':
        if ref in old:del old[ref];note['children'].remove(ref)
    elif ref in old:old[ref]['value']=state['value']
    else:
        note['children'].append(ref)
        old[ref]=dict(id=ref,document=note['document'],pointer=note['pointer']+'/accentuated',parent=note_ref,slot='accentuated',type='integer',value=state['value'])
    if old!=new:raise ValueError('Accent edit changed a locked source fact')
    return dict(status='EXACT_SINGLE_NOTE_ACCENT_SCOPE',note_ref=note_ref,state=deepcopy(state))


def intervene(upper,controls):
    validate_controls(controls)
    from connected_tier2 import realize
    before=realize(upper)
    if controls['accents']==0:return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False)
    evidence=options(before,controls['target_ref']);chosen,decision=sample(evidence,controls);decision['evidence']=evidence
    if chosen is None:return deepcopy(upper),decision
    edited=apply(upper,evidence['target']['note_ref'],chosen['state'])
    decision['influence_check']=verify_effect(before,realize(edited),evidence['target']['note_ref'],chosen['state'])
    return edited,decision
