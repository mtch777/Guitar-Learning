"""Observed contextual voicing/register choices; no new pitch-generation rules.

Existing anchor/interval owners and explicitly released string choices change.
Frets follow the same physical equation. Catalogs are source-linked evidence.
"""
from collections import defaultdict,Counter
from copy import deepcopy
from fractions import Fraction as F
import json
import random


def token(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def notation(documents,event):
    part=documents[f"track-{event['part_id']}.json"]
    beat=part['measures'][event['bar']-1]['voices'][event['voice']]['beats'][event['beat']]
    return part,beat,beat['notes'][event['note']]


def effect_reasons(beat,note):
    # This finite execution contract is deliberately narrower than identification.
    # Unknown nonzero declarations never silently become a playable plain chord.
    from contextual_note_roles import source_refusals
    fake=dict(part_id=0,bar=1,voice=0,beat=0,note=0)
    reasons=source_refusals({'track-0.json':dict(measures=[dict(voices=[dict(beats=[dict(beat,notes=[note])])])])},{'note':fake},['note'])
    for field in ('hp','tieOrigin','tieDestination','rest','fingerVibrato'):
        if field in note and note[field] is not False and note[field] is not None:reasons.append('NOTE_DEPENDENCY:'+field)
    for field in ('letRing','arpeggio','brushStroke','downArpeggio'):
        if field in beat and beat[field] is not False and beat[field] is not None and not (field=='downArpeggio' and beat[field]==0):reasons.append('BEAT_DEPENDENCY:'+field)
    return reasons


def tie_relationships(context):
    """Accepted written continuity, including outgoing endpoints outside overlap."""
    from musical_tier2 import analyze
    graph=analyze(context)['written_ties']
    return {k:graph[k] for k in ('links','unresolved')}


def inventory(tier1,policy='exact_context'):
    """Reads complete preceding facts ONLY, preserving all refusal outcomes."""
    if policy=='source_gesture_context':
        from voicing_gestures import catalog
        return catalog(tier1)
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    from musical_tier2 import geometry_relation
    if policy in ('source_lane_context','source_joint_lane_context'):
        from voicing_context_relations import catalog as context_catalog
        return context_catalog(inventory(tier1,'transposed_voicing_family'),tier1,joint=policy=='source_joint_lane_context')
    if policy=='transposed_voicing_family':
        from family_policy import catalog as family_catalog
        return family_catalog(inventory(tier1,'joint_source_fingering'),project_documents(tier1))
    documents=project_documents(tier1);lower=extract_documents(documents);events=lower['events']
    ties=tie_relationships(lower)
    dependencies=None
    if policy in ('incident_dependencies','joint_source_fingering'):
        from execution_dependencies import build
        dependencies=build(tier1)
    incident={ref for edge in ties['links'] for ref in (edge['origin'],edge['destination'])}
    frames=geometry_relation(source=lower['measure_geometry'])['parameters']['frames']
    index={e['id']:e for e in events};groups=defaultdict(list);by_part=defaultdict(list);pitched=[];fret_ranges=defaultdict(list);span_ranges=defaultdict(list);expression={}
    for event in events:
        groups[event['part_id'],event['onset_q']].append(event)
        part,beat,note=notation(documents,event)
        if part.get('instrumentId')==1024:continue
        pitched.append((event,F(event['onset_q']),F(event['onset_q'])+F(event['duration_q'])))
        expression[event['id']]=effect_reasons(beat,note)
        if type(note.get('fret'))in (int,float) and note['fret']>=0:fret_ranges[event['part_id']].append(note['fret'])
    pitched.sort(key=lambda row:row[1])
    for (part,onset),members in groups.items():by_part[part].append((F(onset),members))
    for part in by_part:by_part[part].sort(key=lambda x:(x[0],x[1][0]['id']))
    neighbors={}
    def pcs(members):return sorted((int(F(e['pitch'])%12) if e['pitch'] is not None and F(e['pitch']).denominator==1 else None for e in members),key=lambda p:-1 if p is None else p)
    for part,rows in by_part.items():
        for i,(_,members) in enumerate(rows):neighbors[part,members[0]['onset_q']]=[pcs(rows[i-1][1]) if i else None,pcs(rows[i+1][1]) if i+1<len(rows) else None]
    result=[]
    for (part_id,onset),members in sorted(groups.items(),key=lambda row:(F(row[0][1]),row[0][0],row[1][0]['id'])):
        members=sorted(members,key=lambda e:(e['voice'],e['beat'],e['note']));part=documents[f'track-{part_id}.json'];reasons=[]
        if type(part.get('instrumentId'))is not int or not 24<=part['instrumentId']<=39:reasons.append('NOT_GUITAR_OR_BASS_PROGRAM')
        if len(members)<2:reasons.append('FEWER_THAN_TWO_NOTES')
        if len({e['voice'] for e in members})!=1:reasons.append('MULTIPLE_VOICES')
        if len({e['duration_q'] for e in members})!=1 or any(F(e['duration_q'])<=0 for e in members):reasons.append('NONUNIFORM_OR_ZERO_DURATION')
        if any(e['pitch'] is None or F(e['pitch']).denominator!=1 for e in members):reasons.append('UNKNOWN_OR_NONINTEGER_PITCH')
        bars={e['bar'] for e in members}
        if len(bars)!=1:reasons.append('CROSS_BAR_COATTACK')
        if any(w['bar'] in bars for k in ('layout_warnings','timing_warnings') for w in lower['source_coverage'][k]):reasons.append('SOURCE_TIMING_UNCERTAIN')
        strings=[];signatures=[]
        for event in members:
            _,beat,note=notation(documents,event);reasons+=effect_reasons(beat,note);strings.append(note.get('string'))
            signatures.append(dict(voice=event['voice'],note_index=event['note'],note={k:v for k,v in note.items() if k!='fret'},beat={k:v for k,v in beat.items() if k!='notes'}))
        if any(type(s)is not int or s<0 for s in strings) or len(set(strings))!=len(strings):reasons.append('AMBIGUOUS_FIXED_STRINGS')
        row=dict(id=members[0]['id'],part_id=part_id,bar=members[0]['bar'],onset_q=onset,member_refs=[e['id'] for e in members],refusal_reasons=sorted(set(reasons)))
        if reasons:result.append(row);continue
        # Pitch-class/rank correspondence is musical, not the donor's string or
        # serialization slot. Strings lock unless the physical control releases
        # a complete observed assignment; occurrence IDs always lock.
        members=sorted(members,key=lambda e:(F(e['pitch'])%12,F(e['pitch']),e['voice'],e['note']))
        row['member_refs']=[e['id'] for e in members]
        signatures=[];strings=[];unit_frets=[]
        for event in members:
            _,beat,note=notation(documents,event);strings.append(note['string']);unit_frets.append(note['fret'])
            signatures.append(dict(voice=event['voice'],note={k:v for k,v in note.items() if k not in ('fret','string')},beat={k:v for k,v in beat.items() if k!='notes'}))
        fretted=[f for f in unit_frets if f>0]
        span_ranges[part_id].append(max(fretted)-min(fretted) if fretted else 0)
        start=F(onset);end=start+F(members[0]['duration_q']);selected=set(row['member_refs']);overlaps=[];uncertainty=[];uncertainty_context=[]
        for other,a,b in pitched:
            if a>=end:break
            if other['id'] in selected:continue
            if b<=start:continue
            unknown=other['pitch'] is None or F(other['pitch']).denominator!=1
            if unknown or expression[other['id']]:
                if policy not in ('incident_dependencies','joint_source_fingering') or other['part_id']==part_id:reasons.append('UNRESOLVED_OVERLAP_EXECUTION')
                else:
                    descriptor=dict(written_pitch_status='unknown_or_noninteger' if unknown else 'known_base_only',execution_reasons=sorted(set(expression[other['id']])),claim='Nominal source overlap; sounding pitch/end unknown')
                    uncertainty.append(dict(occurrence_ref=other['id'],**descriptor))
                    uncertainty_context.append([other['part_id'],other['voice'],str(max(a,start)-start),str(min(b,end)-start),descriptor])
            overlaps.append([other['part_id'],other['voice'],str(max(a,start)-start),str(min(b,end)-start),None if unknown else str(F(other['pitch'])%12)])
        frame=frames[members[0]['bar']-1];pitches=[F(e['pitch']) for e in members];anchor=min(pitches)
        base=dict(part_id=part_id,instrument=part['instrumentId'],member_pitch_classes=[str(p%12) for p in pitches],
                  member_notation=signatures,meter=frame['meter'],metrical_offset_q=str(start-F(frame['start_q'])),overlaps=sorted(overlaps,key=token))
        row.update(refusal_reasons=sorted(set(reasons)),context_key=token(base),full_context_key=token([base,neighbors[part_id,onset]]),
                   realization=dict(anchor=str(anchor),intervals=[str(p-anchor) for p in pitches]),duration_q=members[0]['duration_q'])
        row['fixed_output_strings']=strings
        if policy=='joint_source_fingering':
            row['declared_frets']=part.get('frets')
            row['occupied_strings']=sorted({notation(documents,other)[2]['string'] for other,a,b in pitched
                if other['part_id']==part_id and other['id'] not in selected and a<end and b>start
                and type(notation(documents,other)[2].get('string')) is int})
        row['locked_tie_members']=[ref for ref in row['member_refs'] if ref in incident]
        row['fixed_string_bases']=[str(F(str(part['tuning'][s]))+F(str(part.get('capo') or 0))) for s in strings]
        row['pooled_context_key']=token({k:base[k] for k in ('part_id','instrument','member_pitch_classes')}|dict(duration_q=row['duration_q']))
        # Musical conditioning is distinct from immutable target notation and
        # execution refusals. Do not condition on graphic beam/note-array slots.
        context={k:base[k] for k in ('part_id','instrument','member_pitch_classes','meter','metrical_offset_q','overlaps')}
        context['duration_q']=row['duration_q']
        row['musical_context_key']=token(context)
        row['musical_full_context_key']=token([context,neighbors[part_id,onset]])
        row['source_geometry']=dict(instrument=part['instrumentId'],tuning=part['tuning'],capo=part.get('capo') or 0,
            members=sorted([[str(F(e['pitch'])),s,str(F(str(f)))] for e,s,f in zip(members,strings,unit_frets)],key=token))
        if dependencies is not None:
            row['locked_execution_members']=[ref for ref in row['member_refs'] if ref in dependencies['pinned_members']]
            row['context_uncertainty']=sorted(uncertainty,key=lambda r:r['occurrence_ref'])
            context['execution_uncertainty']=sorted(uncertainty_context,key=token)
            row['dependency_context_key']=token(context)
            row['dependency_full_context_key']=token([context,neighbors[part_id,onset]])
        result.append(row)
    envelopes={str(part):dict(min_fret=min(values),max_fret=max(values),max_simultaneous_span=max(span_ranges[part],default=0),
                            declared_frets=documents[f'track-{part}.json'].get('frets')) for part,values in fret_ranges.items()}
    return dict(units=result,source_occurrences=len(events),execution_dependencies=dependencies,written_tie_relationships=ties,physical_envelopes=envelopes,refusal_counts=dict(Counter(r for row in result for r in row['refusal_reasons'])),
                scope='Observed nominal written voicings with fixed member/string PCs; no inferred key, performed harmony or artist intent')


def physical_choice(target,realization,envelope,declared_only=False):
    pitches=[F(realization['anchor'])+F(i) for i in realization['intervals']]
    frets=[p-F(b) for p,b in zip(pitches,target['fixed_string_bases'])]
    upper=envelope['declared_frets'] if declared_only else envelope['max_fret'];lower=0 if declared_only else envelope['min_fret']
    if type(upper)is not int or upper<=0:return False
    if len(frets)!=len(target['member_refs']) or any(f.denominator!=1 or f<lower or f>upper for f in frets):return False
    if declared_only:return True
    fingered=[f for f in frets if f>0]
    return not fingered or max(fingered)-min(fingered)<=envelope['max_simultaneous_span']


POLICIES=('exact_context','pooled_source','pooled_declared_geometry','source_witnessed_fixed_strings','incident_dependencies','joint_source_fingering','transposed_voicing_family','source_lane_context','source_joint_lane_context','source_gesture_context')


def witnessed_geometry(target,donor,realization):
    """Joint simultaneous shape witness, not independent note/fret bounds."""
    geometry=donor.get('source_geometry');original=target.get('source_geometry')
    if geometry is None or original is None:return False
    pitches=[F(realization['anchor'])+F(i) for i in realization['intervals']]
    if len(pitches)!=len(target['member_refs']):return False
    proposed=dict(instrument=original['instrument'],tuning=original['tuning'],capo=original['capo'],
        members=sorted([[str(p),s,str(p-F(b))] for p,s,b in zip(pitches,target['fixed_output_strings'],target['fixed_string_bases'])],key=token))
    return proposed==geometry


def empirical_options(catalog,target_id,policy='exact_context'):
    if policy not in POLICIES:raise ValueError('Declared context policy required')
    if policy=='source_gesture_context':
        from voicing_gestures import options
        return options(catalog,target_id)
    if policy in ('source_lane_context','source_joint_lane_context'):
        from voicing_context_relations import options
        return options(catalog,target_id)
    if policy=='transposed_voicing_family':
        from family_policy import options
        return options(catalog,target_id)
    rows=catalog['units'];target=next(r for r in rows if r['id']==target_id)
    if target['refusal_reasons']:return dict(status='REFUSED_TARGET',reasons=target['refusal_reasons'],options=[])
    levels=[];rejected=[]
    witnessed=policy in ('source_witnessed_fixed_strings','incident_dependencies','joint_source_fingering')
    fields=('dependency_full_context_key','dependency_context_key') if policy in ('incident_dependencies','joint_source_fingering') else ('musical_full_context_key','musical_context_key') if witnessed else ('full_context_key','context_key') if policy=='exact_context' else ('pooled_context_key',)
    for field in fields:
        donors=[r for r in rows if r['id']!=target_id and not r['refusal_reasons'] and r[field]==target[field]]
        choices={}
        for donor in donors:
            if witnessed and any(
                ref in target['locked_tie_members'] and F(target['realization']['anchor'])+F(old)!=F(donor['realization']['anchor'])+F(new)
                for ref,old,new in zip(target['member_refs'],target['realization']['intervals'],donor['realization']['intervals'])):
                rejected.append(dict(level=field,donor_ref=donor['id'],reason='LOCKED_WRITTEN_TIE_ENDPOINT',realization=donor['realization']));continue
            if policy in ('incident_dependencies','joint_source_fingering') and any(
                ref in target['locked_execution_members'] and F(target['realization']['anchor'])+F(old)!=F(donor['realization']['anchor'])+F(new)
                for ref,old,new in zip(target['member_refs'],target['realization']['intervals'],donor['realization']['intervals'])):
                rejected.append(dict(level=field,donor_ref=donor['id'],reason='LOCKED_EXECUTION_DEPENDENCY',realization=donor['realization']));continue
            if witnessed and policy!='joint_source_fingering' and not witnessed_geometry(target,donor,donor['realization']):
                rejected.append(dict(level=field,donor_ref=donor['id'],reason='NO_JOINT_FIXED_STRING_WITNESS',realization=donor['realization']));continue
            realization=deepcopy(donor['realization'])
            if policy=='joint_source_fingering':
                if any(donor['source_geometry'][k]!=target['source_geometry'][k] for k in ('instrument','tuning','capo')):continue
                realization['strings']=donor['fixed_output_strings']
                limit=donor['declared_frets']
                if any(F(member[2])<0 or F(member[2]).denominator!=1 or
                       type(limit)is int and limit>0 and F(member[2])>limit for member in donor['source_geometry']['members']):
                    rejected.append(dict(level=field,donor_ref=donor['id'],reason='INVALID_OBSERVED_FRET',realization=realization));continue
                if any(new!=old and new in target['occupied_strings'] for old,new in zip(target['fixed_output_strings'],realization['strings'])):
                    rejected.append(dict(level=field,donor_ref=donor['id'],reason='OVERLAPPING_STRING_OCCUPIED',realization=realization));continue
                pinned=set(target['locked_tie_members'])|set(target['locked_execution_members'])
                if any(ref in pinned and old!=new for ref,old,new in zip(target['member_refs'],target['fixed_output_strings'],realization['strings'])):
                    rejected.append(dict(level=field,donor_ref=donor['id'],reason='LOCKED_EXECUTION_STRING',realization=realization));continue
            key=token(realization);choices.setdefault(key,dict(realization=realization,donor_refs=[]))['donor_refs'].append(donor['id'])
        all_options=[choices[k] for k in sorted(choices)]
        options=all_options if policy=='exact_context' or witnessed else [o for o in all_options if physical_choice(target,o['realization'],catalog['physical_envelopes'][str(target['part_id'])],policy=='pooled_declared_geometry')]
        original=dict(target['realization'],strings=target['fixed_output_strings']) if policy=='joint_source_fingering' else target['realization']
        alternative=any(o['realization']!=original for o in options)
        levels.append(dict(level=field,donor_units=len(donors),distinct_realizations=len(all_options),physically_feasible_realizations=len(options),has_alternative=alternative))
        if alternative:return dict(status='SUPPORTED_EMPIRICAL_ALTERNATIVES',target_ref=target_id,context_level=field,levels=levels,options=options,rejected=rejected)
    if options:return dict(status='OBSERVED_SINGLE_REALIZATION',target_ref=target_id,context_level=field,levels=levels,options=options,rejected=rejected)
    return dict(status='NO_ELIGIBLE_ALTERNATIVE',target_ref=target_id,levels=levels,options=[],rejected=rejected)


def select_target(catalog,policy='exact_context'):
    checked=[]
    for row in catalog['units']:
        if row['refusal_reasons']:continue
        option=empirical_options(catalog,row['id'],policy);checked.append(dict(target_ref=row['id'],status=option['status'],levels=option['levels']))
        if option['status']=='SUPPORTED_EMPIRICAL_ALTERNATIVES':return dict(target_ref=row['id'],checked=checked,evidence=option)
    return dict(target_ref=None,checked=checked,status='NO_ELIGIBLE_ALTERNATIVE')


CONTROL_FIELDS={'voicing','register','target_ref','seed'}


def validate_controls(controls):
    if type(controls)is not dict or set(controls) not in (CONTROL_FIELDS,CONTROL_FIELDS|{'context_policy'},CONTROL_FIELDS|{'context_policy','physical'}):raise ValueError('Explicit voicing/register scope, target and seed required')
    if 'physical' in controls and (controls.get('context_policy') not in ('joint_source_fingering','transposed_voicing_family','source_lane_context','source_joint_lane_context','source_gesture_context') or type(controls['physical'])is not int or not 0<=controls['physical']<=100):raise ValueError('Explicit bounded joint physical control required')
    if controls.get('context_policy') in ('joint_source_fingering','transposed_voicing_family','source_lane_context','source_joint_lane_context','source_gesture_context') and 'physical' not in controls:raise ValueError('Joint policy requires physical control')
    if controls.get('context_policy') in ('transposed_voicing_family','source_lane_context','source_joint_lane_context','source_gesture_context') and controls.get('register')!=0:raise ValueError('Family experiment locks bass register')
    if controls.get('context_policy')=='source_lane_context'and controls.get('physical')!=0:raise ValueError('Incident lane experiment locks strings')
    if controls.get('context_policy','exact_context') not in POLICIES:raise ValueError('Declared context policy required')
    if any(type(controls[k])is not int or not 0<=controls[k]<=100 for k in ('voicing','register')):raise ValueError('Integer reference-release controls0..100 required')
    if type(controls['seed'])is not int or type(controls['target_ref'])not in (str,type(None)):raise ValueError('Typed target/seed required')
    if (controls['voicing'] or controls['register'] or controls.get('physical',0)) and not controls['target_ref']:raise ValueError('Nonzero edit requires an explicit source unit')


def sample_choice(catalog,controls):
    """Same finite empirical choice, separated for reproducible control auditing."""
    validate_controls(controls)
    if controls.get('context_policy')=='source_gesture_context':
        from voicing_gestures import sample_choice as gesture_choice
        return gesture_choice(catalog,controls)
    if not controls['voicing'] and not controls['register'] and not controls.get('physical',0):
        return None,dict(status='EXACT_ZERO_LOCK',released=dict(voicing=False,register=False,**({'physical':False} if 'physical' in controls else {})),changed=False)
    target=next((r for r in catalog['units'] if r['id']==controls['target_ref']),None)
    if target is None:raise ValueError('Target is not a source unit')
    evidence=empirical_options(catalog,target['id'],controls.get('context_policy','exact_context'))
    if evidence['status'] not in ('SUPPORTED_EMPIRICAL_ALTERNATIVES','OBSERVED_SINGLE_REALIZATION'):
        return None,dict(status=evidence['status'],evidence=evidence,changed=False)
    rng=random.Random(controls['seed']);released={k:rng.random()<controls[k]/100 for k in ('voicing','register')}
    if 'physical' in controls:released['physical']=rng.random()<controls['physical']/100
    original=target['realization']
    if controls.get('context_policy') in ('joint_source_fingering','transposed_voicing_family','source_lane_context','source_joint_lane_context'):original=dict(original,strings=target['fixed_output_strings'])
    options=[o for o in evidence['options'] if
        (released['voicing'] or o['realization']['intervals']==original['intervals']) and
        (released['register'] or o['realization']['anchor']==original['anchor']) and
        ('physical' not in released or released['physical'] or o['realization']['strings']==original['strings'])]
    if not options:return None,dict(status='NO_OBSERVED_CHOICE_SATISFIES_LOCKS',released=released,evidence=evidence,changed=False)
    population=[o for o in options for _ in o['donor_refs']];chosen=deepcopy(rng.choice(population));changed=original!=chosen['realization']
    return chosen['realization'],dict(status='SOURCE_SUPPORTED_REALIZATION' if changed else 'OBSERVED_COINCIDENCE',released=released,changed=changed,
        target_ref=target['id'],member_refs=target['member_refs'],original=original,chosen=chosen,
        context_level=evidence['context_level'],levels=evidence['levels'],eligible_donor_units=len(population),
        semantics='Leave-target-out observed choices; original register is not preferred; no forced difference or inferred artist style')


def apply_family_choice(upper,target,realization):
    """Shared owned-choice operation for sampling AND exhaustive QA realization."""
    return apply_family_choices(upper,[(target,realization)])


def apply_family_choices(upper,choices_to_apply):
    """Atomic multi-group operation using the SAME spacing and physical owners."""
    from voicing_families import choose_many
    from connected_tier2 import physical_relation
    edited=deepcopy(upper)
    edited['musical_relationships']=choose_many(upper['musical_relationships'],[(t['member_refs'],v['intervals']) for t,v in choices_to_apply])
    choices={c['fact_ref']:c for c in edited['owned_parameters']['source_choices']}
    positions={p['occurrence_ref']:p for p in edited['owned_parameters']['physical_positions']}
    for target,realization in choices_to_apply:
        if len(realization['strings'])!=len(target['member_refs']):raise ValueError('Complete physical assignment required')
        for i,(ref,string)in enumerate(zip(target['member_refs'],realization['strings'])):
            position=positions[ref]
            if 'tuning_array_ref'not in position:raise ValueError('Joint change requires dynamic physical ownership')
            choices[position['string_ref']]['parameter']['normalized']=str(string)
            pitch=F(realization['anchor'])+F(realization['intervals'][i]);geometry=target['source_geometry']
            if position['negative_zero']and F(physical_relation(pitch=pitch,tuning=geometry['tuning'][string],capo=geometry['capo']))!=0:position['negative_zero']=False
    return edited


def intervene(upper,controls):
    """Propose only observed owned parameters, then solve the existing relations."""
    validate_controls(controls)
    if upper['musical_relationships'].get('schema')=='source-declared-chord-degrees/1' and any(controls.get(k,0) for k in ('voicing','register','physical')):
        raise ValueError('Declared-chord ownership has no accepted nonzero control policy yet')
    if controls.get('context_policy')=='source_gesture_context':
        from voicing_gestures import intervene as gesture_intervention
        return gesture_intervention(upper,controls)
    from connected_tier2 import realize
    import musical_tier2 as music
    edited=deepcopy(upper)
    # Even all-zero inputs must satisfy the actual shared inverse, not bypass it.
    before=realize(upper)
    if not controls['voicing'] and not controls['register'] and not controls.get('physical',0):
        return edited,dict(status='EXACT_ZERO_LOCK',released=dict(voicing=False,register=False,**({'physical':False} if 'physical' in controls else {})),changed=False)
    family_mode=controls.get('context_policy') in ('transposed_voicing_family','source_lane_context','source_joint_lane_context')
    if (upper['musical_relationships'].get('schema')=='source-voicing-families/1')!=family_mode:
        raise ValueError('Nonzero policy must match musical ownership representation')
    catalog=inventory(before,controls.get('context_policy','exact_context'));target=next((r for r in catalog['units'] if r['id']==controls['target_ref']),None)
    if target is None:raise ValueError('Target is not a source unit')
    realization,decision=sample_choice(catalog,controls)
    if realization is None:return edited,decision
    if family_mode:
        from voicing_families import realize as family_core
        edited=apply_family_choice(upper,target,realization)
        core=family_core(edited['musical_relationships'])
    else:core=edited['musical_relationships']
    groups=core['coattacks'];refs=set(target['member_refs'])
    group=next(g for g in groups if {m['id'] for m in g['members']}==refs)
    if not family_mode:group['bass_register_anchor']=realization['anchor']
    mapping=dict(zip(target['member_refs'],realization['intervals']))
    if not family_mode:
        for member in group['members']:member['voicing_interval']=mapping[member['id']]
    # Existing musical equations realize pitches; the same analysis recomputes
    # derived contexts. No lower facts or raw frets are patched to force an edit.
    if 'strings' in realization and not family_mode:
        choices={c['fact_ref']:c for c in edited['owned_parameters']['source_choices']}
        positions={p['occurrence_ref']:p for p in edited['owned_parameters']['physical_positions']}
        for ref,string in zip(target['member_refs'],realization['strings']):
            position=positions[ref]
            if 'tuning_array_ref' not in position:raise ValueError('Joint change requires dynamic physical ownership')
            choices[position['string_ref']]['parameter']['normalized']=str(string)
            if family_mode and position['negative_zero']:
                from connected_tier2 import physical_relation
                index=target['member_refs'].index(ref)
                pitch=F(realization['anchor'])+F(realization['intervals'][index])
                geometry=target['source_geometry']
                if F(physical_relation(pitch=pitch,tuning=geometry['tuning'][string],capo=geometry['capo']))!=0:
                    position['negative_zero']=False
    if not family_mode:
        normalized=music.realize(core)
        edited['musical_relationships']=music.strip_lower(music.analyze(normalized))
    if 'contextual_constraints' in edited:
        requests=[row['request'] for row in edited['contextual_constraints']['results']]
        edited.pop('contextual_constraints')
        from contextual_note_roles import evaluate
        edited['contextual_constraints']=evaluate(realize(edited),requests)
    after=realize(edited)
    from source_fact_tier1 import project_documents
    documents=project_documents(after)
    from source_tie_tier1 import extract_documents as tie_context
    if tie_relationships(tie_context(documents))!=catalog['written_tie_relationships']:
        raise ValueError('Locked written tie relationship changed, despite retained source flags')
    if controls.get('context_policy') in ('incident_dependencies','joint_source_fingering','transposed_voicing_family','source_lane_context','source_joint_lane_context'):
        from execution_dependencies import build
        if build(after)['signature']!=catalog['execution_dependencies']['signature']:
            raise ValueError('Locked execution dependency semantics changed')
    # Observed joint geometry is required in addition to pitch-class lock.
    from run_reversible_tier_qa import extract_documents
    events={e['id']:e for e in extract_documents(documents)['events']}
    frets=[]
    for ref in target['member_refs']:
        part,beat,note=notation(documents,events[ref]);fret=note['fret']
        if type(fret)not in (int,float) or F(str(fret)).denominator!=1 or fret<0:raise ValueError('Observed proposal conflicts with fixed-string geometry')
        frets.append(fret)
    envelope=catalog['physical_envelopes'][str(target['part_id'])]
    fingered=[f for f in frets if f>0]
    if family_mode:
        from family_policy import admissible
        donors={r['id']:r for r in catalog['units']}
        for ref in decision['chosen']['donor_refs']:
            witness,reason=admissible(target,donors[ref])
            if reason or witness!=realization:raise ValueError('Translated whole-source shape witness lost')
        if controls.get('context_policy') in ('source_lane_context','source_joint_lane_context'):
            from voicing_context_relations import check_paths,validate_actual
            relation=check_paths(catalog['lane_relationships'],target,realization,allow_string_changes=controls.get('context_policy')=='source_joint_lane_context')
            if relation['status']=='REFUSED':raise ValueError('Observed lane relationship lost')
            validate_actual(before,after,target,realization)
    elif controls.get('context_policy')=='joint_source_fingering':
        donors={r['id']:r for r in catalog['units']}
        for ref in decision['chosen']['donor_refs']:
            donor=donors[ref]
            for member,string in zip(target['member_refs'],realization['strings']):
                _,_,note=notation(documents,events[member])
                if note['string']!=string:raise ValueError('Selected physical choice lost')
            if donor['fixed_output_strings']!=realization['strings'] or donor['realization']!={k:v for k,v in realization.items() if k!='strings'}:raise ValueError('Joint source witness lost')
    elif controls.get('context_policy') in ('source_witnessed_fixed_strings','incident_dependencies'):
        donors={r['id']:r for r in catalog['units']}
        if not all(witnessed_geometry(target,donors[ref],decision['chosen']['realization']) for ref in decision['chosen']['donor_refs']):raise ValueError('Joint source geometry witness lost')
    elif controls.get('context_policy')=='pooled_declared_geometry':
        if type(envelope['declared_frets'])is not int or min(frets)<0 or max(frets)>envelope['declared_frets']:raise ValueError('Choice exceeds declared fret geometry')
    elif min(frets)<envelope['min_fret'] or max(frets)>envelope['max_fret'] or fingered and max(fingered)-min(fingered)>envelope['max_simultaneous_span']:raise ValueError('Observed musical choice violates target physical envelope')
    return edited,dict(decision,
        **({'selected_string_frets':frets} if controls.get('context_policy') in ('joint_source_fingering','transposed_voicing_family','source_lane_context','source_joint_lane_context') else {'fixed_string_frets':frets}),fretted_span=max(fingered)-min(fingered) if fingered else 0,physical_envelope=envelope,
        execution_status='HUMAN_EXECUTION_UNVERIFIED')
