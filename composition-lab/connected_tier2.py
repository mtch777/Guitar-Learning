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


def analyze(tier1,*,families=False,declared_chords=False,declared_chord_profile=None):
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
    effect=lift(tier1);effect_ids={r['id'] for r in realize_effects(effect)}
    events={event_pointer(e):e for e in normalized['events']}
    source_index={r['id']:r for r in tier1['facts']}
    skeleton=[];choices=[];positions=[];coverage=[];unsupported=deepcopy(effect['unsupported'])
    for row in tier1['facts']:
        if row['id'] in effect_ids:
            coverage.append(dict(fact_ref=row['id'],owner='technique_declaration'));continue
        skeleton.append({k:deepcopy(v) for k,v in row.items() if k!='value'})
        if 'value' not in row:
            if not registered_container(row):
                unsupported.append(dict(fact_ref=row['id'],reason='UNREGISTERED_SOURCE_CONTAINER'))
            coverage.append(dict(fact_ref=row['id'],owner='source_structure'));continue
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
    if set(upper)-{'contextual_constraints'}!=fields or upper['schema']!='connected-source-musical-relations/1' or upper['tier']!=2:raise ValueError('Unsupported unified interface or hidden payload')
    if upper['unsupported']:raise ValueError('Unsupported source facts block full inverse')
    structure=upper['source_structure'];parameters=upper['owned_parameters']
    if set(structure)!={'documents','facts','source_scope'} or set(parameters)!={'source_choices','physical_positions','technique_declarations'}:raise ValueError('Unregistered owner payload')
    facts=deepcopy(structure['facts']);index={r['id']:r for r in facts}
    if len(index)!=len(facts) or any('value' in r for r in facts):raise ValueError('Raw or duplicate skeleton scalar')
    if any(r['type'] in ('object','array') and not registered_container(r) for r in facts):raise ValueError('Unregistered source container')
    assigned={r['id']:'source_structure' for r in facts if r['type'] in ('object','array')}
    def assign(ident,value,owner):
        if ident not in index or ident in assigned:raise ValueError('Duplicate or absent scalar owner')
        index[ident]['value']=value;assigned[ident]=owner
    core=upper['musical_relationships']
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
    if len(upper['coverage'])!=len(index) or {r['fact_ref']:r['owner'] for r in upper['coverage']}!=assigned or any(set(r)!={'fact_ref','owner'} for r in upper['coverage']):raise ValueError('Incomplete/duplicate ownership ledger')
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
    # SAME pure observation projection in both directions. No source files,
    # expected answers or cached views can repair inconsistent parameters.
    from run_reversible_tier_qa import extract_documents
    observed=extract_documents(project_documents(restored))
    if json.dumps(observed,sort_keys=True)!=json.dumps(normalized,sort_keys=True):raise ValueError('Source choices conflict with pitch/time relationships')
    if 'contextual_constraints' in upper:
        from contextual_note_roles import verify
        verify(restored,upper['contextual_constraints'])
    return restored


def reconstruct(upper,controls):
    if controls=={'variation':0} and type(controls['variation']) in (int,float):
        return realize(upper)
    from voicing_register import intervene
    edited,_=intervene(upper,controls)
    return realize(edited)


def validate(upper):
    lower=realize(strip_lower(upper))
    if 'input' in upper and json.dumps(lower,sort_keys=True)!=json.dumps(upper['input'],sort_keys=True):raise ValueError('Nested T1 conflicts')
    # Recompute all views to reject a second unchecked analysis authority.
    declared=upper['musical_relationships'].get('schema')=='source-declared-chord-degrees/1'
    from chord_symbol_lexicon import LEGACY_PROFILE
    profile=upper['musical_relationships'].get('admission_profile',LEGACY_PROFILE) if declared else None
    computed=analyze(lower,families=upper['musical_relationships'].get('schema')=='source-voicing-families/1',declared_chords=declared,declared_chord_profile=profile)
    if json.dumps(computed['musical_relationships'],sort_keys=True)!=json.dumps(upper['musical_relationships'],sort_keys=True):raise ValueError('Pitch/time authority conflicts with source choices')
    if 'derived_views' in upper and json.dumps(computed['derived_views'],sort_keys=True)!=json.dumps(upper['derived_views'],sort_keys=True):raise ValueError('Stale or altered derived musical view')
    return lower
