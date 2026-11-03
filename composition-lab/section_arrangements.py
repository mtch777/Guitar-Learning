"""Concurrent T4 material choices, using the existing allocation relationships.

Each existing choice and its obligations survives exactly. This enables distant
uses to have independent choices before T5 explicitly connects their development.
"""
from copy import deepcopy
import support_arrangement as single
import support_material_uses as uses
from source_observation_evidence import digest

SCHEMA='coordinated-section-choices/1'


def _owner(upper,use_id):
    matches=[o for o in upper['choices'] if o['allocation']['use_id']==use_id]
    if len(matches)!=1:raise ValueError('One explicit section choice required')
    return matches[0]


def _view(t3,owner):
    # The single-owner validator only reads this view. All other uses are filled.
    child=dict(t3);child['uses']=deepcopy(t3['uses'])
    use=next(r for r in child['uses'] if r['id']==owner['allocation']['use_id'])
    use.pop('material_ref');use.pop('expression')
    return dict(tier=4,schema=single.SCHEMA,lower_tier=child,
                allocation=owner['allocation'],constraints=owner['constraints'])


def expand(upper):
    if (type(upper)is not dict or set(upper)!={'tier','schema','lower_tier','choices'}
            or upper['tier']!=4 or upper['schema']!=SCHEMA
            or type(upper['choices'])is not list or not upper['choices']):
        raise ValueError('Closed concurrent T4 choices required')
    t3=deepcopy(upper['lower_tier']);seen=set()
    for owner in upper['choices']:
        if type(owner)is not dict or set(owner)!={'allocation','constraints'}:raise ValueError('Closed allocation and obligations required')
        a=owner['allocation'];uid=a.get('use_id')
        if uid in seen:raise ValueError('Two owners claim the same use')
        seen.add(uid)
        matches=[r for r in t3['uses'] if r['id']==uid]
        if len(matches)!=1 or set(matches[0])!=uses.unallocated_fields(matches[0]):raise ValueError('Sole section authority required')
        matches[0].update(material_ref=a.get('material_ref'),expression=deepcopy(a.get('expression')))
    uses._shape(t3)
    for owner in upper['choices']:single._shape(_view(t3,owner))
    return t3


def reconstruct(upper,controls):
    if controls!={'variation':0}:raise ValueError('Explicit current-zero inverse required')
    t3=expand(upper);lower=uses.reconstruct(t3,controls)
    for owner in upper['choices']:single._check_expression(_view(t3,owner),t3,lower)
    return lower


def extend(upper,material_specs,choice_specs,*,equivalent_uses=()):
    """Preserve existing T4 owners and add declared, non-overlapping choices.

    Equivalent uses may share a definition only after exact preceding-model
    equality. No weaker pitch-only test establishes that correspondence.
    """
    if upper.get('schema')==single.SCHEMA:
        t3=single.expand(upper);owners=[deepcopy({k:upper[k]for k in('allocation','constraints')})]
        before=single.reconstruct(upper,{'variation':0})
    else:
        t3=expand(upper);owners=deepcopy(upper['choices']);before=reconstruct(upper,{'variation':0})
    first_new=len(t3['materials'])
    t3=uses.extend_materials(t3,material_specs) if material_specs else deepcopy(t3)
    previous=uses.expand(t3)
    existing={o['allocation']['use_id']for o in owners}
    redundant=set()
    for uid,ref in equivalent_uses:
        if uid in existing:raise ValueError('Cannot retarget an inherited choice during extension')
        selected=next((r for r in t3['uses']if r['id']==uid),None)
        if selected is None:raise ValueError('Unknown proposed equivalent use')
        redundant.add(selected['material_ref'])
        selected['material_ref']=ref
    if uses.expand(t3)!=previous:raise ValueError('Proposed equivalent definition changes preceding musical relationships')
    _,lower,_=uses.realize_pair(t3)
    if lower!=before:raise ValueError('Extension changed current source')
    for spec in choice_specs:
        if type(spec)is not dict or set(spec)!={'use_id','eligible_materials'}:raise ValueError('Explicit choice scope required')
        uid=spec['use_id']
        if uid in existing:raise ValueError('Existing choice cannot be replaced')
        existing.add(uid);use=next((r for r in t3['uses']if r['id']==uid),None)
        if use is None:raise ValueError('Unknown section use')
        owner=dict(allocation=dict(use_id=uid,material_ref=use['material_ref'],expression=deepcopy(use['expression'])),
            constraints=dict(eligible_materials=deepcopy(spec['eligible_materials']),
                target_expression=single._target_expression(t3,uid,lower),
                outside_expression=single._outside_expression(t3,uid,lower),lower_origin=digest(t3['observations'])))
        single._shape(_view(t3,owner));owners.append(owner)
    # Exact preceding equality above establishes these aliases. Keep one
    # definition for a newly shared idea, not an unused copy of its return.
    # Existing vocabulary and every still-eligible choice remain immutable.
    referenced={u['material_ref'] for u in t3['uses']}
    referenced.update(ref for owner in owners for ref in owner['constraints']['eligible_materials'])
    removed={ref for ref in redundant if ref>=first_new and ref not in referenced}
    retained=[i for i in range(len(t3['materials'])) if i not in removed]
    mapping={old:new for new,old in enumerate(retained)}
    t3['materials']=[t3['materials'][i] for i in retained]
    for use in t3['uses']:use['material_ref']=mapping[use['material_ref']]
    for owner in owners:
        owner['allocation']['material_ref']=mapping[owner['allocation']['material_ref']]
        owner['constraints']['eligible_materials']=[mapping[r] for r in owner['constraints']['eligible_materials']]
    child=deepcopy(t3)
    for owner in owners:
        use=next(r for r in child['uses']if r['id']==owner['allocation']['use_id'])
        if (use['material_ref'],use['expression'])!=(owner['allocation']['material_ref'],owner['allocation']['expression']):
            raise ValueError('Inherited choice changed during extension')
        use.pop('material_ref');use.pop('expression')
    result=dict(tier=4,schema=SCHEMA,lower_tier=child,choices=owners)
    if expand(result)!=t3:raise ValueError('Section lift failed exact preceding boundary')
    for owner in owners:single._check_expression(_view(t3,owner),t3,lower)
    return result


def candidate(upper,use_id,material_ref):
    t3=expand(upper);owner=_owner(upper,use_id)
    view=_view(t3,owner)
    chosen=single.candidate(view,material_ref)
    out=deepcopy(upper);_owner(out,use_id)['allocation']=deepcopy(chosen['allocation'])
    # Other owners' inherited expression/execution obligations also remain active.
    reconstruct(out,{'variation':0})
    return out


def intervene(upper,use_id,controls):
    t3=expand(upper);owner=_owner(upper,use_id)
    chosen,report=single.intervene(_view(t3,owner),controls)
    out=deepcopy(upper);_owner(out,use_id)['allocation']=deepcopy(chosen['allocation'])
    reconstruct(out,{'variation':0})
    report=dict(report,use_id=use_id,changed=out!=upper)
    return out,report
