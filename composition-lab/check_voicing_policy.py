"""Independent source denominator oracle for witnessed fixed-string voicings.

Shared primitives: accepted source_tie_tier1 pitch/time decoding and canonical
source_refusals technique semantics. No voicing_register producer calls.
Written ties use the accepted written_tie_edges predicate on independently
assembled raw source lanes, clocks and positions.
This checks source relationships, not acoustic or human playability.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
import json
from contextual_note_roles import source_refusals
from source_tie_tier1 import extract_documents


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def _written_ties(documents,events):
    from musical_tier2 import written_tie_edges
    context={};true=set()
    for event in events:
        part=documents[f"track-{event['part_id']}.json"]
        note=part['measures'][event['bar']-1]['voices'][event['voice']]['beats'][event['beat']]['notes'][event['note']]
        string=note.get('string');fret=note.get('fret');tuning=part.get('tuning');position=None
        if part.get('instrumentId')!=1024 and type(string)is int and tuning is not None and 0<=string<len(tuning) and type(fret)in(int,float):
            position=F(str(tuning[string]))+F(str(part.get('capo')or 0))+F(str(fret))
        ident=event['id']
        context[ident]=dict(id=ident,lane=(event['part_id'],event['voice'],string)if type(string)is int and string>=0 else None,
            onset=F(event['onset_q']),duration=F(event['duration_q']),position=position,
            kind='pitched_position'if position is not None else'unmapped_position',
            valid_position=type(fret)in(int,float)and fret>=0,dead=note.get('dead')is True)
        if note.get('tie')is True:true.add(ident)
    links,unresolved=written_tie_edges(context,true)
    return dict(links=links,unresolved=unresolved)


def _source_units(documents,policy='source_witnessed_fixed_strings'):
    lower=extract_documents(documents)
    events=lower['events']; by_id={e['id']:e for e in events}
    tie_graph=_written_ties(documents,events)
    endpoints={link[key]for link in tie_graph['links']for key in ('origin','destination')}
    dependencies=None
    if policy=='incident_dependencies':
        from check_execution_dependencies import expected
        from source_fact_tier1 import extract_documents as complete_facts
        dependencies=expected(complete_facts(documents))
    frames=lower['measure_geometry']['frames']
    grouped=defaultdict(list)
    for e in events:grouped[e['part_id'],F(e['onset_q'])].append(e)
    def raw(e):
        part=documents[f"track-{e['part_id']}.json"]
        beat=part['measures'][e['bar']-1]['voices'][e['voice']]['beats'][e['beat']]
        return part,beat,beat['notes'][e['note']]
    def expressions(e):
        part,beat,note=raw(e)
        reasons=source_refusals(documents,by_id,[e['id']])
        for k in ('hp','tieOrigin','tieDestination','rest','fingerVibrato'):
            if k in note and note[k] is not False and note[k] is not None:reasons.append('NOTE_DEPENDENCY:'+k)
        for field in ('letRing','arpeggio','brushStroke'):
            if field in beat and beat[field] is not False and beat[field] is not None:reasons.append('BEAT_DEPENDENCY:'+field)
        return reasons
    expression={e['id']:expressions(e) for e in events}
    def pcs(rows):
        return sorted([int(F(e['pitch'])%12) if e['pitch'] is not None and F(e['pitch']).denominator==1 else None for e in rows],key=lambda p:-1 if p is None else p)
    neighbors={}
    for pid in {p for p,t in grouped}:
        sequence=sorted((t,rows)for (p,t),rows in grouped.items()if p==pid)
        for i,(t,rows)in enumerate(sequence):neighbors[pid,t]=[pcs(sequence[i-1][1])if i else None,pcs(sequence[i+1][1])if i+1<len(sequence)else None]
    pitched=[(e,F(e['onset_q']),F(e['onset_q'])+F(e['duration_q']))for e in events if raw(e)[0].get('instrumentId')!=1024]
    units=[]
    for (pid,onset),rows in sorted(grouped.items(),key=lambda x:(x[0][1],x[0][0],x[1][0]['id'])):
        rows=sorted(rows,key=lambda e:(e['voice'],e['beat'],e['note']))
        part=raw(rows[0])[0];reasons=[];bars={e['bar']for e in rows}
        if type(part.get('instrumentId'))is not int or not 24<=part['instrumentId']<=39:reasons.append('NOT_GUITAR_OR_BASS_PROGRAM')
        if len(rows)<2:reasons.append('FEWER_THAN_TWO_NOTES')
        if len({e['voice']for e in rows})!=1:reasons.append('MULTIPLE_VOICES')
        if len({e['duration_q']for e in rows})!=1 or any(F(e['duration_q'])<=0 for e in rows):reasons.append('NONUNIFORM_OR_ZERO_DURATION')
        if any(e['pitch']is None or F(e['pitch']).denominator!=1 for e in rows):reasons.append('UNKNOWN_OR_NONINTEGER_PITCH')
        if len(bars)!=1:reasons.append('CROSS_BAR_COATTACK')
        if any(w['bar']in bars for k in ('layout_warnings','timing_warnings')for w in lower['source_coverage'][k]):reasons.append('SOURCE_TIMING_UNCERTAIN')
        strings=[raw(e)[2].get('string')for e in rows]
        if any(type(s)is not int or s<0 for s in strings)or len(set(strings))!=len(strings):reasons.append('AMBIGUOUS_FIXED_STRINGS')
        for e in rows:reasons.extend(expression[e['id']])
        unit=dict(id=rows[0]['id'],part_id=pid,bar=rows[0]['bar'],onset_q=str(onset),member_refs=[e['id']for e in rows],refusal_reasons=sorted(set(reasons)))
        if reasons:units.append(unit);continue
        rows=sorted(rows,key=lambda e:(F(e['pitch'])%12,F(e['pitch']),e['voice'],e['note']))
        unit['member_refs']=[e['id']for e in rows]
        unit['locked_tie_members']=[ref for ref in unit['member_refs']if ref in endpoints]
        stop=onset+F(rows[0]['duration_q']);selected=set(unit['member_refs']);overlaps=[];uncertainty=[];uncertainty_context=[]
        for other,a,b in pitched:
            if other['id']in selected or not a<stop or not b>onset:continue
            unknown=other['pitch']is None or F(other['pitch']).denominator!=1
            if unknown or expression[other['id']]:
                if policy!='incident_dependencies' or other['part_id']==pid:reasons.append('UNRESOLVED_OVERLAP_EXECUTION')
                else:
                    descriptor=dict(written_pitch_status='unknown_or_noninteger' if unknown else 'known_base_only',execution_reasons=sorted(set(expression[other['id']])),claim='Nominal source overlap; sounding pitch/end unknown')
                    uncertainty.append(dict(occurrence_ref=other['id'],**descriptor))
                    uncertainty_context.append([other['part_id'],other['voice'],str(max(a,onset)-onset),str(min(b,stop)-onset),descriptor])
            overlaps.append([other['part_id'],other['voice'],str(max(a,onset)-onset),str(min(b,stop)-onset),None if unknown else str(F(other['pitch'])%12)])
        frame=frames[rows[0]['bar']-1];sig=frame['signature'];pitches=[F(e['pitch'])for e in rows]
        strings=[raw(e)[2]['string']for e in rows]
        context=dict(part_id=pid,instrument=part['instrumentId'],member_pitch_classes=[str(p%12)for p in pitches],meter=dict(beats=sig[0],beat_unit_q=str(F(4,sig[1]))),metrical_offset_q=str(onset-F(frame['start_q'])),overlaps=sorted(overlaps,key=encoded),duration_q=rows[0]['duration_q'])
        unit.update(refusal_reasons=sorted(set(reasons)),duration_q=rows[0]['duration_q'],realization=dict(anchor=str(min(pitches)),intervals=[str(p-min(pitches))for p in pitches]),fixed_output_strings=strings,
            fixed_string_bases=[str(F(str(part['tuning'][s]))+F(str(part.get('capo')or 0)))for s in strings],
            musical_context_key=encoded(context),musical_full_context_key=encoded([context,neighbors[pid,onset]]),
            source_geometry=dict(instrument=part['instrumentId'],tuning=part['tuning'],capo=part.get('capo')or 0,members=sorted([[str(p),s,str(F(str(raw(e)[2]['fret'])))]for e,p,s in zip(rows,pitches,strings)],key=encoded)))
        if dependencies is not None:
            unit['locked_execution_members']=[ref for ref in unit['member_refs'] if ref in dependencies['pinned_members']]
            unit['context_uncertainty']=sorted(uncertainty,key=lambda r:r['occurrence_ref'])
            context['execution_uncertainty']=sorted(uncertainty_context,key=encoded)
            unit['dependency_context_key']=encoded(context)
            unit['dependency_full_context_key']=encoded([context,neighbors[pid,onset]])
        units.append(unit)
    return units,len(events),tie_graph,dependencies


def _expected_rows(units,policy='source_witnessed_fixed_strings'):
    keys=('dependency_full_context_key','dependency_context_key') if policy=='incident_dependencies' else ('musical_full_context_key','musical_context_key')
    grouped={field:defaultdict(list)for field in keys}
    for row in units:
        if not row['refusal_reasons']:
            for field in grouped:grouped[field][row[field]].append(row)
    result=[]
    for target in units:
        if target['refusal_reasons']:continue
        levels=[];rejected=[];options=[];status=None
        for field in grouped:
            donors=[d for d in grouped[field][target[field]]if d['id']!=target['id']];choices={}
            for donor in donors:
                value=donor['realization'];pitches=[F(value['anchor'])+F(v)for v in value['intervals']]
                original=[F(target['realization']['anchor'])+F(v)for v in target['realization']['intervals']]
                if any(ref in target['locked_tie_members']and pitch!=old for ref,pitch,old in zip(target['member_refs'],pitches,original)):
                    rejected.append(dict(level=field,donor_ref=donor['id'],reason='LOCKED_WRITTEN_TIE_ENDPOINT',realization=value));continue
                if policy=='incident_dependencies' and any(ref in target['locked_execution_members']and pitch!=old for ref,pitch,old in zip(target['member_refs'],pitches,original)):
                    rejected.append(dict(level=field,donor_ref=donor['id'],reason='LOCKED_EXECUTION_DEPENDENCY',realization=value));continue
                actual=dict(instrument=target['source_geometry']['instrument'],tuning=target['source_geometry']['tuning'],capo=target['source_geometry']['capo'],members=sorted([[str(p),s,str(p-F(b))]for p,s,b in zip(pitches,target['fixed_output_strings'],target['fixed_string_bases'])],key=encoded))
                if actual!=donor['source_geometry']:
                    rejected.append(dict(level=field,donor_ref=donor['id'],reason='NO_JOINT_FIXED_STRING_WITNESS',realization=value));continue
                key=encoded(value);choices.setdefault(key,dict(realization=value,donor_refs=[]))['donor_refs'].append(donor['id'])
            options=[choices[k]for k in sorted(choices)];alternative=any(x['realization']!=target['realization']for x in options)
            levels.append(dict(level=field,donor_units=len(donors),distinct_realizations=len(options),physically_feasible_realizations=len(options),has_alternative=alternative))
            if alternative:status='SUPPORTED_EMPIRICAL_ALTERNATIVES';break
        if status is None:status='OBSERVED_SINGLE_REALIZATION'if options else'NO_ELIGIBLE_ALTERNATIVE'
        result.append(dict(target_ref=target['id'],status=status,levels=levels,rejected=rejected,options=options))
    return result


def check(documents,catalog,reported=None,policy='source_witnessed_fixed_strings'):
    """Authenticate all units/eligible contexts and complete donor decisions.

    reported is the producer's all-target audit rows (including options), not
    source truth. Without it, expected_rows is provided for caller comparison.
    """
    issues=[]
    try:
        if policy not in ('source_witnessed_fixed_strings','incident_dependencies'):raise ValueError('Explicit oracle policy required')
        units,event_count,tie_graph,dependencies=_source_units(documents,policy);actual=catalog['units']
        if policy=='incident_dependencies' and encoded(catalog.get('execution_dependencies'))!=encoded(dependencies):issues.append('EXECUTION_DEPENDENCIES_MISMATCH')
        if encoded(catalog.get('written_tie_relationships'))!=encoded(tie_graph):issues.append('WRITTEN_TIE_RELATIONSHIPS_MISMATCH')
        if encoded(catalog['source_occurrences'])!=encoded(event_count):issues.append('SOURCE_OCCURRENCE_COUNT_MISMATCH')
        if len(actual)!=len(units)or [u['id']for u in actual]!=[u['id']for u in units]:issues.append('SOURCE_UNIT_INVENTORY_MISMATCH')
        by_id={u['id']:u for u in actual}
        if len(by_id)!=len(actual):issues.append('DUPLICATE_SOURCE_UNIT')
        for expected in units:
            row=by_id.get(expected['id'])
            if row is None:continue
            for field,value in expected.items():
                if field not in row or encoded(row[field])!=encoded(value):issues.append('SOURCE_UNIT_FIELD_MISMATCH:'+expected['id']+':'+field)
        expected_rows=_expected_rows(units,policy)
        if reported is not None and encoded(reported)!=encoded(expected_rows):issues.append('COMPLETE_POLICY_DECISIONS_MISMATCH')
        return dict(status='PASS_INDEPENDENT_POLICY'if not issues else'FAIL_INDEPENDENT_POLICY',issues=issues,source_occurrences=event_count,source_units=len(units),eligible_units=len(expected_rows),expected_rows=expected_rows,
            accepted_donor_links=sum(len(c['donor_refs'])for r in expected_rows for c in r['options']),rejected_donor_links=sum(len(r['rejected'])for r in expected_rows),
            written_tie_links=len(tie_graph['links']),unresolved_written_ties=len(tie_graph['unresolved']),
            scope='Independent source denominator/context/joint-shape oracle; shared pitch/time parser and source-expression semantics, not human playability')
    except Exception as error:
        return dict(status='FAIL_INDEPENDENT_POLICY',issues=issues+[type(error).__name__+': '+str(error)],scope='Independent source oracle failed; no musical pass')
