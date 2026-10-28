"""Independent enumeration from a separately source-verified component catalog."""
from collections import Counter,defaultdict
from fractions import Fraction as F
import json


def enc(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def physical_preflight(c,target,new):
    old=list(map(F,target['pitches']));new=list(map(F,new));inner=[i for i,r in enumerate(target['member_refs'])if r in target['inner_refs']]
    if any(old[i]!=new[i]for i in range(len(old))if i not in inner):raise ValueError('Locked outer note changed')
    if any(new[i]<=min(old)or new[i]>=max(old)for i in inner):return dict(stage='INNER_PITCH_OUTSIDE_PROTECTED_ENVELOPE')
    if any((old[i]-old[j])*(new[i]-new[j])<0 for i in inner for j in inner):return dict(stage='INNER_STRING_PITCH_ORDER_REVERSED')
    if {p%12 for p in old}!={p%12 for p in new}:return dict(stage='CHORD_FORMULA_SUPPORT_CHANGED')
    source=next((g for g in c['geometries']if set(g['member_refs'])==set(target['member_refs'])),None)
    if source is None or source['reasons']:return dict(stage='SOURCE_GEOMETRY_UNAVAILABLE')
    program,tuning,capo,strings,_,_=json.loads(source['key']);notes=dict(zip(target['strings'],new))
    frets=[notes[s]-F(tuning[s])-F(capo)for s in strings]
    if any(f<0 or f.denominator!=1 for f in frets):return dict(stage='INVALID_NOMINAL_FRET')
    key=enc([program,tuning,capo,strings,[str(f-min(frets))for f in frets],[f==0 for f in frets]])
    witnesses=[g['id']for g in c['geometries']if not g['reasons']and g['key']==key and not set(g['member_refs'])&set(target['excluded_neighborhood'])]
    return dict(stage='WHOLE_GEOMETRY_PREFLIGHT_ONLY'if witnesses else'NO_INDEPENDENT_WHOLE_GEOMETRY',geometry_key=key,witnesses=witnesses,
        remaining=['Actual inverse and whole fact equality outside release','Target fret limit','Execution and ties','Incident paths','Technique classes','Approved pedals','Artist fit and listening'])


def check(c,view,ledger):
    issues=[];counts=Counter();pairs=set();patterns=defaultdict(set)
    try:
        if ledger['schema']!='conditional-source-pattern-ledger/1'or ledger['policy_activated']is not False:raise ValueError('Ledger schema/admission claim differs')
        if ledger['relation']!='Existing same-part/root/kind coupled inner-degree substitution; literal outer occurrences locked'or ledger['scope']!='Source-supported conditional alternatives, before creative admission; all-assumption support is not harmonic truth, preference or playability':raise ValueError('Unsupported ledger meaning')
        units={u['id']:u for u in c['units']}
        for u in units.values():
            if u['base_reasons']:continue
            frame=(min(map(F,u['pitches']))-u['family'][1])//12
            bindings=sorted(zip(u['strings'],[(r['degree_token'],r['relative_octaves']-frame)for r in u['roles']]))
            patterns[enc([u['part_id'],u['family'][2],bindings])].add(u['group_ref'])
        wanted=[g for g in view['groups']if g['hypotheses']];got=ledger['groups']
        if len(got)!=len(wanted):raise ValueError('Group denominator differs')
        target_groups=0
        for source,row in zip(wanted,got):
            ids=[h['id']for h in source['hypotheses']];eligible=[];refusals=[];layouts=defaultdict(dict)
            if row['group_ref']!=source['group_ref']or row['member_refs']!=source['member_refs']or row['all_hypothesis_refs']!=ids:raise ValueError('Target occurrence/assumption scope differs')
            for ident in ids:
                target=units.get(ident)
                if target is None or target['reasons']:
                    refusals.append(dict(hypothesis_ref=ident,reasons=target['reasons']if target else['NO_COMPONENT_UNIT']));continue
                eligible.append(ident)
                for donor in units.values():
                    if donor['base_reasons']or donor['family']!=target['family']or set(donor['member_refs'])&set(target['excluded_neighborhood'])or not set(target['inner_strings'])<=set(donor['inner_strings']):continue
                    bystring={s:i for i,s in enumerate(donor['strings'])};notes=[];roles=[]
                    for ref,s,p,role in zip(target['member_refs'],target['strings'],target['pitches'],target['roles']):
                        notes.append(str(F(donor['pitches'][bystring[s]]if ref in target['inner_refs']else p)))
                        roles.append(donor['roles'][bystring[s]]if ref in target['inner_refs']else role)
                    support=layouts[tuple(notes)].setdefault(ident,dict(target_hypothesis_ref=ident,roles=roles,donor_hypothesis_refs=[],donor_group_refs=set()))
                    support['donor_hypothesis_refs'].append(donor['id']);support['donor_group_refs'].add(donor['group_ref'])
                    counts['hypothesis_donor_links']+=1;pairs.add((source['group_ref'],donor['group_ref']))
            if row['eligible_target_hypothesis_refs']!=eligible or enc(row['refusals'])!=enc(refusals):raise ValueError('Eligibility denominator differs')
            target_groups+=bool(eligible);expected=[]
            for pitches,supported in sorted(layouts.items()):
                first=next(iter(supported));changed=list(pitches)!=list(map(lambda p:str(F(p)),units[first]['pitches']));all_ids=set(supported)==set(ids)
                support=[]
                for ident,s in sorted(supported.items()):
                    s['donor_hypothesis_refs']=sorted(s['donor_hypothesis_refs']);s['donor_group_refs']=sorted(s['donor_group_refs']);support.append(s)
                preflight=physical_preflight(c,units[first],pitches)if changed else dict(stage='UNCHANGED')
                expected.append(dict(pitches=list(pitches),changed=changed,support=support,support_class='ALL_ENUMERATED_TARGET_ASSUMPTIONS'if all_ids else'SOME_ENUMERATED_TARGET_ASSUMPTIONS',preflight=preflight))
                counts['unique_layouts']+=1;counts['changed_layouts']+=int(changed);counts['all_assumption_layouts'if all_ids else'some_assumption_layouts']+=1;counts[preflight['stage']]+=1
            if enc(row['layouts'])!=enc(expected):raise ValueError('Concrete layout/support/preflight differs')
        counts.update(dict(exact_fit_groups=len(wanted),eligible_target_groups=target_groups,unique_source_target_pairs=len(pairs),unique_normalized_patterns=len(patterns),patterns_repeated_across_groups=sum(len(v)>1 for v in patterns.values())))
        if enc(dict(counts))!=enc(ledger['counts']):raise ValueError('Ledger totals differ')
    except Exception as e:issues.append(str(e))
    return dict(status='PASS_INDEPENDENT_PATTERN_LEDGER'if not issues else'FAIL',issues=issues,scope='Enumeration from the independently source-verified catalog; preflight only, no creative admission')
