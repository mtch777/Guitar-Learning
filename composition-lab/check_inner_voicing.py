"""Independent raw-source verification of coupled inner-voicing choices.

No producer catalog/options/apply imports. Extremes are literal pitch bounds,
not identified melody/bass voices. Geometry is observed mechanical evidence.
"""
from collections import Counter,defaultdict
from bisect import bisect_left,bisect_right
from fractions import Fraction as F
from check_voicing_context import _nodes,_paths
from check_declared_allocation import _label,_roles,nominal_contribution,proposal_inventory
from check_voicing_policy import _written_ties,encoded
from check_execution_dependencies import expected as execution_expected
from check_voicing_gesture import _classifications


def _group(nodes,refs,physical=False):
    if type(refs)is not list or not refs or any(type(r)is not str for r in refs)or len(set(refs))!=len(refs):raise ValueError('Exact unique whole source group refs required')
    rows=[nodes[r]for r in refs];key={(n['part'],None if physical else int(n['id'].split(':')[3]),n['onset'])for n in rows}
    if len(key)!=1:raise ValueError('One coattack required')
    k=next(iter(key))
    if set(refs)!={r for r,n in nodes.items()if(n['part'],None if physical else int(r.split(':')[3]),n['onset'])==k}:raise ValueError('Incomplete coattack')
    return rows


def _note(docs,ref):
    p,bar,v,b,n=map(int,ref.split(':')[2:]);part=docs[f'track-{p}.json'];beat=part['measures'][bar-1]['voices'][v]['beats'][b]
    return part,beat,beat['notes'][n]


def _settings(part):
    instrument=part.get('instrumentId');tuning=part.get('tuning');capo=part.get('capo')
    if capo is None:capo=0
    if type(instrument)is not int or not 24<=instrument<=39 or type(tuning)is not list or not tuning:raise ValueError('Known guitar settings required')
    if any(type(p)not in(int,float)for p in tuning)or type(capo)not in(int,float):raise ValueError('Typed physical settings required')
    return [instrument,[str(F(str(p)))for p in tuning],str(F(str(capo))) ]


def _overlap(nodes,refs):
    rows=[nodes[r]for r in refs];lo=min(n['onset']for n in rows);hi=max(n['onset']+n['duration']for n in rows);part=rows[0]['part']
    return sorted(r for r,n in nodes.items()if r not in refs and n['part']==part and ((n['duration']>0 and n['onset']<hi and n['onset']+n['duration']>lo)or(n['duration']==0 and lo<=n['onset']<hi)))


def _overlap_index(nodes):
    bypart=defaultdict(lambda:dict(starts=[],ends=[],points=[]))
    for n in nodes.values():
        row=bypart[n['part']]
        if n['duration']>0:row['starts'].append(n['onset']);row['ends'].append(n['onset']+n['duration'])
        elif n['duration']==0:row['points'].append(n['onset'])
    for row in bypart.values():
        for values in row.values():values.sort()
    return bypart


def _has_outside_overlap(nodes,refs,index):
    rows=[nodes[r]for r in refs];lo=min(n['onset']for n in rows);hi=max(n['onset']+n['duration']for n in rows)
    if hi<=lo:return bool(_overlap(nodes,refs))
    row=index[rows[0]['part']]
    count=bisect_left(row['starts'],hi)-bisect_right(row['ends'],lo)+bisect_left(row['points'],hi)-bisect_left(row['points'],lo)
    count-=sum((n['duration']>0 and n['onset']<hi and n['onset']+n['duration']>lo)or(n['duration']==0 and lo<=n['onset']<hi)for n in rows)
    return count>0


def _physical(docs,refs,nodes):
    strings=[];frets=[];settings=None
    for ref in refs:
        part,beat,note=_note(docs,ref);current=_settings(part)
        if settings is None:settings=current
        if current!=settings:raise ValueError('One physical setting per group')
        string=note.get('string');fret=note.get('fret')
        if type(string)is not int or not 0<=string<len(current[1])or type(fret)not in(int,float):raise ValueError('Known string/fret required')
        q=F(str(fret));limit=part.get('frets')
        if q<0 or q.denominator!=1 or(type(limit)is int and limit>0 and q>limit):raise ValueError('Invalid declared-bound physical position')
        if F(current[1][string])+F(current[2])+q!=nodes[ref]['pitch']:raise ValueError('Physical pitch equation conflict')
        strings.append(string);frets.append(q)
    if len(set(strings))!=len(strings):raise ValueError('Unique strings required')
    return settings,dict(zip(strings,frets))


def _excluded(nodes,rests,refs):
    paths=_paths(nodes,rests,True);selected=set(refs)
    return selected|{r for p in paths.values()if selected&set(p['refs'])for r in p['refs']}


def _plain_reasons(docs,nodes,refs,pinned):
    reasons={r for ref in refs for r in nodes[ref]['reasons']}
    if set(refs)&pinned:reasons.add('PINNED_EXECUTION')
    if any(nodes[r]['pitch']is None or F(nodes[r]['pitch']).denominator!=1 for r in refs):reasons.add('UNKNOWN_WRITTEN_PITCH')
    if any(nodes[r]['duration']<=0 for r in refs)or len({nodes[r]['duration']for r in refs})!=1:reasons.add('NONUNIFORM_OR_NONPOSITIVE_DURATION')
    part=_note(docs,refs[0])[0]
    if any(b.get('sustainPedal')is True for m in part.get('measures',[])for v in m.get('voices',[])for b in v.get('beats',[])):reasons.add('UNKNOWN_PEDAL_SOUNDING_END')
    for ref in refs:
        _,beat,note=_note(docs,ref)
        if note.get('spn')is not None or note.get('courtesyAccidental')is True:reasons.add('UNCOUPLED_SOURCE_PITCH_SPELLING')
        if any(k in note for k in('leftFinger','rightFinger','fingering')):reasons.add('UNCOUPLED_FINGER_DECLARATION')
        if isinstance(beat.get('chord'),dict)and set(beat['chord'])-{'text','width'}:reasons.add('UNINTERPRETED_CHORD_DIAGRAM')
    try:_physical(docs,refs,nodes)
    except (KeyError,TypeError,ValueError)as e:reasons.add(str(e))
    return sorted(reasons)


def _prepare(tier1):
    docs,lower,nodes,rests=_nodes(tier1);ties=_written_ties(docs,lower['events']);execution=execution_expected(tier1)
    pinned={r for e in ties['links']for r in(e['origin'],e['destination'])}|{e['destination']for e in ties['unresolved']}|set(execution['pinned_members'])
    native=proposal_inventory(tier1);units=[];interval_index=_overlap_index(nodes);neighbors=defaultdict(set)
    for path in _paths(nodes,rests,True).values():
        for ref in path['refs']:neighbors[ref].update(path['refs'])
    for base in native['units']:
        refs=base['member_refs'];rows=[nodes[r]for r in refs];lo=min(n['pitch']for n in rows);hi=max(n['pitch']for n in rows)
        outer=[r for r in refs if nodes[r]['pitch']in(lo,hi)];inner=[r for r in refs if r not in outer];part,beat,text,h=_label(docs,refs)
        reasons=list(base['reasons'])
        if not inner:reasons.append('NO_STRICT_INNER_COMPONENT')
        if _has_outside_overlap(nodes,refs,interval_index):reasons.append('OUTSIDE_SAME_PART_OVERLAP')
        units.append(dict(id=base['id'],group_ref=base['group_ref'],part_id=rows[0]['part'],member_refs=refs,outer_refs=outer,inner_refs=inner,inner_strings=[nodes[r]['string']for r in inner],strings=base['strings'],roles=base['roles'],pitches=[str(nodes[r]['pitch'])for r in refs],family=[rows[0]['part'],h['root_pc'],h['kind']],root_pc=h['root_pc'],kind=h['kind'],excluded_neighborhood=sorted(set(refs)|{r for ref in refs for r in neighbors[ref]}),base_reasons=base['reasons'],reasons=sorted(set(reasons))))
    groups=defaultdict(list)
    for ref,n in nodes.items():groups[n['part'],n['onset']].append(ref)
    geometries=[]
    for ordinal,(key,refs)in enumerate(sorted(groups.items(),key=lambda kv:(kv[0][1],kv[0][0]))):
        reasons=_plain_reasons(docs,nodes,refs,pinned)
        if _has_outside_overlap(nodes,refs,interval_index):reasons.append('OUTSIDE_SAME_PART_OVERLAP')
        settings=None;frets={}
        try:settings,frets=_physical(docs,refs,nodes)
        except (KeyError,TypeError,ValueError):pass
        shape_key=None
        if not reasons and frets:
            order=sorted(frets);origin=min(frets.values())
            shape_key=encoded(settings+[order,[str(frets[s]-origin)for s in order],[frets[s]==0 for s in order]])
        geometries.append(dict(key=shape_key,id=refs[0],group_ref='coattack:'+str(ordinal),member_refs=refs,settings=settings,frets={str(s):str(f)for s,f in frets.items()},reasons=sorted(set(reasons))))
    return docs,lower,nodes,rests,ties,execution,pinned,units,geometries


def inventory(tier1):
    """Complete source eligibility and pre-realization component denominator."""
    docs,lower,nodes,rests,ties,execution,pinned,units,geometries=_prepare(tier1);links=[]
    for target in units:
        if target['reasons']:continue
        excluded=set(target['excluded_neighborhood']);strings=target['inner_strings']
        for donor in units:
            if donor['base_reasons']or(target['part_id'],target['root_pc'],target['kind'])!=(donor['part_id'],donor['root_pc'],donor['kind'])or excluded&set(donor['member_refs']):continue
            bystring={nodes[r]['string']:r for r in donor['member_refs']}
            if not set(strings)<=set(bystring):continue
            selected=[bystring[s]for s in strings];lo=min(nodes[r]['pitch']for r in donor['member_refs']);hi=max(nodes[r]['pitch']for r in donor['member_refs'])
            if any(not lo<nodes[r]['pitch']<hi for r in selected):continue
            links.append(dict(target_ref=target['id'],donor_ref=donor['id'],source_inner_refs=selected,changed=any(nodes[t]['pitch']!=nodes[s]['pitch']for t,s in zip(target['inner_refs'],selected))))
    return dict(status='PASS_INDEPENDENT_INNER_SOURCE_INVENTORY',units=units,geometries=geometries,component_links=links,counts=dict(declared_groups=len(units),eligible_targets=sum(not u['reasons']for u in units),raw_geometry_groups=len(geometries),eligible_geometry_groups=sum(not g['reasons']for g in geometries),component_links=len(links),changed_component_links=sum(r['changed']for r in links)),scope='Complete source structural/component denominator before after-state formula/geometry/technique checks; no preference or artistic claim')


def check(before_T1,after_T1,target_refs,donor_refs,geometry_refs,*,contact_coverage=None):
    issues=[];novel=[];changed=[]
    try:
        docs,lower,nodes,rests,ties,execution,pinned,units,geometries=_prepare(before_T1)
        after_docs,after_lower,new_nodes,new_rests=_nodes(after_T1)
        target=_group(nodes,target_refs);donor=_group(nodes,donor_refs)
        if contact_coverage is None:geometry=_group(nodes,geometry_refs,physical=True)
        elif type(geometry_refs)is not list or geometry_refs:raise ValueError('Contact route requires empty geometry_refs')
        unit=next((u for u in units if set(u['member_refs'])==set(target_refs)),None)
        dunit=next((u for u in units if set(u['member_refs'])==set(donor_refs)),None)
        geom=next((g for g in geometries if set(g['member_refs'])==set(geometry_refs)),None)
        if unit is None or unit['reasons']:raise ValueError('Ineligible complete declared target')
        if dunit is None or dunit['base_reasons']:raise ValueError('Ineligible complete source component')
        if contact_coverage is None and(geom is None or geom['reasons']):raise ValueError('Ineligible whole geometry witness')
        if(unit['part_id'],unit['root_pc'],unit['kind'])!=(dunit['part_id'],dunit['root_pc'],dunit['kind']):raise ValueError('Source root/formula/part mismatch')
        excluded=set(unit['excluded_neighborhood'])
        if excluded&set(donor_refs)or excluded&set(geometry_refs):raise ValueError('Source evidence inside complete target neighborhood')
        part,beat,text,h=_label(docs,target_refs);dp,db,dt,dh=_label(docs,donor_refs)
        before_roles=_roles(target,h);after_roles=_roles([new_nodes[r]for r in target_refs],h)
        outer=set(unit['outer_refs']);inner=unit['inner_refs'];inner_strings=unit['inner_strings'];low=min(n['pitch']for n in target);high=max(n['pitch']for n in target)
        if any(new_nodes[r]['pitch']!=nodes[r]['pitch']for r in outer):issues.append('PROTECTED_OUTER_PITCH_CHANGED')
        source_bystring={nodes[r]['string']:r for r in donor_refs};dlo=min(n['pitch']for n in donor);dhi=max(n['pitch']for n in donor)
        for r in inner:
            s=nodes[r]['string'];source=source_bystring.get(s)
            if source is None or not dlo<nodes[source]['pitch']<dhi:issues.append('NO_STRICT_SOURCE_INNER_COMPONENT');continue
            if new_nodes[r]['pitch']!=nodes[source]['pitch']:issues.append('COUPLED_SOURCE_COMPONENT_MISMATCH')
            if not low<new_nodes[r]['pitch']<high:issues.append('INNER_OUTSIDE_LITERAL_BOUNDARIES')
        for ai,a in enumerate(inner):
            for b in inner[ai+1:]:
                if(nodes[a]['pitch']-nodes[b]['pitch'])*(new_nodes[a]['pitch']-new_nodes[b]['pitch'])<0:issues.append('INNER_PITCH_ORDER_REVERSED')
        allowed={f"track-{int(r.split(':')[2])}.json#/measures/{int(r.split(':')[3])-1}/voices/{r.split(':')[4]}/beats/{r.split(':')[5]}/notes/{r.split(':')[6]}/fret"for r in inner}
        if encoded({k:v for k,v in before_T1.items()if k!='facts'})!=encoded({k:v for k,v in after_T1.items()if k!='facts'}):issues.append('SOURCE_HEADER_CHANGED')
        if [r['id']for r in before_T1['facts']]!=[r['id']for r in after_T1['facts']]:raise ValueError('Source fact inventory/order changed')
        for a,b in zip(before_T1['facts'],after_T1['facts']):
            if encoded(a)==encoded(b):continue
            if a['id']not in allowed or encoded({k:v for k,v in a.items()if k!='value'})!=encoded({k:v for k,v in b.items()if k!='value'}):issues.append('LOCKED_SOURCE_FACT_CHANGED:'+a['id'])
        settings,outfrets=_physical(after_docs,target_refs,new_nodes)
        if contact_coverage is not None:
            from check_fretting_contacts import check as contact_check
            _group(new_nodes,target_refs,physical=True)
            original_settings,original_frets=_physical(docs,target_refs,nodes)
            if settings!=original_settings or set(outfrets)!=set(original_frets):issues.append('CONTACT_SETTINGS_OR_STRINGS_CHANGED')
            physical_reasons=_plain_reasons(after_docs,new_nodes,target_refs,pinned)
            if _has_outside_overlap(new_nodes,target_refs,_overlap_index(new_nodes)):physical_reasons.append('OUTSIDE_SAME_PART_OVERLAP')
            issues.extend(physical_reasons)
            required=[dict(string=s,fret=int(f))for s,f in sorted(outfrets.items())]
            contact_verdict=contact_check(required,contact_coverage,max_digits=4,search_limit=100000)
            if contact_coverage.get('status')!='COVERED'or contact_verdict['status']!='PASS_INDEPENDENT_FRETTING_CONTACTS'or not contact_verdict['complete']:
                issues.append('CONTACT_COVERAGE_NOT_VERIFIED')
                issues.extend(contact_verdict['issues'])
        else:
            gsettings,gfrets=_physical(docs,geometry_refs,nodes)
            if settings!=gsettings or set(outfrets)!=set(gfrets):issues.append('GEOMETRY_SETTINGS_OR_STRINGS_MISMATCH')
            else:
                deltas={outfrets[s]-gfrets[s]for s in outfrets}
                if len(deltas)!=1:issues.append('NO_UNIFORM_FRET_GEOMETRY_TRANSLATION')
                if any((outfrets[s]==0)!=(gfrets[s]==0)for s in outfrets):issues.append('GEOMETRY_OPEN_STATUS_CHANGED')
        if set(nodes)!=set(new_nodes):raise ValueError('Source occurrence inventory changed')
        for r in target_refs:
            if nodes[r]['string']!=new_nodes[r]['string']:issues.append('SOURCE_STRINGS_CHANGED')
            if nodes[r]['pitch']!=new_nodes[r]['pitch']:
                changed.append(r)
                if r in pinned:issues.append('PINNED_EXECUTION_CHANGED')
        if encoded(_written_ties(after_docs,after_lower['events']))!=encoded(ties):issues.append('TIE_RELATIONSHIPS_CHANGED')
        if encoded(execution_expected(after_T1)['signature'])!=encoded(execution['signature']):issues.append('EXECUTION_RELATIONSHIPS_CHANGED')
        bp=_paths(nodes,rests,True);ap=_paths(new_nodes,new_rests,True)
        if set(bp)!=set(ap):raise ValueError('Written path topology changed')
        touched={k for k in bp if set(changed)&(set(bp[k]['refs'])|set(ap[k]['refs']))}
        for k in touched:
            if bp[k]['reasons']or ap[k]['reasons']:issues.extend(bp[k]['reasons']+ap[k]['reasons']);continue
            if bp[k]['signature']!=ap[k]['signature']:
                witness=[p['refs']for p in bp.values()if not p['reasons']and p['signature']==ap[k]['signature']and not excluded&set(p['refs'])]
                if not witness:novel.append(dict(kind=k[0],center=k[1],status='UNWITNESSED_PLAIN_STRING_CONTEXT_NOT_MELODY_IDENTITY'))
        contribution=nominal_contribution(nodes,new_nodes,set(target_refs));cissues=list(contribution['issues'])
        if contribution['cells']and all(set(c['target_before'])==set(c['target_after'])for c in contribution['cells']):cissues=[x for x in cissues if x!='TARGET_WRITTEN_PC_MULTISET_CHANGED']
        else:cissues.append('TARGET_WRITTEN_PC_SET_CHANGED')
        issues.extend(cissues)
        if _classifications(nodes)!=_classifications(new_nodes):issues.append('COATTACK_TECHNIQUE_CLASS_CHANGED')
        from freeze_technique_baseline import retained
        if encoded([t['approved_pedal_phrases']for t in retained(docs)['tracks']])!=encoded([t['approved_pedal_phrases']for t in retained(after_docs)['tracks']]):issues.append('APPROVED_PEDAL_CHANGED')
        result=dict(status='PASS_LOCKED_INNER_VOICING'if not issues else'FAIL',issues=sorted(set(issues)),changed_refs=changed,protected_outer_refs=sorted(outer),source_inner_refs=[source_bystring.get(s)for s in inner_strings],geometry_refs=geometry_refs,novel_plain_contexts=novel,nominal_contribution=contribution,scope='Literal outer-envelope and source coupled inner degrees, doubling released. No identified melody, artist preference, acoustic or human-playability acceptance')
        if contact_coverage is not None:
            result.update(status='PASS_PROVISIONAL_INNER_CONTACTS'if not issues else'FAIL',human_playability='UNVERIFIED',contact_check=contact_verdict,
                scope='Provisional nominal contact coverage replaces only observed-whole-geometry evidence; all source/music/execution guards retained. Reach, comfort, movement, clean tone, melodic identity and artist fit unverified')
        return result
    except Exception as e:return dict(status='FAIL',issues=sorted(set(issues+[type(e).__name__+': '+str(e)])),changed_refs=changed,novel_plain_contexts=novel)
