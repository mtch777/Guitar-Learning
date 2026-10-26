"""Observed spacing choices under a transposition-equivariant context.

No root/function is asserted. The lowest written pitch sets the coordinate origin.
"""
from copy import deepcopy
from fractions import Fraction as F
import json


def token(v):return json.dumps(v,sort_keys=True,separators=(',',':'))


def catalog(base,documents):
    result=deepcopy(base)
    for row in result['units']:
        if row['refusal_reasons']:continue
        notes=[]
        for ref in row['member_refs']:
            _,_,part,bar,voice,beat,note=ref.split(':')
            notes.append(documents[f'track-{part}.json']['measures'][int(bar)-1]['voices'][int(voice)]['beats'][int(beat)]['notes'][int(note)])
        if any(n.get('spn') is not None for n in notes):
            row['refusal_reasons']=['SOURCE_PITCH_DECLARATION_NOT_COUPLED'];continue
        anchor=F(row['realization']['anchor']);intervals=row['realization']['intervals']
        order=sorted(range(len(intervals)),key=lambda i:(F(intervals[i])%12,F(intervals[i]),row['member_refs'][i]))
        for field in ('member_refs','fixed_output_strings','fixed_string_bases'):
            row[field]=[row[field][i] for i in order]
        row['realization']['intervals']=[intervals[i] for i in order]
        for field in ('locked_tie_members','locked_execution_members'):
            pinned=set(row[field]);row[field]=[r for r in row['member_refs'] if r in pinned]
        context=json.loads(row['dependency_context_key'])
        context['member_pitch_classes']=[str(F(v)%12) for v in row['realization']['intervals']]
        for overlap in context['overlaps']:
            if overlap[-1] is not None:overlap[-1]=str((F(overlap[-1])-anchor)%12)
        context['overlaps'].sort(key=token)
        neighbors=json.loads(row['dependency_full_context_key'])[1]
        for i,notes in enumerate(neighbors):
            if notes is not None:neighbors[i]=sorted((None if p is None else int((F(p)-anchor)%12) for p in notes),key=lambda p:-1 if p is None else p)
        row['family_context_key']=token(context)
        row['family_full_context_key']=token([context,neighbors])
    result['scope']='Bass-relative spacing and nominal pitch context; no known root, harmonic function or artist intent'
    return result


def admissible(target,donor):
    """Same p=b+r and p=tuning[string]+capo+fret, not separate pitch rules."""
    realization=dict(anchor=target['realization']['anchor'],intervals=deepcopy(donor['realization']['intervals']),strings=deepcopy(donor['fixed_output_strings']))
    original=[F(target['realization']['anchor'])+F(r) for r in target['realization']['intervals']]
    proposed=[F(realization['anchor'])+F(r) for r in realization['intervals']]
    if any(ref in target['locked_tie_members'] and a!=b for ref,a,b in zip(target['member_refs'],original,proposed)):return realization,'LOCKED_WRITTEN_TIE_ENDPOINT'
    if any(ref in target['locked_execution_members'] and a!=b for ref,a,b in zip(target['member_refs'],original,proposed)):return realization,'LOCKED_EXECUTION_DEPENDENCY'
    if any(target['source_geometry'][k]!=donor['source_geometry'][k] for k in ('instrument','tuning','capo')):return realization,'INCOMPATIBLE_INSTRUMENT_SETTINGS'
    delta=F(target['realization']['anchor'])-F(donor['realization']['anchor'])
    tuning=donor['source_geometry']['tuning'];capo=F(str(donor['source_geometry']['capo']))
    for i,(pitch,string) in enumerate(zip(proposed,realization['strings'])):
        source_pitch=F(donor['realization']['anchor'])+F(donor['realization']['intervals'][i])
        source_fret=source_pitch-F(str(tuning[string]))-capo
        fret=pitch-F(str(tuning[string]))-capo
        if fret!=source_fret+delta:raise ValueError('Physical and musical family equations conflict')
        for value,limit in ((source_fret,donor['declared_frets']),(fret,target['declared_frets'])):
            if value.denominator!=1 or value<0 or type(limit)is int and limit>0 and value>limit:return realization,'INVALID_TRANSLATED_OR_SOURCE_FRET'
        if (source_fret==0)!=(fret==0):return realization,'OPEN_STRING_STATUS_CHANGED'
    if any(new!=old and new in target['occupied_strings'] for old,new in zip(target['fixed_output_strings'],realization['strings'])):return realization,'OVERLAPPING_STRING_OCCUPIED'
    pinned=set(target['locked_tie_members'])|set(target['locked_execution_members'])
    if any(ref in pinned and a!=b for ref,a,b in zip(target['member_refs'],target['fixed_output_strings'],realization['strings'])):return realization,'LOCKED_EXECUTION_STRING'
    return realization,None


def options(catalog,target_id):
    target=next(r for r in catalog['units'] if r['id']==target_id)
    if target['refusal_reasons']:return dict(status='REFUSED_TARGET',reasons=target['refusal_reasons'],options=[])
    levels=[];rejected=[];choices={}
    original=dict(target['realization'],strings=target['fixed_output_strings'])
    for field in ('family_full_context_key','family_context_key'):
        donors=[r for r in catalog['units'] if r['id']!=target_id and not r['refusal_reasons'] and r[field]==target[field]]
        choices={}
        for donor in donors:
            value,reason=admissible(target,donor)
            if reason:
                rejected.append(dict(level=field,donor_ref=donor['id'],reason=reason,realization=value));continue
            key=token(value);choices.setdefault(key,dict(realization=value,donor_refs=[]))['donor_refs'].append(donor['id'])
        values=[choices[k] for k in sorted(choices)]
        alternative=any(c['realization']!=original for c in values)
        levels.append(dict(level=field,donor_units=len(donors),distinct_realizations=len(values),physically_feasible_realizations=len(values),has_alternative=alternative))
        if alternative:return dict(status='SUPPORTED_EMPIRICAL_ALTERNATIVES',target_ref=target_id,context_level=field,levels=levels,options=values,rejected=rejected)
    return dict(status='OBSERVED_SINGLE_REALIZATION' if values else 'NO_ELIGIBLE_ALTERNATIVE',target_ref=target_id,context_level=field,levels=levels,options=values,rejected=rejected)
