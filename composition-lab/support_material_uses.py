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
    return {'id','slot_ref'} | ({'rhythm_offset_q', 'rhythm_lane_shares', 'entry_shares', 'degree_steps', 'degree_octaves', 'degree_strings', 'degree_member_steps', 'contact_strings', 'subdivision_factors', 'bend_excursions'} & set(use))


def _shape(upper):
    if type(upper)is not dict:raise ValueError('Exact material-use T3 required')
    fields={'tier','schema','lower_tier','materials','slots','uses'}
    if upper.get('schema')==DIRECT_SCHEMA and 'expression_insertions'in upper:
        fields.add('expression_insertions')
        placements=upper['expression_insertions']
        if type(placements)is not dict or any(type(ref)is not str or mode!='append'
                for ref,mode in placements.items()):
            raise ValueError('Explicit stable expression append placements required')
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
        if type(use)is dict and 'rhythm_lane_shares'in use:
            fields.add('rhythm_lane_shares')
            if type(use['rhythm_lane_shares'])is not dict:
                raise ValueError('Explicit lane proportions required')
            if 'rhythm_offset_q'in use:
                raise ValueError('Two active material clock authorities are forbidden')
        if type(use)is dict and 'entry_shares'in use:
            fields.add('entry_shares')
            if (upper['schema']!=DIRECT_SCHEMA or type(use['entry_shares'])is not dict
                    or 'rhythm_lane_shares'not in use
                    or set(use['entry_shares'])!=set(use['rhythm_lane_shares'])):
                raise ValueError('Joint entry/content clock requires complete matching lane owners')
        if type(use)is dict and any(k in use for k in ('degree_steps', 'degree_octaves', 'degree_strings')):
            fields.update(('degree_steps', 'degree_octaves', 'degree_strings'))
        if type(use)is dict and 'degree_member_steps'in use:fields.add('degree_member_steps')
        if type(use)is dict and 'bend_excursions'in use:
            fields.add('bend_excursions')
            if type(use['bend_excursions'])is not dict:
                raise ValueError('Explicit stable bend excursion choices required')
        if type(use)is dict and 'contact_strings'in use:
            fields.add('contact_strings')
            if type(use['contact_strings'])is not dict:
                raise ValueError('Explicit existing physical contact choices required')
            if use['contact_strings'] and use.get('degree_strings'):
                raise ValueError('Two active physical contact authorities are forbidden')
        if type(use)is dict and 'subdivision_factors'in use:
            fields.add('subdivision_factors')
            factors=use['subdivision_factors']
            if type(factors)is not dict or any(type(k)is not str or type(v)is not int or v<1 or v&(v-1) for k,v in factors.items()):
                raise ValueError('Explicit power-of-two reattack factors required')
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
        if set(use.get('subdivision_factors',{}))-{g['id'] for g in definition['lower_tier']['coattacks']}:
            raise ValueError('Subdivision must name stable complete material coattacks')
        from material_approaches import SCHEMA as approach_schema
        if definition['schema']==approach_schema:
            if upper['schema']not in (APPROACH_SCHEMA,DIRECT_SCHEMA,RHYTHM_SCHEMA) or use.get('approach_mode')not in ('original','flip'):
                raise ValueError('Each approach use needs its own explicit direction choice')
        elif 'approach_mode'in use:raise ValueError('An ordinary material has no approach choice')
        from material_degree_paths import SCHEMA as degree_schema, expand as expand_degrees
        if definition['schema'] == degree_schema:
            if any(k not in use for k in ('degree_steps', 'degree_octaves', 'degree_strings')):
                raise ValueError('Each degree-path use needs explicit movement and octave choices')
            expand_degrees(definition, use['degree_steps'], use['degree_octaves'],use.get('degree_member_steps'))
            if type(use['degree_strings']) is not dict:
                raise ValueError('Explicit per-occurrence string choices required')
        elif any(k in use for k in ('degree_steps', 'degree_octaves', 'degree_strings','degree_member_steps')):
            raise ValueError('An ordinary material has no degree-path choice')
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


def resolved_definition(definition,use,*,parent=None,slot=None):
    """Resolve current choices through one clock owner before placement."""
    from material_approaches import SCHEMA as approach_schema, expand as expand_approach
    solved=expand_approach(definition,use['approach_mode'])if definition['schema']==approach_schema else definition
    from material_degree_paths import SCHEMA as degree_schema, expand as expand_degrees
    if definition['schema']==degree_schema:
        solved=expand_degrees(definition,use['degree_steps'],use['degree_octaves'],use.get('degree_member_steps'))
    if use.get('bend_excursions'):
        from material_bend_excursions import resolve, parent_ties, check_targets
        if slot is None:raise ValueError('Bend choices require explicit current placement')
        _,event,_=_maps(definition,slot)
        solved=resolve(solved,use['bend_excursions'],tied_refs=parent_ties(definition,parent,event))
        check_targets(definition,solved,use['bend_excursions'])
    if 'rhythm_offset_q'in use and 'rhythm_lane_shares'in use:
        raise ValueError('Two active material clock authorities are forbidden')
    if 'entry_shares'in use:
        # Entry and content proportions must solve notation together. Their
        # normalized full-bar intermediate need not itself be notatable.
        return solved
    if 'rhythm_offset_q'in use or 'rhythm_lane_shares'in use:
        if parent is not None:solved=material.rhythm_context(solved,parent)
        if 'rhythm_lane_shares'in use:
            from material_slot_clock import solve
            solved,_=solve(solved,use['rhythm_lane_shares'])
        else:
            from material_rhythm_displacement import solve
            solved,_=solve(solved,use['rhythm_offset_q'])
    return solved


def place(definition,slot,use,*,parent=None):
    """Resolve one distinct use. The immutable definition is never rewritten."""
    if definition.get('external_pitch_refs') and definition['scope']!=slot['scope']:
        raise ValueError('Material relocation needs explicit external movement correspondence')
    if definition.get('unresolved_execution_locks') and definition['scope']!=slot['scope']:
        raise ValueError('Unresolved execution relocation requires explicit context correspondence')
    if parent is not None:
        foreign=material.expression_rows(parent);foreign_ids={r['id']for r in foreign}
        if any(row['id']in foreign_ids for row in definition['lower_tier']['source_structure']):
            raise ValueError('Stored material duplicates an existing expression owner')
        if definition['scope']!=slot['scope'] and any(material._owns(row['id'],scope)for row in foreign
               for scope in (definition['scope'],slot['scope'])):
            raise ValueError('Material relocation would readdress existing expression owners')
    from material_degree_paths import SCHEMA as degree_schema
    solved=resolved_definition(definition,use,parent=parent,slot=slot)
    source=material.expand(solved);fact,event,delta=_maps(definition,slot)
    if definition['schema'] == degree_schema:
        _degree_strings(source, definition, use['degree_strings'])
    if 'contact_strings'in use:
        _write_strings(source,use['contact_strings'],
            set(_contact_owners(source)))
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


def realize_pair(upper, *, with_projection=False):
    """Return the restored parent (T2 or legacy cell T3), T1 and identities."""
    _shape(upper);pieces=[];contracts=[];ledger=[]
    joint_entry=any('entry_shares'in use for use in upper['uses'])
    projection=dict(beats={},events={},spans={})
    for use in upper['uses']:
        piece,records,identities=place(upper['materials'][use['material_ref']],upper['slots'][use['slot_ref']],use,
                                     parent=upper['lower_tier'])
        pieces.append(piece);contracts.append(records);ledger.extend(identities)
    if len({r['current_address']for r in ledger})!=len(ledger):raise ValueError('Overlapping active material uses')
    restored=material.restore_fragments(upper['lower_tier'],pieces)
    _resolve_expression_insertions(upper,restored)
    if upper['schema']==DIRECT_SCHEMA:
        from connected_tier2 import realize
        from melodic_movement_ownership import SLOT,_shape as movement_shape,retime_from_parent
        if SLOT in restored['owned_parameters']:
            _,refs,references=movement_shape(restored)
            moved=[u for u in upper['uses'] if F(u.get('rhythm_offset_q','0'))!=0 or u.get('rhythm_lane_shares')]
            permitted=[r for r in refs+references if any(material._event(r,upper['slots'][u['slot_ref']]['scope']) for u in moved)]
            if permitted:
                original_pieces=[]
                for use in upper['uses']:
                    base=deepcopy(use);base.pop('rhythm_offset_q',None);base.pop('rhythm_lane_shares',None)
                    piece,_,_=place(upper['materials'][use['material_ref']],upper['slots'][use['slot_ref']],base,parent=upper['lower_tier'])
                    original_pieces.append(piece)
                original_clock=material.restore_fragments(upper['lower_tier'],original_pieces)
                restored=retime_from_parent(original_clock,restored,permitted)
        result=restored;lower=realize(result)
    else:
        result={k:deepcopy(v)for k,v in upper.items()if k not in ('materials','slots','uses')};result['schema']=cell.TIER3_SCHEMA
        result['lower_tier']=restored
        lower=cell.reconstruct(result,{'variation':0})
    for use,piece,records in ([] if joint_entry else zip(upper['uses'],pieces,contracts)):
        definition=upper['materials'][use['material_ref']]
        material.validate_fragment_execution(piece,records,lower,
            execution_locks=definition.get('unresolved_execution_locks'),
            origin_q=definition['source_start_q'])
    from material_degree_paths import SCHEMA as degree_schema, selected_refs
    contact_documents=None
    for use in upper['uses']:
        definition=upper['materials'][use['material_ref']]
        degree_owned=definition['schema']==degree_schema
        if contact_documents is None and (degree_owned or use.get('contact_strings')):
            from source_fact_tier1 import project_documents
            contact_documents=project_documents(lower)
        if degree_owned:
            _validate_material_contacts_in_documents(upper,use['id'],contact_documents,set(selected_refs(definition)))
        if use.get('contact_strings'):
            selected={g['id']for g in definition['lower_tier']['coattacks']
                if any(m['id']in use['contact_strings']for m in g['members'])}
            _validate_material_contacts_in_documents(upper,use['id'],contact_documents,selected)
    from material_approaches import SCHEMA as approach_schema, validate_membership
    for use in upper['uses']:
        definition=upper['materials'][use['material_ref']]
        if definition['schema']==approach_schema:
            _,event,_=_maps(definition,upper['slots'][use['slot_ref']])
            validate_membership(definition,lower,event_map=event)
    if any(any(v>1 for v in u.get('subdivision_factors',{}).values()) for u in upper['uses']):
        if upper['schema']!=DIRECT_SCHEMA:
            raise ValueError('Subdivision needs explicit projection of the legacy cell owner')
        from material_subdivision import plan_maps
        projection=plan_maps(_subdivision_plans(upper,result,pieces,contracts))
        result,lower,ledger=_subdivide_result(upper,result,lower,pieces,contracts,ledger,
                                             validate_execution=not joint_entry)
    if joint_entry:
        from material_use_entry_clock import realize as entry_realize
        result,lower,ledger,projection=entry_realize(upper,result,lower,pieces,contracts,ledger,projection)
    return (result,lower,ledger,projection) if with_projection else (result,lower,ledger)


def _resolve_expression_insertions(upper,parent):
    """Resolve a saved insertion AFTER current material membership exists.

    The optional owner remains the only value authority. An append relationship
    owns its position relative to current siblings, including derived dots;
    neither their values nor an expanded container is stored in the T3.
    """
    placements=upper.get('expression_insertions',{})
    if not placements:return
    groups={g['id']:(g,field) for key,field in (
        ('optional_note_accents','note_structure'),('optional_beat_palm_mutes','beat_structure'))
        for g in parent['owned_parameters'].get(key,{}).get('groups',[])}
    for ref in placements:
        if ref not in groups or groups[ref][0]['state']['kind']!='explicit':
            raise ValueError('Expression insertion requires an existing explicit optional owner')
        group,field=groups[ref]
        group['state']['child_index']=len(group[field]['children'])


def _subdivision_fragment(piece,parent,scope):
    """Give the planner transient current optional membership, not stored notes."""
    fragment=deepcopy(piece)
    present={r['id'] for r in fragment['source_structure']}
    present.update(r['id'] for g in fragment['technique_declarations'] for r in g['structure'])
    for row in material.expression_rows(parent):
        if not material._owns(row['id'],scope) or row['id'] in present:continue
        fragment['source_structure'].append({k:deepcopy(v) for k,v in row.items() if k!='value'})
        if 'value'in row:
            fragment['source_choices'].append(dict(fact_ref=row['id'],owner='transient_expression',
                parameter=scalar_relation(row['type'],source=row['value'])))
        present.add(row['id'])
    return fragment


def _subdivision_plans(upper,parent,pieces,contracts):
    from material_subdivision import plan
    plans=[]
    for use,piece,records in zip(upper['uses'],pieces,contracts):
        counts=use.get('subdivision_factors',{})
        if not any(v>1 for v in counts.values()):continue
        slot=upper['slots'][use['slot_ref']]
        fragment=_subdivision_fragment(piece,parent,slot['scope'])
        plans.append(plan(fragment,{use['id']+':'+ref:value for ref,value in counts.items()},observed_execution=records))
    return plans


def _subdivide_result(upper,parent,lower,pieces,contracts,ledger,*,validate_execution=True):
    from material_subdivision import plan_maps
    from material_subdivision_projection import project
    from connected_tier2 import realize
    plans=_subdivision_plans(upper,parent,pieces,contracts)
    maps=plan_maps(plans)
    # A fresh attack may retain an outgoing hold: the LAST child carries that
    # written tie. Splitting an incoming continuation would break its sustained
    # identity and is separately refused. Use the existing written-tie relation.
    import backing_written_tie_constraints as ties
    import backing_pitch_ownership as backing
    def plain(model):
        core=model['musical_relationships']
        from written_tie_pitch_ownership import SCHEMA as tie_schema,expand as expand_ties
        if core.get('schema')==tie_schema:return expand_ties(core)
        return backing.expand(core) if core.get('schema')in backing.SCHEMAS else core
    selected=[r for r,children in maps['events'].items() if len(children)>1]
    before_ties=ties.from_tier1(plain(parent),lower,selected)
    if any(edge['destination_ref']in selected for edge in before_ties['relations']):
        raise ValueError('SUBDIVISION_BLOCKED: incoming written tie needs a different reattack intention')
    result=project(parent,plans)
    changed=realize(result)
    # Existing execution contracts use current coordinates. Project UNSPLIT
    # endpoints and verify against the new score; split endpoints were refused
    # by the planner rather than guessed to mean an attack or final release.
    from material_subdivision_projection import _rewrite,BEAT
    def mapped_fact(ref):
        match=BEAT.fullmatch(ref)
        base=match[1]+match[2] if match else None
        return maps['beats'][base][0]+ref[len(base):] if base in maps['beats'] else ref
    def mapped_event(ref):return maps['events'].get(ref,[ref])[0]
    projected_selected=[child for ref in selected for child in maps['events'][ref]]
    actual_ties=ties.from_tier1(plain(result),changed,projected_selected)
    expected_ties=[ties.relation(dict(origin=maps['events'].get(edge['origin_ref'],[edge['origin_ref']])[-1],
        destination=mapped_event(edge['destination_ref']),kind=edge['kind'])) for edge in before_ties['relations']]
    expected_ties.sort(key=lambda r:(ties.address(r['destination_ref']),ties.address(r['origin_ref'])))
    if actual_ties['relations']!=expected_ties:
        raise ValueError('SUBDIVISION_CHANGED_WRITTEN_TIE: final child must retain the original outgoing hold')
    for use,piece,records in ([] if not validate_execution else zip(upper['uses'],pieces,contracts)):
        definition=upper['materials'][use['material_ref']]
        guard=definition.get('unresolved_execution_locks')
        if not set(piece['realization_order'])&set(maps['events']) and guard is None:continue
        projected=dict(realization_order=[r for old in piece['realization_order'] for r in maps['events'].get(old,[old])],
            physical_positions=[dict(occurrence_ref=r) for p in piece['physical_positions']
                                for r in maps['events'].get(p['occurrence_ref'],[p['occurrence_ref']])])
        expected=[]
        for record in records:
            current=_rewrite(record,mapped_fact,mapped_event)
            current['id']=execution.identity(current);expected.append(current)
        identities=None;facts=None
        if guard is not None:
            nodes=execution._snapshot(execution.encoded(changed))['nodes']
            identities={child:(old if i==0 else old+'@subdivision:'+str(i)+'/'+str(len(children)))
                for old,children in maps['events'].items() for i,child in enumerate(children) if child in nodes}
            facts={mapped_fact(record['source_fact_ref']):record['source_fact_ref']
                   for record in records if record['source_fact_ref'] is not None}
        material.validate_fragment_execution(projected,expected,changed,execution_locks=guard,
            identity_map=identities,fact_identity_map=facts,origin_q=definition['source_start_q'])
    identities={row['current_address']:row for row in ledger}; additions={}
    for planned in plans:
        for child in planned['event_map']:
            original=identities[child['parent_occurrence']]
            row=deepcopy(original);fraction=child['relative_parent_offset']
            if fraction!='0':row['identity']+='@subdivision:'+fraction
            row['current_address']=child['current_address']
            additions.setdefault(child['parent_occurrence'],[]).append(row)
    mapped=[child for row in ledger for child in additions.get(row['current_address'],[row])]
    if len({r['identity'] for r in mapped})!=len(mapped) or len({r['current_address'] for r in mapped})!=len(mapped):
        raise ValueError('Subdivision lost stable identity or aliased current addresses')
    return result,changed,mapped


def subdivision_candidate(upper,requests,*,percent=100):
    """Halve and reattack the CURRENT children of every named parent.

    requests maps use IDs to explicitly selected stable coattack IDs. Percentage
    targets are checked over the complete selected CURRENT attack denominator.
    No partial output is committed if the requested count cannot be realized.
    """
    if type(percent)is not int or percent not in (0,50,100) or type(requests)is not dict:
        raise ValueError('Explicit subdivision request and 0/50/100 target required')
    _shape(upper);out=deepcopy(upper);units=[]
    lookup={u['id']:u for u in out['uses']}
    for use_id,refs in requests.items():
        if use_id not in lookup or type(refs)is not list or len(refs)!=len(set(refs)) or not refs:
            raise ValueError('Unique selected coattacks in existing uses required')
        use=lookup[use_id];allowed={g['id'] for g in out['materials'][use['material_ref']]['lower_tier']['coattacks']}
        if set(refs)-allowed:raise ValueError('Unknown subdivision coattack')
        for ref in refs:units.append((use,ref,use.get('subdivision_factors',{}).get(ref,1)))
    denominator=sum(factor for _,_,factor in units)
    if not denominator:raise ValueError('Empty subdivision scope is not applicable')
    target=(denominator*percent+50)//100
    # Exact subset sum, preserving the frozen request order. Whole-parent
    # consequences remain indivisible; no rounding away blocked children.
    reachable={0:[]}
    for i,(_,_,factor) in enumerate(units):
        for count,selected in list(reachable.items()):
            if count+factor<=target and count+factor not in reachable:reachable[count+factor]=selected+[i]
    if target not in reachable:raise ValueError('Subdivision target conflicts with indivisible current children')
    for i in reachable[target]:
        use,ref,factor=units[i];use.setdefault('subdivision_factors',{})[ref]=factor*2
    _,after,after_ledger=realize_pair(out)
    _,before,before_ledger=realize_pair(upper) if out!=upper else (None,after,after_ledger)
    measured=_measure_subdivision(upper,requests,before,before_ledger,after,after_ledger)
    if measured['current_attacks']!=denominator or measured['changed_current_attacks']!=target:
        raise ValueError('Final subdivision output misses the frozen change target')
    if measured['original_onsets_moved'] or measured['added_attacks']!=target:
        raise ValueError('Subdivision changed parent placement or lost child attacks')
    return out,dict(requested_percent=percent,unit='complete_coattack',**measured,changed=out!=upper)


def _measure_subdivision(upper,requests,before,before_ledger,after,after_ledger):
    """Read actual reconstructed durations against stable CURRENT identities."""
    roots=[];note_roots=[]
    for use in upper['uses']:
        selected=set(requests.get(use['id'],[]))
        definition=upper['materials'][use['material_ref']]
        for group in definition['lower_tier']['coattacks']:
            if group['id']in selected:
                roots.append(use['id']+'/'+group['members'][0]['id'])
                note_roots.extend(use['id']+'/'+m['id'] for m in group['members'])
    roots=set(roots);note_roots=set(note_roots)
    def state(t1,ledger):
        from run_reversible_tier_qa import extract_documents
        from source_fact_tier1 import project_documents
        events={e['id']:e for e in extract_documents(project_documents(t1))['events']}
        return {row['identity']:events[row['current_address']] for row in ledger}
    before_state=state(before,before_ledger);after_state=state(after,after_ledger)
    def belongs(identity,selection):return identity in selection or identity.split('@subdivision:',1)[0]in selection
    old={k:v for k,v in before_state.items() if belongs(k,roots)}
    new={k:v for k,v in after_state.items() if belongs(k,roots)}
    if not set(old)<=set(new):raise ValueError('Subdivision lost an existing logical child')
    changed=sum(F(old[k]['duration_q'])!=F(new[k]['duration_q']) for k in old)
    moved=sum(F(old[k]['onset_q'])!=F(new[k]['onset_q']) for k in old)
    old_notes={k:v for k,v in before_state.items() if belongs(k,note_roots)}
    new_notes={k:v for k,v in after_state.items() if belongs(k,note_roots)}
    if not set(old_notes)<=set(new_notes):raise ValueError('Subdivision lost an existing member identity')
    return dict(current_attacks=len(old),changed_current_attacks=changed,
                added_attacks=len(new)-len(old),original_onsets_moved=moved,
                current_note_attacks=len(old_notes),
                changed_note_durations=sum(F(old_notes[k]['duration_q'])!=F(new_notes[k]['duration_q']) for k in old_notes),
                added_note_attacks=len(new_notes)-len(old_notes))


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
    current,_,_,projection=realize_pair(upper,with_projection=True);realize(changed_t2)
    expected=deepcopy(current);out=deepcopy(upper)
    old=current['owned_parameters'];new=changed_t2['owned_parameters']
    target=out['lower_tier']['owned_parameters']
    placements=deepcopy(out.get('expression_insertions',{}))
    beats=projection['beats']
    from material_subdivision_projection import BEAT
    def descendants(ref):
        match=BEAT.fullmatch(ref);base=match[1]+match[2] if match else None
        return [child+ref[len(base):] for child in beats[base]] if base in beats else [ref]
    for key in ('optional_note_accents','optional_beat_palm_mutes'):
        if key not in old:continue
        before={g['id']:g for g in old[key]['groups']};after={g['id']:g for g in new.get(key,{}).get('groups',[])}
        saved={g['id']:g for g in target[key]['groups']}
        if set(before)!=set(after):raise ValueError('Expression packing cannot readdress owners')
        prefix,field=('accent-slot:','note_structure') if key=='optional_note_accents' else ('palm-mute-slot:','beat_structure')
        mapped=set()
        for group in saved.values():
            children=[prefix+ref for ref in descendants(group[field]['id'])]
            if not set(children)<=set(after) or mapped&set(children):raise ValueError('Expression packing lost child ownership')
            states=[after[ref]['state'] for ref in children]
            values=[{k:v for k,v in state.items() if k!='child_index'} for state in states]
            if any(value!=values[0] for value in values):
                raise ValueError('INDEPENDENT_CHILD_EXPRESSION_OWNER_REQUIRED')
            state=deepcopy(values[0])
            if state['kind']=='absent':
                placements.pop(group['id'],None)
            elif group['state']['kind']=='explicit' and all(
                    before[ref]['state']['kind']=='explicit'
                    and after[ref]['state']['child_index']==before[ref]['state']['child_index']
                    for ref in children):
                # A value edit retains its existing original/relative position.
                state['child_index']=group['state']['child_index']
            elif all(after[ref]['state']['child_index']==len(after[ref][field]['children'])
                     for ref in children):
                # The current index is NOT an index into the sparse parent.
                # Keep that parent valid, then resolve this same append intention
                # after each material realization; later children may omit text.
                state['child_index']=len(group[field]['children'])
                placements[group['id']]='append'
            else:
                raise ValueError('Unsupported expression insertion position; no sibling-order guess')
            group['state']=state;mapped.update(children)
        if mapped!=set(after):raise ValueError('Expression packing lost child ownership')
        for group in expected['owned_parameters'][key]['groups']:
            state=deepcopy(after[group['id']]['state'])
            group['state']=state
    key='observed_dynamics'
    if key in old:
        from observed_dynamics import choose,choose_relative,current_marking,RELATIVE_SCHEMA
        before={r['fact_ref']:r for r in old[key]['current']};after={r['fact_ref']:r for r in new.get(key,{}).get('current',[])}
        saved={r['fact_ref']:r for r in target[key]['current']}
        if set(before)!=set(after) or set(before)!=set(saved):raise ValueError('Expression packing cannot readdress dynamics')
        choices={ref:current_marking(new[key],ref) for ref in after}
        if new[key]['schema']==RELATIVE_SCHEMA:
            expected['owned_parameters'][key]=choose_relative(old[key],choices)
            target[key]=choose_relative(target[key],choices)
        else:
            for ref,value in choices.items():
                expected['owned_parameters'][key]=choose(expected['owned_parameters'][key],ref,value)
                target[key]=choose(target[key],ref,value)
    if expected!=changed_t2:raise ValueError('Expression packing changed a protected relationship or owner')
    if placements:out['expression_insertions']=placements
    else:out.pop('expression_insertions',None)
    if expand(out)!=changed_t2:raise ValueError('Saved expression choices conflict with material notation or owners')
    return out


def bind_written_ties(upper):
    """Attach shared sustain ownership without refitting existing definitions.

    Existing uses may own attack heads. Continuations must still reside in the
    common parent; migrating an already independently owned tail is a separate
    operation. Subdivision projects the shared edge onto the final child.
    """
    from written_tie_pitch_ownership import SCHEMA as tie_schema,lift,expand as expand_ties
    if upper.get('schema')!=DIRECT_SCHEMA:raise ValueError('Direct common material parent required')
    before,lower,_=realize_pair(upper)
    if upper['lower_tier']['musical_relationships'].get('schema')==tie_schema:return deepcopy(upper)
    unsplit=deepcopy(upper)
    for use in unsplit['uses']:use.pop('subdivision_factors',None)
    complete,unsplit_lower,_=realize_pair(unsplit)
    wrapped=deepcopy(complete)
    wrapped['musical_relationships']=lift(complete['musical_relationships'],tier1=unsplit_lower)
    tails={r['destination_ref'] for r in wrapped['musical_relationships']['relationships']}
    scopes=[s['scope'] for s in upper['slots']]
    if any(material._event(ref,scope) for ref in tails for scope in scopes):
        raise ValueError('MATERIAL_TIE_AUTHORITY_MIGRATION_REQUIRED: existing definition owns a continuation')
    out=deepcopy(upper)
    # Existing source/expression owners remain the stored parent, including
    # optional membership derived later by a use's rhythm choice. Replacing
    # that parent with today's expanded notation would apply the choice twice.
    out['lower_tier']['musical_relationships']=material._remove(wrapped,scopes)['musical_relationships']
    after,restored,_=realize_pair(out)
    comparison=deepcopy(after);comparison['musical_relationships']=expand_ties(after['musical_relationships'])
    if comparison!=before or restored!=lower:
        raise ValueError('Written sustain ownership changed existing choices or realization')
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


def lift_degree_paths(upper, use_id, *, path_refs, interpretations, evidence_ref):
    """Transfer complete material pitch paths to collection-degree relationships."""
    return lift_degree_paths_many(upper,{use_id:dict(path_refs=path_refs,
        interpretations=interpretations,evidence_ref=evidence_ref)})


def lift_degree_paths_many(upper,requests):
    """Compose disjoint degree ownership once, then verify the complete inverse."""
    from material_degree_paths import fit
    if type(requests)is not dict or not requests:raise ValueError('Explicit nonempty degree ownership requests required')
    before, lower, _ = realize_pair(upper)
    out = deepcopy(upper)
    for use_id,request in requests.items():
        if type(request)is not dict or set(request)!={'path_refs','interpretations','evidence_ref'}:
            raise ValueError('Closed path, interpretation and evidence request required')
        matches=[u for u in out['uses'] if u['id']==use_id]
        if len(matches)!=1:raise ValueError('One existing material use required')
        chosen=matches[0];ref=chosen['material_ref']
        if sum(u['material_ref']==ref for u in upper['uses'])!=1:
            raise ValueError('Refining a shared definition needs an explicit shared decision')
        out['materials'][ref]=fit(upper['materials'][ref],**request)
        chosen.update(degree_steps={},degree_octaves={},degree_strings={})
    after, realized, _ = realize_pair(out)
    if after != before or realized != lower:
        raise ValueError('Degree-path ownership changed preceding musical relationships')
    return out


def _degree_strings(fragment, definition, strings):
    """A declared contact choice changes the existing physical owner only."""
    from material_degree_paths import selected_refs
    selected = set(selected_refs(definition))
    physical = {p['occurrence_ref'] for p in fragment['physical_positions']}
    allowed = {m['id'] for g in definition['lower_tier']['coattacks']
               if g['id'] in selected for m in g['members'] if m['id'] in physical}
    _write_strings(fragment,strings,allowed)


def _contact_owners(fragment):
    """Existing pitched positions and explicitly dead string contacts.

    A dead contact owns its string without requiring a fundamental pitch or a
    fret equation. Its absent or explicit fret field stays with its current owner.
    Unknown unpitched members never become dead notes by assumption.
    """
    from material_subdivision import _field_values
    from bend_gesture_ownership import pointer
    result={p['occurrence_ref']:p['string_ref']for p in fragment['physical_positions']}
    unknown=[m['id']for g in fragment['coattacks']for m in g['members']
             if m.get('voicing_interval')is None and m['id']not in result]
    if not unknown:return result
    fields,value=_field_values(fragment)
    choices={r['fact_ref']for r in fragment['source_choices']}
    for ref in unknown:
        base=pointer(ref);dead=base+'/dead';string=base+'/string'
        if dead not in fields or value(dead)is not True:continue
        if (string not in fields or string not in choices
                or fields[string]['type']!='integer' or type(value(string))is not int
                or value(string)<0):continue
        result[ref]=string
    return result


def _write_strings(fragment,strings,allowed):
    """Update the existing string fact and pitched tuning link, never a pitch."""
    if (type(strings) is not dict or set(strings) - allowed
            or any(type(v) is not int or v < 0 for v in strings.values())):
        raise ValueError('String choices must name permitted stable physical member identities')
    choices = {r['fact_ref']: r for r in fragment['source_choices']}
    positions = {r['occurrence_ref']: r for r in fragment['physical_positions']}
    contacts = _contact_owners(fragment)
    for ref, string in strings.items():
        position = positions.get(ref)
        choice = choices.get(contacts.get(ref))
        if choice is None:
            raise ValueError('Existing string authority belongs to another relationship')
        choice['parameter'].update(normalized=str(string), negative_zero=False)
        if position is not None and 'tuning_ref' in position:
            position['tuning_ref'] = position['tuning_ref'].rsplit('/', 1)[0] + '/' + str(string)


def _degree_refinger(upper, use):
    """Solve instrument contacts; this does not choose the musical pitches."""
    from itertools import product
    from material_degree_paths import expand as expand_degrees, selected_refs
    from backing_motion_relations import physical_contacts
    from source_fact_tier1 import project_documents
    base=deepcopy(upper)
    for current_use in base['uses']:current_use.pop('subdivision_factors',None)
    docs = project_documents(reconstruct(base, {'variation': 0}))
    definition = upper['materials'][use['material_ref']]
    solved = material.expand(expand_degrees(definition, use['degree_steps'], use['degree_octaves'],use.get('degree_member_steps')))
    selected = set(selected_refs(definition)); result = {}
    _, event, _ = _maps(definition, upper['slots'][use['slot_ref']])
    for group in solved['coattacks']:
        if group['id'] not in selected:
            continue
        track = docs[f"track-{group['part_id']}.json"]
        members = [m for m in group['members'] if m.get('voicing_interval') is not None]
        pitches = [F(group['bass_register_anchor']) + F(m['voicing_interval']) for m in members]
        if any(p.denominator != 1 for p in pitches):
            raise ValueError('Whole-semitone physical realization required')
        original = []; reserved = set()
        for member in group['members']:
            _, _, bar, voice, beat, note = execution.address(event(member['id']))
            raw = track['measures'][bar-1]['voices'][voice]['beats'][beat]['notes'][note]
            if type(raw.get('string')) is not int:
                raise ValueError('Unpitched member string occupancy is unresolved; cannot relocate contacts')
            if member.get('voicing_interval') is None:
                reserved.add(raw['string'])
            else:
                original.append(raw['string'])
        contacts = [physical_contacts(int(p), track['tuning'], track.get('capo') or 0,
                    max_fret=track.get('frets')) for p in pitches]
        possible = [c for c in product(*contacts) if len({r['string'] for r in c}) == len(c)
                    and not ({r['string'] for r in c} & reserved)]
        if not possible:
            raise ValueError('No distinct-string coattack within declared instrument bounds')
        chosen = min(possible, key=lambda c: (sum(r['string'] != s for r, s in zip(c, original)),
                     sum(abs(r['string']-s) for r, s in zip(c, original)),
                     tuple(r['string'] for r in c)))
        result.update((m['id'], c['string']) for m, c in zip(members, chosen))
    return result


def _validate_degree_contacts(upper, use_id, lower):
    from material_degree_paths import selected_refs
    use = next(u for u in upper['uses'] if u['id'] == use_id)
    definition = upper['materials'][use['material_ref']]
    selected = set(selected_refs(definition))
    _validate_material_contacts(upper,use_id,lower,selected)


def _validate_material_contacts(upper,use_id,lower,selected):
    from source_fact_tier1 import project_documents
    _validate_material_contacts_in_documents(upper,use_id,project_documents(lower),selected)


def _validate_material_contacts_in_documents(upper,use_id,docs,selected):
    """Reuse only the current call's validated T1 view; every contact check remains."""
    use=next(u for u in upper['uses']if u['id']==use_id)
    definition=upper['materials'][use['material_ref']]
    physical = {p['occurrence_ref'] for p in definition['lower_tier']['physical_positions']}
    _, event, _ = _maps(definition, upper['slots'][use['slot_ref']])
    for group in definition['lower_tier']['coattacks']:
        if group['id'] not in selected:
            continue
        strings = []
        for member in group['members']:
            _, part, bar, voice, beat, note = execution.address(event(member['id']))
            track = docs[f'track-{part}.json']
            raw = track['measures'][bar-1]['voices'][voice]['beats'][beat]['notes'][note]
            if type(raw.get('string')) is int:
                if not 0<=raw['string']<len(track['tuning']):
                    raise ValueError('Contact string exceeds the declared instrument tuning')
                strings.append(raw['string'])
            if member['id'] not in physical:
                continue
            fret = F(str(raw['fret']))
            if fret.denominator != 1 or fret < 0 or ('frets' in track and fret > track['frets']):
                raise ValueError('Degree-path contact exceeds declared instrument bounds')
        if len(set(strings)) != len(strings):
            raise ValueError('Coattack members cannot occupy the same string')


def degree_path_candidate(upper, use_id, *, displacements, octaves, member_steps=None, refinger=False):
    """Change existing degree/whole-octave choices; all other owners stay intact."""
    if type(refinger) is not bool:
        raise ValueError('Explicit permission to change strings required')
    _shape(upper)
    matches = [deepcopy(u) for u in upper['uses'] if u['id'] == use_id]
    if len(matches) != 1 or 'degree_steps' not in matches[0]:
        raise ValueError('Use has no degree-path owner')
    matches[0].update(degree_steps=deepcopy(displacements), degree_octaves=deepcopy(octaves))
    if member_steps is not None:matches[0]['degree_member_steps']=deepcopy(member_steps)
    strings=None
    if refinger:
        strings={use_id:_degree_refinger(upper,matches[0])}
    request=dict(displacements=displacements,octaves=octaves)
    if member_steps is not None:request['member_steps']=member_steps
    return degree_choices_candidate(upper,{use_id:request},contact_strings=strings)


def degree_choices_candidate(upper,requests,*,contact_strings=None,bend_excursions=None):
    """One atomic pitch/contact transaction through retained material and tie owners.

    Explicit head strings close over the existing sustain equality. A tail is
    never independently re-fingered, and ordinary all-tail materials need no
    invented degree path. Saved definitions and original evidence stay intact.
    """
    _shape(upper)
    if type(requests)is not dict:raise ValueError('Explicit degree requests keyed by use identity required')
    contacts={}if contact_strings is None else contact_strings
    curves={}if bend_excursions is None else bend_excursions
    if type(contacts)is not dict:raise ValueError('Explicit physical requests keyed by use identity required')
    if type(curves)is not dict:raise ValueError('Explicit bend requests keyed by use identity required')
    indexed={u['id']:u for u in upper['uses']}
    if (set(requests)|set(contacts)|set(curves))-set(indexed):raise ValueError('Unknown requested material use')
    before,before_score,_=realize_pair(upper)
    out=deepcopy(upper);updated={u['id']:u for u in out['uses']}
    for use_id,request in requests.items():
        if (type(request)is not dict or set(request)not in
                ({'displacements','octaves'},{'displacements','octaves','member_steps'})):
            raise ValueError('Closed common degree, octave and optional member choices required')
        use=updated[use_id]
        if 'degree_steps'not in use:raise ValueError('Use has no degree-path owner')
        use.update(degree_steps=deepcopy(request['displacements']),degree_octaves=deepcopy(request['octaves']))
        if 'member_steps'in request:use['degree_member_steps']=deepcopy(request['member_steps'])
    # Pitch start and curve extent resolve together. Neither intermediate is
    # required to be a valid held target; only the complete operation commits.
    for use_id,values in curves.items():
        if type(values)is not dict:raise ValueError('Explicit stable bend occurrence mapping required')
        selected=updated[use_id]
        selected['bend_excursions']=dict(selected.get('bend_excursions',{}),**deepcopy(values))
    # Relationships use the pre-subdivision written identities. Placement maps
    # those into each use; existing subdivisions inherit the same parent contact.
    owners={}; current={}; explicit={}
    for use in upper['uses']:
        definition=upper['materials'][use['material_ref']]
        _,event,_=_maps(definition,upper['slots'][use['slot_ref']])
        for ref in _contact_owners(definition['lower_tier']):
            key=(use['id'],ref);address=event(ref)
            if address in owners:raise ValueError('Overlapping physical material owners')
            owners[address]=key;current[key]=address
    for use_id,values in contacts.items():
        if type(values)is not dict:raise ValueError('Explicit per-occurrence contact map required')
        for ref,string in values.items():
            key=(use_id,ref)
            if key not in current or type(string)is not int or string<0:
                raise ValueError('Contact requires one existing pitched/dead string owner and a nonnegative string')
            explicit[current[key]]=string
    shared=upper['lower_tier']['musical_relationships']
    from written_tie_pitch_ownership import SCHEMA as tie_schema
    rows=shared['relationships']if shared.get('schema')==tie_schema else[]
    targets={r['destination_ref']:r['origin_ref']for r in rows}
    children={}
    for destination,origin in targets.items():children.setdefault(origin,[]).append(destination)
    planned=dict(explicit)
    for address,string in explicit.items():
        head=address
        while head in targets:head=targets[head]
        if head!=address:
            if explicit.get(head)!=string:
                raise ValueError('Dependent contact must be requested through its written attack head')
            continue
        pending=[head]
        while pending:
            member=pending.pop()
            if member not in owners:raise ValueError('Written tie contact lacks an existing material physical owner')
            if member in planned and planned[member]!=string:
                raise ValueError('Conflicting contacts within one written sustain')
            planned[member]=string;pending.extend(children.get(member,[]))
    for address,string in planned.items():
        use_id,ref=owners[address];use=updated[use_id]
        # Move the old compatibility overlay instead of keeping two authorities.
        inherited=use.pop('contact_strings',{})
        if use.get('degree_strings'):
            inherited=deepcopy(use['degree_strings']);use['degree_strings']={}
        use['contact_strings']=dict(inherited,**{ref:string})
    after_t2, after, _ = realize_pair(out)
    if 'stable_pitch_preference' in before or 'stable_pitch_preference' in after_t2:
        if before.get('stable_pitch_preference')!=after_t2.get('stable_pitch_preference'):
            raise ValueError('Pitch/contact edits cannot replace the saved tonal preference')
        from stable_pitch_policy import enforce_transition
        # Both exact scores were produced by this transaction's complete
        # realize_pair calls. Reuse those results, not a cache or stale source;
        # the identical policy need not reconstruct each whole score twice.
        enforce_transition(before,before_score,after)
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
