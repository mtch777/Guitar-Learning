"""Distinct timed uses of one musical material; source definitions never change.

Placement solves current_bar = destination_first + (source_bar-source_first),
and current_onset = destination_start + relative_material_onset. These are
coordinates, not new note choices or an alternative generation engine.
"""
from copy import deepcopy
from fractions import Fraction as F
import re

import musical_support_material as material
import musical_cell_development as cell
import backing_execution_constraints as execution
from technique_observation_relations import scalar_relation,identify
from source_observation_evidence import digest

SCHEMA='source-musical-material-uses/1'
APPROACH_SCHEMA='source-musical-material-uses/2'
DIRECT_SCHEMA='source-musical-material-uses-direct/1'
RHYTHM_SCHEMA='source-musical-material-uses/3'


def unallocated_fields(use):
    """A section owns allocation, while local use timing remains independent."""
    return {'id','slot_ref'} | ({'rhythm_offset_q'} if 'rhythm_offset_q' in use else set())


def _shape(upper):
    if type(upper)is not dict:raise ValueError('Exact material-use T3 required')
    fields={'tier','schema','lower_tier','materials','slots','uses'}
    if upper.get('schema')!=DIRECT_SCHEMA:fields|={'relationship','instance_attack_refs','observations'}
    if (set(upper)!=fields or upper['tier']!=3
            or upper['schema']not in (SCHEMA,APPROACH_SCHEMA,DIRECT_SCHEMA,RHYTHM_SCHEMA)):raise ValueError('Exact material-use T3 required')
    if upper['schema']==DIRECT_SCHEMA and (type(upper['lower_tier'])is not dict
            or upper['lower_tier'].get('tier')!=2):raise ValueError('Direct material uses require a T2 parent')
    if any(type(upper[k])is not list for k in ('materials','slots','uses')):raise ValueError('Explicit material/slot/use lists required')
    # Inactive vocabulary remains a real definition, not an unchecked storage slot.
    for definition in upper['materials']:material.expand(definition)
    used=set();identities=set()
    for use in upper['uses']:
        fields={'id','slot_ref','material_ref','expression'}
        if upper['schema']in (APPROACH_SCHEMA,DIRECT_SCHEMA,RHYTHM_SCHEMA) and type(use)is dict and 'approach_mode'in use:fields.add('approach_mode')
        if upper['schema']in (RHYTHM_SCHEMA,DIRECT_SCHEMA) and type(use)is dict and 'rhythm_offset_q'in use:
            fields.add('rhythm_offset_q')
            value=use['rhythm_offset_q']
            if type(value)is not str or str(F(value))!=value:raise ValueError('Canonical common rhythmic displacement required')
        if (type(use)is not dict or set(use)!=fields
                or type(use['id'])is not str or not re.fullmatch(r'[A-Za-z0-9:_-]+',use['id'])
                or use['id']in identities or type(use['slot_ref'])is not int
                or not 0<=use['slot_ref']<len(upper['slots'])or use['slot_ref']in used
                or type(use['material_ref'])is not int or not 0<=use['material_ref']<len(upper['materials'])):
            raise ValueError('One unique use per owned slot and explicit material reference required')
        identities.add(use['id']);used.add(use['slot_ref'])
        slot=upper['slots'][use['slot_ref']]
        if type(slot)is not dict or set(slot)!={'scope','start_q','bar_spans_q'}:raise ValueError('Closed destination geometry required')
        scope=slot['scope']
        if type(scope)is not dict or set(scope)!={'parts','first_bar','last_bar'}:raise ValueError('Closed destination scope required')
        material._scope(scope['parts'],scope['first_bar'],scope['last_bar'])
        if type(slot['start_q'])is not str or str(F(slot['start_q']))!=slot['start_q']or F(slot['start_q'])<0:
            raise ValueError('Canonical destination clock required')
        definition=upper['materials'][use['material_ref']]
        from material_approaches import SCHEMA as approach_schema
        if definition['schema']==approach_schema:
            if upper['schema']not in (APPROACH_SCHEMA,DIRECT_SCHEMA,RHYTHM_SCHEMA) or use.get('approach_mode')not in ('original','flip'):
                raise ValueError('Each approach use needs its own explicit direction choice')
        elif 'approach_mode'in use:raise ValueError('An ordinary material has no approach choice')
        if (scope['parts']!=definition['scope']['parts']or slot['bar_spans_q']!=definition['bar_spans_q']
                or scope['last_bar']-scope['first_bar']!=definition['scope']['last_bar']-definition['scope']['first_bar']):
            raise ValueError('MVP placement preserves instrument bindings and complete bar geometry')
    if used!=set(range(len(upper['slots']))):raise ValueError('Unfilled owned material slot')


def _maps(definition,slot):
    old=definition['scope'];delta=slot['scope']['first_bar']-old['first_bar']
    def fact(ref):
        if ref is None:return None
        match=re.fullmatch(r'(track-(\d+)\.json#)/measures/(\d+)(/.*)?',ref)
        if match is None:return ref  # tuning/capo/track settings keep their owner
        prefix,p,mi,tail=match.groups();mi=int(mi)
        if int(p)not in old['parts']or not old['first_bar']<=mi+1<=old['last_bar']:
            raise ValueError('Material reference crosses its source scope')
        return prefix+'/measures/'+str(mi+delta)+(tail or'')
    def event(ref):
        song,p,b,v,beat,note=execution.address(ref)
        if p not in old['parts']or not old['first_bar']<=b<=old['last_bar']or v!=0:
            raise ValueError('Material occurrence crosses source scope')
        return f'event:{song}:{p}:{b+delta}:{v}:{beat}:{note}'
    return fact,event,delta


def _row(row,fact):
    out=deepcopy(row);out['id']=fact(row['id']);out['pointer']=out['id'].split('#',1)[1]
    out['parent']=fact(row['parent'])
    if 'children'in out:out['children']=[fact(r)for r in row['children']]
    return out


def _dynamic(fragment,part,level):
    """Instance expression uses the existing typed categorical declaration owner."""
    from local_dynamics import source_rules
    if type(level)is not str or level not in source_rules()[1]:raise ValueError('Known target dynamic required')
    groups=fragment['technique_declarations']
    for g in groups:
        if g['field']=='velocity'and g['source_fact_ref'].startswith(f'track-{part}.json#'):
            if len(g['parameters'])!=1 or len(g['structure'])!=1 or g['structure'][0]['type']!='string':
                raise ValueError('Unsupported expression declaration')
            g['parameters'][0]['parameter']=scalar_relation('string',source=level)
    beats=[r for r in fragment['source_structure']if r['document']==f'track-{part}.json'
        and re.fullmatch(r'/measures/\d+/voices/0/beats/\d+',r['pointer'])]
    if not beats:raise ValueError('No destination beat for expression boundary')
    root=beats[0];ref=root['id']+'/velocity'
    if any(g['source_fact_ref']==ref for g in groups):return
    if ref in root['children']:raise ValueError('Competing dynamic owner')
    root['children'].append(ref)
    row=dict(id=ref,document=root['document'],pointer=root['pointer']+'/velocity',parent=root['id'],slot='velocity',type='string')
    owner=identify(row)
    groups.append(dict(id='technique:'+ref,source_fact_ref=ref,**owner,structure=[row],
        parameters=[dict(fact_ref=ref,unit='1',parameter=scalar_relation('string',source=level))],
        meaning='Source technique declaration; numerical units normalized, unspecified execution remains unknown'))
    fragment['coverage'].append(dict(fact_ref=ref,owner='technique_declaration'))


def place(definition,slot,use,*,parent=None):
    """Resolve one distinct use. The immutable definition is never rewritten."""
    if parent is not None:
        foreign=material.expression_rows(parent);foreign_ids={r['id']for r in foreign}
        if any(row['id']in foreign_ids for row in definition['lower_tier']['source_structure']):
            raise ValueError('Stored material duplicates an existing expression owner')
        if definition['scope']!=slot['scope'] and any(material._owns(row['id'],scope)for row in foreign
               for scope in (definition['scope'],slot['scope'])):
            raise ValueError('Material relocation would readdress existing expression owners')
    from material_approaches import SCHEMA as approach_schema, expand as expand_approach
    solved=expand_approach(definition,use['approach_mode'])if definition['schema']==approach_schema else definition
    if 'rhythm_offset_q' in use:
        from material_rhythm_displacement import solve
        if parent is not None:solved=material.rhythm_context(solved,parent)
        solved,_=solve(solved,use['rhythm_offset_q'])
    source=material.expand(solved);fact,event,delta=_maps(definition,slot)
    out={k:deepcopy(v)for k,v in source.items()};shift=F(slot['start_q'])-F(definition['source_start_q'])
    out['source_structure']=[_row(r,fact)for r in source['source_structure']]
    for field in ('source_choices','coverage'):
        for row in out[field]:row['fact_ref']=fact(row['fact_ref'])
    for row in out['physical_positions']:
        row['occurrence_ref']=event(row['occurrence_ref'])
        for key in ('fact_ref','string_ref','capo_ref','tuning_ref','tuning_array_ref'):
            if key in row:row[key]=fact(row[key])
    for group in out['technique_declarations']:
        group['source_fact_ref']=fact(group['source_fact_ref']);group['id']='technique:'+group['source_fact_ref']
        group['owner_ref']=fact(group['owner_ref'])
        group['structure']=[_row(r,fact)for r in group['structure']]
        for row in group['parameters']:row['fact_ref']=fact(row['fact_ref'])
    mapping=[]
    for group in out['coattacks']:
        group['id']=use['id']+':'+group['id'];group['bar']+=delta;group['onset_q']=str(F(group['onset_q'])+shift)
        for member in group['members']:
            old=member['id'];member['id']=event(old);member['bar']+=delta
            mapping.append(dict(identity=use['id']+'/'+old,source_occurrence=old,current_address=member['id']))
    out['realization_order']=[event(r)for r in source['realization_order']]
    if len({r['current_address']for r in mapping})!=len(mapping):raise ValueError('Noninjective material placement')
    records=deepcopy(definition['observed_execution'])
    for row in records:
        for key in ('member_refs','tied_member_refs'):row[key]=[event(r)for r in row[key]]
        for key in ('origin_ref','destination_ref','candidate_destination_ref'):
            if row[key]is not None:row[key]=event(row[key])
        row['source_fact_ref']=fact(row['source_fact_ref']);row['id']=execution.identity(row)
    if type(use['expression'])is not list:raise ValueError('Explicit instance expression list required')
    seen=set();pitched={execution.address(r['occurrence_ref'])[1]for r in out['physical_positions']}
    for expression in use['expression']:
        if (type(expression)is not dict or set(expression)!={'part_id','level'}or type(expression['part_id'])is not int
                or expression['part_id']not in pitched or expression['part_id']in seen):
            raise ValueError('One declared pitched-part expression override; percussion remains source-pattern expression')
        seen.add(expression['part_id']);_dynamic(out,expression['part_id'],expression['level'])
    return out,records,mapping


def lift(upper):
    previous=material.expand_t3(upper)
    out=deepcopy(upper);out['schema']=SCHEMA
    out['slots']=[dict(scope=deepcopy(m['scope']),start_q=m['source_start_q'],bar_spans_q=deepcopy(m['bar_spans_q']))for m in out['materials']]
    out['uses']=[dict(id=f'material-use:{i}',slot_ref=i,material_ref=i,expression=[])for i in range(len(out['materials']))]
    restored,_,_=realize_pair(out)
    if restored!=previous:raise ValueError('Use identities changed the current preceding musical model')
    return out


def from_tier2(t2,specifications):
    """Own material directly above T2, without requiring an unrelated cell.

    Original observations and foreign owners remain in the preceding T2. Only
    the declared material fragments move to their explicit T3 relationships.
    """
    from connected_tier2 import realize
    if type(t2)is not dict:raise ValueError('A complete connected T2 model is required')
    if type(specifications)is not list or not specifications:
        raise ValueError('At least one explicit material scope required')
    realize(t2)  # Reject lower payloads and malformed owners before construction.
    out=dict(tier=3,schema=DIRECT_SCHEMA,lower_tier=deepcopy(t2),materials=[],slots=[],uses=[])
    out=extend_materials(out,specifications)
    if expand(out)!=t2:raise ValueError('Direct material ownership changed preceding T2 relationships')
    return out


def realize_pair(upper):
    """Return the restored parent (T2 or legacy cell T3), T1 and identities."""
    _shape(upper);pieces=[];contracts=[];ledger=[]
    for use in upper['uses']:
        piece,records,identities=place(upper['materials'][use['material_ref']],upper['slots'][use['slot_ref']],use,
                                     parent=upper['lower_tier'])
        pieces.append(piece);contracts.append(records);ledger.extend(identities)
    if len({r['current_address']for r in ledger})!=len(ledger):raise ValueError('Overlapping active material uses')
    restored=material.restore_fragments(upper['lower_tier'],pieces)
    if upper['schema']==DIRECT_SCHEMA:
        from connected_tier2 import realize
        result=restored;lower=realize(result)
    else:
        result={k:deepcopy(v)for k,v in upper.items()if k not in ('materials','slots','uses')};result['schema']=cell.TIER3_SCHEMA
        result['lower_tier']=restored
        lower=cell.reconstruct(result,{'variation':0})
    for piece,records in zip(pieces,contracts):material.validate_fragment_execution(piece,records,lower)
    from material_approaches import SCHEMA as approach_schema, validate_membership
    for use in upper['uses']:
        definition=upper['materials'][use['material_ref']]
        if definition['schema']==approach_schema:
            _,event,_=_maps(definition,upper['slots'][use['slot_ref']])
            validate_membership(definition,lower,event_map=event)
    return result,lower,ledger


def expand(upper):
    parent=realize_pair(upper)[0]
    return parent if upper['schema']==DIRECT_SCHEMA else cell.expand(parent)


def reconstruct(upper,controls):
    if controls!={'variation':0}:raise ValueError('Arrangement choices are owned by T4, not this material-use inverse')
    return realize_pair(upper)[1]


def pack_expression(upper,changed_t2):
    """Pack existing current expression choices without replacing material owners.

    The caller uses the existing T2 policy on expand(upper). Only live choice
    leaves return to the saved parent; derived notation membership does not.
    """
    if upper.get('schema')!=DIRECT_SCHEMA:raise ValueError('Direct material-use T3 required for expression packing')
    from connected_tier2 import realize
    current=expand(upper);realize(changed_t2)
    expected=deepcopy(current);out=deepcopy(upper)
    old=current['owned_parameters'];new=changed_t2['owned_parameters']
    target=out['lower_tier']['owned_parameters']
    for key in ('optional_note_accents','optional_beat_palm_mutes'):
        if key not in old:continue
        before={g['id']:g for g in old[key]['groups']};after={g['id']:g for g in new.get(key,{}).get('groups',[])}
        saved={g['id']:g for g in target[key]['groups']}
        if set(before)!=set(after) or set(before)!=set(saved):raise ValueError('Expression packing cannot readdress owners')
        for group in expected['owned_parameters'][key]['groups']:
            state=deepcopy(after[group['id']]['state'])
            group['state']=state;saved[group['id']]['state']=deepcopy(state)
    key='observed_dynamics'
    if key in old:
        before={r['fact_ref']:r for r in old[key]['current']};after={r['fact_ref']:r for r in new.get(key,{}).get('current',[])}
        saved={r['fact_ref']:r for r in target[key]['current']}
        if set(before)!=set(after) or set(before)!=set(saved):raise ValueError('Expression packing cannot readdress dynamics')
        for row in expected['owned_parameters'][key]['current']:
            value=after[row['fact_ref']]['definition_ref']
            row['definition_ref']=value;saved[row['fact_ref']]['definition_ref']=value
    if expected!=changed_t2:raise ValueError('Expression packing changed a protected relationship or owner')
    if expand(out)!=changed_t2:raise ValueError('Saved expression choices conflict with material notation or owners')
    return out


def extend_materials(upper,specifications):
    """Add disjoint owners without refitting or replacing any existing material.

    This update preserves the old vocabulary, uses, observations and cell owner.
    New definitions consume only the current preceding T2 relationships.
    """
    current,lower,_=realize_pair(upper)
    complete=current if upper['schema']==DIRECT_SCHEMA else cell.expand(current)
    out=deepcopy(upper);scopes=[]
    occupied=[s['scope'] for s in upper['slots']]
    for spec in specifications:
        scope=material._scope(**dict(parts=spec['parts'],first=spec['first_bar'],last=spec['last_bar']))
        if any(set(scope['parts'])&set(s['parts']) and
               max(scope['first_bar'],s['first_bar'])<=min(scope['last_bar'],s['last_bar'])
               for s in occupied+scopes):
            raise ValueError('New material overlaps an existing owner')
        definition=material.fit(complete,lower=lower,**spec)
        mi=len(out['materials']);si=len(out['slots'])
        out['materials'].append(definition)
        out['slots'].append(dict(scope=scope,start_q=definition['source_start_q'],bar_spans_q=deepcopy(definition['bar_spans_q'])))
        out['uses'].append(dict(id=f'material-use:{si}',slot_ref=si,material_ref=mi,expression=[]))
        scopes.append(scope)
    out['lower_tier']=material._remove(upper['lower_tier'],scopes)
    restored,after,_=realize_pair(out)
    if restored!=current or after!=lower:raise ValueError('Additional ownership changed existing musical relationships')
    return out


def lift_approach(upper,use_id,attack_refs,interpretations,evidence_ref):
    """Refine one disjoint material without replacing another musical owner."""
    from material_approaches import fit
    before,lower,_=realize_pair(upper)
    matches=[u for u in upper['uses']if u['id']==use_id]
    if len(matches)!=1:raise ValueError('One existing material use required')
    ref=matches[0]['material_ref']
    if sum(u['material_ref']==ref for u in upper['uses'])!=1:
        raise ValueError('Refining a shared definition requires explicit shared ownership')
    out=deepcopy(upper)
    if out['schema']not in (DIRECT_SCHEMA,RHYTHM_SCHEMA):out['schema']=APPROACH_SCHEMA
    out['materials'][ref]=fit(upper['materials'][ref],lower,attack_refs,interpretations,evidence_ref)
    next(u for u in out['uses']if u['id']==use_id)['approach_mode']='original'
    after,realized,_=realize_pair(out)
    if after!=before or realized!=lower:raise ValueError('Approach ownership changed preceding relationships')
    return out


def approach_candidate(upper,use_id,mode):
    if mode not in ('original','flip'):raise ValueError('Explicit approach direction required')
    _shape(upper)
    out=deepcopy(upper);matches=[u for u in out['uses']if u['id']==use_id]
    if len(matches)!=1 or 'approach_mode'not in matches[0]:raise ValueError('Use has no approach owner')
    matches[0]['approach_mode']=mode
    reconstruct(out,{'variation':0})
    return out


def intervene_approach(upper,use_id,controls):
    import random
    if (type(controls)is not dict or set(controls)!={'release','mode','seed'}
            or type(controls['release'])is not int or not 0<=controls['release']<=100
            or controls['mode']not in ('original','flip')or type(controls['seed'])is not int):
        raise ValueError('Explicit approach release, direction and seed required')
    _shape(upper);selected=next((u for u in upper['uses']if u['id']==use_id),None)
    if selected is None or 'approach_mode'not in selected:raise ValueError('Use has no approach owner')
    current=selected['approach_mode'];requested=controls['mode']
    proposal=approach_candidate(upper,use_id,requested)if controls['release']else None
    released=random.Random(f'approach:release:{controls["seed"]}').random()<controls['release']/100
    options=[current]if current==requested else[current,requested]
    chosen=random.Random(f'approach:selection:{controls["seed"]}').choice(options)if released else current
    out=proposal if proposal is not None and chosen==requested else approach_candidate(upper,use_id,current)
    return out,dict(released=released,release_percent=controls['release'],mode=chosen,
                    changed=out!=upper,seed=controls['seed'])
