"""One complete T1 input; source choices and connected musical relationships.

Registered choices preserve notation/provenance, without claiming musical meaning.
Pitched frets have ONE authority: coattack pitch minus tuning and capo.
"""
from copy import deepcopy
from fractions import Fraction as F
import json
import re
from source_fact_tier1 import validate as validate_source,project_documents
from source_field_registry import REGISTERED_SOURCE_FIELDS,REGISTERED_SOURCE_CONTAINERS
from technique_observation_relations import lift,realize as realize_effects,scalar_relation
import musical_tier2 as music


def address_pattern(row):
    return ('metadata' if row['document']=='metadata.json' else 'track',re.sub(r'/\d+(?=/|$)','/*',row['pointer']))


def registered(row):
    return row['type'] in REGISTERED_SOURCE_FIELDS.get(address_pattern(row),())


def registered_container(row):
    scope,path=address_pattern(row)
    if (scope,path) in REGISTERED_SOURCE_CONTAINERS:
        return row['type'] in REGISTERED_SOURCE_CONTAINERS[scope,path]
    return not path or any(scope==d and p.startswith(path+'/') for d,p in REGISTERED_SOURCE_FIELDS)


def owner_kind(row):
    scope,path=address_pattern(row)
    if scope=='metadata':return 'captured_catalog_declaration'
    if '/chord/' in path:return 'source_chord_annotation'
    if '/duration/' in path or path.endswith(('/dots','/dotted','/tuplet','/type','/graceNote','/beamStart','/beamStop','/tupletStart','/tupletStop')):return 'source_notation_choice'
    if '/notes/' in path:return 'physical_or_note_declaration'
    if path.endswith('/beats/*/slapping'):return 'source_beat_execution_declaration'
    if '/automations/' in path or '/trackAutomations/' in path or '/tempo/' in path:return 'source_clock_or_control'
    if '/measures/' in path:return 'source_structure_declaration'
    return 'instrument_or_track_setting'


def physical_relation(*,pitch=None,fret=None,tuning,capo):
    """ONE relationship: pitch = tuning + capo + fret, solved either way."""
    if (pitch is None)==(fret is None):raise ValueError('Exactly one physical side required')
    base=F(str(tuning))+F(str(capo))
    return str(base+F(str(fret))) if pitch is None else str(F(pitch)-base)


def event_pointer(event):
    return f"track-{event['part_id']}.json#/measures/{event['bar']-1}/voices/{event['voice']}/beats/{event['beat']}/notes/{event['note']}"


def analyze(tier1,*,families=False,declared_chords=False,declared_chord_profile=None,note_accent_slots=False,rhythm_groups=False,rhythm_group_profile='plain_repeat',palm_mute_slots=False,step_tempos=False):
    if type(step_tempos)is not bool:raise ValueError('Explicit global step-tempo ownership mode required')
    if type(rhythm_groups)is not bool:raise ValueError('Explicit rhythm ownership mode required')
    if rhythm_group_profile not in ('plain_repeat','written_time')or (not rhythm_groups and rhythm_group_profile!='plain_repeat'):raise ValueError('Explicit supported rhythm-owner profile required')
    if type(palm_mute_slots)is not bool:raise ValueError('Explicit optional palm-mute ownership mode required')
    if type(note_accent_slots)is not bool:raise ValueError('Explicit optional-accent ownership mode required')
    if type(declared_chords)is not bool or families and declared_chords:raise ValueError('Choose one explicit musical ownership representation')
    if declared_chord_profile is not None and not declared_chords:raise ValueError('Chord profile requires declared chord ownership')
    validate_source(tier1)
    from run_reversible_tier_qa import extract_documents
    from source_tie_tier1 import extract_documents as full_context
    from technique_tier2 import analyze as techniques
    documents=project_documents(tier1)
    normalized=extract_documents(documents)
    core=music.strip_lower(music.analyze(normalized))
    declared_view=None
    if declared_chords:
        from declared_chord_ownership import LABEL,CAPO,lift as degree_lift,inspect as degree_inspect
        from chord_symbol_lexicon import CURRENT_PROFILE
        profile=CURRENT_PROFILE if declared_chord_profile is None else declared_chord_profile
        labels={r['id']:r['value'] for r in tier1['facts'] if LABEL.fullmatch(r['id']) and 'value' in r}
        capos={int(CAPO.fullmatch(r['id'])[1]):r['value'] for r in tier1['facts'] if CAPO.fullmatch(r['id']) and 'value' in r}
        declared_view=degree_inspect(core,labels,capos,profile=profile);core=degree_lift(core,labels,capos,profile=profile)
    if families:
        from voicing_families import lift as family_lift
        core=family_lift(core)
    timing_values={}
    if rhythm_groups:
        from group_rhythm_relations import lift as rhythm_lift,expand as rhythm_expand
        core=rhythm_lift(tier1,core,structural=rhythm_group_profile=='written_time');_,timing_values=rhythm_expand(core)
    tempo_model=None;tempo_values={}
    if step_tempos:
        from step_tempo_relations import lift as tempo_lift,expand as tempo_expand
        tempo_model=tempo_lift(tier1);tempo_values=tempo_expand(tempo_model)
    effect=lift(tier1);slot_model=None;mute_model=None;slot_ids=set()
    if note_accent_slots:
        from optional_accent_slots import lift as lift_slots,realize as realize_slots
        slot_model=lift_slots(tier1);slot_ids={r['id']for r in realize_slots(slot_model)}
    if palm_mute_slots:
        from optional_palm_mute_slots import lift as lift_mutes,realize as realize_mutes
        mute_model=lift_mutes(tier1);slot_ids.update(r['id']for r in realize_mutes(mute_model))
    effect['groups']=[g for g in effect['groups']if g['source_fact_ref']not in slot_ids]
    effect_ids={r['id'] for r in realize_effects(effect)}
    events={event_pointer(e):e for e in normalized['events']}
    source_index={r['id']:r for r in tier1['facts']}
    skeleton=[];choices=[];positions=[];coverage=[];unsupported=deepcopy(effect['unsupported'])
    for row in tier1['facts']:
        if row['id']in slot_ids:continue
        if row['id'] in effect_ids:
            coverage.append(dict(fact_ref=row['id'],owner='technique_declaration'));continue
        skeleton.append({k:deepcopy(v) for k,v in row.items() if k!='value'})
        if 'value' not in row:
            if not registered_container(row):
                unsupported.append(dict(fact_ref=row['id'],reason='UNREGISTERED_SOURCE_CONTAINER'))
            coverage.append(dict(fact_ref=row['id'],owner='source_structure'));continue
        if row['id']in timing_values:
            if row['value']!=timing_values[row['id']]:raise ValueError('Source notation rhythm encoding conflict')
            coverage.append(dict(fact_ref=row['id'],owner='source_group_rhythm'));continue
        if row['id']in tempo_values:
            if type(row['value'])is not int or row['value']!=tempo_values[row['id']]:raise ValueError('Source global tempo equation conflict')
            coverage.append(dict(fact_ref=row['id'],owner='global_step_tempo'));continue
        event=events.get(row['parent']) if row['slot']=='fret' else None
        if event is not None and event['pitch'] is not None and row['type'] in ('integer','float'):
            part=documents[row['document']];note_ref=row['parent']
            string_ref=note_ref+'/string';string=source_index[string_ref]['value']
            capo_ref=row['document']+'#/capo'
            if physical_relation(fret=row['value'],tuning=part['tuning'][string],capo=part.get('capo') or 0)!=event['pitch']:raise ValueError('Source pitch physical equation differs')
            positions.append(dict(fact_ref=row['id'],occurrence_ref=event['id'],string_ref=string_ref,tuning_array_ref=row['document']+'#/tuning',capo_ref=capo_ref if 'capo' in part else None,negative_zero=row['type']=='float' and str(row['value'])=='-0.0'))
            coverage.append(dict(fact_ref=row['id'],owner='written_pitch_relationship'));continue
        if not registered(row):
            unsupported.append(dict(fact_ref=row['id'],reason='UNREGISTERED_SOURCE_FIELD_OR_TYPE'));coverage.append(dict(fact_ref=row['id'],owner='unsupported'));continue
        owner=owner_kind(row)
        choices.append(dict(fact_ref=row['id'],owner=owner,parameter=scalar_relation(row['type'],source=row['value'])))
        coverage.append(dict(fact_ref=row['id'],owner=owner))
    tech=techniques(tier1);tech.pop('input');tech.pop('technique_observations')
    # These are derived views. Neither is an inverse input or pitch authority.
    from execution_dependencies import build as execution_dependencies
    derived=dict(harmonic_context=music.strip_lower(music.analyze(full_context(documents))),techniques=tech,
                 execution_dependencies=execution_dependencies(tier1))
    if declared_chords:derived['declared_chord_ownership']=declared_view
    output=dict(tier=2,schema='connected-source-musical-relations/1',input=deepcopy(tier1),
                source_structure=dict(documents=deepcopy(tier1['documents']),facts=skeleton,source_scope=tier1['scope']),
                owned_parameters=dict(source_choices=choices,physical_positions=positions,technique_declarations=effect),
                musical_relationships=core,derived_views=derived,coverage=coverage,unsupported=unsupported)
    if note_accent_slots:
        output['schema']='connected-source-musical-relations/2'
        output['owned_parameters']['optional_note_accents']=slot_model
        output['coverage']=dict(schema='conditional-source-ownership/1',fixed=coverage,
            rules=[dict(relation=g['id'])for g in slot_model['groups']])
    if palm_mute_slots:
        output['schema']='connected-source-musical-relations/3'
        output['owned_parameters']['optional_beat_palm_mutes']=mute_model
        output['coverage']=dict(schema='conditional-source-ownership/1',fixed=coverage,
            rules=[dict(relation=g['id'])for model in (slot_model,mute_model)if model for g in model['groups']])
    if step_tempos:
        output['schema']='connected-source-musical-relations/4'
        output['owned_parameters']['global_step_tempos']=tempo_model
    if not unsupported:
        restored=realize(strip_lower(output))
        if json.dumps(restored,sort_keys=True)!=json.dumps(tier1,sort_keys=True):raise ValueError('Complete forward/reverse discrepancy')
    return output


def strip_lower(upper):
    result=deepcopy(upper);result.pop('input',None);result.pop('derived_views',None)
    return result


def realize(upper):
    """No source/lower/derived-view access. Unknown owners block reconstruction."""
    fields={'tier','schema','source_structure','owned_parameters','musical_relationships','coverage','unsupported'}
    if set(upper)-{'contextual_constraints','membership_lock'}!=fields or upper['schema']not in ('connected-source-musical-relations/1','connected-source-musical-relations/2','connected-source-musical-relations/3','connected-source-musical-relations/4') or upper['tier']!=2:raise ValueError('Unsupported unified interface or hidden payload')
    if upper['unsupported']:raise ValueError('Unsupported source facts block full inverse')
    structure=upper['source_structure'];parameters=upper['owned_parameters']
    tempo_optional=upper['schema']=='connected-source-musical-relations/4'
    mute_optional=upper['schema']=='connected-source-musical-relations/3'or(tempo_optional and 'optional_beat_palm_mutes'in parameters)
    optional=upper['schema']=='connected-source-musical-relations/2' or((mute_optional or tempo_optional)and 'optional_note_accents'in parameters)
    expected_parameters={'source_choices','physical_positions','technique_declarations'}|({'optional_note_accents'}if optional else set())|({'optional_beat_palm_mutes'}if mute_optional else set())|({'global_step_tempos'}if tempo_optional else set())
    if set(structure)!={'documents','facts','source_scope'} or set(parameters)!=expected_parameters:raise ValueError('Unregistered owner payload')
    facts=deepcopy(structure['facts']);index={r['id']:r for r in facts}
    if len(index)!=len(facts) or any('value' in r for r in facts):raise ValueError('Raw or duplicate skeleton scalar')
    if any(r['type'] in ('object','array') and not registered_container(r) for r in facts):raise ValueError('Unregistered source container')
    assigned={r['id']:'source_structure' for r in facts if r['type'] in ('object','array')}
    if optional:
        from optional_accent_slots import realize as realize_slots
        for row in realize_slots(parameters['optional_note_accents']):
            if row['id']in index:raise ValueError('Overlapping optional-accent/structure ownership')
            index[row['id']]=row;assigned[row['id']]='optional_note_accent'
    if mute_optional:
        from optional_palm_mute_slots import realize as realize_mutes
        for row in realize_mutes(parameters['optional_beat_palm_mutes']):
            if row['id']in index:raise ValueError('Overlapping optional palm-mute ownership')
            index[row['id']]=row;assigned[row['id']]='optional_beat_palm_mute'
    def assign(ident,value,owner):
        if ident not in index or ident in assigned:raise ValueError('Duplicate or absent scalar owner')
        index[ident]['value']=value;assigned[ident]=owner
    if tempo_optional:
        from step_tempo_relations import expand as tempo_expand
        for ident,value in tempo_expand(parameters['global_step_tempos']).items():
            if ident not in index or index[ident]['type']!='integer'or not registered(index[ident]):raise ValueError('Unknown tempo scalar')
            assign(ident,value,'global_step_tempo')
    core=upper['musical_relationships']
    rhythm_model=None
    if core.get('schema')in('source-group-rhythm/1','source-group-rhythm/2'):
        from group_rhythm_relations import expand as rhythm_expand
        rhythm_model=core;core,timing_values=rhythm_expand(core)
        for ident,value in timing_values.items():
            if ident not in index or index[ident]['type']!='integer' or not registered(index[ident]):raise ValueError('Unknown rhythmic notation scalar')
            assign(ident,value,'source_group_rhythm')
    if core.get('schema')=='source-declared-chord-degrees/1':
        from declared_chord_ownership import validate as degree_core,label_values,capo_values
        core=degree_core(core,label_values(parameters['source_choices'],facts),capo_values(parameters['source_choices'],facts))
    if core.get('schema')=='source-voicing-families/1':
        from voicing_families import validate as family_core
        core=family_core(core)
    normalized=music.reconstruct(core,dict(variation=0));events={e['id']:e for e in normalized['events']}
    known_frets={event_pointer(e)+'/fret' for e in normalized['events'] if e['pitch'] is not None}
    for choice in parameters['source_choices']:
        if set(choice)!={'fact_ref','owner','parameter'}:raise ValueError('Unregistered source choice payload')
        row=index[choice['fact_ref']]
        if row['id'] in known_frets:raise ValueError('Known fret must use its musical pitch relationship')
        if not registered(row) or choice['owner']!=owner_kind(row):raise ValueError('Unregistered source choice')
        assign(row['id'],scalar_relation(row['type'],parameter=choice['parameter']),choice['owner'])
    for position in parameters['physical_positions']:
        common={'fact_ref','occurrence_ref','string_ref','capo_ref','negative_zero'}
        if set(position) not in (common|{'tuning_ref'},common|{'tuning_array_ref'}):raise ValueError('Unregistered physical payload')
        row=index[position['fact_ref']];event=events[position['occurrence_ref']]
        note=event_pointer(event)
        if row['id']!=note+'/fret' or position['string_ref']!=note+'/string' or row['type'] not in ('integer','float') or type(position['negative_zero']) is not bool:raise ValueError('Physical occurrence owner conflict')
        string=index[position['string_ref']]['value']
        tuning_array=row['document']+'#/tuning'
        if type(string) is not int or string<0 or tuning_array not in index or index[tuning_array]['type']!='array':raise ValueError('Physical string/tuning conflict')
        tuning_ref=tuning_array+f'/{string}'
        if tuning_ref not in index[tuning_array]['children'] or tuning_ref not in assigned:raise ValueError('Physical string/tuning conflict')
        if 'tuning_array_ref' in position:
            if position['tuning_array_ref']!=tuning_array:raise ValueError('Physical tuning array conflict')
        elif position['tuning_ref']!=tuning_ref:raise ValueError('Physical string/tuning conflict')
        expected_capo=row['document']+'#/capo'
        if position['capo_ref']!=(expected_capo if expected_capo in index else None):raise ValueError('Physical capo presence conflict')
        capo=index[expected_capo]['value'] if expected_capo in index else None
        # Existing source semantics treats absent/null/zero capo as no shift;
        # the declaration choice itself remains distinct and exactly owned.
        value=physical_relation(pitch=event['pitch'],tuning=index[tuning_ref]['value'],capo=capo or 0)
        assign(row['id'],scalar_relation(row['type'],parameter=dict(normalized=value,negative_zero=position['negative_zero'])),'written_pitch_relationship')
    for row in realize_effects(parameters['technique_declarations']):
        if row['id'] in index:raise ValueError('Overlapping technique/structure ownership')
        index[row['id']]=row;assigned[row['id']]='technique_declaration'
    coverage=upper['coverage']
    if optional or mute_optional:
        rules=[];emitted=[]
        if optional:
            from optional_accent_slots import coverage as slot_coverage
            model=parameters['optional_note_accents'];rules.extend(dict(relation=g['id'])for g in model['groups']);emitted.extend(slot_coverage(model))
        if mute_optional:
            from optional_palm_mute_slots import coverage as mute_coverage
            model=parameters['optional_beat_palm_mutes'];rules.extend(dict(relation=g['id'])for g in model['groups']);emitted.extend(mute_coverage(model))
        if type(coverage)is not dict or set(coverage)!={'schema','fixed','rules'}or coverage['schema']!='conditional-source-ownership/1' or type(coverage['fixed'])is not list or coverage['rules']!=rules:raise ValueError('Invalid conditional ownership ledger')
        coverage=coverage['fixed']+emitted
    if type(coverage)is not list or any(type(r)is not dict or set(r)!={'fact_ref','owner'}for r in coverage) or len(coverage)!=len(index) or {r['fact_ref']:r['owner'] for r in coverage}!=assigned:raise ValueError('Incomplete/duplicate ownership ledger')
    # Source order is defined only by ordered skeleton membership, not caches.
    ordered=[];seen=set()
    def visit(ident):
        if ident in seen:raise ValueError('Cyclic source structure')
        seen.add(ident);row=index[ident];ordered.append(row)
        for child in row.get('children',[]):visit(child)
    for document in structure['documents']:visit(document['fact_ref'])
    if seen!=set(index):raise ValueError('Unreachable source owner')
    restored=dict(tier=1,schema='complete-source-facts/1',documents=deepcopy(structure['documents']),facts=ordered,scope=structure['source_scope'])
    validate_source(restored)
    if tempo_optional:
        from step_tempo_relations import validate_source as validate_tempos
        validate_tempos(parameters['global_step_tempos'],restored)
    # SAME pure observation projection in both directions. No source files,
    # expected answers or cached views can repair inconsistent parameters.
    from run_reversible_tier_qa import extract_documents
    observed=extract_documents(project_documents(restored))
    if json.dumps(observed,sort_keys=True)!=json.dumps(normalized,sort_keys=True):raise ValueError('Source choices conflict with pitch/time relationships')
    if rhythm_model is not None:
        from group_rhythm_relations import validate_source_groups
        validate_source_groups(rhythm_model,restored)
    if 'contextual_constraints' in upper:
        from contextual_note_roles import verify
        verify(restored,upper['contextual_constraints'])
    if 'membership_lock' in upper:
        from context_membership import verify
        verify(restored,upper['membership_lock'])
    return restored


def reconstruct(upper,controls):
    if controls=={'variation':0} and type(controls['variation']) in (int,float):
        return realize(upper)
    if controls.get('context_policy')=='source_rhythmic_component_tempo':
        from local_step_tempos import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')=='source_local_palm_mute':
        from local_palm_mutes import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')=='source_complete_group_rhythm':
        from local_group_rhythm import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')=='source_local_melodic_contour':
        from melodic_contour_intervention import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')=='source_local_note_accent':
        from local_accents import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')=='source_local_dynamic_transition':
        from dynamic_context import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')=='source_local_dynamic_level':
        from local_dynamics import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    from voicing_register import intervene
    edited,_=intervene(upper,controls)
    return realize(edited)


def validate(upper):
    lower=realize(strip_lower(upper))
    if 'input' in upper and json.dumps(lower,sort_keys=True)!=json.dumps(upper['input'],sort_keys=True):raise ValueError('Nested T1 conflicts')
    # Recompute all views to reject a second unchecked analysis authority.
    model=upper['musical_relationships'];rhythm=model.get('schema')in('source-group-rhythm/1','source-group-rhythm/2')
    structural=rhythm and model['schema']=='source-group-rhythm/2'
    if rhythm:
        from group_rhythm_relations import expand as rhythm_expand,lift as rhythm_lift
        model,_=rhythm_expand(model)
        if rhythm_lift(lower,model,structural=structural)!=upper['musical_relationships']:raise ValueError('Noncanonical shared rhythm ownership')
    declared=model.get('schema')=='source-declared-chord-degrees/1'
    from chord_symbol_lexicon import LEGACY_PROFILE
    profile=model.get('admission_profile',LEGACY_PROFILE) if declared else None
    computed=analyze(lower,families=model.get('schema')=='source-voicing-families/1',declared_chords=declared,declared_chord_profile=profile,note_accent_slots='optional_note_accents'in upper['owned_parameters'],palm_mute_slots='optional_beat_palm_mutes'in upper['owned_parameters'],step_tempos=upper['schema']=='connected-source-musical-relations/4',rhythm_groups=rhythm,rhythm_group_profile='written_time'if structural else'plain_repeat')
    # Stable occurrence-group IDs may move relative to other parts in time.
    # For rhythm owners exact source comparison + canonical re-lift above checks
    # identity and equations without renumbering unrelated source occurrences.
    if not rhythm and json.dumps(computed['musical_relationships'],sort_keys=True)!=json.dumps(upper['musical_relationships'],sort_keys=True):raise ValueError('Pitch/time authority conflicts with source choices')
    if 'derived_views' in upper and json.dumps(computed['derived_views'],sort_keys=True)!=json.dumps(upper['derived_views'],sort_keys=True):raise ValueError('Stale or altered derived musical view')
    return lower
