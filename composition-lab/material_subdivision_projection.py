"""Project a material's reattacks into the existing typed T2 owners.

Only the saved per-use multiplicity is authoritative. This projection consumes
the CURRENT resolved owners, never source files or generated-note observations.
Pitch/contact/expression inheritance is evaluated again on every inverse.
"""
from copy import deepcopy
from fractions import Fraction as F
import re

import musical_support_material as material
import melodic_movement_ownership as movement
from technique_observation_relations import scalar_relation

BEAT = re.compile(r'(track-\d+\.json#/measures/\d+/voices/\d+/beats/)(\d+)(/.*)?$')
EVENT = re.compile(r'event:\d+:\d+:\d+:\d+:\d+:\d+$')


def _shape_row(row, target_beat):
    """Readdress a typed descriptor, keeping immediate membership and slot order."""
    out = deepcopy(row)
    old = BEAT.fullmatch(row['id'])
    if old is None:
        return out
    source_beat = old[1]+old[2]
    def ref(value):
        return target_beat+value[len(source_beat):] if value == source_beat or value.startswith(source_beat+'/') else value
    out['id'] = ref(out['id']); out['pointer'] = out['id'].split('#',1)[1]
    out['parent'] = ref(out['parent'])
    if 'children' in out:out['children'] = [ref(c) for c in out['children']]
    if row['id'] == source_beat:out['slot'] = int(target_beat.rsplit('/',1)[1])
    return out


def _rewrite(value, fact, event):
    """Readdress live references only; immutable evidence never enters this helper."""
    if isinstance(value, list):return [_rewrite(v,fact,event) for v in value]
    if isinstance(value, dict):return {k:_rewrite(v,fact,event) for k,v in value.items()}
    if isinstance(value,str):
        if EVENT.fullmatch(value):return event(value)
        if BEAT.fullmatch(value):return fact(value)
    return value


def project(t2, plans):
    """Apply complete bar maps from material_subdivision.plan atomically.

    A split target with a foreign pitch/gesture dependency is refused rather
    than guessing whether the dependency means its attack or its final release.
    References to UNSPLIT occurrences move with their identity.
    """
    from material_subdivision import plan_maps
    maps = plan_maps(plans)
    beats, events, spans = maps['beats'], maps['events'], maps['spans']
    if not any(len(v)>1 for v in beats.values()):return deepcopy(t2)
    source = deepcopy(t2); out = deepcopy(t2)
    def beat_of(ref):
        match = BEAT.fullmatch(ref)
        return match[1]+match[2] if match else None
    def targets(ref):return beats.get(beat_of(ref),[beat_of(ref)])
    def fact(ref, child=0):
        base=beat_of(ref)
        if base not in beats:return ref
        return beats[base][child]+ref[len(base):]
    def event(ref, child=0):return events.get(ref,[ref])[child]
    def keep(ref,child):
        base=beat_of(ref)
        return child==0 or base is None or ref[len(base):].lstrip('/').split('/',1)[0] not in ('text','chord')
    split_refs={r for r,dest in events.items() if len(dest)>1}
    changed_refs={r for r,dest in events.items() if dest!=[r]}
    # These owners carry their own source-coordinate evidence/constraints. A
    # mapped occurrence needs an explicit owner adapter, not a recursive rewrite.
    known={'source_choices','physical_positions','technique_declarations',
           'optional_note_accents','optional_beat_palm_mutes','observed_dynamics','global_step_tempos'}
    for key,value in source['owned_parameters'].items():
        if key not in known and any(ref in repr(value) for ref in changed_refs):
            raise ValueError('SUBDIVISION_OWNER_PROJECTION_REQUIRED: '+key)
    for key in ('contextual_constraints','membership_lock','stable_pitch_preference'):
        if key in source and any(ref in repr(source[key]) for ref in changed_refs):
            raise ValueError('SUBDIVISION_CONTEXT_PROJECTION_REQUIRED: '+key)
    core=source['musical_relationships']
    if core.get('schema') not in ('musical-context-relations/2','backing-relative-pitches/1',
                                'backing-relative-pitches/2','backing-relative-pitches/3','backing-relative-pitches/4'):
        raise ValueError('SUBDIVISION_CORE_PROJECTION_REQUIRED: '+str(core.get('schema')))
    for link in core.get('relationships',[]):
        if {link['occurrence_ref'],link['backing_ref']}&split_refs:
            raise ValueError('SUBDIVISION_LINK_ENDPOINT_MEANING_REQUIRED')
    # Reject remapped guarded endpoints until their full contracts have an
    # explicit coordinate projection. Unaffected guards remain byte-for-byte.
    for key,value in core.items():
        if key not in ('core','relationships','written_tie_constraints') and key.endswith('constraints') and any(r in repr(value) for r in changed_refs):
            raise ValueError('SUBDIVISION_GUARD_PROJECTION_REQUIRED: '+key)
    if 'written_tie_constraints'in core:
        import backing_written_tie_constraints as ties
        guard=core['written_tie_constraints'];mapped=deepcopy(guard)
        for edge in guard['relations']:
            if {edge['origin_ref'],edge['destination_ref']}&split_refs:
                raise ValueError('SUBDIVISION_LINK_ENDPOINT_MEANING_REQUIRED')
        mapped['relations']=[ties.relation(dict(origin=event(r['origin_ref']),destination=event(r['destination_ref']),kind=r['kind'])) for r in guard['relations']]
        mapped['relations'].sort(key=lambda r:(ties.address(r['destination_ref']),ties.address(r['origin_ref'])))
        refs=sorted((event(r['occurrence_ref']) for r in guard['incidence']),key=ties.address)
        mapped['incidence']=[dict(occurrence_ref=ref,relation_refs=[r['id'] for r in mapped['relations'] if ref in (r['origin_ref'],r['destination_ref'])]) for ref in refs]
        ties.shape(mapped,refs)
        out['musical_relationships']['written_tie_constraints']=mapped

    old_arrays=material._arrays(source); arrays=material._arrays(out)
    def descriptors(rows):
        result=[]
        for row in rows:
            base=beat_of(row['id'])
            if base in beats:
                for child,ref in enumerate(beats[base]):
                    if not keep(row['id'],child):continue
                    current=_shape_row(row,ref)
                    if row['id']==base and child:
                        current['children']=[c for c in current['children'] if c[len(ref):].split('/')[1] not in ('text','chord')]
                    result.append(current)
            else:
                row=deepcopy(row)
                if 'children'in row:
                    row['children']=[target for c in row['children'] for target in beats.get(c,[c])]
                result.append(row)
        return result
    arrays['source_structure'][:]=descriptors(old_arrays['source_structure'])
    structure={r['id']:r for r in old_arrays['source_structure']}
    for field in ('source_choices','physical_positions','coverage'):
        result=[]
        for row in old_arrays[field]:
            ref=row['fact_ref'];base=beat_of(ref);count=len(beats.get(base,[base]))
            for child in range(count):
                if not keep(ref,child):continue
                item=_rewrite(row,lambda r:fact(r,child),lambda r:event(r,child))
                if field=='source_choices' and count>1:
                    suffix=ref[len(base):]
                    if suffix in ('/type','/duration/1'):
                        item['parameter']=scalar_relation('integer',source=scalar_relation('integer',parameter=row['parameter'])*count)
                    elif suffix in ('/beamStart','/beamStop'):
                        typ=structure[ref]['type']; value=scalar_relation(typ,parameter=row['parameter'])
                        item['parameter']=scalar_relation(typ,source=value if (child==0 if suffix=='/beamStart' else child==count-1) else (False if typ=='boolean' else 0))
                result.append(item)
        arrays[field][:]=result
    groups=[]
    for group in old_arrays['technique_declarations']:
        ref=group['source_fact_ref'];base=beat_of(ref)
        for child,target in enumerate(beats.get(base,[base])):
            value=_rewrite(group,lambda r:fact(r,child),lambda r:event(r,child))
            value['structure']=[_shape_row(r,target) if base in beats else deepcopy(r) for r in group['structure']]
            value['id']='technique:'+value['source_fact_ref'];groups.append(value)
    arrays['technique_declarations'][:]=groups
    for name,field,prefix in (('optional_note_accents','note_structure','accent-slot:'),
                              ('optional_beat_palm_mutes','beat_structure','palm-mute-slot:')):
        model=out['owned_parameters'].get(name)
        if model is None:continue
        groups=[]
        for group in source['owned_parameters'][name]['groups']:
            shape=group[field];base=beat_of(shape['id'])
            for target in beats.get(base,[base]):
                value=deepcopy(group)
                if base in beats:value[field]=_shape_row(shape,target)
                if field=='beat_structure' and base in beats and target!=beats[base][0]:
                    value[field]['children']=[c for c in value[field]['children'] if c[len(target):].split('/')[1] not in ('text','chord')]
                value['id']=prefix+value[field]['id'];groups.append(value)
        model['groups']=sorted(groups,key=lambda g:g['id'])
    dynamic=source['owned_parameters'].get('observed_dynamics')
    if dynamic is not None:
        from observed_dynamics import project as project_dynamics
        fact_map={r['fact_ref']:[fact(r['fact_ref'],i) for i in range(len(beats.get(beat_of(r['fact_ref']),[None])))]
                  for r in dynamic['current'] if beat_of(r['fact_ref']) in beats}
        out['owned_parameters']['observed_dynamics']=project_dynamics(dynamic,fact_map,events)
    if isinstance(out['coverage'],dict):
        out['coverage']['rules']=[dict(relation=g['id']) for name in ('optional_note_accents','optional_beat_palm_mutes')
                                for g in out['owned_parameters'].get(name,{}).get('groups',[])]
    body=movement._body(out['musical_relationships']); old_body=movement._body(core)
    new_groups=[]
    for group in old_body['coattacks']:
        first=group['members'][0]['id'];count=len(events.get(first,[first]))
        for child in range(count):
            value=deepcopy(group)
            for member in value['members']:
                old=member['id']; member['id']=event(old,child)
                _,_,_,_,member['beat'],_=map(int,member['id'].split(':')[1:])
                if count>1:
                    member['duration_q']=spans[old][child]['duration_q']
            if count>1:value['onset_q']=spans[first][child]['onset_q']
            value['id']=group['id']+':subdivision:'+str(child);new_groups.append(value)
    new_groups.sort(key=lambda g:(F(g['onset_q']),g['bar'],g['part_id']))
    for i,g in enumerate(new_groups):g['id']='coattack:'+str(i)
    body['coattacks']=new_groups
    body['realization_order']=[dest for ref in old_body['realization_order'] for dest in events.get(ref,[ref])]
    body['source_quality']['expected']=body['source_quality']['actual']=len(body['realization_order'])
    if 'relationships'in out['musical_relationships']:
        out['musical_relationships']['relationships']=_rewrite(core['relationships'],fact,event)
    from group_rhythm_relations import VIEWS,refresh
    if any(k in body for k in VIEWS):
        refreshed=refresh(deepcopy(body))
        for k in VIEWS:
            if k in body:body[k]=refreshed[k]
    # Grammar-derived order is required; preserve graces after regular events.
    # No re-analysis, source reads or evidence repair occurs here.
    return material.restore_fragments(out,[])
