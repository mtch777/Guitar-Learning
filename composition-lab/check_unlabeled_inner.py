"""Independent raw/native all-assumptions inner-component oracle.

No producer catalog, options, choice, apply or harmonic population calls.
Existing raw guard implementation is shared explicitly, not producer decisions.
"""
from collections import defaultdict,Counter
from copy import deepcopy
from fractions import Fraction as F
from source_fact_tier1 import validate as validate_source
from check_voicing_context import _nodes,_paths
from check_voicing_policy import _written_ties,encoded
from check_execution_dependencies import expected as execution_expected
from check_harmonic_evidence import native_forms
from check_inner_voicing import _plain_reasons,_has_outside_overlap,_overlap_index,_check_raw,_note
from check_fretting_contacts import expected as contact_expected

def _source(tier1):
    validate_source(tier1);docs,lower,nodes,rests=_nodes(tier1)
    ties=_written_ties(docs,lower['events']);execution=execution_expected(tier1)
    pinned={r for e in ties['links']for r in(e['origin'],e['destination'])}|{e['destination']for e in ties['unresolved']}|set(execution['pinned_members'])
    neighbors=defaultdict(set)
    for p in _paths(nodes,rests,True).values():
        for r in p['refs']:neighbors[r].update(p['refs'])
    raw=defaultdict(list)
    for r,n in nodes.items():raw[n['part'],int(r.split(':')[3]),n['onset']].append(r)
    groups=[];units={};index=_overlap_index(nodes);native={};scope_refusals=[]
    warnings=lower['source_coverage']['layout_warnings']+lower['source_coverage']['timing_warnings']
    for ordinal,key in enumerate(sorted(raw,key=lambda k:(k[2],k[1],k[0]))):
        part,bar,onset=key;refs=raw[key];gid=f'coattack:{ordinal}';p=docs[f'track-{part}.json'];inst=p.get('instrumentId');values=[nodes[r]['pitch']for r in refs];reasons=[];hh=[]
        if type(inst)is not int or not 0<=inst<=127:reasons.append('NONPITCHED_OR_UNKNOWN_INSTRUMENT')
        if any(w['bar']==bar for w in warnings):reasons.append('UNCERTAIN_SOURCE_CLOCK')
        if any(nodes[r]['duration']<=0 for r in refs):reasons.append('GRACE_OR_NONPOSITIVE_DURATION')
        if any(v is None for v in values):reasons.append('UNKNOWN_WRITTEN_PITCH')
        elif any(v.denominator!=1 for v in values):reasons.append('NONINTEGER_WRITTEN_PITCH')
        elif len({v%12 for v in values})<2:reasons.append('INSUFFICIENT_DISTINCT_PITCH_CLASSES')
        strings=[nodes[r]['string']for r in refs];component_reasons=[]
        if type(inst)is not int or not 24<=inst<=39:component_reasons.append('OUTSIDE_GUITAR_COMPONENT_SCOPE')
        if any(type(s)is not int or s<0 for s in strings)or len(set(strings))!=len(strings):component_reasons.append('NONUNIQUE_OR_UNKNOWN_STRING')
        if any(type(_note(docs,r)[2].get('fret'))not in(int,float)for r in refs):component_reasons.append('MISSING_NUMERIC_SOURCE_FRET')
        if not reasons and component_reasons:scope_refusals.append(dict(group_ref=gid,reasons=sorted(component_reasons)))
        if not reasons:
            pcs={int(v%12)for v in values}
            for kind,formula,definitions in native_forms():
                if len(formula)<2:continue
                for root in range(12):
                    if {(root+x)%12 for x in formula}!=pcs:continue
                    ident=f'{gid}:root-{root}:{kind}';roles=[];ambiguous=False
                    for v in values:
                        matches=[d for d in definitions if(v-root-d['theoretical_semitones'])%12==0]
                        if len(matches)!=1:ambiguous=True;break
                        d=matches[0];roles.append(dict(degree_token=d['token'],relative_octaves=int((v-root-d['theoretical_semitones'])/12)))
                    hh.append(dict(id=ident,root_pc=root,kind=kind,formula=formula))
                    native[ident]=dict(root_pc=root,kind=kind,pcs=sorted(pcs),degrees=[(d['token'],d['theoretical_semitones'])for d in definitions],slash_bass_pc=None)
                    if component_reasons:continue
                    if ambiguous:
                        scope_refusals.append(dict(group_ref=gid,hypothesis_ref=ident,reasons=['AMBIGUOUS_DEGREE_ASSIGNMENT']));continue
                    base=_plain_reasons(docs,nodes,refs,pinned);lo,hi=min(values),max(values);inner=[r for r in refs if lo<nodes[r]['pitch']<hi]
                    eligibility=list(base)
                    if not inner:eligibility.append('NO_STRICT_INNER_COMPONENT')
                    if _has_outside_overlap(nodes,refs,index):eligibility.append('OUTSIDE_SAME_PART_OVERLAP')
                    units[ident]=dict(id=ident,group_ref=gid,source_unit_ref=refs[0],hypothesis_ref=ident,member_refs=refs,part_id=part,root_pc=root,kind=kind,
                        strings=[nodes[r]['string']for r in refs],roles=roles,pitches=list(map(str,values)),family=[part,root,kind],inner_refs=inner,outer_refs=[r for r in refs if r not in inner],
                        inner_strings=[nodes[r]['string']for r in inner],excluded_neighborhood=sorted(set(refs)|{x for r in refs for x in neighbors[r]}),base_reasons=base,reasons=sorted(set(eligibility)))
        groups.append(dict(id=refs[0],group_ref=gid,member_refs=refs,part_id=part,onset_q=str(onset),fit_refusals=reasons,hypotheses=hh))
    prepared=(docs,lower,nodes,rests,ties,execution,pinned,list(units.values()),[]);families=defaultdict(list)
    for unit in units.values():families[tuple(unit['family'])].append(unit)
    return dict(prepared=prepared,groups=groups,units=units,native=native,families=families,component_scope_refusals=scope_refusals,
        group_index={g['id']:g for g in groups},layout_cache={})

def _layouts(source,target_ref):
    if target_ref in source['layout_cache']:return source['layout_cache'][target_ref]
    group=source['group_index'].get(target_ref)
    if group is None:raise ValueError('Original whole source target identity required')
    units=source['units'];out={};all_ids=[h['id']for h in group['hypotheses']]
    for hid in all_ids:
        target=units.get(hid)
        if target is None or target['reasons']:continue
        excluded=set(target['excluded_neighborhood']);wanted=set(target['inner_strings'])
        for donor in source['families'][tuple(target['family'])]:
            if donor['base_reasons']or donor['family']!=target['family']or excluded&set(donor['member_refs'])or not wanted<=set(donor['inner_strings']):continue
            slots={s:i for i,s in enumerate(donor['strings'])};roles=[];pitches=[]
            for ref,string,role,pitch in zip(target['member_refs'],target['strings'],target['roles'],target['pitches']):
                inner=ref in target['inner_refs'];roles.append(deepcopy(donor['roles'][slots[string]]if inner else role));pitches.append(str(F(donor['pitches'][slots[string]]if inner else pitch)))
            row=out.setdefault(tuple(pitches),{})
            support=row.setdefault(hid,dict(target_hypothesis_ref=hid,roles=roles,donor_hypothesis_refs=[],donor_group_refs=set()))
            if support['roles']!=roles:raise ValueError('Multiple degree spellings in one supported layout')
            support['donor_hypothesis_refs'].append(donor['id']);support['donor_group_refs'].add(donor['group_ref'])
    rows=[]
    original=tuple(str(source['prepared'][2][r]['pitch'])for r in group['member_refs'])
    for pitches,supported in sorted(out.items()):
        support=[]
        for hid,s in sorted(supported.items()):
            support.append(dict(target_hypothesis_ref=hid,roles=s['roles'],donor_hypothesis_refs=sorted(s['donor_hypothesis_refs']),donor_group_refs=sorted(s['donor_group_refs'])))
        rows.append(dict(pitches=list(pitches),support=support,donor_refs=sorted({g for s in support for g in s['donor_group_refs']}),changed=pitches!=original,
            all_assumptions=set(supported)==set(all_ids)))
    source['layout_cache'][target_ref]=(group,rows)
    return group,rows

def inventory(tier1):
    return _inventory(_source(tier1))

def _inventory(c):
    rows=[]
    for g in c['groups']:
        _,layouts=_layouts(c,g['id']);rows.append(dict(target_ref=g['id'],group_ref=g['group_ref'],all_hypothesis_refs=[h['id']for h in g['hypotheses']],layouts=layouts))
    return dict(status='PASS_INDEPENDENT_UNLABELED_POPULATION',groups=c['groups'],units=list(c['units'].values()),targets=rows,component_scope_refusals=c['component_scope_refusals'],
        counts=dict(groups=len(c['groups']),hypotheses=sum(len(g['hypotheses'])for g in c['groups']),component_hypotheses=len(c['units']),
            unique_layouts=sum(len(r['layouts'])for r in rows),universal_layouts=sum(v['all_assumptions']for r in rows for v in r['layouts'])))

def _matching_option(group,rows,option):
    if type(option)is not dict or type(option.get('changed'))is not bool:raise ValueError('Typed option required')
    support=option.get('support')
    matches=[r for r in rows if encoded(r['support'])==encoded(support)]
    if len(matches)!=1:raise ValueError('Omitted/forged/duplicate native assumption or donor support')
    row=matches[0]
    if not row['all_assumptions']:raise ValueError('Outcome does not cover all retained assumptions')
    if option.get('support_class')!='ALL_ENUMERATED_TARGET_ASSUMPTIONS':raise ValueError('Incorrect universal support claim')
    if option.get('donor_refs')!=row['donor_refs']or option['changed']!=row['changed']:raise ValueError('Donor occurrence weighting or changed flag differs')
    if 'pitches'in option and option['pitches']!=row['pitches']:raise ValueError('Reported concrete pitches differ')
    return row

def _option_coverage(option):
    relationship=option.get('relationship',{});support=option['support'];proof=relationship.get('checks',[])
    if [p.get('hypothesis_ref')for p in proof]!=[s['target_hypothesis_ref']for s in support]:raise ValueError('Omitted or duplicated hypothesis guard proof')
    covers=[p['checks']['contact_coverage']for p in proof]
    if not covers or any(encoded(c)!=encoded(covers[0])for c in covers):raise ValueError('Conditional physical proofs disagree')
    for p in proof:
        checks=p['checks']
        if checks.get('status')!='PROVISIONAL_INNER_CONTACT_RELATIONSHIPS'or checks.get('human_playability')!='UNVERIFIED'or checks.get('physical_policy')!='provisional_contact_inner_preview':raise ValueError('Conditional guard or physical acceptance promoted')
    if relationship.get('status')!='PROVISIONAL_ALL_ASSUMPTION_INNER_RELATIONSHIPS':raise ValueError('Conditional relationship acceptance promoted')
    if relationship.get('human_playability')!='UNVERIFIED'or relationship.get('musical_fit')!='UNVERIFIED_FOR_THIS_CHANGE':raise ValueError('Unverified acceptance promoted')
    expected=[dict(hypothesis_ref=s['target_hypothesis_ref'],status='EXACT_PROPOSED_DEGREE_RECOVERY')for s in support]
    if relationship.get('degree_roundtrip')!=expected:raise ValueError('Incomplete inverse degree proof')
    return covers[0]

def _edited_context(before,source,after_nodes,changed):
    from check_nominal_harmony import expected as nominal_expected,_fits,_focal_role
    if 'temporal_view'not in source:source['temporal_view']=nominal_expected(before)
    view=source['temporal_view'];nodes=source['prepared'][2];rows={r['occurrence_ref']:r for r in view['occurrence_inventory']};parts=sorted({n['part']for n in nodes.values()});cells=[]
    # Empty parts still have source geometry coverage obligations.
    parts=sorted(p['partId']for name,p in source['prepared'][0].items()if name.startswith('track-'))
    for cell in view['cells']:
        active=sorted(set(changed)&set(cell['active_refs']))
        if not active:continue
        issues={p['part_id']:p['reasons']for p in cell['part_refusals']}
        for part in sorted({nodes[r]['part']for r in active}):
            for scope,ps in (('focal_part_minus_edited',[part]),('ensemble_minus_edited',parts)):
                refs=[r for r in cell['active_refs']if r not in changed and nodes[r]['part']in ps];refs=sorted(refs)
                included=[r for r in refs if rows[r]['domain']!='nonpitched'];excluded=[dict(occurrence_ref=r,reason='EXPLICIT_NONPITCHED_INSTRUMENT')for r in refs if rows[r]['domain']=='nonpitched']
                reasons=sorted({x for r in included for x in rows[r]['qualifications']});pcs=tuple(sorted({nodes[r]['pitch']%12 for r in included if nodes[r]['pitch']is not None}))
                if len(pcs)<2:reasons.append('INSUFFICIENT_DISTINCT_PITCH_CLASSES')
                pop=dict(id=f"{cell['id']}:{part}:{scope}",support_refs=refs,included_refs=included,excluded_refs=excluded,refusals=reasons,hypotheses=[]if reasons else deepcopy(_fits(pcs)))
                refusal=sorted({x for p in ps for x in issues.get(p,[])});focal=issues.get(part,[]);queries=[]
                for ref in active:
                    if nodes[ref]['part']!=part:continue
                    roles=[]if refusal or focal else[dict(hypothesis=h,before=_focal_role(nodes[ref]['pitch'],rows[ref]['domain'],h),after=_focal_role(after_nodes[ref]['pitch'],rows[ref]['domain'],h))for h in pop['hypotheses']]
                    queries.append(dict(occurrence_ref=ref,role_changes=roles))
                cells.append(dict(cell_ref=cell['id'],start_q=cell['start_q'],end_q=cell['end_q'],scope=scope,part_ids=ps,excluded_edited_refs=active,population=pop,scope_refusals=refusal,focal_refusals=focal,queries=queries))
    return dict(schema='edited-set-nominal-context/1',changed_refs=sorted(changed),cells=cells,
        unscoped_edited_refs=sorted(set(changed)&set(view['unscoped_positive_occurrence_refs'])),crossing_edited_refs=sorted(set(changed)&set(view['crossing_occurrence_refs'])),
        semantics='Conditional roles against unchanged written support; unknown/no fit remains unresolved, not a musical intent or role lock')

def _simulated_after(tier1,source,group,row):
    """Oracle-only raw state for guard evaluation, never a production generator."""
    docs,_,nodes,*_=source['prepared'];after=deepcopy(tier1);facts={f['id']:f for f in after['facts']}
    for ref,pitch in zip(group['member_refs'],row['pitches']):
        if F(pitch)==nodes[ref]['pitch']:continue
        part,_,note=_note(docs,ref);capo=part.get('capo')
        if capo is None:capo=0
        fret=F(pitch)-F(str(part['tuning'][note['string']]))-F(str(capo))
        p,bar,voice,beat,ni=map(int,ref.split(':')[2:]);key=f'track-{p}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}/notes/{ni}/fret'
        fact=facts[key]
        if fret.denominator!=1:raise ValueError('Nonintegral proposed physical fret')
        if fact['type']=='integer':fact['value']=int(fret)
        elif fact['type']=='float':fact['value']=float(fret)
        else:raise ValueError('Unsupported source fret type')
    return after

def _oracle_admission(tier1,source,group,row):
    if not row['all_assumptions']:return False,['NOT_SUPPORTED_UNDER_ALL_RETAINED_ASSUMPTIONS']
    if not row['changed']:return True,[]
    try:
        after=_simulated_after(tier1,source,group,row);_,_,nodes,_=_nodes(after)
        required=[]
        for ref in group['member_refs']:
            part,_,note=_note(source['prepared'][0],ref);capo=part.get('capo')
            if capo is None:capo=0
            fret=nodes[ref]['pitch']-F(str(part['tuning'][note['string']]))-F(str(capo))
            if fret.denominator!=1:raise ValueError('Nonintegral contact fret')
            required.append(dict(string=note['string'],fret=int(fret)))
        contacts=contact_expected(required)
        coverage=dict(schema='fretting-contact-coverage/1',required=sorted(required,key=lambda r:r['string']),max_digits=4,search_limit=100000,
            examined=contacts['examined_subsets'],status=contacts['status'],minimum_contacts=contacts['minimum_contacts'],covers=contacts['covers'],human_playability='UNVERIFIED')
        first=row['support'][0];tu=source['units'][first['target_hypothesis_ref']];du=source['units'][first['donor_hypothesis_refs'][0]]
        result=_check_raw(tier1,after,group['member_refs'],du['member_refs'],[],contact_coverage=coverage,
            native_context=dict(prepared=source['prepared'],target_unit=tu,donor_unit=du,native_hypothesis=source['native'][tu['id']]))
        return result['status']=='PASS_PROVISIONAL_INNER_CONTACTS',result['issues']
    except Exception as exc:return False,[str(exc)]

def check_options(tier1,target_ref,reported):
    """Complete raw/native layouts and admission denominator, not producer calls."""
    try:source=_source(tier1)
    except Exception as exc:return dict(status='FAIL',issues=[str(exc)],expected_rows=[])
    return _check_options(source,tier1,target_ref,reported)

def _check_options(source,tier1,target_ref,reported):
    issues=[];expected_rows=[]
    try:
        group,rows=_layouts(source,target_ref)
        if reported['all_hypothesis_refs']!=[h['id']for h in group['hypotheses']]:raise ValueError('All-assumption denominator differs')
        target=reported['target']
        if type(target)is dict:
            if target.get('group_ref')!=group['group_ref']or target.get('member_refs')!=group['member_refs']:raise ValueError('Original target source identity differs')
        elif target!=target_ref:raise ValueError('Original target source identity differs')
        if reported.get('target_ref')!=target_ref:raise ValueError('Original event target reference differs')
        actual=reported['options']+reported['rejected']
        if len(actual)!=len(rows):raise ValueError('Missing/extra concrete outcome')
        seen=set()
        for option in actual:
            matches=[r for r in rows if encoded(r['support'])==encoded(option.get('support'))]
            if len(matches)!=1:raise ValueError('Source donor/assumption/role provenance differs')
            row=matches[0];key=tuple(row['pitches'])
            if key in seen:raise ValueError('Duplicate concrete outcome')
            seen.add(key)
            if type(option.get('changed'))is not bool or option['changed']!=row['changed']or option.get('donor_refs')!=row['donor_refs']:raise ValueError('Donor weights/changed outcome differ')
            expected_class='ALL_ENUMERATED_TARGET_ASSUMPTIONS'if row['all_assumptions']else'SOME_ENUMERATED_TARGET_ASSUMPTIONS'
            if option.get('support_class')!=expected_class:raise ValueError('Support class differs from full source denominator')
            if 'pitches'in option and option['pitches']!=row['pitches']:raise ValueError('Concrete outcome differs')
            admitted,reasons=_oracle_admission(tier1,source,group,row)
            if admitted!=(option in reported['options']):raise ValueError('Independent raw-guard admission differs: '+str(reasons))
            if admitted and row['changed']:
                coverage=_option_coverage(option)
                simulated=_simulated_after(tier1,source,group,row)
                actual_check=_check_actual(source,tier1,simulated,group['member_refs'],option,contact_coverage=coverage)
                if actual_check['issues']:raise ValueError('Reported proof differs: '+str(actual_check['issues']))
            expected_rows.append(dict(**row,admitted=admitted,independent_refusals=reasons))
        expected_status='NO_EXACT_HARMONIC_ASSUMPTIONS'if not group['hypotheses']else'SUPPORTED_ALL_ASSUMPTION_INNER_CHOICES'if any(r['admitted']and r['changed']for r in expected_rows)else'NO_ADMITTED_CHANGED_INNER_COMPONENT'
        if reported.get('status')!=expected_status:raise ValueError('Availability status differs from complete native population')
    except Exception as exc:issues.append(str(exc))
    return dict(status='PASS_INDEPENDENT_UNLABELED_OPTIONS'if not issues else'FAIL',issues=issues,expected_rows=expected_rows)

def check(before_T1,after_T1,target_refs,reported_option,*,contact_coverage=None):
    try:c=_source(before_T1)
    except Exception as exc:return dict(status='FAIL',issues=[str(exc)])
    return _check_actual(c,before_T1,after_T1,target_refs,reported_option,contact_coverage=contact_coverage)

def _check_actual(c,before_T1,after_T1,target_refs,reported_option,*,contact_coverage=None):
    issues=[];raw=None
    try:
        if type(target_refs)is not list or not target_refs:raise ValueError('Exact target source refs required')
        group,rows=_layouts(c,target_refs[0])
        if target_refs!=group['member_refs']:raise ValueError('Whole target membership/order differs')
        row=_matching_option(group,rows,reported_option);_,_,after,_=_nodes(after_T1)
        if [str(after[r]['pitch'])for r in target_refs]!=row['pitches']:raise ValueError('Actual outcome differs from all-assumption source component')
        units=c['units'];first=row['support'][0];tu=units[first['target_hypothesis_ref']];du=units[first['donor_hypothesis_refs'][0]]
        for s in row['support']:
            h=c['native'][s['target_hypothesis_ref']];degree=dict(h['degrees'])
            for ref,role in zip(target_refs,s['roles']):
                if h['root_pc']+degree[role['degree_token']]+12*role['relative_octaves']!=after[ref]['pitch']:raise ValueError('Native degree roundtrip differs')
        changed={r for r in target_refs if c['prepared'][2][r]['pitch']!=after[r]['pitch']}
        if reported_option['changed']!=bool(changed):raise ValueError('Actual changed flag differs')
        expected_context=_edited_context(before_T1,c,after,changed)
        if encoded(reported_option.get('relationship',{}).get('edited_set_context'))!=encoded(expected_context):raise ValueError('Edited-set excluded context differs from raw/native source')
        reported_coverage=_option_coverage(reported_option)
        if contact_coverage is None:contact_coverage=reported_coverage
        elif encoded(contact_coverage)!=encoded(reported_coverage):raise ValueError('External and reported contact proofs disagree')
        if contact_coverage is None:raise ValueError('Explicit provisional contact proof required')
        raw=_check_raw(before_T1,after_T1,target_refs,du['member_refs'],[],contact_coverage=contact_coverage,
            native_context=dict(prepared=c['prepared'],target_unit=tu,donor_unit=du,native_hypothesis=c['native'][tu['id']]))
        if raw['status']!='PASS_PROVISIONAL_INNER_CONTACTS':issues.extend(raw['issues'])
    except Exception as exc:issues.append(str(exc))
    return dict(status='PASS_PROVISIONAL_ALL_ASSUMPTIONS_INNER'if not issues else'FAIL',issues=issues,raw_guard_result=raw,human_playability='UNVERIFIED',
        scope='All finite-vocabulary source assumptions support the same outcome; not identified harmonic truth, melodic identity, artist fit or physical comfort')

class Oracle:
    """One raw/native preparation per immutable audit input; no producer cache.

    The runner owns this object, never a reported JSON/control payload. Its
    input is retained only for independent checks, not for musical realization.
    """
    def __init__(self,tier1):self.tier1=tier1;self._source=_source(tier1)
    def inventory(self):return deepcopy(_inventory(self._source))
    def check_options(self,target_ref,reported):return _check_options(self._source,self.tier1,target_ref,reported)
    def check(self,after_T1,target_refs,reported_option,*,contact_coverage=None):
        return _check_actual(self._source,self.tier1,after_T1,target_refs,reported_option,contact_coverage=contact_coverage)
