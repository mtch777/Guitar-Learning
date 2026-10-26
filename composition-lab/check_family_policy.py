"""Independent raw-source oracle for transposition-equivariant voicing choices.

Shares accepted extraction/refusal primitives with the prior source oracle, never
imports family_policy or voicing_register candidate generation.
"""
from copy import deepcopy
from fractions import Fraction as F
import json
from check_voicing_policy import _source_units, encoded


def _pc(value,anchor):
    return None if value is None else str((F(value)-anchor)%12)


def _context(value,anchor):
    if isinstance(value,list):
        context,neighbors=value
        return [_context(context,anchor),[None if row is None else sorted([None if p is None else int((F(p)-anchor)%12) for p in row],key=lambda p:-1 if p is None else p) for row in neighbors]]
    result=deepcopy(value)
    result['member_pitch_classes']=sorted([_pc(p,anchor) for p in value['member_pitch_classes']],key=lambda p:-1 if p is None else F(p))
    result['overlaps']=sorted([row[:-1]+[_pc(row[-1],anchor)]for row in value['overlaps']],key=encoded)
    return result


def normalized_units(documents):
    units,count,ties,dependencies=_source_units(documents,'joint_source_fingering')
    for row in units:
        if row['refusal_reasons']:continue
        for ref in row['member_refs']:
            # Original source addresses are supplied by the shared parser; raw
            # declaration values are checked here, outside producer admission.
            _,_,pid,bar,voice,beat,note=ref.split(':')
            source=documents['track-'+pid+'.json']['measures'][int(bar)-1]['voices'][int(voice)]['beats'][int(beat)]['notes'][int(note)]
            if source.get('spn') is not None:
                row['refusal_reasons']=sorted(set(row['refusal_reasons'])|{'SOURCE_PITCH_DECLARATION_NOT_COUPLED'})
        if row['refusal_reasons']:continue
        old=deepcopy(row);anchor=F(row['realization']['anchor']);intervals=row['realization']['intervals']
        order=sorted(range(len(intervals)),key=lambda i:(F(intervals[i])%12,F(intervals[i]),row['member_refs'][i]))
        for field in ('member_refs','fixed_output_strings','fixed_string_bases'):
            row[field]=[old[field][i]for i in order]
        row['realization']['intervals']=[intervals[i]for i in order]
        for field in ('locked_tie_members','locked_execution_members'):
            row[field]=[ref for ref in row['member_refs']if ref in old[field]]
        row['family_context_key']=encoded(_context(json.loads(old['dependency_context_key']),anchor))
        row['family_full_context_key']=encoded(_context(json.loads(old['dependency_full_context_key']),anchor))
    return units,count,ties,dependencies


def expected_rows(units):
    result=[];keys=('family_full_context_key','family_context_key')
    for target in units:
        if target['refusal_reasons']:continue
        levels=[];rejected=[];options=[];status=None
        for field in keys:
            donors=[d for d in units if not d['refusal_reasons']and d['id']!=target['id']and d[field]==target[field]];choices={}
            for donor in donors:
                value=dict(anchor=target['realization']['anchor'],intervals=deepcopy(donor['realization']['intervals']),strings=deepcopy(donor['fixed_output_strings']))
                delta=F(value['anchor'])-F(donor['realization']['anchor'])
                pitches=[F(value['anchor'])+F(i)for i in value['intervals']]
                old=[F(target['realization']['anchor'])+F(i)for i in target['realization']['intervals']]
                reason=None
                if any(ref in target['locked_tie_members']and p!=q for ref,p,q in zip(target['member_refs'],pitches,old)):reason='LOCKED_WRITTEN_TIE_ENDPOINT'
                elif any(ref in target['locked_execution_members']and p!=q for ref,p,q in zip(target['member_refs'],pitches,old)):reason='LOCKED_EXECUTION_DEPENDENCY'
                elif any(target['source_geometry'][k]!=donor['source_geometry'][k]for k in ('instrument','tuning','capo')):reason='INCOMPATIBLE_INSTRUMENT_SETTINGS'
                else:
                    geometry=donor['source_geometry'];bases=[F(str(geometry['tuning'][s]))+F(str(geometry['capo']))for s in value['strings']]
                    donor_pitches=[F(donor['realization']['anchor'])+F(i)for i in value['intervals']]
                    source_frets=[p-b for p,b in zip(donor_pitches,bases)]
                    translated=[p-b for p,b in zip(pitches,bases)]
                    def invalid(frets,limit):return any(f<0 or f.denominator!=1 or(type(limit)is int and limit>0 and f>limit)for f in frets)
                    for a,b in zip(source_frets,translated):
                        if invalid([a],donor['declared_frets']) or invalid([b],target['declared_frets']) or a+delta!=b:
                            reason='INVALID_TRANSLATED_OR_SOURCE_FRET';break
                        if (a==0)!=(b==0):reason='OPEN_STRING_STATUS_CHANGED';break
                    if reason is None and any(new!=prior and new in target['occupied_strings']for prior,new in zip(target['fixed_output_strings'],value['strings'])):reason='OVERLAPPING_STRING_OCCUPIED'
                    if reason is None and any(ref in set(target['locked_tie_members'])|set(target['locked_execution_members'])and new!=prior for ref,prior,new in zip(target['member_refs'],target['fixed_output_strings'],value['strings'])):reason='LOCKED_EXECUTION_STRING'
                if reason:
                    rejected.append(dict(level=field,donor_ref=donor['id'],reason=reason,realization=value));continue
                choices.setdefault(encoded(value),dict(realization=value,donor_refs=[]))['donor_refs'].append(donor['id'])
            options=[choices[k]for k in sorted(choices)]
            original=dict(target['realization'],strings=target['fixed_output_strings'])
            alternative=any(c['realization']!=original for c in options)
            levels.append(dict(level=field,donor_units=len(donors),distinct_realizations=len(options),physically_feasible_realizations=len(options),has_alternative=alternative))
            if alternative:status='SUPPORTED_EMPIRICAL_ALTERNATIVES';break
        if status is None:status='OBSERVED_SINGLE_REALIZATION'if options else'NO_ELIGIBLE_ALTERNATIVE'
        result.append(dict(target_ref=target['id'],status=status,levels=levels,rejected=rejected,options=options))
    return result


def check(documents,catalog,reported=None):
    issues=[]
    try:
        units,count,ties,dependencies=normalized_units(documents)
        actual=catalog['units']
        if encoded(catalog.get('source_occurrences'))!=encoded(count):issues.append('SOURCE_OCCURRENCE_COUNT_MISMATCH')
        if encoded(catalog.get('written_tie_relationships'))!=encoded(ties):issues.append('WRITTEN_TIE_RELATIONSHIPS_MISMATCH')
        if encoded(catalog.get('execution_dependencies'))!=encoded(dependencies):issues.append('EXECUTION_DEPENDENCIES_MISMATCH')
        if [u['id']for u in actual]!=[u['id']for u in units]:issues.append('SOURCE_UNIT_INVENTORY_MISMATCH')
        by_id={u['id']:u for u in actual}
        if len(by_id)!=len(actual):issues.append('DUPLICATE_SOURCE_UNIT')
        for row in units:
            other=by_id.get(row['id'])
            if other is None:continue
            for key,value in row.items():
                if key not in other or encoded(other[key])!=encoded(value):issues.append('SOURCE_UNIT_FIELD_MISMATCH:'+row['id']+':'+key)
        rows=expected_rows(units)
        if reported is not None and encoded(reported)!=encoded(rows):issues.append('COMPLETE_POLICY_DECISIONS_MISMATCH')
        return dict(status='PASS_INDEPENDENT_POLICY'if not issues else'FAIL_INDEPENDENT_POLICY',issues=issues,source_occurrences=count,source_units=len(units),eligible_units=len(rows),expected_rows=rows,accepted_donor_links=sum(len(c['donor_refs'])for row in rows for c in row['options']),rejected_donor_links=sum(len(row['rejected'])for row in rows),scope='Independent relative-coordinate context and joint physical witness enumeration; shared source extraction/detector predicates; not musical suitability or human playability')
    except Exception as error:
        return dict(status='FAIL_INDEPENDENT_POLICY',issues=issues+[type(error).__name__+': '+str(error)])
