"""Source-local dynamic transitions at an exact, known metrical position.

This policy adds context to the existing dynamic owner and sampler. It does not
invent phrase roles, loudness offsets, or a different inverse. Evidence is one
vote per source declaration, never one vote per inherited note.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
from source_fact_tier1 import project_documents
import local_dynamics as dynamics

POLICY='source_local_dynamic_transition'


def inventory(tier1):
    from source_tie_tier1 import extract_documents
    from musical_tier2 import geometry_relation
    try:
        from source_semantics import whole_measure_rest
    except ModuleNotFoundError as exc:
        if exc.name!='source_semantics':raise
        from songsterr_automation.songsterr_api.source_semantics import whole_measure_rest
    view=dynamics.inventory(tier1);docs=project_documents(tier1)
    lower=extract_documents(docs)
    events={e['id'] for e in lower['events']}
    geometry=geometry_relation(source=lower['measure_geometry'])['parameters']
    frames={f['ordinal']:f for f in geometry['frames']}
    members={p['part_id']:set(p['frame_refs'])for p in geometry['parts']}
    warnings=lower['source_coverage']['layout_warnings']+lower['source_coverage']['timing_warnings']
    # The existing context extractor rejects missing/conflicting meter above.
    # Retain exact declaration provenance without treating shared meter as a
    # reused dynamic outcome (it stays locked during this intervention).
    parts={n:p for n,p in docs.items()if n.startswith('track-')}
    meter_evidence={};meter_refs=[]
    for mi in range(max((len(p.get('measures',[]))for p in parts.values()),default=0)):
        explicit=[]
        for name,part in sorted(parts.items()):
            if mi>=len(part.get('measures',[])):continue
            signature=part['measures'][mi].get('signature')
            if signature:explicit.append((name+f'#/measures/{mi}/signature',signature))
        if explicit:
            meter_refs=sorted(ref for ref,_ in explicit)
        meter_evidence[mi+1]=meter_refs[:]
    positions={};locations={};nonnull=defaultdict(list)
    for name,part in sorted(docs.items()):
        if not name.startswith('track-'):continue
        pid=part['partId'];state={}
        for bar,measure in enumerate(part.get('measures',[]),1):
            frame=frames.get(bar)
            for voice,v in enumerate(measure.get('voices',[])):
                offset=F(0);clock_known=True
                for beat,b in enumerate(v.get('beats',[])):
                    base=f'{name}#/measures/{bar-1}/voices/{voice}/beats/{beat}'
                    issues=[]
                    if frame is None or frame['id']not in members.get(pid,set()):issues.append('MISSING_SOURCE_FRAME')
                    if frame is not None and F(frame['duration_q'])!=F(frame['meter']['beats'])*F(frame['meter']['beat_unit_q']):issues.append('NONNOMINAL_FRAME_METRICAL_SCOPE')
                    if any(w.get('bar')==bar and(w.get('part_id')is None or w['part_id']==pid)for w in warnings):issues.append('UNCERTAIN_SOURCE_CLOCK')
                    if b.get('graceNote'):issues.append('GRACE_SOURCE_CONTEXT')
                    duration=b.get('duration')
                    valid=type(duration)is list and len(duration)==2 and all(type(x)is int for x in duration)and duration[1]>0 and duration[0]>=0
                    if not valid:issues.append('UNKNOWN_BEAT_DURATION');clock_known=False
                    if not clock_known:issues.append('UNKNOWN_BAR_OFFSET')
                    if frame is not None and clock_known and not F(0)<=offset<F(frame['duration_q']):issues.append('OUTSIDE_SOURCE_FRAME')
                    def record(ref,incoming):
                        positions[ref]=dict(incoming=incoming,frame=frame,position=offset,issues=issues[:])
                        locations[ref]=(bar,beat)
                    if 'velocity'in b:record(base+'/velocity',state.get(voice))
                    if b.get('velocity')is not None:
                        state[voice]=(b['velocity'],base+'/velocity')
                        nonnull[pid,voice].append(base+'/velocity')
                    for ni,n in enumerate(b.get('notes',[])):
                        if 'velocity'in n:record(base+f'/notes/{ni}/velocity',state.get(voice))
                    if not b.get('graceNote')and valid:
                        offset+=F(frame['duration_q'])if frame is not None and whole_measure_rest(measure,v)else F(*duration)*4
    _,markings=dynamics.source_rules();contexts=[]
    for declaration in view['declarations']:
        ref=declaration['fact_ref'];p=positions[ref]
        reasons=declaration['reasons']+p['issues'];incoming=p['incoming']
        previous_ref=incoming[1]if incoming else None;previous_mark=incoming[0]if incoming else None
        if incoming is None:reasons.append('MISSING_INCOMING_DYNAMIC')
        elif type(previous_mark)is not str or previous_mark not in markings:reasons.append('UNKNOWN_INCOMING_DYNAMIC')
        if any(r not in events for r in declaration['influence_refs']):reasons.append('UNLOCATED_INFLUENCED_NOTE')
        boundary=None
        if declaration['scope']=='beat':
            following=[r for r in nonnull[declaration['part_id'],declaration['voice']]if locations[r]>locations[ref]]
            boundary=following[0]if following else None
        dependencies={ref,*declaration['influence_refs']}
        if previous_ref:dependencies.add(previous_ref)
        if boundary:dependencies.add(boundary)
        meter=deepcopy(p['frame']['meter'])if p['frame']is not None else None
        key=None if reasons else[declaration['part_id'],declaration['voice'],declaration['scope'],previous_mark,meter['beats'],str(F(meter['beat_unit_q'])),str(p['position'])]
        contexts.append(dict(fact_ref=ref,part_id=declaration['part_id'],voice=declaration['voice'],scope=declaration['scope'],
            outcome_marking=deepcopy(declaration['marking']),incoming_marking=deepcopy(previous_mark),incoming_fact_ref=previous_ref,
            following_boundary_fact_ref=boundary,source_meter=meter,position_q=str(p['position']),context_key=key,
            meter_source_refs=meter_evidence[declaration['bar']],
            reasons=sorted(set(reasons)),dependency_refs=sorted(dependencies),influence_refs=declaration['influence_refs'][:]))
    return dict(schema='source-local-dynamic-context/1',declarations=view['declarations'],states=view['states'],contexts=contexts)


def options(tier1,target_ref,prepared=None):
    view=inventory(tier1)if prepared is None else prepared
    target=next((r for r in view['declarations']if r['fact_ref']==target_ref),None)
    if target is None:raise ValueError('Original dynamic declaration required')
    context=next(r for r in view['contexts']if r['fact_ref']==target_ref)
    donors=[];excluded=[]
    if context['context_key']is not None:
        dependencies=set(context['dependency_refs'])
        for row in view['contexts']:
            if row['context_key']!=context['context_key']:continue
            if row['fact_ref']==target_ref:
                excluded.append(dict(fact_ref=row['fact_ref'],reason='SELF_DECLARATION'));continue
            shared=sorted(dependencies.intersection(row['dependency_refs']))
            if shared:
                excluded.append(dict(fact_ref=row['fact_ref'],reason='REUSED_TARGET_DEPENDENCY',shared_refs=shared));continue
            donors.append(row)
    witness=None
    for i,a in enumerate(donors):
        for b in donors[i+1:]:
            if a['outcome_marking']!=b['outcome_marking']and not set(a['dependency_refs']).intersection(b['dependency_refs']):
                witness=[a['fact_ref'],b['fact_ref']];break
        if witness:break
    levels=defaultdict(list)
    for row in donors:levels[row['outcome_marking']].append(row['fact_ref'])
    observed=[dict(marking=m,donor_refs=sorted(refs),changed=m!=target['marking'])for m,refs in sorted(levels.items())]
    status='NO_SUPPORTED_DYNAMIC_CONTEXT'if context['reasons']else'CONTEXT_SUPPORTED_DYNAMIC_CHOICES'if witness else'NO_INDEPENDENT_CONTEXTUAL_MULTI_CHOICE'
    return dict(target_ref=target_ref,target=deepcopy(target),context=deepcopy(context),observed_options=observed,
        options=deepcopy(observed)if witness else[],witness_pair=witness,excluded=excluded,status=status)


def validate_controls(controls):
    if type(controls)is not dict or controls.get('context_policy')!=POLICY:raise ValueError('Explicit dynamic transition controls required')
    dynamics.validate_controls(dict(controls,context_policy=dynamics.POLICY))


def sample(evidence,controls):
    validate_controls(controls)
    return dynamics.sample(evidence,dict(controls,context_policy=dynamics.POLICY))


def intervene(upper,controls):
    validate_controls(controls)
    from connected_tier2 import realize
    if controls['dynamics']==0:return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False)
    before=realize(upper);evidence=options(before,controls['target_ref']);chosen,decision=sample(evidence,controls)
    decision['evidence']=evidence
    if chosen is None:return deepcopy(upper),decision
    edited=dynamics.apply(upper,controls['target_ref'],chosen['marking'])
    decision['influence_check']=dynamics.verify_effect(before,realize(edited),evidence['target'],chosen['marking'])
    return edited,decision
