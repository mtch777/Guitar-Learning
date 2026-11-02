"""One executed bend: start + relative trajectory = arrival.

The current start OR current arrival is authoritative, never both. An excursion
can be owned or depend on an earlier explicitly selected source gesture. This
does not infer a preferred note, chord root, emotional intent or bend timing.
"""
from copy import deepcopy
from fractions import Fraction as F
import random

import backing_pitch_ownership as backing
import backing_written_tie_constraints as ties
import backing_execution_constraints as execution
import group_rhythm_relations as rhythm
import musical_tier2 as music
from source_observation_evidence import digest, validate_origin, assert_only_parameter_changes

SLOT = 'bend_gesture'
SCHEMA = 'start-arrival-bend-gesture/1'
POLICY = 'source_bend_excursion'


def relation(*, extent, frame, frame_pitch=None, base=None):
    """Same additive equation, with either the pitch or its frame supplied."""
    extent = music.fraction(extent)
    if extent <= 0 or frame not in ('start', 'arrival'):
        raise ValueError('Positive excursion and explicit start/arrival frame required')
    if (base is None) == (frame_pitch is None):
        raise ValueError('Exactly one side of the pitch relationship required')
    offset = extent if frame == 'arrival' else F(0)
    if base is None:
        base = music.fraction(frame_pitch) - offset
    else:
        base = music.fraction(base)
        frame_pitch = str(base + offset)
    return dict(base=str(base), arrival=str(base + extent), frame_pitch=frame_pitch)


def pointer(ref):
    _, part, bar, voice, beat, note = backing.address(ref)
    return f'track-{part}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}/notes/{note}'


def _body(core):
    if core.get('schema') in backing.SCHEMAS:
        return backing._body(core['core'])
    return backing._body(core)


def _normal(core):
    return backing._normal(backing.expand(core) if core.get('schema') in backing.SCHEMAS else core)


def _group(upper, ref):
    rows = [g for g in upper['owned_parameters']['technique_declarations']['groups']
            if g['source_fact_ref'] == pointer(ref) + '/bend']
    if len(rows) != 1 or rows[0]['field'] != 'bend':
        raise ValueError('One explicit bend declaration required')
    return rows[0]


def _curve(group, *, hold=False):
    """Read exact declared heights and normalized source time, not played pitch."""
    prefix = group['source_fact_ref']
    values = {p['fact_ref']: p['parameter'].get('normalized') for p in group['parameters']}
    shapes = {r['id']: r for r in group['structure']}
    point_root = shapes.get(prefix + '/points')
    if not point_root or point_root['type'] != 'array':
        raise ValueError('Explicit bend point array required')
    points = []
    for point in point_root['children']:
        time = point + ('/precisePosition' if point + '/precisePosition' in values else '/position')
        height = point + '/tone'
        if values.get(time) is None or values.get(height) is None:
            raise ValueError('Numerical bend time and height required')
        points.append((music.fraction(values[time]), music.fraction(values[height])))
    if len(points) < 2 or points[0][0] != 0 or points[-1][0] != 1:
        raise ValueError('Full normalized bend duration required')
    peak = points[-1][1]
    if peak <= 0 or any(x <= a or y < b for (a,b),(x,y) in zip(points,points[1:])):
        raise ValueError('Monotonic rise or constant hold required')
    if hold:
        if any(y != peak for x,y in points):
            raise ValueError('Tied continuation must hold the same plateau')
    elif points[0][1] != 0 or not any(y == peak and x < 1 for x,y in points):
        raise ValueError('Unbent start and a declared arrival hold required')
    if prefix + '/tone' in values and music.fraction(values[prefix + '/tone']) != peak:
        raise ValueError('Bend extent declaration contradicts its curve')
    return peak, points


def _context(upper, lower):
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    docs=project_documents(lower)
    normal = _normal(upper['musical_relationships'])
    nodes,true_ids=ties.context(normal,extract_documents(docs)['tie_notation'])
    return docs,nodes,true_ids


def _chain(upper, origin_ref, context):
    docs,nodes,true_ids=context
    scope = ties.build(nodes,true_ids,[origin_ref])
    links = scope['relations']
    if len(links) != 1 or links[0]['origin_ref'] != origin_ref:
        raise ValueError('One independent bend origin and adjacent tied hold required')
    refs = [origin_ref, links[0]['destination_ref']]
    full = ties.build(nodes,true_ids,refs)
    if len(full['relations']) != 1:
        raise ValueError('Complete simple tie closure required')
    oa, ha = map(backing.address, refs)
    if oa[:4] != ha[:4] or ha[4] != oa[4] + 1:
        raise ValueError('Adjacent same-bar/voice tied hold required')
    notes = []
    for ref in refs:
        _,p,b,v,i,n = backing.address(ref)
        beat = docs[f'track-{p}.json']['measures'][b-1]['voices'][v]['beats'][i]
        note = beat['notes'][n]
        if note.get('dead') or note.get('rest') or any(k in note for k in ('slide','hp','harmonic','trill','grace')):
            raise ValueError('Overlapping execution needs its own complete permission')
        notes.append(note)
    extent, _ = _curve(_group(upper, origin_ref))
    if 'bend' in notes[1]:
        other, _ = _curve(_group(upper, refs[1]), hold=True)
        if other != extent:
            raise ValueError('Continuation excursion differs from its origin')
    return refs, full, extent


def lift(upper, *, reference_ref, target_ref):
    from connected_tier2 import realize, strip_lower
    original = strip_lower(upper)
    if SLOT in original['owned_parameters']:
        raise ValueError('An existing gesture owner must be updated, not rebuilt')
    lower = realize(original)
    validate_origin(original.get('source_origin'))
    if digest(lower) != original['source_origin']['facts_sha256']:
        raise ValueError('Original observations required when establishing a gesture')
    context=_context(original,lower)
    reference, _, observed_extent = _chain(original, reference_ref,context)
    targets, constraint, extent = _chain(original, target_ref,context)
    if set(reference) & set(targets):
        raise ValueError('Independent reference and target gestures required')
    core = original['musical_relationships']
    body = _body(core); index = backing._index(body)
    if F(index[reference_ref][0]['onset_q'])>=F(index[target_ref][0]['onset_q']):
        raise ValueError('Reference gesture must begin earlier than its target')
    if core.get('schema') in backing.SCHEMAS and set(targets) & {r['occurrence_ref'] for r in core['relationships']}:
        raise ValueError('Selected pitch already has a dependency owner')
    bases = []
    for ref in targets:
        group, member = index[ref]
        if len(group['members']) != 1 or group['timing_uncertain'] or member.get('voicing_interval') != '0':
            raise ValueError('Independent single-note bend base required for this control')
        bases.append(group['bass_register_anchor'])
    if len(set(bases)) != 1:
        raise ValueError('Tied written bases differ')
    owned = []
    for ref in targets:
        try: group = _group(original, ref)
        except ValueError:
            if ref == target_ref: raise
            continue
        for i,p in enumerate(group['parameters']):
            if p['fact_ref'].endswith('/tone'):
                owned.append(dict(group_ref=group['id'], parameter_index=i, fact_ref=p['fact_ref'],
                    unit=p['unit'], coefficient=str(F(p['parameter']['normalized'])/extent),
                    negative_zero=p['parameter']['negative_zero']))
    result = deepcopy(original)
    for group in _body(result['musical_relationships'])['coattacks']:
        group.pop('interpretation',None)
    for field in rhythm.VIEWS: _body(result['musical_relationships']).pop(field,None)
    for ref in targets: del backing._index(_body(result['musical_relationships']))[ref][0]['bass_register_anchor']
    selected = {p['fact_ref'] for p in owned}
    for group in result['owned_parameters']['technique_declarations']['groups']:
        group['parameters'] = [p for p in group['parameters'] if p['fact_ref'] not in selected]
    result['owned_parameters'][SLOT] = dict(schema=SCHEMA, reference_refs=reference, target_refs=targets,
        observations=dict(origin=deepcopy(original['source_origin']), reference_excursion=str(observed_extent)),
        parameters=dict(frame='start', frame_pitch=bases[0], excursion=str(extent)),
        curve_amplitudes=owned, written_ties=constraint, execution=execution.build(lower,targets))
    if realize(result) != lower: raise ValueError('Bend ownership did not preserve the complete input')
    return result


def expand(upper):
    result = deepcopy(upper); owner = result['owned_parameters'].pop(SLOT)
    fields={'schema','reference_refs','target_refs','observations','parameters','curve_amplitudes','written_ties','execution'}
    if type(owner) is not dict or set(owner) != fields or owner['schema'] != SCHEMA:
        raise ValueError('Exact bend gesture ownership required')
    obs=owner['observations']; pars=owner['parameters']
    if set(obs) != {'origin','reference_excursion'} or obs['origin'] != upper.get('source_origin'):
        raise ValueError('Original observation identity changed')
    validate_origin(obs['origin'])
    if music.fraction(obs['reference_excursion'])<=0:
        raise ValueError('Historical reference excursion must be positive')
    if set(pars) != {'frame','frame_pitch','excursion'}:
        raise ValueError('Exactly one current frame and excursion required')
    source_refs, refs=owner['reference_refs'],owner['target_refs']
    if any(type(a)is not list or len(a)!=2 or len(set(a))!=2 for a in (source_refs,refs)) or set(source_refs)&set(refs):
        raise ValueError('Independent complete gesture references required')
    for ref in source_refs+refs: backing.address(ref)
    live, _ = _curve(_group(result,source_refs[0]))
    extent = str(live) if pars['excursion']=='reference_excursion' else pars['excursion']
    solved=relation(extent=extent,frame=pars['frame'],frame_pitch=pars['frame_pitch'])
    index=backing._index(_body(result['musical_relationships']))
    if F(index[source_refs[0]][0]['onset_q'])>=F(index[refs[0]][0]['onset_q']):
        raise ValueError('Reference gesture must begin earlier than its target')
    for ref in refs:
        group, member=index[ref]
        if len(group['members'])!=1 or 'bass_register_anchor' in group or member.get('voicing_interval')!='0':
            raise ValueError('Missing/duplicate bend base owner')
        group['bass_register_anchor']=solved['base']
    groups={g['id']:g for g in result['owned_parameters']['technique_declarations']['groups']}
    expected_tones={r['id'] for g in groups.values() if g['field']=='bend' and g['owner_ref']in{pointer(ref)for ref in refs}
                    for r in g['structure'] if r.get('slot')=='tone' and r['type']in('integer','float')}
    if {r.get('fact_ref')for r in owner['curve_amplitudes']}!=expected_tones:
        raise ValueError('Incomplete bend amplitude ownership')
    used=set()
    for row in sorted(owner['curve_amplitudes'], key=lambda r:(r['group_ref'],r['parameter_index'])):
        if set(row)!={'group_ref','parameter_index','fact_ref','unit','coefficient','negative_zero'} or row['fact_ref'] in used:
            raise ValueError('Exact unique curve coefficient required')
        used.add(row['fact_ref']); group=groups[row['group_ref']]
        allowed={r['id'] for r in group['structure'] if r.get('slot')=='tone' and r['type']in('integer','float')}
        if row['fact_ref']not in allowed or group['owner_ref']not in {pointer(r) for r in refs} or row['unit']!='50':
            raise ValueError('Amplitude owner escaped selected bend declarations')
        if any(p['fact_ref']==row['fact_ref']for p in group['parameters']):raise ValueError('Duplicate curve scalar owner')
        if type(row['parameter_index'])is not int or not 0<=row['parameter_index']<=len(group['parameters']):
            raise ValueError('Curve parameter order changed')
        coefficient=music.fraction(row['coefficient'])
        if not 0<=coefficient<=1 or type(row['negative_zero'])is not bool:raise ValueError('Normalized rise/hold coefficient required')
        group['parameters'].insert(row['parameter_index'],dict(fact_ref=row['fact_ref'],unit=row['unit'],
            parameter=dict(normalized=str(coefficient*F(extent)),negative_zero=row['negative_zero'])))
    if result['musical_relationships']['schema']==backing.PLAIN:
        rhythm.refresh(result['musical_relationships'])
    else:
        backing.expand(result['musical_relationships'])
    return result


def validate_execution(upper, lower):
    owner=upper['owned_parameters'][SLOT]; plain=expand(upper)
    context=_context(plain,lower)
    reference, _, _=_chain(plain,owner['reference_refs'][0],context)
    refs, scope, _=_chain(plain,owner['target_refs'][0],context)
    if reference!=owner['reference_refs'] or refs!=owner['target_refs'] or scope!=owner['written_ties']:
        raise ValueError('Saved gesture closure changed')
    execution.validate(owner['execution'],lower,refs)
    from source_fact_tier1 import project_documents
    from backing_motion_intervention import original_contact
    docs=project_documents(lower); index=backing._index(_normal(plain['musical_relationships']))
    for ref in refs:
        _,p,b,v,i,n=backing.address(ref); doc=docs[f'track-{p}.json']
        original_contact(doc,doc['measures'][b-1]['voices'][v]['beats'][i]['notes'][n],music.member_pitch(*index[ref]))


def validate_controls(controls):
    if type(controls)is not dict or set(controls)!={'context_policy','bend','intent','seed'}:
        raise ValueError('Explicit bend excursion controls required')
    if controls['context_policy']!=POLICY or controls['intent']not in ('keep_start','keep_arrival'):
        raise ValueError('Explicit start/arrival intention required')
    if type(controls['bend'])is not int or not 0<=controls['bend']<=100 or type(controls['seed'])is not int:
        raise ValueError('Bounded integer release and seed required')


from source_observation_evidence import controlled_update as _controlled_update
@_controlled_update
def intervene(upper, controls):
    from connected_tier2 import realize
    validate_controls(controls)
    before=realize(upper); current=upper['owned_parameters'][SLOT]
    result=deepcopy(upper); pars=result['owned_parameters'][SLOT]['parameters']
    released=controls['bend']==100 or controls['bend']>0 and random.Random(controls['seed']).random()<controls['bend']/100
    if released:
        expanded=expand(upper); group,member=backing._index(_body(expanded['musical_relationships']))[current['target_refs'][0]]
        base=music.member_pitch(group,member); extent,_=_curve(_group(expanded,current['target_refs'][0]))
        frame='start' if controls['intent']=='keep_start' else 'arrival'
        pars['frame_pitch']=relation(base=base,extent=str(extent),frame=frame)['frame_pitch']
        pars['frame']=frame;pars['excursion']='reference_excursion'
    prefix=('owned_parameters',SLOT,'parameters')
    assert_only_parameter_changes(upper,result,[prefix+(k,)for k in ('frame','frame_pitch','excursion')])
    after=realize(result)
    # Retaining a dependency does not grant permission to move its other end.
    # These controls release only this complete gesture's fret/amplitude facts.
    allowed={pointer(ref)+'/fret' for ref in current['target_refs']}|{r['fact_ref']for r in current['curve_amplitudes']}
    if {k:v for k,v in before.items()if k!='facts'}!={k:v for k,v in after.items()if k!='facts'} or len(before['facts'])!=len(after['facts']):
        raise ValueError('Bend control changed protected source structure')
    for old,new in zip(before['facts'],after['facts']):
        if old['id']in allowed:
            if 'value'not in old or 'value'not in new or {k:v for k,v in old.items()if k!='value'}!={k:v for k,v in new.items()if k!='value'}:
                raise ValueError('Bend control changed protected source identity or type')
        elif old!=new:
            raise ValueError('BEND_SCOPE_CONFLICT: an unselected source fact would change')
    decision=dict(released=released,changed=after!=before,relationship_changed=result!=upper,
        intent=controls['intent'],before_parameters=deepcopy(current['parameters']),after_parameters=deepcopy(pars))
    return result,decision
