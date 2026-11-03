"""A T4 choice allocates an existing coordinated material to a timed use.

The foreground and all other uses stay owned by their existing relationships.
Only complete, geometry-compatible support material is admitted in this MVP.
"""
from copy import deepcopy
import random

import support_material_uses as uses
import musical_support_material as material
import backing_execution_constraints as execution
from local_dynamics import inventory
from source_observation_evidence import digest

SCHEMA='coordinated-support-arrangement/1'
POLICY='coordinated_support_allocation'


def _shape(upper):
    if (type(upper)is not dict or set(upper)!={'tier','schema','lower_tier','allocation','constraints'}
            or upper['tier']!=4 or upper['schema']!=SCHEMA):raise ValueError('Closed T4 support allocation required')
    a=upper['allocation'];c=upper['constraints']
    if type(a)is not dict or set(a)!={'use_id','material_ref','expression'}:raise ValueError('Closed material allocation required')
    if type(c)is not dict or set(c)!={'eligible_materials','target_expression','outside_expression','lower_origin'}:raise ValueError('Closed allocation constraints required')
    if type(c['eligible_materials'])is not list or any(type(r)is not int or not 0<=r<len(upper['lower_tier']['materials'])for r in c['eligible_materials'])or len(set(c['eligible_materials']))!=len(c['eligible_materials']):
        raise ValueError('Explicit unique admitted source material vocabulary required')
    if type(c['lower_origin'])is not str or c['lower_origin']!=digest(upper['lower_tier']['observations']):
        raise ValueError('Existing observation commitment differs')
    from local_dynamics import source_rules
    levels=source_rules()[1]
    if type(c['target_expression'])is not list or type(c['outside_expression'])is not list:raise ValueError('Explicit expression obligations required')
    seen=set()
    for row in c['target_expression']:
        if (type(row)is not dict or set(row)!={'part_id','level'}or type(row['part_id'])is not int
                or row['part_id']in seen or type(row['level'])is not str or row['level']not in levels):raise ValueError('Closed target expression obligation required')
        seen.add(row['part_id'])
    seen=set()
    for row in c['outside_expression']:
        if (type(row)is not dict or set(row)!={'occurrence_ref','level','known'}or type(row['level'])is not str
                or row['level']not in levels or type(row['known'])is not bool or row['occurrence_ref']in seen):raise ValueError('Closed inherited expression obligation required')
        execution.address(row['occurrence_ref']);seen.add(row['occurrence_ref'])
    if type(a['material_ref'])is not int or a['material_ref']not in c['eligible_materials']:raise ValueError('Material outside declared vocabulary')
    matches=[r for r in upper['lower_tier']['uses']if r['id']==a['use_id']]
    if len(matches)!=1 or set(matches[0])!=uses.unallocated_fields(matches[0]):raise ValueError('Sole T4 owner required for selected use')


def expand(upper):
    _shape(upper);out=deepcopy(upper['lower_tier']);a=upper['allocation']
    use=next(r for r in out['uses']if r['id']==a['use_id'])
    use.update(material_ref=a['material_ref'],expression=deepcopy(a['expression']))
    uses._shape(out)
    return out


def reconstruct(upper,controls):
    if controls!={'variation':0}:raise ValueError('Use explicit T4 intervention; inverse has no second musical selector')
    t3=expand(upper);lower=uses.reconstruct(t3,controls)
    _check_expression(upper,t3,lower)
    return lower


def _check_expression(upper,t3,lower):
    selected=next(r for r in t3['uses']if r['id']==upper['allocation']['use_id'])
    scope=t3['slots'][selected['slot_ref']]['scope']
    expected={r['part_id']:r['level']for r in upper['constraints']['target_expression']}
    if not set(expected)<=set(scope['parts']):raise ValueError('Expression obligation outside owned parts')
    states={r['occurrence_ref']:r for r in inventory(lower)['states']}
    for ref,row in states.items():
        part=execution.address(ref)[1]
        if material._event(ref,scope)and part in expected and (not row['known']or row['marking']!=expected[part]):
            raise ValueError('Persisted target dynamic lock differs')
    for obligation in upper['constraints']['outside_expression']:
        ref=obligation['occurrence_ref'];row=states.get(ref)
        if material._event(ref,scope)or row is None or (row['marking'],row['known'])!=(obligation['level'],obligation['known']):
            raise ValueError('Persisted outside expression dependency differs')


def _outside_expression(t3,use_id,lower):
    selected=next(r for r in t3['uses']if r['id']==use_id);scope=t3['slots'][selected['slot_ref']]['scope']
    representatives={}
    for row in inventory(lower)['states']:
        ref=row['occurrence_ref'];origin=row['origin_fact_ref']
        if not material._event(ref,scope)and material._owns(origin,scope):
            # One witness for each inherited declaration/part/voice, not a note cache.
            addr=execution.address(ref);key=(addr[1],addr[3],origin,row['marking'],row['known'])
            representatives.setdefault(key,dict(occurrence_ref=ref,level=row['marking'],known=row['known']))
    return list(representatives.values())


def _target_expression(t3,use_id,lower):
    use=next(r for r in t3['uses']if r['id']==use_id)
    scope=t3['slots'][use['slot_ref']]['scope']
    fragment,_,_=uses.place(t3['materials'][use['material_ref']],t3['slots'][use['slot_ref']],use)
    pitched={p['occurrence_ref']for p in fragment['physical_positions']}
    levels={}
    for state in inventory(lower)['states']:
        if state['occurrence_ref']not in pitched:continue
        if not state['known']:raise ValueError('Unknown target dynamics; do not invent an expression lock')
        levels.setdefault(execution.address(state['occurrence_ref'])[1],set()).add(state['marking'])
    if any(len(v)!=1 for v in levels.values()):raise ValueError('MVP requires a constant target guitar dynamic; changing envelopes remain unsupported')
    return [dict(part_id=p,level=next(iter(v)))for p,v in sorted(levels.items())]


def lift(t3,use_id,eligible_materials):
    _,lower,_=uses.realize_pair(t3)
    lower_model=deepcopy(t3);use=next((r for r in lower_model['uses']if r['id']==use_id),None)
    if use is None:raise ValueError('Existing timed use required')
    a=dict(use_id=use_id,material_ref=use.pop('material_ref'),expression=use.pop('expression'))
    result=dict(tier=4,schema=SCHEMA,lower_tier=lower_model,allocation=a,
        constraints=dict(eligible_materials=deepcopy(eligible_materials),
            target_expression=_target_expression(t3,use_id,lower),outside_expression=_outside_expression(t3,use_id,lower),lower_origin=digest(t3['observations'])))
    if expand(result)!=t3:raise ValueError('T4 zero changed current T3')
    for ref in eligible_materials:
        if type(ref)is not int or not 0<=ref<len(t3['materials']):raise ValueError('Invalid material vocabulary')
        probe=deepcopy(t3);next(r for r in probe['uses']if r['id']==use_id)['material_ref']=ref
        uses._shape(probe)
    return result


def verify_preservation(before,after,before_lower,after_lower):
    """Protect the complete existing model AND every source fact outside the use."""
    left=deepcopy(before);right=deepcopy(after)
    left['allocation']=right['allocation']=None
    if left!=right:raise ValueError('Allocation altered existing relationships or original evidence')
    t3=expand(before);selected=next(r for r in t3['uses']if r['id']==before['allocation']['use_id'])
    scope=t3['slots'][selected['slot_ref']]['scope']
    outside=lambda model:[r for r in model['facts']if not material._owns(r['id'],scope)]
    if outside(before_lower)!=outside(after_lower)or before_lower['documents']!=after_lower['documents']or before_lower['scope']!=after_lower['scope']:
        raise ValueError('Arrangement changed source facts outside its permitted material region')
    # A declaration can affect later notes without changing their source facts.
    states=lambda model:{r['occurrence_ref']:(r['marking'],r['known'])for r in inventory(model)['states']if not material._event(r['occurrence_ref'],scope)}
    if states(before_lower)!=states(after_lower):raise ValueError('Instance dynamics leaked beyond the selected region')
    expected={e['part_id']:e['level']for e in after['constraints']['target_expression']}
    for row in inventory(after_lower)['states']:
        ref=row['occurrence_ref'];part=execution.address(ref)[1]
        if material._event(ref,scope)and part in expected and (not row['known']or row['marking']!=expected[part]):
            raise ValueError('Target dynamic lock was not preserved')


def candidate(upper,material_ref):
    """Intentional allocation, independently validated; no raw-note replacement."""
    _shape(upper)
    if material_ref not in upper['constraints']['eligible_materials']:raise ValueError('Unsupported material choice')
    before=reconstruct(upper,{'variation':0});out=deepcopy(upper)
    if material_ref!=upper['allocation']['material_ref']:
        out['allocation'].update(material_ref=material_ref,expression=deepcopy(upper['constraints']['target_expression']))
    after=reconstruct(out,{'variation':0});verify_preservation(upper,out,before,after)
    return out


def intervene(upper,controls):
    if (type(controls)is not dict or set(controls)!={'context_policy','arrangement','material_ref','seed'}
            or controls['context_policy']!=POLICY or type(controls['arrangement'])is not int
            or not 0<=controls['arrangement']<=100 or type(controls['seed'])is not int
            or type(controls['material_ref'])is not int):raise ValueError('Explicit allocation/release/seed controls required')
    _shape(upper);requested=controls['material_ref'];current=upper['allocation']['material_ref']
    if requested not in upper['constraints']['eligible_materials']:raise ValueError('Unsupported material choice')
    released=random.Random(f'support-allocation:release:{controls["seed"]}').random()<controls['arrangement']/100
    options=[current]if requested==current else[current,requested]
    chosen=random.Random(f'support-allocation:selection:{controls["seed"]}').choice(options)if released else current
    out=candidate(upper,chosen)
    return out,dict(policy=POLICY,released=released,release_percent=controls['arrangement'],seed=controls['seed'],
        current_material=current,requested_material=requested,chosen_material=chosen,changed=digest(out)!=digest(upper),
        original_observations_unchanged=out['lower_tier']['observations']==upper['lower_tier']['observations'])
