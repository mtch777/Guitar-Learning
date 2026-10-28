"""Independent candidate-after audit for observed declared-degree placement.

Uses raw preceding-tier facts and accepted source/detector primitives. Never
imports allocation proposal, selection, application, or policy code.
"""
from collections import Counter
from fractions import Fraction as F
import json
from source_fact_tier1 import project_documents
from check_declared_chord_ownership import native_interpretations,CURRENT_PROFILE
from check_voicing_context import _nodes,_paths
from check_voicing_policy import _written_ties,encoded
from check_execution_dependencies import expected as execution_expected
from check_voicing_gesture import _classifications


def _group(nodes,refs):
    if type(refs)is not list or not refs or any(type(r)is not str for r in refs)or len(set(refs))!=len(refs):raise ValueError('Unique complete occurrence list required')
    chosen=[nodes[r]for r in refs]
    if len({(n['part'],n['onset'])for n in chosen})!=1:raise ValueError('One source coattack required')
    part,onset=chosen[0]['part'],chosen[0]['onset']
    if set(refs)!={r for r,n in nodes.items()if(n['part'],n['onset'])==(part,onset)}:raise ValueError('Incomplete coattack membership')
    return chosen


def _label(docs,refs):
    addresses={tuple(map(int,r.split(':')[2:6]))for r in refs}
    if len(addresses)!=1:raise ValueError('One declaring beat/voice required')
    part,bar,voice,beat=next(iter(addresses));p=docs[f'track-{part}.json'];b=p['measures'][bar-1]['voices'][voice]['beats'][beat]
    text=b.get('chord',{}).get('text');h=native_interpretations(text,CURRENT_PROFILE)
    if len(h)!=1:raise ValueError('Unique supported literal chord required')
    return p,b,text,h[0]


def _roles(nodes,h):
    roles=[]
    for n in nodes:
        if n['pitch']is None or n['pitch'].denominator!=1:raise ValueError('Known integral written pitch required')
        matches=[(token,semitones)for token,semitones in h['degrees']if(n['pitch']-h['root_pc']-semitones)%12==0]
        if len(matches)!=1:raise ValueError('Unique supported formula degree required')
        token,offset=matches[0];roles.append((token,int((n['pitch']-h['root_pc']-offset)/12)))
    if len({int(n['pitch']%12)for n in nodes})<2:raise ValueError('At least two observed pitch classes required')
    if {int(n['pitch']%12)for n in nodes}!=set(h['pcs']):raise ValueError('Exact observed formula support required')
    if h['slash_bass_pc']is not None and min(n['pitch']for n in nodes)%12!=h['slash_bass_pc']:raise ValueError('Explicit slash bass conflict')
    return roles


def nominal_contribution(before,after,selected):
    """Pointwise target multiset equality; outside uncertainty cancels, never guessed."""
    selected=set(selected);issues=[];cells=[]
    def typed(value):
        if isinstance(value,F):return ['rational',str(value)]
        if type(value)is dict:return ['dict',[[k,typed(v)]for k,v in sorted(value.items())]]
        if type(value)is list:return ['list',[typed(v)for v in value]]
        return [type(value).__name__,value]
    if not selected or set(before)!=set(after)or not selected<=set(before):return dict(status='FAIL',issues=['SOURCE_NODE_INVENTORY_CHANGED'],cells=[],unchanged_outside_uncertainty_refs=[])
    for ref in set(before)-selected:
        if typed(before[ref])!=typed(after[ref]):issues.append('OUTSIDE_NODE_CHANGED:'+ref)
    points=set()
    for ref in selected:
        for table in (before,after):
            n=table[ref];pitch=n.get('pitch')
            if pitch is None or type(pitch)is bool or F(pitch).denominator!=1:issues.append('UNKNOWN_SELECTED_PITCH:'+ref)
            if F(n['duration'])<=0:issues.append('INVALID_SELECTED_DURATION:'+ref)
            points.update((F(n['onset']),F(n['onset'])+F(n['duration'])))
        if before[ref]['onset']!=after[ref]['onset']or before[ref]['duration']!=after[ref]['duration']:issues.append('SELECTED_CLOCK_CHANGED:'+ref)
    if issues:return dict(status='FAIL',issues=sorted(set(issues)),cells=[],unchanged_outside_uncertainty_refs=[])
    lo,hi=min(points),max(points)
    for ref,n in before.items():
        if ref not in selected and n['onset']<hi and n['onset']+n['duration']>lo:points.update((max(lo,n['onset']),min(hi,n['onset']+n['duration'])))
    uncertain=set()
    for start,end in zip(sorted(points),sorted(points)[1:]):
        if end<=start:continue
        def contribution(table):return Counter(int(table[r]['pitch']%12)for r in selected if table[r]['onset']<end and table[r]['onset']+table[r]['duration']>start)
        a,b=contribution(before),contribution(after)
        if a!=b:issues.append('TARGET_WRITTEN_PC_MULTISET_CHANGED')
        outside=[r for r,n in before.items()if r not in selected and n['onset']<end and n['onset']+n['duration']>start]
        unknown=[r for r in outside if before[r].get('pitch')is None or before[r].get('reasons')or type(before[r].get('instrument'))is not int or before[r].get('instrument')not in range(128)and before[r].get('instrument')!=1024]
        uncertain.update(unknown)
        cells.append(dict(start_q=str(start),end_q=str(end),target_before=dict(sorted(a.items())),target_after=dict(sorted(b.items())),unchanged_outside_refs=sorted(outside),unchanged_outside_uncertainty_refs=sorted(unknown)))
    return dict(status='PASS_EXACT_NOMINAL_CONTRIBUTION'if not issues else'FAIL',issues=sorted(set(issues)),cells=cells,unchanged_outside_uncertainty_refs=sorted(uncertain),all_unchanged_context_completions_invariant=not issues,scope='Exact written target contribution and outside projection, not known acoustic harmony or performed endpoints')


def check(before_T1,after_T1,target_refs,donor_refs,typed_nominal=False):
    issues=[];witnesses=[];changed=[];touched=set()
    try:
        if type(typed_nominal)is not bool:raise ValueError('Typed nominal permission must be bool')
        docs,lower,nodes,rests=_nodes(before_T1);after_docs,after_lower,new_nodes,new_rests=_nodes(after_T1)
        target=_group(nodes,target_refs);donor=_group(nodes,donor_refs);selected=set(target_refs)
        if selected&set(donor_refs):raise ValueError('Leave-target-out whole source donor required')
        part,beat,text,h=_label(docs,target_refs);dp,db,dt,dh=_label(docs,donor_refs)
        if type(part.get('instrumentId'))is not int or not 24<=part['instrumentId']<=39:raise ValueError('Declared allocation guitar scope required')
        if any(b.get('sustainPedal')is True for m in part.get('measures',[])for v in m.get('voices',[])for b in v.get('beats',[])):raise ValueError('Part contains unmodeled pedal sounding end')
        if any(set(b.get('chord',{}))-{'text','width'}for b in (beat,db)):raise ValueError('Uninterpreted chord diagram or annotation fields')
        if target[0]['part']!=donor[0]['part']or h['root_pc']!=dh['root_pc']or h['kind']!=dh['kind']or h['degrees']!=dh['degrees']:raise ValueError('Same source part/root/kind/formula required')
        if len(target)!=len(donor):raise ValueError('Source cardinality mismatch')
        for p in (part,dp):
            capo=p.get('capo')
            if capo is not None and not(type(capo)in(int,float)and capo==0):raise ValueError('Unverified capo label convention')
        for ref in target_refs+donor_refs:
            pid,bar,voice,bi,ni=map(int,ref.split(':')[2:]);note=docs[f'track-{pid}.json']['measures'][bar-1]['voices'][voice]['beats'][bi]['notes'][ni]
            if any(k in note for k in ('leftFinger','rightFinger','fingering')):raise ValueError('Source finger declaration is not coupled to this release')
            if note.get('spn')is not None or note.get('courtesyAccidental')is True:raise ValueError('Source pitch/spelling declaration is not coupled to this release')
        if any(n['reasons']for n in target+donor):raise ValueError('Unresolved target/donor execution')
        if any(n['duration']<=0 for n in target+donor):raise ValueError('Positive written duration required')
        for p,b in ((part,beat),(dp,db)):
            if b.get('sustainPedal')is True:raise ValueError('Pedal sounding end unknown')
        old_roles=_roles(target,h);source_roles=_roles(donor,dh);new_target=[new_nodes[r]for r in target_refs];new_roles=_roles(new_target,h)
        if Counter(t for t,_ in old_roles)!=Counter(t for t,_ in new_roles)or Counter(t for t,_ in source_roles)!=Counter(t for t,_ in old_roles):issues.append('DEGREE_MULTISET_CHANGED')
        if min(n['pitch']for n in target)!=min(n['pitch']for n in new_target):issues.append('BASS_PITCH_CHANGED')
        old_ties=_written_ties(docs,lower['events']);new_ties=_written_ties(after_docs,after_lower['events'])
        if encoded(old_ties)!=encoded(new_ties):issues.append('TIE_RELATIONSHIPS_CHANGED')
        old_execution=execution_expected(before_T1);new_execution=execution_expected(after_T1)
        if encoded(old_execution['signature'])!=encoded(new_execution['signature']):issues.append('EXECUTION_RELATIONSHIPS_CHANGED')
        pinned={ref for link in old_ties['links']for ref in(link['origin'],link['destination'])}|{r['destination']for r in old_ties['unresolved']}|set(old_execution['pinned_members'])
        allowed={f"track-{int(r.split(':')[2])}.json#/measures/{int(r.split(':')[3])-1}/voices/{r.split(':')[4]}/beats/{r.split(':')[5]}/notes/{r.split(':')[6]}/fret"for r in target_refs}
        if encoded({k:v for k,v in before_T1.items()if k!='facts'})!=encoded({k:v for k,v in after_T1.items()if k!='facts'}):issues.append('SOURCE_HEADER_CHANGED')
        a,b=before_T1['facts'],after_T1['facts']
        if [r['id']for r in a]!=[r['id']for r in b]:raise ValueError('Source fact order/inventory changed')
        for x,y in zip(a,b):
            if encoded(x)==encoded(y):continue
            if x['id']not in allowed or encoded({k:v for k,v in x.items()if k!='value'})!=encoded({k:v for k,v in y.items()if k!='value'}):issues.append('LOCKED_SOURCE_FACT_CHANGED:'+x['id'])
        if set(nodes)!=set(new_nodes):raise ValueError('Occurrence inventory changed')
        source_strings={n['string']:n for n in donor}
        if len(source_strings)!=len(donor)or len({n['string']for n in target})!=len(target)or set(source_strings)!={n['string']for n in target}:raise ValueError('Exact unique fixed-string correspondence required')
        for n in target:
            m=new_nodes[n['id']];d=source_strings[n['string']]
            if m['string']!=n['string']:issues.append('STRINGS_LOCKED')
            if m['pitch']!=d['pitch']:issues.append('NO_OBSERVED_WHOLE_FIXED_STRING_LAYOUT')
            if m['pitch']!=n['pitch']:
                changed.append(n['id'])
                if n['id']in pinned:issues.append('PINNED_EXECUTION_CHANGED')
            for ref,entry,document in ((n['id'],m,after_docs),(d['id'],d,docs)):
                pid,bar,voice,bi,ni=map(int,ref.split(':')[2:]);p=document[f'track-{pid}.json'];note=p['measures'][bar-1]['voices'][voice]['beats'][bi]['notes'][ni];fret=F(str(note['fret']));tuning=p.get('tuning');string=note['string']
                if type(string)is not int or type(tuning)is not list or not 0<=string<len(tuning):raise ValueError('Missing physical string/tuning')
                if F(str(tuning[string]))+F(str(p.get('capo')or 0))+fret!=entry['pitch']:issues.append('PHYSICAL_EQUATION_CONFLICT')
                limit=p.get('frets')
                if fret<0 or fret.denominator!=1 or(type(limit)is int and limit>0 and fret>limit):issues.append('INVALID_OBSERVED_OR_RESULTING_FRET')
            for other in new_nodes.values():
                if other['id']!=m['id']and other['part']==m['part']and other['string']==m['string']and other['onset']<m['onset']+m['duration']and other['onset']+other['duration']>m['onset']:issues.append('OCCUPIED_STRING')
        before_paths=_paths(nodes,rests,typed_nominal);after_paths=_paths(new_nodes,new_rests,typed_nominal)
        if set(before_paths)!=set(after_paths):raise ValueError('Fixed-lane path centers changed')
        touched={key for key in before_paths if set(changed)&(set(before_paths[key]['refs'])|set(after_paths[key]['refs']))}
        excluded={r for key in touched for r in before_paths[key]['refs']+after_paths[key]['refs']}
        for key in touched:
            old,new=before_paths[key],after_paths[key]
            if old['reasons']or new['reasons']:issues.extend(old['reasons']+new['reasons']);continue
            if old['signature']==new['signature']:continue
            support=[p['refs']for p in before_paths.values()if not p['reasons']and p['signature']==new['signature']and not excluded.intersection(p['refs'])]
            if not support:issues.append('NO_INDEPENDENT_SOURCE_'+key[0].upper())
            else:witnesses.append(dict(center=key[1],kind=key[0],source_refs=support))
        if _classifications(nodes)!=_classifications(new_nodes):issues.append('COATTACK_TECHNIQUE_CLASS_CHANGED')
        from freeze_technique_baseline import retained
        if encoded([t['approved_pedal_phrases']for t in retained(docs)['tracks']])!=encoded([t['approved_pedal_phrases']for t in retained(after_docs)['tracks']]):issues.append('APPROVED_PEDAL_CHANGED')
        contribution=nominal_contribution(nodes,new_nodes,selected)
        issues.extend(contribution['issues'])
        return dict(status='PASS_LOCKED_DECLARED_ALLOCATION'if not issues else'FAIL',issues=sorted(set(issues)),changed_refs=changed,affected_paths=len(touched),witness_count=len(witnesses),typed_nominal=typed_nominal,witnesses=witnesses,nominal_contribution=contribution,unchanged_outside_uncertainty_refs=contribution['unchanged_outside_uncertainty_refs'],scope='Source-observed whole fixed-string degree placement; no identified melody, acoustic harmony, preference or artist-fit claim')
    except Exception as error:return dict(status='FAIL',issues=sorted(set(issues+[type(error).__name__+': '+str(error)])),changed_refs=changed,witness_count=len(witnesses))


def proposal_inventory(before_T1):
    """Raw source denominator BEFORE outcome/path filtering; no proposal calls."""
    docs,lower,nodes,rests=_nodes(before_T1)
    ties=_written_ties(docs,lower['events']);execution=execution_expected(before_T1)
    pinned={r for e in ties['links']for r in(e['origin'],e['destination'])}|{e['destination']for e in ties['unresolved']}|set(execution['pinned_members'])
    by_group={}
    for ref,n in nodes.items():by_group.setdefault((n['part'],int(ref.split(':')[3]),n['onset']),[]).append(ref)
    units=[];fallback=[]
    for ordinal,(key,refs) in enumerate(sorted(by_group.items(),key=lambda kv:(kv[0][2],kv[0][1],kv[0][0]))):
        try:
            part,beat,text,h=_label(docs,refs);chosen=[nodes[r]for r in refs]
            capo=part.get('capo')
            if capo is not None and not(type(capo)in(int,float)and capo==0):raise ValueError('Unverified capo')
            if any(n['duration']<=0 or 'UNCERTAIN_SOURCE_CLOCK'in n['reasons']for n in chosen):raise ValueError('Invalid owner timing')
            roles=_roles(chosen,h)
        except (ValueError,KeyError,TypeError,AttributeError) as exc:
            fallback.append(dict(group_ref='coattack:'+str(ordinal),member_refs=refs,reason=str(exc)));continue
        reasons={r for n in chosen for r in n['reasons']}
        strings=[n['string']for n in chosen]
        if any(type(v)is not int or v<0 for v in strings)or len(set(strings))!=len(strings):reasons.add('NONUNIQUE_OR_UNKNOWN_STRING')
        if len({n['duration']for n in chosen})!=1:reasons.add('NONUNIFORM_WRITTEN_CHORD_DURATION')
        if set(refs)&pinned:reasons.add('PINNED_EXECUTION')
        if type(part.get('instrumentId'))is not int or not 24<=part['instrumentId']<=39:reasons.add('OUTSIDE_GUITAR_SCOPE')
        if any(b.get('sustainPedal')is True for m in part.get('measures',[])for v in m.get('voices',[])for b in v.get('beats',[])):reasons.add('UNKNOWN_PEDAL_SOUNDING_END')
        if set(beat.get('chord',{}))-{'text','width'}:reasons.add('UNINTERPRETED_CHORD_DIAGRAM')
        for ref in refs:
            pid,bar,voice,bi,ni=map(int,ref.split(':')[2:]);note=docs[f'track-{pid}.json']['measures'][bar-1]['voices'][voice]['beats'][bi]['notes'][ni]
            if note.get('spn')is not None or note.get('courtesyAccidental')is True:reasons.add('UNCOUPLED_SOURCE_PITCH_SPELLING')
            if any(k in note for k in('leftFinger','rightFinger','fingering')):reasons.add('UNCOUPLED_FINGER_DECLARATION')
            fret=F(str(note['fret']));limit=part.get('frets')
            if fret<0 or fret.denominator!=1 or(type(limit)is int and limit>0 and fret>limit):reasons.add('INVALID_SOURCE_FRET')
        match_key=encoded([key[0],h['root_pc'],h['kind'],len(refs),sorted(Counter(t for t,o in roles).items()),str(min(n['pitch']for n in chosen)),sorted(strings)])
        units.append(dict(id=refs[0],group_ref='coattack:'+str(ordinal),member_refs=refs,key=match_key,reasons=sorted(reasons),roles=[dict(degree_token=t,relative_octaves=o)for t,o in roles],strings=strings))
    pools={}
    for u in units:
        if not u['reasons']:pools.setdefault(u['key'],[]).append(u)
    links=[dict(target_ref=a['id'],donor_ref=b['id'],changed=[dict(zip(b['strings'],b['roles']))[s]for s in a['strings']]!=a['roles'])for values in pools.values()for a in values for b in values]
    return dict(status='PASS_INDEPENDENT_RAW_PROPOSAL_INVENTORY',units=units,fallback_groups=fallback,proposed_links=links,counts=dict(all_groups=len(by_group),declared_groups=len(units),eligible_groups=sum(not u['reasons']for u in units),proposed_links=len(links),changed_proposed_links=sum(r['changed']for r in links)),scope='Complete raw source/key donor links before physical-after/context outcome verification; no independent claim for every rejected-after predicate')
