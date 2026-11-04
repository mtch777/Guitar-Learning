"""Coordinated support material owned above the existing complete T2 owners.

One shared pulse partition supplies every beat, rest and coattack clock.
Equal pitch trajectories and voicings are shared, not repeated note payloads.
The lower fragment retains notation, physical choices and technique declarations.
This module does not infer instrument roles or choose an arrangement.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
from math import gcd

import musical_tier2 as music
import melodic_movement_ownership as movement
import musical_cell_development as cell
import backing_execution_constraints as execution
from group_rhythm_relations import relation as clock_relation
from group_rhythm_relations import VIEWS, refresh as refresh_views
from source_fact_tier1 import project_documents
from source_observation_evidence import digest, validate_origin

SCHEMA = 'source-musical-cell-material/1'
MATERIAL = 'coordinated-support-material/1'
ARRAYS = ('source_structure', 'source_choices', 'physical_positions',
          'technique_declarations', 'coverage', 'coattacks', 'realization_order')


def _arrays(t2):
    p=t2['owned_parameters'];body=movement._body(t2['musical_relationships'])
    coverage=t2['coverage']
    if type(coverage)is dict:
        if (set(coverage)!={'schema','fixed','rules'} or coverage['schema']!='conditional-source-ownership/1'
                or type(coverage['fixed'])is not list or type(coverage['rules'])is not list):
            raise ValueError('Exact conditional source ownership required')
        coverage=coverage['fixed']
    return dict(source_structure=t2['source_structure']['facts'],
        source_choices=p['source_choices'],physical_positions=p['physical_positions'],
        technique_declarations=p['technique_declarations']['groups'],coverage=coverage,
        coattacks=body['coattacks'],realization_order=body['realization_order'])


def expression_rows(t2):
    """Transient grammar from existing owners; never an additional authority."""
    parameters=t2['owned_parameters'];rows=[]
    if 'optional_note_accents'in parameters:
        from optional_accent_slots import realize
        rows.extend(realize(parameters['optional_note_accents']))
    if 'optional_beat_palm_mutes'in parameters:
        from optional_palm_mute_slots import realize
        rows.extend(realize(parameters['optional_beat_palm_mutes']))
    if 'observed_dynamics'in parameters:
        from observed_dynamics import realize
        rows.extend(realize(parameters['observed_dynamics'],t2.get('source_origin')))
    if len({r['id']for r in rows})!=len(rows):raise ValueError('Overlapping expression owners')
    return rows


def rhythm_context(definition,parent):
    """Supply existing beat membership to a temporary clock solve only.

    Optional mute owners remain in the parent. Their resolved containers are
    transient solve inputs; only the resulting notation child can return to
    that same owner in restore_fragments. No expression state is copied into
    stored material definitions.
    """
    model=parent['owned_parameters'].get('optional_beat_palm_mutes')
    if model is None:return definition
    from optional_palm_mute_slots import realize
    beats={r['id']:r for r in realize(model)if r['type']=='object'}
    result=deepcopy(definition);rows=result['lower_tier']['source_structure']
    existing={r['id']for r in rows}
    for slot in definition['slots']:
        ref=slot['beat_ref']
        if ref not in beats:continue
        if ref in existing:raise ValueError('Material duplicates an optional beat owner')
        rows.append(deepcopy(beats[ref]));existing.add(ref)
    return result


def _return_beat_membership(parent,fragment):
    """Return only derived dots membership to the existing optional beat owner."""
    model=parent['owned_parameters'].get('optional_beat_palm_mutes')
    if model is None:return fragment
    from optional_palm_mute_slots import expand
    from technique_observation_relations import scalar_relation
    groups={g['beat_structure']['id']:g for g in model['groups']}
    piece=deepcopy(fragment);rows=piece['source_structure']
    structure={r['id']:r for r in rows}
    choices={r['fact_ref']:r for r in piece['source_choices']}
    coverage={r['fact_ref']:r for r in piece['coverage']}
    if (len(structure)!=len(rows) or len(choices)!=len(piece['source_choices'])
            or len(coverage)!=len(piece['coverage'])):
        raise ValueError('Duplicate material notation authority')
    retained=[]
    for row in rows:
        ref=row['id']
        if ref not in groups:
            retained.append(row);continue
        group=groups[ref];prior=expand(group)[0]
        if {k:v for k,v in row.items()if k!='children'}!={k:v for k,v in prior.items()if k!='children'}:
            raise ValueError('Transient rhythm changed an existing beat owner')
        if row['children']==prior['children']:continue
        dot=ref+'/dots'
        if dot in prior['children'] or row['children']!=prior['children']+[dot]:
            raise ValueError('Rhythm may only append its declared dots child')
        leaf=structure.get(dot);choice=choices.get(dot);owner=coverage.get(dot)
        expected=dict(id=dot,document=row['document'],pointer=row['pointer']+'/dots',
                      parent=ref,slot='dots',type='integer')
        if (leaf!=expected or choice is None or set(choice)!={'fact_ref','owner','parameter'}
                or choice['owner']!='source_notation_choice'
                or owner!=dict(fact_ref=dot,owner='source_notation_choice')
                or scalar_relation('integer',parameter=choice['parameter'])not in (1,2)):
            raise ValueError('New beat membership lacks its exact dots owner')
        group['beat_structure']['children'].append(dot)
        if expand(group)[0]!=row:raise ValueError('Notation changed optional beat expression')
    piece['source_structure']=retained
    return piece


def _scope(parts, first, last):
    if (type(parts)is not list or not parts or len(set(parts))!=len(parts)
            or any(type(p)is not int or p<0 for p in parts)
            or type(first)is not int or type(last)is not int or not 1<=first<=last):
        raise ValueError('Explicit unique parts and complete positive bar range required')
    return dict(parts=deepcopy(parts),first_bar=first,last_bar=last)


def _owns(ref,scope):
    return type(ref)is str and any(ref==p or ref.startswith(p+'/') for p in (
        f'track-{part}.json#/measures/{bar-1}/voices/0/beats'
        for part in scope['parts'] for bar in range(scope['first_bar'],scope['last_bar']+1)))


def _event(ref,scope):
    _,p,b,v,_,_=execution.address(ref)
    return p in scope['parts'] and scope['first_bar']<=b<=scope['last_bar'] and v==0


def _cut(t2,scope):
    selected={}
    for field,rows in _arrays(t2).items():
        if field=='coattacks':
            chosen=[r for r in rows if r['part_id']in scope['parts'] and scope['first_bar']<=r['bar']<=scope['last_bar']]
            if any(not _event(m['id'],scope)for g in chosen for m in g['members']):
                raise ValueError('A complete coattack cannot be partly owned')
        elif field=='realization_order':chosen=[r for r in rows if _event(r,scope)]
        else:
            key='id'if field=='source_structure'else'source_fact_ref'if field=='technique_declarations'else'fact_ref'
            chosen=[r for r in rows if _owns(r[key],scope)]
        selected[field]=deepcopy(chosen)
    refs={m['id']for g in selected['coattacks']for m in g['members']}
    if refs!=set(selected['realization_order']):raise ValueError('Incomplete material event order')
    for link in t2['musical_relationships'].get('relationships',[]):
        if link['occurrence_ref']in refs or link['backing_ref']in refs:
            raise ValueError('Existing backing owner cannot be replaced by a material owner')
    active=t2['owned_parameters'].get(movement.SLOT)
    if active:
        # Pitch and contact choices stay with the existing movement owner;
        # this material may own their clock without duplicating those choices.
        members=set(movement._members(active['attacks']))
        retained=[p for p in t2['owned_parameters']['physical_positions'] if p['occurrence_ref'] in members]
        contacts={p[k] for p in retained for k in ('fact_ref','string_ref')}
        selected['physical_positions']=[p for p in selected['physical_positions'] if p['occurrence_ref'] not in members]
        for field in ('source_choices','coverage'):
            selected[field]=[r for r in selected[field] if r['fact_ref'] not in contacts]
    return selected


def _pool(rows,value):
    if value not in rows:rows.append(deepcopy(value))
    return rows.index(value)


def pitch_path(*,pitches=None,start=None,steps=None):
    """The existing signed interval equation, including a one-attack line."""
    if pitches is not None:
        if start is not None or steps is not None or not pitches:raise ValueError('One pitch path side required')
        start=pitches[0]
        steps=[music.relation(anchor=a,pitch=b)['interval']for a,b in zip(pitches,pitches[1:])]
    elif type(start)is not str or type(steps)is not list:raise ValueError('Start and signed steps required')
    result=[str(F(start))]
    for step in steps:result.append(music.relation(anchor=result[-1],interval=step)['pitch'])
    return dict(start=start,steps=deepcopy(steps),pitches=result)


def fit(t2, *, parts, first_bar, last_bar, lower=None):
    """Extract from the current preceding representation; no source/cache reads.

    Current material is not added to original observation counts. Source origin
    remains the unchanged input commitment; historical source claims need their
    independent comparison, not this constructor.
    """
    scope=_scope(parts,first_bar,last_bar);fragment=_cut(t2,scope)
    lower=movement._realize(t2)if lower is None else lower
    docs=project_documents(lower);core=movement._body(t2['musical_relationships'])
    # Complete T2 owns the source clock even where its optional normalized
    # geometry view is absent. Read the existing clock relation during fitting.
    from source_key_tier1 import extract_documents as written_context
    frames=[dict(start_q=r['start_q'],duration_q=r['span_q'])for r in written_context(docs)['measure_geometry']['frames']]
    start=F(frames[first_bar-1]['start_q'])
    spans=[F(frames[b-1]['duration_q'])for b in range(first_bar,last_bar+1)];span=sum(spans,F(0))
    slots=[];boundaries={F(0),span}
    for part in parts:
        score=docs[f'track-{part}.json']
        for bar in range(first_bar,last_bar+1):
            measure=score['measures'][bar-1];voices=measure.get('voices',[])
            if measure.get('rest') or len(voices)!=1 or voices[0].get('rest'):
                raise ValueError('Complete explicit single-voice material required')
            pos=F(frames[bar-1]['start_q'])-start;end=pos+F(frames[bar-1]['duration_q'])
            for bi,beat in enumerate(voices[0].get('beats',[])):
                d=beat.get('duration')
                if (type(d)is not list or len(d)!=2 or any(type(v)is not int or v<=0 for v in d)
                        or beat.get('graceNote')):raise ValueError('Known positive non-grace written clock required')
                duration=F(*d)*4;ref=f'track-{part}.json#/measures/{bar-1}/voices/0/beats/{bi}'
                slots.append(dict(beat_ref=ref,start=pos,end=pos+duration,fraction_scale=gcd(*d)))
                boundaries.update((pos,pos+duration));pos+=duration
            if pos!=end:raise ValueError('Material voice must fill its unchanged source frame exactly')
    ticks=sorted(boundaries)
    if ticks[0]!=0 or ticks[-1]!=span:raise ValueError('Material clock outside declared span')
    clock=clock_relation(start_q='0',span_q=str(span),durations_q=[str(b-a)for a,b in zip(ticks,ticks[1:])])
    for slot in slots:
        slot['from_pulse']=ticks.index(slot.pop('start'));slot['to_pulse']=ticks.index(slot.pop('end'))
    by_beat={r['beat_ref']:r for r in slots};notation={r['beat_ref']+f'/duration/{i}'for r in slots for i in (0,1)}
    owned_notation=set()
    for row in fragment['source_choices']:
        if row['fact_ref']in notation:
            parameter=row.pop('parameter')
            if set(parameter)!={'normalized','negative_zero'} or parameter['negative_zero']:
                raise ValueError('Unsupported duration scalar realization')
            owned_notation.add(row['fact_ref'])
    if owned_notation!=notation:raise ValueError('Every written duration must have one removable owner')
    paths=[];voicings=[];bindings=[];lanes=defaultdict(list);external=[]
    active=t2['owned_parameters'].get(movement.SLOT)
    if active:
        index=movement.backing._index(core)
        for ref in movement._members(active['attacks']):
            if _event(ref,scope):
                kind,_,_=movement._authority(index,ref,stored=True)
                external.append(dict(occurrence_ref=ref,kind=kind))
    for g in fragment['coattacks']:
        if g['timing_uncertain']:raise ValueError('Uncertain clock cannot establish material allocation')
        if 'interpretation'in g:
            if not music.same(g['interpretation'],music.interpreted(g)):
                raise ValueError('Derived interpretation conflicts with its pitch/time relationships')
            # Preserve its interface presence, never a stale pitch-derived view.
            g['interpretation']=None
        if g.get('bass_register_anchor')is not None:lanes[g['part_id']].append(g)
    path_binding={}
    for part,groups in lanes.items():
        trajectory=pitch_path(pitches=[g['bass_register_anchor']for g in groups]);trajectory.pop('pitches')
        pi=_pool(paths,trajectory)
        path_binding.update({g['id']:(pi,i)for i,g in enumerate(groups)})
    for g in fragment['coattacks']:
        members=g['members'];first=members[0]
        if len({(m['voice'],m['beat'])for m in members})!=1:raise ValueError('One complete source beat per material coattack required')
        beat=f"track-{g['part_id']}.json#/measures/{g['bar']-1}/voices/{first['voice']}/beats/{first['beat']}"
        slot=by_beat[beat];a=ticks[slot['from_pulse']];b=ticks[slot['to_pulse']]
        if F(g['onset_q'])!=start+a or any(F(m['duration_q'])!=b-a for m in members):
            raise ValueError('Written beat and coattack clocks disagree')
        shape=[m.pop('voicing_interval',None)for m in members];vi=_pool(voicings,shape)
        path,ordinal=path_binding.get(g['id'],(None,None))
        bindings.append(dict(coattack_ref=g['id'],beat_ref=beat,voicing_ref=vi,pitch_path_ref=path,attack=ordinal))
        del g['onset_q'];g.pop('bass_register_anchor',None)
        for m in members:del m['duration_q']
    refs=set(fragment['realization_order']);internal=[]
    for record in execution._snapshot(execution.encoded(lower))['records']:
        linked=set(record['member_refs'])|set(record['tied_member_refs'])
        linked.update(record[k]for k in ('origin_ref','destination_ref','candidate_destination_ref')if record[k]is not None)
        if linked&refs:
            if linked-refs:raise ValueError('Technique/tie dependency crosses material boundary')
            internal.append(record)
    result=dict(schema=MATERIAL,scope=scope,source_start_q=str(start),span_q=str(span),bar_spans_q=list(map(str,spans)),
        pulse_shares=clock['shares'],slots=slots,pitch_paths=paths,voicings=voicings,bindings=bindings,
        lower_tier=fragment,observed_execution=internal,
        provenance=dict(origin=deepcopy(t2['source_origin']),current_input_sha256=digest(t2),bindings_sha256=digest(bindings),
            meaning='Current material; no additional original observations'))
    if external:result['external_pitch_refs']=external
    validate_execution(result,lower)
    if expand(result)!=_cut(t2,scope):raise ValueError('Material inverse changed its preceding owners')
    return result


def expand(material):
    """Solve the SAME pulse, pitch and voicing relationships into their T2 owners."""
    from material_approaches import SCHEMA as approach_schema, expand as expand_approach
    if material.get('schema') == approach_schema:
        return expand(expand_approach(material))
    from material_degree_paths import SCHEMA as degree_schema, expand as expand_degrees
    if material.get('schema') == degree_schema:
        return expand(expand_degrees(material))
    fields={'schema','scope','source_start_q','span_q','bar_spans_q','pulse_shares','slots','pitch_paths','voicings',
            'bindings','lower_tier','observed_execution','provenance'}
    if type(material)is dict and 'external_pitch_refs' in material:fields.add('external_pitch_refs')
    if type(material)is not dict or set(material)!=fields or material['schema']!=MATERIAL:
        raise ValueError('Exact material interface required; hidden payload forbidden')
    scope=material['scope']
    if type(scope)is not dict or set(scope)!={'parts','first_bar','last_bar'}:raise ValueError('Closed material scope required')
    _scope(scope['parts'],scope['first_bar'],scope['last_bar'])
    provenance=material['provenance']
    if (type(provenance)is not dict or set(provenance)!={'origin','current_input_sha256','bindings_sha256','meaning'}
            or provenance['meaning']!='Current material; no additional original observations'
            or type(provenance['current_input_sha256'])is not str or len(provenance['current_input_sha256'])!=64
            or any(c not in '0123456789abcdef'for c in provenance['current_input_sha256'])
            or provenance['bindings_sha256']!=digest(material['bindings'])):
        raise ValueError('Closed material provenance and unchanged binding identities required')
    validate_origin(provenance['origin'])
    if type(material['lower_tier'])is not dict or set(material['lower_tier'])!=set(ARRAYS) or any(type(v)is not list for v in material['lower_tier'].values()):
        raise ValueError('Only declared lower-owner arrays may be stored')
    external={}
    for row in material.get('external_pitch_refs',[]):
        if (type(row)is not dict or set(row)!={'occurrence_ref','kind'}
                or row['kind'] not in ('singleton','upper_member')
                or row['occurrence_ref'] in external or not _event(row['occurrence_ref'],scope)):
            raise ValueError('Unique existing external movement references required')
        external[row['occurrence_ref']]=row['kind']
    if set(external)-set(material['lower_tier']['realization_order']):
        raise ValueError('Dangling external pitch reference')
    if type(material['pitch_paths'])is not list or type(material['voicings'])is not list or type(material['bindings'])is not list:
        raise ValueError('Explicit relationship lists required')
    for path in material['pitch_paths']:
        if (type(path)is not dict or set(path)!={'start','steps'} or type(path['start'])is not str
                or type(path['steps'])is not list or any(type(s)is not str for s in path['steps'])):
            raise ValueError('Stored pitch paths contain start/steps only; extraction pitches forbidden')
        if any(str(F(v))!=v for v in [path['start']]+path['steps']):raise ValueError('Canonical signed pitch coordinates required')
    for voicing in material['voicings']:
        if type(voicing)is not list or not voicing or any(v is not None and(type(v)is not str or str(F(v))!=v)for v in voicing):
            raise ValueError('Canonical complete voicing required')
    for binding in material['bindings']:
        if (type(binding)is not dict or set(binding)!={'coattack_ref','beat_ref','voicing_ref','pitch_path_ref','attack'}
                or type(binding['coattack_ref'])is not str or type(binding['beat_ref'])is not str
                or type(binding['voicing_ref'])is not int or not 0<=binding['voicing_ref']<len(material['voicings'])):
            raise ValueError('Closed typed coattack binding required')
        p,i=binding['pitch_path_ref'],binding['attack']
        if (p is None and i is not None)or(p is not None and(type(p)is not int or not 0<=p<len(material['pitch_paths'])or type(i)is not int or not 0<=i<=len(material['pitch_paths'][p]['steps']))):
            raise ValueError('Invalid pitch-path occurrence binding')
    if ({b['pitch_path_ref']for b in material['bindings']if b['pitch_path_ref']is not None}!=set(range(len(material['pitch_paths'])))
            or {b['voicing_ref']for b in material['bindings']}!=set(range(len(material['voicings'])))):
        raise ValueError('Unbound material pitch/voicing payload forbidden')
    if sum(map(F,material['bar_spans_q']),F(0))!=F(material['span_q']):raise ValueError('Material frame/span conflict')
    solved=clock_relation(start_q='0',span_q=material['span_q'],shares=material['pulse_shares'])
    ticks=list(map(F,solved['onsets_q']))+[F(material['span_q'])]
    result=deepcopy(material['lower_tier']);slots={};values={}
    for slot in material['slots']:
        if set(slot)!={'beat_ref','fraction_scale','from_pulse','to_pulse'}:raise ValueError('Unknown material slot')
        a,b=slot['from_pulse'],slot['to_pulse'];ref=slot['beat_ref'];scale=slot['fraction_scale']
        if (type(a)is not int or type(b)is not int or not 0<=a<b<len(ticks)or ref in slots
                or type(scale)is not int or scale<=0 or not _owns(ref,scope)):
            raise ValueError('Invalid/duplicate pulse or beat binding')
        length=ticks[b]-ticks[a];whole=length/4;slots[ref]=(ticks[a],length)
        values[ref+'/duration/0']=whole.numerator*scale;values[ref+'/duration/1']=whole.denominator*scale
    seen=set()
    for row in result['source_choices']:
        ref=row['fact_ref']
        if ref in values:
            if 'parameter'in row:raise ValueError('Duplicate lower timing authority')
            row['parameter']=dict(normalized=str(values[ref]),negative_zero=False);seen.add(ref)
    if seen!=set(values):raise ValueError('Lost duration owner')
    paths=[pitch_path(**p)['pitches']for p in material['pitch_paths']]
    bindings={b['coattack_ref']:b for b in material['bindings']}
    if len(bindings)!=len(material['bindings'])or set(bindings)!={g['id']for g in result['coattacks']}:
        raise ValueError('Complete unique coattack bindings required')
    for g in result['coattacks']:
        binding=bindings[g['id']];onset,duration=slots[binding['beat_ref']]
        if 'onset_q'in g or 'bass_register_anchor'in g:raise ValueError('Duplicate lower clock/pitch authority')
        if 'interpretation'in g and g['interpretation']is not None:
            raise ValueError('Derived interpretation must be a presence marker, not a cached payload')
        g['onset_q']=str(F(material['source_start_q'])+onset)
        path=binding['pitch_path_ref'];ordinal=binding['attack']
        singleton=any(external.get(m['id'])=='singleton' for m in g['members'])
        if singleton:
            if path is not None:raise ValueError('External singleton pitch cannot have a material pitch path')
        else:g['bass_register_anchor']=None if path is None else paths[path][ordinal]
        shape=material['voicings'][binding['voicing_ref']]
        if len(shape)!=len(g['members']):raise ValueError('Missing or added voicing member')
        for m,interval in zip(g['members'],shape):
            if 'duration_q'in m or 'voicing_interval'in m:raise ValueError('Duplicate lower hold/voicing authority')
            m['duration_q']=str(duration)
            if external.get(m['id'])=='upper_member':
                if interval is not None:raise ValueError('External member has duplicate interval authority')
            else:m['voicing_interval']=interval
            expected=f"track-{g['part_id']}.json#/measures/{m['bar']-1}/voices/{m['voice']}/beats/{m['beat']}"
            if expected!=binding['beat_ref']:raise ValueError('Coattack retargeted onto another valid beat')
        if 'interpretation'in g:
            if any(m['id'] in external for m in g['members']):
                raise ValueError('External pitch must defer derived interpretation to its owner')
            g['interpretation']=music.interpreted(g)
    return result


def validate_execution(material,lower):
    """Keep internal gesture endpoints; reject new or old crossing dependencies.

    Whole-part guard records cannot be attached unchanged to a new allocation:
    retiring another complete support material deliberately retires its gestures.
    This boundary protects the complete selected material using the SAME existing
    execution records/occupancy and affected-unknown admission predicates.
    """
    validate_fragment_execution(material['lower_tier'],material['observed_execution'],lower)


def validate_fragment_execution(fragment,observed_execution,lower):
    refs=set(fragment['realization_order']);pitched=defaultdict(list)
    for position in fragment['physical_positions']:
        ref=position['occurrence_ref'];pitched[execution.address(ref)[1]].append(ref)
    for group in pitched.values():execution.build(lower,group)
    internal=[]
    for record in execution._snapshot(execution.encoded(lower))['records']:
        touched=set(record['member_refs'])|set(record['tied_member_refs'])
        touched.update(record[k]for k in ('origin_ref','destination_ref','candidate_destination_ref')if record[k]is not None)
        if touched&refs:
            if touched-refs:raise ValueError('Technique/tie dependency crosses material boundary')
            internal.append(record)
    if sorted(internal,key=lambda r:r['id'])!=sorted(observed_execution,key=lambda r:r['id']):
        raise ValueError('MATERIAL_EXECUTION_CHANGED: original internal gesture relationships differ')


def _remove(t2,scopes):
    result=deepcopy(t2);arrays=_arrays(result)
    for scope in scopes:
        cut=_cut(result,scope)
        for field in ARRAYS:
            # Identity is the complete owned row, not a position in a new array.
            removed={digest(r)for r in cut[field]}
            arrays[field][:]=[r for r in arrays[field]if digest(r)not in removed]
    if scopes:
        core=movement._body(result['musical_relationships'])
        for name in VIEWS:
            if name in core:core[name]=None
    return result


def _restore(skeleton,materials):
    """Rejoin existing typed owners; no re-analysis/relearning of the score."""
    return restore_fragments(skeleton,[expand(m)for m in materials])


def restore_fragments(skeleton,fragments):
    """Compose resolved material instances through the existing lower owners."""
    result=deepcopy(skeleton);arrays=_arrays(result)
    for fragment in fragments:
        fragment=_return_beat_membership(result,deepcopy(fragment))
        for field in ARRAYS:arrays[field].extend(fragment[field])
    # Restore ordered source ownership using its existing container grammar.
    from technique_observation_relations import realize as effects
    rows={r['id']:r for r in arrays['source_structure']}
    if len(rows)!=len(arrays['source_structure']):raise ValueError('Overlapping material structure')
    all_rows=dict(rows)
    for row in effects(result['owned_parameters']['technique_declarations']):
        if row['id']in all_rows:raise ValueError('Duplicate technique ownership')
        all_rows[row['id']]=row
    for row in expression_rows(result):
        if row['id']in all_rows:raise ValueError('Duplicate expression ownership')
        all_rows[row['id']]=row
    order=[];seen=set()
    def visit(ref):
        if ref in seen or ref not in all_rows:raise ValueError('Broken material membership/identity')
        seen.add(ref);order.append(ref)
        for child in all_rows[ref].get('children',[]):visit(child)
    for document in result['source_structure']['documents']:visit(document['fact_ref'])
    if seen!=set(all_rows):raise ValueError('Unreachable material owner')
    rank={ref:i for i,ref in enumerate(order)}
    for field in ('source_structure','source_choices','physical_positions','technique_declarations','coverage'):
        key='id'if field=='source_structure'else'source_fact_ref'if field=='technique_declarations'else'fact_ref'
        arrays[field].sort(key=lambda r:rank[r[key]])
    arrays['coattacks'].sort(key=lambda g:(F(g['onset_q']),g['bar'],g['part_id']))
    # Coattack labels are canonical serialization coordinates. Occurrence IDs,
    # active owners and historical observation identities are NOT renumbered.
    mapping={g['id']:f'coattack:{i}'for i,g in enumerate(arrays['coattacks'])}
    if len(mapping)!=len(arrays['coattacks']):raise ValueError('Duplicate active coattack identity')
    for g in arrays['coattacks']:g['id']=mapping[g['id']]
    # Existing normalized extraction emits regular notes, THEN graces, per part.
    # Preserve that declared order; address order alone corrupts untouched grace
    # occurrences elsewhere even though all current pitches remain identical.
    durations={m['id']:F(m['duration_q'])for g in arrays['coattacks']for m in g['members']}
    def event_order(ref):
        song,part,bar,voice,beat,note=execution.address(ref)
        return song,part,durations[ref]==0,bar,voice,beat,note
    arrays['realization_order'].sort(key=event_order)
    core=movement._body(result['musical_relationships'])
    core['source_quality']['expected']=core['source_quality']['actual']=len(arrays['realization_order'])
    present=[name for name in VIEWS if name in core]
    if present:
        if fragments and any(core[name]is not None for name in present):
            raise ValueError('Owned material requires derived-view presence markers, not cached source views')
        current=refresh_views(deepcopy(core))
        for name in present:
            if core[name]is not None and not music.same(core[name],current[name]):
                raise ValueError('Derived view conflicts with current pitch/time relationships')
            core[name]=current[name]
    return result


def lift_t3(upper,specifications):
    """Add material ownership alongside the LIVE cell owner at the same tier."""
    if upper.get('schema')!=cell.TIER3_SCHEMA:raise ValueError('Current cell contract required')
    complete=cell.expand(upper);lower=cell.reconstruct(upper,{'variation':0})
    materials=[];scopes=[];claimed=set()
    for spec in specifications:
        material=fit(complete,lower=lower,**spec);scope=material['scope']
        ids={r['fact_ref']for r in material['lower_tier']['coverage']}
        if claimed&ids:raise ValueError('Material owners overlap')
        claimed.update(ids);materials.append(material);scopes.append(scope)
    result=deepcopy(upper);result['schema']=SCHEMA
    result['lower_tier']=_remove(upper['lower_tier'],scopes);result['materials']=materials
    if expand_t3(result)!=upper:raise ValueError('Material lifting changed the live preceding T3')
    return result


def expand_t3(upper):
    if (upper.get('schema')!=SCHEMA or set(upper)!={'tier','schema','lower_tier','relationship',
            'instance_attack_refs','observations','materials'}or upper['tier']!=3):
        raise ValueError('Exact composed T3 material interface required')
    result=deepcopy(upper);materials=result.pop('materials');result['schema']=cell.TIER3_SCHEMA
    result['lower_tier']=_restore(result['lower_tier'],materials)
    lower=cell.reconstruct(result,{'variation':0})
    for material in materials:validate_execution(material,lower)
    return result
