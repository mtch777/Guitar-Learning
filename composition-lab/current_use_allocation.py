"""Live material-instance allocation; definition keys keep their source meaning.

The persisted binding contains identities, not a copied note result. Resolution
reads the current donor's parameters again before the existing material inverse.
"""
from copy import deepcopy
from dataclasses import dataclass
import re

from source_observation_evidence import digest

FIELD='source_use_ref'

def resolve(upper):
    import support_material_uses as uses
    if not any(FIELD in row for row in upper.get('uses',[])):
        return upper,[]
    if upper.get('schema')!=uses.DIRECT_SCHEMA:
        raise ValueError('Live current-use allocation requires direct material ownership')
    original={row.get('id'):row for row in upper['uses']}
    if len(original)!=len(upper['uses']):raise ValueError('Unique material-use identities required')
    resolved={};visiting=set();bindings=[]
    def visit(identity):
        if identity in resolved:return resolved[identity]
        if identity in visiting:raise ValueError('Cyclic current-use allocation')
        if identity not in original:raise ValueError('Unknown live source use')
        visiting.add(identity);row=original[identity]
        if FIELD not in row:result=deepcopy(row)
        else:
            if set(row)!={'id','slot_ref',FIELD,'destination_material_ref','expression'}:
                raise ValueError('Live allocation cannot own independent donor parameters')
            if type(row[FIELD])is not str:raise ValueError('Typed live source use required')
            if type(row['destination_material_ref'])is not int or not 0<=row['destination_material_ref']<len(upper['materials']):
                raise ValueError('Existing destination material identity required')
            source=visit(row[FIELD])
            result=deepcopy(source)
            result.update(id=identity,slot_ref=row['slot_ref'],expression=deepcopy(row['expression']))
            bindings.append(dict(source_use_id=row[FIELD],destination_use_id=identity,
                source_material_ref=source['material_ref'],destination_material_ref=row['destination_material_ref']))
        visiting.remove(identity);resolved[identity]=result
        return result
    result=deepcopy(upper)
    result['uses']=[visit(row['id'])for row in upper['uses']]
    return result,bindings

@dataclass(frozen=True)
class Placement:
    definition_sha256:str
    slot_sha256:str
    parent_sha256:str
    dynamic_refs:tuple

def validate_placement(value,definition,slot,parent):
    if (type(value)is not Placement or value.definition_sha256!=digest(definition)
            or value.slot_sha256!=digest(slot)or value.parent_sha256!=digest(parent)):
        raise ValueError('Unverified current allocation placement')

def _inside(ref,scope):
    import musical_support_material as material
    return material._event(ref,scope)if ref.startswith('event:')else material._owns(ref,scope)


def activity_refs(scope):
    """Only existing complete-bar/voice rest declarations can follow activity."""
    return {f'track-{part}.json#/measures/{bar-1}{suffix}'
        for part in scope['parts']for bar in range(scope['first_bar'],scope['last_bar']+1)
        for suffix in ('/rest','/voices/0/rest')}


def _realize_activity(parent,scope,fragment,event):
    """A complete single-voice bar is silent iff its allocated line is silent.

    Keep declaration presence and type. This is a consequence of the activity
    choice, not a copied source flag or an independent note-writing operation.
    """
    sounding=set()
    for group in fragment['coattacks']:
        for member in group['members']:
            _,part,bar,_,_,_=map(int,event(member['id']).split(':')[1:])
            sounding.add((part,bar))
    structures={row['id']:row for row in parent['source_structure']['facts']}
    allowed=activity_refs(scope)
    for choice in parent['owned_parameters']['source_choices']:
        ref=choice['fact_ref']
        if ref not in allowed:continue
        shape=structures.get(ref)
        match=re.fullmatch(r'track-(\d+)\.json#/measures/(\d+)(?:/voices/0)?/rest',ref)
        part,measure=map(int,match.groups())
        voices=structures[f'track-{part}.json#/measures/{measure}/voices']
        if (shape is None or shape['type']!='boolean' or
                choice['owner']!='source_structure_declaration' or
                set(choice['parameter'])!={'symbol'} or
                type(choice['parameter']['symbol'])is not bool or len(voices['children'])!=1):
            raise ValueError('Complete typed single-voice activity ownership required')
        choice['parameter']['symbol']=(part,measure+1)not in sounding

def prepare(upper,bindings):
    """Project an explicit current instance into an owned silent destination.

    Musical values still come from the material inverse. Only existing optional
    expression containers and their CURRENT derivation/influence are projected.
    """
    import support_material_uses as uses
    import musical_support_material as material
    import observed_expression as expression
    import observed_dynamics as dynamics
    from material_subdivision_projection import _rewrite
    out=deepcopy(upper);parent=out['lower_tier'];parameters=parent['owned_parameters']
    contexts={}
    for binding in bindings:
        target=next(u for u in out['uses']if u['id']==binding['destination_use_id'])
        definition=out['materials'][binding['source_material_ref']]
        destination=out['materials'][binding['destination_material_ref']]
        slot=out['slots'][target['slot_ref']];scope=slot['scope'];source_scope=definition['scope']
        if destination['scope']!=scope:raise ValueError('Explicit current destination definition frame required')
        if material.expand(destination)['coattacks']:
            raise ValueError('NONEMPTY_DESTINATION_REQUIRES_SEMANTIC_CORRESPONDENCE')
        if source_scope['parts']!=scope['parts']or source_scope==scope:
            raise ValueError('Distinct compatible current allocation frames required')
        # Geometry and stable source references, not list-order pairing.
        fact,event,_=uses._maps(definition,slot)
        fragment=material.expand(definition)
        _realize_activity(parent,scope,fragment,event)
        refs=fragment['realization_order']
        mapped=[event(ref)for ref in refs]
        if len(mapped)!=len(set(mapped)):raise ValueError('Noninjective live instance correspondence')
        if definition.get('external_pitch_refs')or definition.get('unresolved_execution_locks'):
            raise ValueError('Source closure requires explicit external allocation correspondence')
        # Existing dependencies may not be reassigned to new notes at reused
        # addresses just because the destination happened to be silent.
        core=parent['musical_relationships']
        for field in ('relationships','unresolved','written_tie_constraints'):
            value=core.get(field,[])
            for ref in re.findall(r'event:\d+:\d+:\d+:\d+:\d+:\d+',repr(value)):
                if _inside(ref,scope):raise ValueError('Destination has a retained foreign dependency')
        # A complete silent region has no attack-specific destination choice to
        # silently transfer onto an unrelated source attack.
        target_dynamic=[]
        dynamic=parameters.get('observed_dynamics')
        if dynamic is None:raise ValueError('Explicit destination dynamic owner required')
        dynamic_rows=dynamics.realize(dynamic,parent.get('source_origin'))
        for row in dynamic_rows:
            if _inside(row['id'],scope):
                if '/notes/'in row['id']:raise ValueError('Silent note override needs explicit allocation correspondence')
                target_dynamic.append(row['id'])
        donor_dynamic={row['id']for row in dynamic_rows if _inside(row['id'],source_scope)}
        for name,field,prefix in (('optional_note_accents','note_structure','accent-slot:'),
                                  ('optional_beat_palm_mutes','beat_structure','palm-mute-slot:')):
            model=parameters.get(name)
            if model is None:raise ValueError('Typed current expression container ownership required')
            originals=list(model['groups']);kept=[];added=[]
            for group in originals:
                shape=group[field]
                if _inside(shape['id'],scope):continue
                kept.append(group)
                if not _inside(shape['id'],source_scope):continue
                copied=_rewrite(group,fact,event)
                copied[field]=uses._row(shape,fact)
                copied['id']=prefix+copied[field]['id']
                if field=='beat_structure':
                    children=copied[field]['children']
                    removed={fact(ref)for ref in donor_dynamic}
                    retained=[ref for ref in children if ref not in removed]
                    state=copied['state']
                    if state['kind']=='explicit':state['child_index']=sum(ref in retained for ref in children[:state['child_index']])
                    target_velocity=copied[field]['id']+'/velocity'
                    if target_velocity in target_dynamic:retained.append(target_velocity)
                    copied[field]['children']=retained
                added.append(copied)
            model['groups']=sorted(kept+added,key=lambda row:row['id'])
            if len({row['id']for row in model['groups']})!=len(model['groups']):raise ValueError('Competing allocated expression containers')
        if isinstance(parent['coverage'],dict):
            parent['coverage']['rules']=[dict(relation=g['id'])for name in ('optional_note_accents','optional_beat_palm_mutes')for g in parameters[name]['groups']]
        if 'observed_expression'in parameters:
            evidence=parameters['observed_expression'];lineage=expression._lineage(evidence)
            copies={key:{}for key in lineage};retired={key:[]for key in lineage}
            for key,rows in lineage.items():
                for current in {ref for targets in rows.values()for ref in targets}:
                    if _inside(current,scope):retired[key].append(current)
                    if _inside(current,source_scope):copies[key][current]=[event(current)if key=='event_map'else fact(current)]
            parameters['observed_expression']=expression.allocate_current(evidence,
                instance_id=binding['destination_use_id'],scope=scope,copies=copies,retired=retired)
        # Destination base dynamics remains its timed owner. Current generated
        # notes acquire an influence assignment, not original-observation votes.
        declared=[]
        for row in dynamic_rows:
            if '/notes/'in row['id']:continue
            match=re.fullmatch(r'track-(\d+)\.json#/measures/(\d+)/voices/(\d+)/beats/(\d+)/velocity',row['id'])
            if match:declared.append((tuple(map(int,match.groups())),row['id']))
        assignments={}
        for ref in mapped:
            _,part,bar,voice,beat,note=map(int,ref.split(':')[1:])
            candidates=[(address,decl)for address,decl in declared if address[0]==part and address[2]==voice and (address[1],address[3])<=(bar-1,beat)]
            if not candidates:raise ValueError('Unknown destination dynamic envelope')
            assignments[ref]=max(candidates,key=lambda pair:(pair[0][1],pair[0][3]))[1]
        parameters['observed_dynamics']=dynamics.allocate_influence(dynamic,
            instance_id=binding['destination_use_id'],scope=scope,assignment=assignments)
        contexts[binding['destination_use_id']]=(definition,slot,tuple(target_dynamic))
    return out,{uid:Placement(digest(definition),digest(slot),digest(parent),refs)for uid,(definition,slot,refs)in contexts.items()}
