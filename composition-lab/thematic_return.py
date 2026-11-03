"""A later scene may recall the LIVE earlier arrangement of a shared idea.

Fixed form: only the declared return's material choice is abstracted here.
Independent expression, performance details, other scenes and ending stay below.
"""
from copy import deepcopy
from fractions import Fraction as F
import random
import section_arrangements as sections
from source_observation_evidence import digest

SCHEMA='live-thematic-return/1'
POLICY='live_thematic_return'
MODES=('independent','recall')


def _shape(upper):
    if (type(upper)is not dict or set(upper)!={'tier','schema','lower_tier','relationship'}
            or upper['tier']!=5 or upper['schema']!=SCHEMA):raise ValueError('Closed live thematic return required')
    r=upper['relationship']
    if type(r)is not dict or set(r)!={'source_use','return_use','mode','independent_material_ref'}:
        raise ValueError('Explicit source, return, intention and independent choice required')
    if r['mode']not in MODES or r['source_use']==r['return_use'] or type(r['independent_material_ref'])is not int:
        raise ValueError('Distinct scenes and declared return intention required')
    lower=upper['lower_tier'];source=sections._owner(lower,r['source_use']);target=sections._owner(lower,r['return_use'])
    if set(target['allocation'])!={'use_id','expression'}:raise ValueError('T5 is the sole return material owner')
    if r['independent_material_ref']not in target['constraints']['eligible_materials']:raise ValueError('Independent return choice outside vocabulary')
    uses={u['id']:u for u in lower['lower_tier']['uses']};slots=lower['lower_tier']['slots']
    a=slots[uses[r['source_use']]['slot_ref']];b=slots[uses[r['return_use']]['slot_ref']]
    if (a['scope']['parts']!=b['scope']['parts']or a['bar_spans_q']!=b['bar_spans_q']
            or F(a['start_q'])+sum(map(F,a['bar_spans_q']))>=F(b['start_q'])):
        raise ValueError('A later matching scene with intervening music required')
    return r,source,target


def material_relation(*,source_material,independent_material,mode):
    """The same explicit dependency is checked at fit and solved at inverse."""
    if mode not in MODES:raise ValueError('Unknown return intention')
    return source_material if mode=='recall'else independent_material


def expand(upper):
    r,source,_=_shape(upper);out=deepcopy(upper['lower_tier'])
    sections._owner(out,r['return_use'])['allocation']['material_ref']=material_relation(
        source_material=source['allocation']['material_ref'],independent_material=r['independent_material_ref'],mode=r['mode'])
    sections.expand(out)
    return out


def reconstruct(upper,controls):
    if controls!={'variation':0}:raise ValueError('Explicit current-zero inverse required')
    return sections.reconstruct(expand(upper),controls)


def fit(lower,source_use,return_use):
    sections.reconstruct(lower,{'variation':0})
    source=sections._owner(lower,source_use);target=sections._owner(lower,return_use)
    if source['allocation']['material_ref']!=target['allocation']['material_ref']:
        raise ValueError('Shared source idea must be established before development')
    child=deepcopy(lower);ref=sections._owner(child,return_use)['allocation'].pop('material_ref')
    out=dict(tier=5,schema=SCHEMA,lower_tier=child,
        relationship=dict(source_use=source_use,return_use=return_use,mode='independent',independent_material_ref=ref))
    if expand(out)!=lower:raise ValueError('Return relation failed exact preceding boundary')
    return out


def candidate(upper,mode):
    before=expand(upper);r,_,_=_shape(upper)
    out=deepcopy(upper);out['relationship']['mode']=mode
    proposed=expand(out);ref=sections._owner(proposed,r['return_use'])['allocation']['material_ref']
    # Reuse scoped update checks; expression remains independently owned.
    checked=sections.candidate(before,r['return_use'],ref)
    # candidate() may normalize expression at a changed use. It must already be
    # the exact expression required by this return's own locked obligations.
    target=sections._owner(out['lower_tier'],r['return_use'])
    target['allocation']['expression']=deepcopy(sections._owner(checked,r['return_use'])['allocation']['expression'])
    if expand(out)!=checked:raise ValueError('Return changed an unrelated choice')
    reconstruct(out,{'variation':0})
    return out


def change_source(upper,material_ref):
    """An ordinary T4 choice propagates through an existing recall dependency."""
    r,_,_=_shape(upper);before=expand(upper)
    first=sections.candidate(before,r['source_use'],material_ref)
    out=deepcopy(upper)
    sections._owner(out['lower_tier'],r['source_use'])['allocation']=deepcopy(sections._owner(first,r['source_use'])['allocation'])
    if r['mode']=='recall':
        final=sections.candidate(first,r['return_use'],material_ref)
        sections._owner(out['lower_tier'],r['return_use'])['allocation']['expression']=deepcopy(sections._owner(final,r['return_use'])['allocation']['expression'])
    else:final=first
    if expand(out)!=final:raise ValueError('Shared development changed unrelated owners')
    reconstruct(out,{'variation':0})
    return out


def intervene(upper,controls):
    if (type(controls)is not dict or set(controls)!={'context_policy','return','mode','seed'}
            or controls['context_policy']!=POLICY or type(controls['return'])is not int
            or not 0<=controls['return']<=100 or controls['mode']not in MODES or type(controls['seed'])is not int):
        raise ValueError('Explicit return intention, release and seed required')
    r,_,_=_shape(upper);current=r['mode'];requested=controls['mode']
    # A nonzero request needs a feasible alternative before random release.
    # Otherwise an impossible recall can look supported when the draw keeps
    # the current independent state. Zero remains an exact current-state lock.
    requested_result=candidate(upper,requested) if controls['return']>0 else None
    release=random.Random(f'thematic-return:release:{controls["seed"]}').random()<controls['return']/100
    options=[current]if current==requested else[current,requested]
    chosen=random.Random(f'thematic-return:selection:{controls["seed"]}').choice(options)if release else current
    out=requested_result if requested_result is not None and chosen==requested else candidate(upper,chosen)
    return out,dict(policy=POLICY,released=release,release_percent=controls['return'],seed=controls['seed'],
        current=current,requested=requested,chosen=chosen,changed=digest(out)!=digest(upper),
        material_changed=expand(out)!=expand(upper))
