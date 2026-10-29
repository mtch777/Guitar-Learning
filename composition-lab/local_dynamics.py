"""Source-supported written dynamics through existing categorical owners.

A beat declaration governs its full inherited region; a note override governs
only that note. This is source-relative expression control, not inferred emotion
or calibrated loudness. The approved state projection is unchanged.
"""
from copy import deepcopy
import math
from source_fact_tier1 import validate,project_documents

POLICY='source_local_dynamic_level'


def source_rules():
    # The isolated bundle registers the exact same approved module by its short
    # name. Normal callers can import its repository package directly.
    try:
        from source_dynamics import dynamic_observations,MARKINGS
    except ModuleNotFoundError as exc:
        if exc.name!='source_dynamics':raise
        from songsterr_automation.songsterr_api.source_dynamics import dynamic_observations,MARKINGS
    return dynamic_observations,MARKINGS


def inventory(tier1):
    validate(tier1)
    dynamic_observations,MARKINGS=source_rules()
    docs=project_documents(tier1);song=docs['metadata.json']['songId']
    declarations=[];states=[]
    for name,part in sorted(docs.items()):
        if not name.startswith('track-'):continue
        pid=part['partId'];beats={};origins={}
        def fact(bar,voice,beat,note=None):
            base=f'{name}#/measures/{bar-1}/voices/{voice}/beats/{beat}'
            return base+(f'/notes/{note}'if note is not None else'')+'/velocity'
        for bar,measure in enumerate(part.get('measures',[]),1):
            for voice,v in enumerate(measure.get('voices',[])):
                for bi,b in enumerate(v.get('beats',[])):
                    beats.setdefault(voice,[]).append((bar,bi,b))
                    for ni,owner in [(None,b)]+list(enumerate(b.get('notes',[]))):
                        if 'velocity'not in owner:continue
                        raw=owner['velocity'];known=type(raw)is str and raw in MARKINGS
                        row=dict(fact_ref=fact(bar,voice,bi,ni),scope='beat'if ni is None else'note',part_id=pid,
                            voice=voice,bar=bar,beat=bi,note=ni,marking=deepcopy(raw),known=known,influence_refs=[],
                            reasons=[]if known else['UNKNOWN_MARKING'])
                        declarations.append(row);origins[row['fact_ref']]=row
        for row in dynamic_observations(part):
            origin=row['marking_origin'];origin_ref=None if origin is None else fact(origin['bar'],origin['voice'],origin['beat'],origin.get('note'))
            ref=f"event:{song}:{row['occurrence']}"
            states.append(dict(occurrence_ref=ref,marking=row['marking'],known=row['known'],provenance=row['provenance'],origin_fact_ref=origin_ref))
            if origin_ref is not None:origins[origin_ref]['influence_refs'].append(ref)
        for row in origins.values():
            row['influence_refs'].sort()
            if not row['influence_refs']:row['reasons'].append('NO_INFLUENCED_NOTES')
            if not row['known'] or row['scope']!='beat':continue
            active=False
            for bar,bi,b in beats[row['voice']]:
                if (bar,bi)==(row['bar'],row['beat']):active=True
                elif active and b.get('velocity')is not None:
                    mark=b['velocity']
                    if type(mark)is str and mark in MARKINGS:break
                    row['reasons'].append('UNKNOWN_BEAT_BOUNDARY')
                if active:
                    for note in b.get('notes',[]):
                        if note.get('rest'):continue
                        mark=note.get('velocity')
                        if mark is not None and (type(mark)is not str or mark not in MARKINGS):row['reasons'].append('UNKNOWN_NOTE_OVERRIDE')
            row['reasons']=sorted(set(row['reasons']))
    for row in declarations:row['reasons']=sorted(set(row['reasons']))
    return dict(schema='source-local-dynamics/1',declarations=sorted(declarations,key=lambda r:r['fact_ref']),states=sorted(states,key=lambda r:r['occurrence_ref']))


def options(tier1,target_ref,prepared=None):
    view=inventory(tier1)if prepared is None else prepared
    target=next((r for r in view['declarations']if r['fact_ref']==target_ref),None)
    if target is None:raise ValueError('Target is not an existing dynamic declaration')
    levels={}
    if not target['reasons']:
        for donor in view['declarations']:
            if donor['fact_ref']==target_ref or donor['reasons']:continue
            if any(donor[k]!=target[k]for k in ('part_id','voice','scope')):continue
            if set(donor['influence_refs'])&set(target['influence_refs']):continue
            levels.setdefault(donor['marking'],[]).append(donor['fact_ref'])
    choices=[dict(marking=level,donor_refs=sorted(refs),changed=level!=target['marking'])for level,refs in sorted(levels.items())]
    return dict(target_ref=target_ref,target=deepcopy(target),options=choices,
        status='SOURCE_SUPPORTED_DYNAMIC_CHOICES'if any(r['changed']for r in choices)else'NO_ADMITTED_DYNAMIC_CHANGE')


def validate_controls(controls):
    if type(controls)is not dict or set(controls)!={'context_policy','dynamics','target_ref','seed'} or controls['context_policy']!=POLICY:
        raise ValueError('Explicit local dynamics controls required; other dimensions locked')
    value=controls['dynamics']
    if type(value)not in (int,float)or not math.isfinite(value)or not 0<=value<=100:raise ValueError('Dynamics release must be 0..100')
    if type(controls['seed'])is not int or type(controls['target_ref'])is not str or not controls['target_ref']:raise ValueError('Typed seed and source declaration required')


def sample(evidence,controls):
    """Reuse the established release probability and source-vote sampler."""
    validate_controls(controls)
    from declared_degree_choices import sample as release
    chosen,decision=release(evidence,dict(voicing=controls['dynamics'],seed=controls['seed']))
    if chosen is not None:decision['status']='SOURCE_SUPPORTED_DYNAMIC_LEVEL'if decision['changed']else'OBSERVED_COINCIDENCE'
    return chosen,decision


def apply(upper,target_ref,marking):
    """Update the sole categorical owner; the existing inverse creates facts."""
    _,MARKINGS=source_rules()
    if type(marking)is not str or marking not in MARKINGS:raise ValueError('Known written dynamic required')
    edited=deepcopy(upper);groups=edited['owned_parameters']['technique_declarations']['groups']
    group=next((g for g in groups if g['source_fact_ref']==target_ref),None)
    if group is None or group['field']!='velocity' or len(group['parameters'])!=1 or len(group['structure'])!=1 or group['structure'][0]['type']!='string':
        raise ValueError('Existing sole dynamic declaration owner required')
    p=group['parameters'][0]
    if p['fact_ref']!=target_ref or p['unit']!='1' or set(p['parameter'])!={'symbol'}:raise ValueError('Unexpected dynamic owner relation')
    p['parameter']['symbol']=marking
    return edited


def verify_effect(before,after,target,marking):
    """Unchanged raw facts AND unchanged effective state outside full influence."""
    old={r['id']:r for r in before['facts']};new={r['id']:r for r in after['facts']}
    if set(old)!=set(new)or before['documents']!=after['documents']or before['scope']!=after['scope']:raise ValueError('Dynamic edit changed source topology')
    for ref,row in old.items():
        wanted=deepcopy(row)
        if ref==target['fact_ref']:wanted['value']=marking
        if wanted!=new[ref]:raise ValueError('Locked source fact changed: '+ref)
    old_states=inventory(before)['states'];new_states=inventory(after)['states'];influence=set(target['influence_refs'])
    expected=[]
    for row in old_states:
        row=deepcopy(row)
        if row['occurrence_ref']in influence:row['marking']=marking;row['known']=True
        expected.append(row)
    if expected!=new_states:raise ValueError('Effective dynamic influence escaped declared scope')
    return dict(status='EXACT_DECLARED_DYNAMIC_INFLUENCE',influenced_occurrences=len(influence),outside_occurrences=len(old_states)-len(influence))


def intervene(upper,controls):
    validate_controls(controls)
    from connected_tier2 import realize
    before=realize(upper)
    if controls['dynamics']==0:return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False)
    evidence=options(before,controls['target_ref']);chosen,decision=sample(evidence,controls)
    decision['evidence']=evidence
    if chosen is None:return deepcopy(upper),decision
    edited=apply(upper,controls['target_ref'],chosen['marking']);after=realize(edited)
    decision['influence_check']=verify_effect(before,after,evidence['target'],chosen['marking'])
    return edited,decision
