"""Independent raw-field, musical-lock and joint-source fingering checker.

No producer intervention/sampler calls. Candidate enumeration is shared with the
independent policy oracle, and accepted technique predicates are recomputed.
"""
from fractions import Fraction as F
import random
from source_fact_tier1 import project_documents
from check_voicing_policy import _source_units,_expected_rows,_written_ties,encoded


def _note(documents,ref):
    _,song,p,m,v,b,n=ref.split(':')
    document=f'track-{p}.json';pointer=f'/measures/{int(m)-1}/voices/{v}/beats/{b}/notes/{n}'
    part=documents[document];note=part['measures'][int(m)-1]['voices'][int(v)]['beats'][int(b)]['notes'][int(n)]
    return part,note,document+'#'+pointer


def _pitch(part,note,require_geometry=True):
    string=note.get('string');fret=note.get('fret');tuning=part.get('tuning')
    if type(string)is not int or type(tuning)is not list or not 0<=string<len(tuning):raise ValueError('Invalid physical string/tuning')
    if type(fret)not in(int,float):raise ValueError('Invalid physical fret')
    if require_geometry and(F(str(fret))<0 or F(str(fret)).denominator!=1):raise ValueError('Invalid physical fret')
    limit=part.get('frets')
    if require_geometry and type(limit)is int and limit>0 and F(str(fret))>limit:raise ValueError('Outside declared instrument frets')
    return F(str(tuning[string]))+F(str(part.get('capo')or 0))+F(str(fret))


def check(before_T1,after_T1,controls,decision):
    issues=[];changed=[];allowed=set()
    try:
        fields={'voicing','register','physical','context_policy','target_ref','seed'}
        if type(controls)is not dict or set(controls)!=fields or controls['context_policy']not in('joint_source_fingering','transposed_voicing_family'):raise ValueError('Explicit joint controls required')
        if any(type(controls[k])is not int or not 0<=controls[k]<=100 for k in ('voicing','register','physical'))or type(controls['seed'])is not int:raise ValueError('Typed bounded release controls required')
        family=controls['context_policy']=='transposed_voicing_family'
        if family and controls['register']!=0:raise ValueError('Family experiment locks register at zero')
        before=project_documents(before_T1);after=project_documents(after_T1)
        if family:
            from check_family_policy import normalized_units,expected_rows
            units,_,ties,dependencies=normalized_units(before)
        else:units,_,ties,dependencies=_source_units(before,'joint_source_fingering')
        by_id={r['id']:r for r in units}
        all_zero=not any(controls[k]for k in ('voicing','register','physical'))
        target=by_id.get(controls['target_ref'])
        if target is None and not all_zero:raise ValueError('Unknown source target')
        refs=target['member_refs']if target else[]
        for ref in refs:
            _,_,base=_note(before,ref);allowed.update((base+'/fret',base+'/string'))
        if encoded({k:v for k,v in before_T1.items()if k!='facts'})!=encoded({k:v for k,v in after_T1.items()if k!='facts'}):issues.append('T1_HEADER_CHANGED')
        a=before_T1['facts'];b=after_T1['facts']
        if [r['id']for r in a]!=[r['id']for r in b]or len({r['id']for r in b})!=len(b):issues.append('SOURCE_FACT_INVENTORY_OR_ORDER_CHANGED')
        old={r['id']:r for r in a};new={r['id']:r for r in b}
        for ident,row in old.items():
            actual=new.get(ident)
            if actual is None:continue
            if encoded(row)==encoded(actual):continue
            changed.append(ident)
            if ident not in allowed or all_zero:issues.append('LOCKED_SOURCE_FIELD_CHANGED:'+ident)
            if encoded({k:v for k,v in row.items()if k!='value'})!=encoded({k:v for k,v in actual.items()if k!='value'}):issues.append('SOURCE_SHAPE_OR_TYPE_CHANGED:'+ident)
        original=dict(target['realization'],strings=target['fixed_output_strings'])if target and not target['refusal_reasons']else None
        selected=None;released=None;expected_status='EXACT_ZERO_LOCK'
        if not all_zero:
            if target['refusal_reasons']:expected_status='REFUSED_TARGET'
            else:
                rows=expected_rows(units)if family else _expected_rows(units,'joint_source_fingering')
                evidence=next(r for r in rows if r['target_ref']==target['id'])
                if evidence['status']not in('SUPPORTED_EMPIRICAL_ALTERNATIVES','OBSERVED_SINGLE_REALIZATION'):expected_status=evidence['status']
                else:
                    rng=random.Random(controls['seed']);released={k:rng.random()<controls[k]/100 for k in ('voicing','register','physical')}
                    options=[o for o in evidence['options']if(released['voicing']or o['realization']['intervals']==original['intervals'])and(released['register']or o['realization']['anchor']==original['anchor'])and(released['physical']or o['realization']['strings']==original['strings'])]
                    if not options:expected_status='NO_OBSERVED_CHOICE_SATISFIES_LOCKS'
                    else:
                        population=[o for o in options for _ in o['donor_refs']];selected=rng.choice(population)
                        expected_status='OBSERVED_COINCIDENCE'if selected['realization']==original else'SOURCE_SUPPORTED_REALIZATION'
                        if encoded(decision.get('released'))!=encoded(released)or encoded(decision.get('chosen'))!=encoded(selected):issues.append('SEEDED_SOURCE_CHOICE_MISMATCH')
                        if encoded(decision.get('original'))!=encoded(original)or decision.get('target_ref')!=target['id']or decision.get('member_refs')!=refs:issues.append('CHOICE_IDENTITY_OR_ORIGINAL_MISMATCH')
                        if encoded(decision.get('eligible_donor_units'))!=encoded(len(population)):issues.append('EMPIRICAL_WEIGHT_DENOMINATOR_MISMATCH')
                        if decision.get('context_level')!=evidence['levels'][-1]['level']:issues.append('CONTEXT_LEVEL_MISMATCH')
        if type(decision)is not dict or decision.get('status')!=expected_status:issues.append('CHOICE_STATUS_MISMATCH')
        if selected is None:
            if changed:issues.append('SOURCE_CHANGED_WITHOUT_SUPPORTED_CHOICE')
            if decision.get('changed')is not False:issues.append('CHANGED_FLAG_MISMATCH')
        else:
            want=selected['realization'];pitches=[F(want['anchor'])+F(v)for v in want['intervals']];after_geometry=[]
            for ref,expected_pitch,expected_string,old_string in zip(refs,pitches,want['strings'],target['fixed_output_strings']):
                old_part,old_note,_=_note(before,ref);part,note,_=_note(after,ref);pitch=_pitch(part,note)
                if pitch!=expected_pitch or note['string']!=expected_string:issues.append('ACTUAL_JOINT_REALIZATION_MISMATCH:'+ref)
                if pitch%12!=_pitch(old_part,old_note,require_geometry=False)%12:issues.append('MEMBER_PITCH_CLASS_CHANGED:'+ref)
                if not released['physical']and note['string']!=old_string:issues.append('LOCKED_STRING_CHANGED:'+ref)
                if expected_string!=old_string and expected_string in target['occupied_strings']:issues.append('NEW_NOMINAL_STRING_COLLISION:'+ref)
                after_geometry.append([str(pitch),note['string'],str(F(str(note['fret'])))])
            if len({r[1]for r in after_geometry})!=len(after_geometry):issues.append('DUPLICATE_SELECTED_STRING')
            for donor_ref in selected['donor_refs']:
                donor=by_id[donor_ref];raw_geometry=[]
                delta=F(target['realization']['anchor'])-F(donor['realization']['anchor'])if family else F(0)
                for member in donor['member_refs']:
                    part,note,_=_note(before,member);source_pitch=_pitch(part,note);source_fret=F(str(note['fret']));fret=source_fret+delta
                    if family:
                        if any(part[k]!=_note(before,refs[0])[0][k]for k in ('instrumentId','tuning'))or (part.get('capo')or 0)!=(_note(before,refs[0])[0].get('capo')or 0):issues.append('INCOMPATIBLE_TRANSFER_SETTINGS')
                        if (source_fret==0)!=(fret==0):issues.append('TRANSFER_OPEN_STATUS_CHANGED')
                    raw_geometry.append([str(source_pitch+delta),note['string'],str(fret)])
                if sorted(after_geometry,key=encoded)!=sorted(raw_geometry,key=encoded):issues.append('NO_COMPLETE_RAW_JOINT_SOURCE_WITNESS:'+donor_ref)
            # Candidate intervals/register were already independently filtered;
            # this also authenticates the actual source pitches after inversion.
            actual_pitches=[_pitch(*_note(after,ref)[:2])for ref in refs];anchor=min(actual_pitches)
            if not released['register']and anchor!=F(original['anchor']):issues.append('LOCKED_REGISTER_CHANGED')
            if not released['voicing']and [str(p-anchor)for p in actual_pitches]!=original['intervals']:issues.append('LOCKED_VOICING_CHANGED')
            if type(decision.get('changed'))is not bool or decision['changed']!=(want!=original):issues.append('CHANGED_FLAG_MISMATCH')
        from source_tie_tier1 import extract_documents
        from check_execution_dependencies import expected
        after_events=extract_documents(after)['events']
        if encoded(_written_ties(after,after_events))!=encoded(ties):issues.append('WRITTEN_TIE_SEMANTICS_CHANGED')
        if encoded(expected(after_T1)['signature'])!=encoded(dependencies['signature']):issues.append('EXECUTION_SEMANTICS_CHANGED')
        return dict(status='PASS_LOCKED_DIMENSIONS'if not issues else'FAIL_LOCKED_DIMENSIONS',issues=issues,changed_source_paths=changed,allowed_paths=sorted(allowed),
            source_joint_witnesses=len(selected['donor_refs'])if selected else 0,
            scope='Independent source fields, seeded conditional choices, pitch/string locks, nominal collisions and retained predicates; not certified human playability')
    except Exception as error:
        return dict(status='FAIL_LOCKED_DIMENSIONS',issues=issues+[type(error).__name__+': '+str(error)],changed_source_paths=changed,allowed_paths=sorted(allowed))
