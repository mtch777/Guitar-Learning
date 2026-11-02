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
    if path.endswith(('/beats/*/slapping','/beats/*/popping')):return 'source_beat_execution_declaration'
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


def analyze(tier1,*,families=False,declared_chords=False,declared_chord_profile=None,note_accent_slots=False,rhythm_groups=False,rhythm_group_profile='plain_repeat',palm_mute_slots=False,step_tempos=False,dynamic_evidence=False,backing_bindings=None,figure_register_refs=None,expressive_figure_seed_refs=None,figure_register_evidence=False,muted_figure_register_refs=None,figure_register_observation_profile=None,coattack_treatment_bindings=None):
    if type(figure_register_evidence)is not bool or (figure_register_evidence and ((figure_register_refs is None and muted_figure_register_refs is None) or backing_bindings is None or expressive_figure_seed_refs is not None)):
        raise ValueError('Original register observations require one explicit plain pre-owned figure')
    if muted_figure_register_refs is not None and (figure_register_refs is not None or expressive_figure_seed_refs is not None or backing_bindings is None):
        raise ValueError('One explicit muted figure with complete backing bindings required')
    if figure_register_observation_profile is not None and (not figure_register_evidence or muted_figure_register_refs is None):
        raise ValueError('Explicit written-register profile requires opted-in muted figure evidence')
    if figure_register_evidence and muted_figure_register_refs is not None:
        from figure_register_observations import WRITTEN_PROFILE
        if figure_register_observation_profile != WRITTEN_PROFILE:
            raise ValueError('EXPLICIT_PLAIN_WRITTEN_OBSERVATION_PROFILE_REQUIRED')
    if expressive_figure_seed_refs is not None and (figure_register_refs is not None or backing_bindings is None):
        raise ValueError('One explicit expressive figure with complete backing bindings required')
    if type(dynamic_evidence)is not bool:raise ValueError('Explicit original dynamic observation ownership required')
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
    from source_observation_evidence import origin
    source_origin=origin(tier1);dynamic_model=None;dynamic_ids=set()
    if dynamic_evidence:
        from observed_dynamics import lift as lift_dynamics,realize as realize_dynamics
        dynamic_model=lift_dynamics(tier1,source_origin)
        dynamic_ids={r['id'] for r in realize_dynamics(dynamic_model,source_origin)}
    effect=lift(tier1);slot_model=None;mute_model=None;slot_ids=set()
    if note_accent_slots:
        from optional_accent_slots import lift as lift_slots,realize as realize_slots
        slot_model=lift_slots(tier1);slot_ids={r['id']for r in realize_slots(slot_model)}
    if palm_mute_slots:
        from optional_palm_mute_slots import lift as lift_mutes,realize as realize_mutes
        mute_model=lift_mutes(tier1);slot_ids.update(r['id']for r in realize_mutes(mute_model))
    effect['groups']=[g for g in effect['groups']if g['source_fact_ref']not in slot_ids|dynamic_ids]
    effect_ids={r['id'] for r in realize_effects(effect)}
    events={event_pointer(e):e for e in normalized['events']}
    source_index={r['id']:r for r in tier1['facts']}
    skeleton=[];choices=[];positions=[];coverage=[];unsupported=deepcopy(effect['unsupported'])
    for row in tier1['facts']:
        if row['id']in slot_ids:continue
        if row['id']in dynamic_ids:
            coverage.append(dict(fact_ref=row['id'],owner='observed_dynamic_selection'));continue
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
    output=dict(tier=2,schema='connected-source-musical-relations/1',input=deepcopy(tier1),source_origin=source_origin,
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
    if dynamic_evidence:
        output['schema']='connected-source-musical-relations/5'
        output['owned_parameters']['observed_dynamics']=dynamic_model
    if backing_bindings is not None:
        from backing_pitch_ownership import lift as own_intervals
        output['musical_relationships']=own_intervals(output['musical_relationships'],backing_bindings,tier1=tier1,preserve_execution=figure_register_refs is not None or muted_figure_register_refs is not None)
    if figure_register_refs is not None:
        from figure_register_ownership import lift as own_figure_register
        output['musical_relationships']=own_figure_register(output['musical_relationships'],figure_register_refs)
    if expressive_figure_seed_refs is not None:
        from figure_register_ownership import lift_expressive
        output['musical_relationships']=lift_expressive(output['musical_relationships'],tier1=tier1,seed_refs=expressive_figure_seed_refs)
    if muted_figure_register_refs is not None:
        from figure_register_ownership import lift_muted
        output['musical_relationships']=lift_muted(output['musical_relationships'],tier1=tier1,ordered_refs=muted_figure_register_refs)
    if figure_register_evidence:
        from figure_register_observations import SLOT,lift as observe_registers
        output['owned_parameters'][SLOT]=observe_registers(strip_lower(output),profile=figure_register_observation_profile)
    if coattack_treatment_bindings is not None:
        from coattack_treatment_ownership import lift as own_coattack_treatment
        output['musical_relationships']=own_coattack_treatment(
            output['musical_relationships'],tier1,coattack_treatment_bindings,
            source_origin=source_origin)
    if not unsupported:
        restored=realize(strip_lower(output))
        if json.dumps(restored,sort_keys=True)!=json.dumps(tier1,sort_keys=True):raise ValueError('Complete forward/reverse discrepancy')
    return output


def strip_lower(upper):
    result=deepcopy(upper);result.pop('input',None);result.pop('derived_views',None)
    return result


def realize(upper):
    """No source/lower/derived-view access. Unknown owners block reconstruction."""
    if 'melodic_movement' in upper.get('owned_parameters', {}):
        from melodic_movement_ownership import expand, validate_execution
        restored = realize(expand(upper))
        validate_execution(upper, restored)
        return restored
    if 'bend_gesture' in upper.get('owned_parameters',{}):
        from bend_gesture_ownership import expand,validate_execution
        restored=realize(expand(upper));validate_execution(upper,restored)
        if 'stable_pitch_preference' in upper:
            from stable_pitch_policy import stable_spans
            stable_spans(upper,restored)
        return restored
    fields={'tier','schema','source_structure','owned_parameters','musical_relationships','coverage','unsupported'}
    if set(upper)-{'contextual_constraints','membership_lock','source_origin','stable_pitch_preference'}!=fields or upper['schema']not in ('connected-source-musical-relations/1','connected-source-musical-relations/2','connected-source-musical-relations/3','connected-source-musical-relations/4','connected-source-musical-relations/5') or upper['tier']!=2:raise ValueError('Unsupported unified interface or hidden payload')
    if 'stable_pitch_preference' in upper:
        from stable_pitch_policy import validate as validate_stable_preference
        validate_stable_preference(upper)
    if 'source_origin' in upper:
        from source_observation_evidence import validate_origin
        validate_origin(upper['source_origin'])
    if upper['unsupported']:raise ValueError('Unsupported source facts block full inverse')
    structure=upper['source_structure'];parameters=upper['owned_parameters']
    dynamic_optional=upper['schema']=='connected-source-musical-relations/5'
    if dynamic_optional and 'source_origin' not in upper:raise ValueError('Original observation origin missing')
    tempo_optional=upper['schema']=='connected-source-musical-relations/4'or(dynamic_optional and 'global_step_tempos'in parameters)
    mute_optional=upper['schema']=='connected-source-musical-relations/3'or((tempo_optional or dynamic_optional) and 'optional_beat_palm_mutes'in parameters)
    optional=upper['schema']=='connected-source-musical-relations/2' or((mute_optional or tempo_optional or dynamic_optional)and 'optional_note_accents'in parameters)
    expected_parameters={'source_choices','physical_positions','technique_declarations'}|({'optional_note_accents'}if optional else set())|({'optional_beat_palm_mutes'}if mute_optional else set())|({'global_step_tempos'}if tempo_optional else set())|({'observed_dynamics'}if dynamic_optional else set())
    if 'figure_register_observations' in parameters:
        from figure_register_observations import SLOT,validate as validate_register_observations
        validate_register_observations(parameters[SLOT],upper.get('source_origin'))
        expected_parameters.add(SLOT)
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
    upper_motion_model=core if core.get('schema') in ('source-upper-voicing-motion/1','source-upper-voicing-motion/2') else None
    if upper_motion_model is not None:
        from upper_voicing_motion import expand as expand_upper_motion,validate_origin as validate_upper_motion_origin
        validate_upper_motion_origin(upper_motion_model,upper.get('source_origin'))
        core=expand_upper_motion(core)
    treatment_model=core if core.get('schema')=='coattack-treatment-ownership/1' else None
    if treatment_model is not None:
        from coattack_treatment_ownership import expand as expand_treatment,validate_origin as validate_treatment_origin
        validate_treatment_origin(treatment_model,upper.get('source_origin'))
        core=expand_treatment(core)
    figure_model=core if core.get('schema')in('figure-register-ownership/1','figure-register-ownership/2','figure-register-ownership/3') else None
    if figure_model is not None:
        from figure_register_ownership import expand as expand_figure_register
        core=expand_figure_register(core)
    backing_model=None
    if core.get('schema')in('backing-relative-pitches/1','backing-relative-pitches/2','backing-relative-pitches/3','backing-relative-pitches/4'):
        from backing_pitch_ownership import expand as expand_backing
        backing_model=core
        core=expand_backing(core)
    note_rest_model=None
    if core.get('schema')=='source-note-rest-timing/1':
        from note_rest_timing import validate_model as validate_note_rest,expand as expand_note_rest
        note_rest_model=core
        validate_note_rest(core,upper.get('source_origin'))
        core,timing_values=expand_note_rest(core)
        for ident,value in timing_values.items():
            if ident not in index or index[ident]['type']!='integer' or not registered(index[ident]):raise ValueError('Unknown note/rest notation scalar')
            assign(ident,value,'source_note_rest_timing')
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
    if dynamic_optional:
        from observed_dynamics import realize as realize_dynamics
        for row in realize_dynamics(parameters['observed_dynamics'],upper['source_origin']):
            if row['id'] in index:raise ValueError('Overlapping dynamic observation ownership')
            index[row['id']]=row;assigned[row['id']]='observed_dynamic_selection'
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
    if upper_motion_model is not None:
        from upper_voicing_motion import validate_execution as validate_upper_motion_execution
        validate_upper_motion_execution(upper_motion_model,restored,normal=core)
    if treatment_model is not None:
        from coattack_treatment_ownership import validate_execution as validate_treatment_execution
        validate_treatment_execution(treatment_model,restored)
    if backing_model is not None:
        from backing_pitch_ownership import validate_contacts
        validate_contacts(restored,backing_model,normal=core)
    if figure_model is not None:
        from figure_register_ownership import validate_execution
        validate_execution(figure_model,restored)
    if dynamic_optional:
        from observed_dynamics import validate_source as validate_dynamic_occurrences
        validate_dynamic_occurrences(parameters['observed_dynamics'],restored)
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
    if note_rest_model is not None:
        from note_rest_timing import validate_source as validate_note_rest_source
        validate_note_rest_source(note_rest_model,restored)
    if 'contextual_constraints' in upper:
        from contextual_note_roles import verify
        verify(restored,upper['contextual_constraints'])
    if 'membership_lock' in upper:
        from context_membership import verify
        verify(restored,upper['membership_lock'])
    if 'stable_pitch_preference' in upper:
        from stable_pitch_policy import stable_spans
        stable_spans(upper,restored)
    return restored


def reconstruct(upper,controls):
    result=_reconstruct(upper,controls)
    if 'stable_pitch_preference' in upper:
        from stable_pitch_policy import enforce_transition
        enforce_transition(upper,realize(upper),result)
    return result


def _reconstruct(upper,controls):
    if controls.get('context_policy') == 'source_melodic_movement':
        from melodic_movement_ownership import intervene
        edited, _ = intervene(upper, controls)
        return realize(edited)
    if controls.get('context_policy')=='source_note_rest_timing':
        from local_note_rest_timing import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')=='source_bend_excursion':
        from bend_gesture_ownership import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')=='source_upper_voicing_motion':
        from upper_voicing_motion import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')=='source_coattack_treatment':
        from coattack_treatment_ownership import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')in('observed_guitar_figure_register','source_guitar_figure_register','source_expressive_figure_register','source_muted_figure_register'):
        from observed_figure_register import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy') in ('source_keyboard_note_register','backing_motion_with_note_register'):
        from observed_note_register import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls=={'variation':0} and type(controls['variation']) in (int,float):
        return realize(upper)
    if controls.get('context_policy')=='observed_backing_motion':
        from backing_motion_intervention import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
    if controls.get('context_policy')=='source_local_melodic_figure':
        from melodic_figure_intervention import intervene
        edited,_=intervene(upper,controls)
        return realize(edited)
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
    if 'melodic_movement' in upper.get('owned_parameters', {}):
        from melodic_movement_ownership import expand
        lower = validate(expand(upper))
        if realize(strip_lower(upper)) != lower:
            raise ValueError('Melodic movement disagrees with shared relationships')
        return lower
    if 'bend_gesture' in upper.get('owned_parameters',{}):
        from bend_gesture_ownership import expand
        lower=validate(expand(upper))
        if realize(strip_lower(upper))!=lower:raise ValueError('Bend gesture differs from shared pitch/curve relationships')
        return lower
    if upper['musical_relationships'].get('schema') in ('source-upper-voicing-motion/1','source-upper-voicing-motion/2'):
        from upper_voicing_motion import expand,validate_origin
        shared=upper['musical_relationships'];validate_origin(shared,upper.get('source_origin'))
        plain=deepcopy(upper);plain['musical_relationships']=expand(shared)
        lower=validate(plain)
        if realize(strip_lower(upper))!=lower:
            raise ValueError('Upper-motion owner disagrees with existing relationships')
        return lower
    if upper['musical_relationships'].get('schema')=='coattack-treatment-ownership/1':
        from coattack_treatment_ownership import expand
        shared=upper['musical_relationships']
        plain=deepcopy(upper);plain['musical_relationships']=expand(shared)
        lower=validate(plain)
        # Re-lifting edited notes would replace original observation evidence.
        # Validate the stored authority and SAME inverse against the plain result.
        if realize(strip_lower(upper))!=lower:
            raise ValueError('Coattack treatment differs from its shared relationships')
        return lower
    if upper['musical_relationships'].get('schema')in('figure-register-ownership/1','figure-register-ownership/2','figure-register-ownership/3'):
        from figure_register_ownership import expand,lift,lift_expressive,lift_muted,EXPRESSIVE_SCHEMA,MUTED_SCHEMA
        shared=upper['musical_relationships']
        plain=deepcopy(upper);plain['musical_relationships']=expand(shared)
        lower=validate(plain)
        rebuilt=(lift_expressive(plain['musical_relationships'],tier1=lower,seed_refs=shared['execution_contract']['closure']['seed_refs'])
                 if shared['schema']==EXPRESSIVE_SCHEMA else
                 lift_muted(plain['musical_relationships'],tier1=lower,ordered_refs=shared['groups'][0]['occurrence_refs'])
                 if shared['schema']==MUTED_SCHEMA else lift(plain['musical_relationships'],shared['groups'][0]['occurrence_refs']))
        if rebuilt!=shared:
            raise ValueError('Noncanonical figure register ownership')
        if realize(strip_lower(upper))!=lower:
            raise ValueError('Figure register owner disagrees with existing relationships')
        return lower
    if upper['musical_relationships'].get('schema')in('backing-relative-pitches/1','backing-relative-pitches/2','backing-relative-pitches/3','backing-relative-pitches/4'):
        from backing_pitch_ownership import expand,lift,legacy_relift,LEGACY_SCHEMA,MEMBER_SCHEMA,EXECUTED_SCHEMAS
        shared=upper['musical_relationships']
        plain=deepcopy(upper);plain['musical_relationships']=expand(shared)
        bindings=[{k:v for k,v in r.items() if k!='interval_semitones'} for r in shared['relationships']]
        lower=validate(plain)
        rebuilt=legacy_relift(plain['musical_relationships'],bindings) if shared['schema']==LEGACY_SCHEMA else lift(plain['musical_relationships'],bindings,tier1=lower,preserve_execution=shared['schema'] in EXECUTED_SCHEMAS,member_scope=shared['schema']==MEMBER_SCHEMA)
        if rebuilt!=shared:
            raise ValueError('Noncanonical backing interval ownership')
        if realize(strip_lower(upper))!=lower:
            raise ValueError('Backing interval owner disagrees with previous representation')
        return lower
    lower=realize(strip_lower(upper))
    if 'input' in upper and json.dumps(lower,sort_keys=True)!=json.dumps(upper['input'],sort_keys=True):raise ValueError('Nested T1 conflicts')
    # Recompute all views to reject a second unchecked analysis authority.
    model=upper['musical_relationships'];rhythm=model.get('schema')in('source-group-rhythm/1','source-group-rhythm/2')
    note_rest=model.get('schema')=='source-note-rest-timing/1'
    if note_rest:
        from note_rest_timing import expand as expand_note_rest
        model,_=expand_note_rest(model)
    structural=rhythm and model['schema']=='source-group-rhythm/2'
    if rhythm:
        from group_rhythm_relations import expand as rhythm_expand,lift as rhythm_lift
        model,_=rhythm_expand(model)
        if rhythm_lift(lower,model,structural=structural)!=upper['musical_relationships']:raise ValueError('Noncanonical shared rhythm ownership')
    declared=model.get('schema')=='source-declared-chord-degrees/1'
    from chord_symbol_lexicon import LEGACY_PROFILE
    profile=model.get('admission_profile',LEGACY_PROFILE) if declared else None
    computed=analyze(lower,families=model.get('schema')=='source-voicing-families/1',declared_chords=declared,declared_chord_profile=profile,note_accent_slots='optional_note_accents'in upper['owned_parameters'],palm_mute_slots='optional_beat_palm_mutes'in upper['owned_parameters'],step_tempos='global_step_tempos'in upper['owned_parameters'],rhythm_groups=rhythm,rhythm_group_profile='written_time'if structural else'plain_repeat')
    # Stable occurrence-group IDs may move relative to other parts in time.
    # For rhythm owners exact source comparison + canonical re-lift above checks
    # identity and equations without renumbering unrelated source occurrences.
    compared=model if note_rest else upper['musical_relationships']
    if not rhythm and json.dumps(computed['musical_relationships'],sort_keys=True)!=json.dumps(compared,sort_keys=True):raise ValueError('Pitch/time authority conflicts with source choices')
    if 'derived_views' in upper and json.dumps(computed['derived_views'],sort_keys=True)!=json.dumps(upper['derived_views'],sort_keys=True):raise ValueError('Stale or altered derived musical view')
    return lower
