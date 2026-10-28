"""Independent raw-source oracle for fixed-lane target-context obligations.

No imports of producer graph, path, option or candidate functions. Shares only
accepted source extraction/rest/expression predicates and independent tie rules.
"""
from collections import defaultdict
from fractions import Fraction as F
import json
from source_fact_tier1 import project_documents
from check_voicing_policy import _source_units, _written_ties, encoded
from check_family_policy import normalized_units


def _raw(docs,event):
    part=docs['track-'+str(event['part_id'])+'.json']
    beat=part['measures'][event['bar']-1]['voices'][event['voice']]['beats'][event['beat']]
    return part,beat,beat['notes'][event['note']]


def _nodes(tier1):
    from source_tie_tier1 import extract_documents
    docs=project_documents(tier1);lower=extract_documents(docs)
    from source_semantics import layout,rests
    from contextual_note_roles import source_refusals
    parts=[docs[k]for k in sorted((k for k in docs if k.startswith('track-')),key=lambda k:int(k[6:-5]))]
    headers,_=layout(parts);rest_rows=[];rest_bad=set()
    for part in parts:
        rows,rest_warnings=rests(part,headers)
        rest_rows.extend(dict(part_id=part['partId'],**row)for row in rows)
        rest_bad.update((part['partId'],w['bar'])for w in rest_warnings)
    warnings={w['bar']for field in ('layout_warnings','timing_warnings')for w in lower['source_coverage'][field]}
    by_id={e['id']:e for e in lower['events']};nodes={}
    for e in lower['events']:
        part,beat,note=_raw(docs,e);reasons=source_refusals(docs,by_id,[e['id']])
        for k in ('hp','tieOrigin','tieDestination','rest','fingerVibrato'):
            if k in note and note[k]is not False and note[k]is not None:reasons.append('NOTE_DEPENDENCY:'+k)
        for k in ('letRing','arpeggio','brushStroke','downArpeggio','slapping'):
            if k in beat and beat[k]is not False and beat[k]is not None and not(k=='downArpeggio'and beat[k]==0):reasons.append('BEAT_DEPENDENCY:'+k)
        if e['bar']in warnings:reasons.append('UNCERTAIN_SOURCE_CLOCK')
        if(e['part_id'],e['bar'])in rest_bad:reasons.append('CONFLICTING_SOURCE_REST')
        if e['pitch']is None or F(e['pitch']).denominator!=1:reasons.append('UNKNOWN_PITCH')
        if F(e['duration_q'])<=0:reasons.append('GRACE_OR_NONPOSITIVE_DURATION')
        string=note.get('string')
        if type(string)is not int or string<0:reasons.append('UNKNOWN_STRING_LANE')
        nodes[e['id']]=dict(id=e['id'],part=e['part_id'],voice=e['voice'],string=string,pitch=None if e['pitch']is None else F(e['pitch']),onset=F(e['onset_q']),duration=F(e['duration_q']),reasons=sorted(set(reasons)),note_declarations={k:v for k,v in note.items()if k not in('fret','string','spn','tieOrigin','tieDestination')},beat_declarations={k:v for k,v in beat.items()if k not in('notes','duration')},instrument=part.get('instrumentId'),dead_fret_declaration=dict(present='fret'in note,type=type(note.get('fret')).__name__,value=note.get('fret'))if note.get('dead')is True else None,pure_dead_nominal=note.get('dead')is True and e['pitch']is None and note.get('spn')is None and note.get('courtesyAccidental')is not True and type(part.get('instrumentId'))is int and 0<=part['instrumentId']<=127 and type(string)is int and string>=0)
    return docs,lower,nodes,rest_rows


def _paths(nodes,rests,typed_nominal=False):
    if type(typed_nominal)is not bool:raise ValueError('Typed nominal permission must be bool')
    def nominal_kind(n):
        if n is None:return 'BOUNDARY'
        if n.get('pure_dead_nominal')is True and n['pitch']is None:return 'UNPITCHED_DEAD'
        if n['pitch']is not None and F(n['pitch']).denominator==1 and n['note_declarations'].get('dead')is not True:return 'PITCHED'
        return 'UNKNOWN'
    lanes=defaultdict(list);out={};unknown=[n for n in nodes.values()if type(n['string'])is not int or n['string']<0]
    for n in nodes.values():lanes[n['part'],n['voice'],n['string']].append(n)
    for lane,values in lanes.items():
        values.sort(key=lambda n:(n['onset'],n['id']))
        for i,n in enumerate(values):
            windows={'edge':[n,values[i+1]if i+1<len(values)else None], 'triple':[values[i-1]if i else None,n,values[i+1]if i+1<len(values)else None]}
            if typed_nominal and nominal_kind(n)=='UNPITCHED_DEAD'and(i==0 or nominal_kind(values[i-1])!='UNPITCHED_DEAD'):
                stop=i+1
                while stop<len(values)and nominal_kind(values[stop])=='UNPITCHED_DEAD':stop+=1
                windows['unpitched_span']=[values[i-1]if i else None]+values[i:stop]+[values[stop]if stop<len(values)else None]
            for kind,window in windows.items():
                present=[x for x in window if x is not None]
                reasons=[r for x in present for r in x['reasons']if not(typed_nominal and nominal_kind(x)=='UNPITCHED_DEAD'and r in('UNKNOWN_PITCH','unresolved_sounding_pitch_dead'))]
                if typed_nominal and any(nominal_kind(x)=='UNKNOWN'for x in present):reasons.append('UNKNOWN_NOMINAL_SLOT')
                lo=None if window[0]is None else present[0]['onset'];hi=None if window[-1]is None else present[-1]['onset']+present[-1]['duration']
                if any((x['part'],x['voice'])==lane[:2]
                       and(lo is None or x['onset']>=lo or x['onset']+x['duration']>lo)
                       and(hi is None or x['onset']<hi)for x in unknown):reasons.append('UNKNOWN_LANE_ADJACENCY')
                gaps=[];motion=[];patterns=[]
                for a,b in zip(window,window[1:]):
                    if a is None or b is None:gaps.append(None);motion.append(None);patterns.append(None);continue
                    gap=b['onset']-a['onset']-a['duration'];gaps.append(str(gap));motion.append(None if a['pitch']is None or b['pitch']is None else str(b['pitch']-a['pitch']))
                    if b['onset']<=a['onset']or gap<0:reasons.append('AMBIGUOUS_OR_OVERLAPPING_LANE')
                    patterns.append(sorted([[str(F(r['onset_q'])-a['onset']),r['duration_q'],r['source']]for r in rests if(r['part_id'],r['voice'])==lane[:2]and F(r['onset_q'])<b['onset']and F(r['onset_q'])+F(r['duration_q'])>a['onset']]))
                signature=[kind,list(lane),[None if x is None or x['pitch']is None else str(x['pitch']%12)for x in window],motion,[None if x is None else str(x['duration'])for x in window],gaps,[None if x is None else x['note_declarations']for x in window],patterns,[None if x is None else x['beat_declarations']for x in window]]
                if typed_nominal and any(nominal_kind(x)=='UNPITCHED_DEAD'for x in present):
                    # Keep the unpitched event in its original slot. Pair-index
                    # coordinates explicitly distinguish bracketing from adjacency.
                    slot_kinds=[nominal_kind(x)for x in window]
                    known_indices=[i for i,k in enumerate(slot_kinds)if k=='PITCHED']
                    known_pairs=[[a,b,str(window[b]['pitch']-window[a]['pitch'])]for ai,a in enumerate(known_indices)for b in known_indices[ai+1:]]
                    dead_positions=[None if x is None or nominal_kind(x)!='UNPITCHED_DEAD'else x.get('dead_fret_declaration')for x in window]
                    signature=['typed-nominal-slots/1',signature,slot_kinds,known_pairs,dead_positions]
                out[kind,n['id']]=dict(signature=encoded(signature),refs=[x['id']for x in present],reasons=sorted(set(reasons)))
    return out


def check(tier1_before,tier1_after,target_refs,donor_refs,allow_string_changes=False):
    return check_many(tier1_before,tier1_after,[target_refs],[donor_refs],allow_string_changes)


def check_many(tier1_before,tier1_after,target_groups,donor_ids_by_group,allow_string_changes=False):
    """Independent shared validator: one whole after graph, never partial edits."""
    issues=[];witnesses=[];changed=[]
    try:
        if type(allow_string_changes)is not bool:raise ValueError('Explicit typed lane-topology permission required')
        if type(target_groups)is not list or not target_groups or type(donor_ids_by_group)is not list or len(target_groups)!=len(donor_ids_by_group):raise ValueError('Exact paired group lists required')
        for target_refs,donor_refs in zip(target_groups,donor_ids_by_group):
            if type(target_refs)is not list or not target_refs or any(type(r)is not str for r in target_refs)or len(set(target_refs))!=len(target_refs):raise ValueError('Exact unique target references required')
            if type(donor_refs)is not list or not donor_refs or any(type(r)is not str for r in donor_refs)or len(set(donor_refs))!=len(donor_refs):raise ValueError('Whole observed donor references required')
        flat=[r for group in target_groups for r in group]
        if len(set(flat))!=len(flat):raise ValueError('Overlapping target groups')
        docs,lower,nodes,rests=_nodes(tier1_before);after_docs,after_lower,new_nodes,new_rests=_nodes(tier1_after)
        units,_,ties,deps=normalized_units(docs);by_id={u['id']:u for u in units};targets=[]
        for group in target_groups:
            unit=next((u for u in units if set(u['member_refs'])==set(group)),None)
            if unit is None or unit['refusal_reasons']:raise ValueError('Target outside admitted complete source unit')
            targets.append(unit)
        refs=[ref for unit in targets for ref in unit['member_refs']];selected=set(refs)
        pinned={ref for unit in targets for field in ('locked_tie_members','locked_execution_members')for ref in unit[field]}
        allowed=set()
        for ref in refs:
            e=next(e for e in lower['events']if e['id']==ref)
            allowed.add('track-'+str(e['part_id'])+'.json#/measures/'+str(e['bar']-1)+'/voices/'+str(e['voice'])+'/beats/'+str(e['beat'])+'/notes/'+str(e['note'])+'/fret')
            if allow_string_changes:allowed.add('track-'+str(e['part_id'])+'.json#/measures/'+str(e['bar']-1)+'/voices/'+str(e['voice'])+'/beats/'+str(e['beat'])+'/notes/'+str(e['note'])+'/string')
        if encoded({k:v for k,v in tier1_before.items()if k!='facts'})!=encoded({k:v for k,v in tier1_after.items()if k!='facts'}):issues.append('SOURCE_HEADER_CHANGED')
        a=tier1_before['facts'];b=tier1_after['facts']
        if [r['id']for r in a]!=[r['id']for r in b]:raise ValueError('Source fact inventory/order changed')
        for old,new in zip(a,b):
            if encoded(old)==encoded(new):continue
            if old['id']not in allowed or encoded({k:v for k,v in old.items()if k!='value'})!=encoded({k:v for k,v in new.items()if k!='value'}):issues.append('LOCKED_SOURCE_FACT_CHANGED:'+old['id'])
        if set(nodes)!=set(new_nodes):raise ValueError('Source occurrence inventory changed')
        for ref in refs:
            n,m=nodes[ref],new_nodes[ref]
            if n['string']!=m['string']and not allow_string_changes:issues.append('STRINGS_LOCKED')
            if n['pitch']is None or m['pitch']is None or n['pitch']%12!=m['pitch']%12:issues.append('MEMBER_PC_CHANGED')
            if n['pitch']!=m['pitch']or n['string']!=m['string']:changed.append(ref)
            if ref in pinned:
                if n['pitch']!=m['pitch']or n['string']!=m['string']:issues.append('PINNED_EXECUTION_PITCH_OR_STRING_CHANGED')
            if m['string']!=n['string']:
                if not any((x['part'],x['voice'],x['string'])==(n['part'],n['voice'],n['string'])for x in new_nodes.values()):issues.append('EMPTY_OLD_LANE_BOUNDARY_UNSUPPORTED')
            for ident,other in new_nodes.items():
                if ident==ref or other['part']!=m['part']or other['string']!=m['string']:continue
                if other['onset']<m['onset']+m['duration']and other['onset']+other['duration']>m['onset']:issues.append('OCCUPIED_TARGET_STRING')
        for unit,donor_refs in zip(targets,donor_ids_by_group):
            refs=unit['member_refs']
            if len({new_nodes[r]['string']for r in refs})!=len(refs):issues.append('DUPLICATE_SELECTED_STRING')
            if min(nodes[r]['pitch']for r in refs)!=min(new_nodes[r]['pitch']for r in refs):issues.append('BASS_REGISTER_CHANGED')
            for donor_ref in donor_refs:
                donor=by_id.get(donor_ref)
                if donor is None or donor['refusal_reasons']or set(donor['member_refs'])&selected:issues.append('INVALID_OR_TARGET_DONOR');continue
                context=json.loads(unit['family_context_key']);other=json.loads(donor['family_context_key'])
                if len(donor['member_refs'])!=len(refs)or any(context[k]!=other[k]for k in('part_id','instrument','member_pitch_classes','duration_q','meter','metrical_offset_q')):issues.append('DONOR_BASE_CONTEXT_CHANGED')
                if any(unit['source_geometry'][k]!=donor['source_geometry'][k]for k in('instrument','tuning','capo')):issues.append('INCOMPATIBLE_SOURCE_SETTINGS')
                delta=min(nodes[r]['pitch']for r in refs)-min(nodes[r]['pitch']for r in donor['member_refs'])
                for target,source in zip(refs,donor['member_refs']):
                    n,m,d=nodes[target],new_nodes[target],nodes[source]
                    se=next(e for e in lower['events']if e['id']==source);te=next(e for e in after_lower['events']if e['id']==target)
                    sp,_,sn=_raw(docs,se);tp,_,tn=_raw(after_docs,te);sf=F(str(sn['fret']));tf=F(str(tn['fret']))
                    if m['pitch']!=d['pitch']+delta or m['string']!=d['string']or tf!=sf+delta:issues.append('NO_WHOLE_TRANSLATED_FIXED_STRING_WITNESS')
                    if(sf==0)!=(tf==0):issues.append('OPEN_STATUS_CHANGED')
                    for fret,part in((sf,sp),(tf,tp)):
                        limit=part.get('frets')
                        if fret<0 or fret.denominator!=1 or(type(limit)is int and limit>0 and fret>limit):issues.append('INVALID_SOURCE_OR_TRANSLATED_FRET')
        from check_execution_dependencies import expected
        if encoded(_written_ties(after_docs,after_lower['events']))!=encoded(ties):issues.append('TIE_RELATIONSHIPS_CHANGED')
        if encoded(expected(tier1_after)['signature'])!=encoded(deps['signature']):issues.append('EXECUTION_RELATIONSHIPS_CHANGED')
        before_paths=_paths(nodes,rests);after_paths=_paths(new_nodes,new_rests)
        if set(before_paths)!=set(after_paths):raise ValueError('Unexpected source path-center inventory change')
        if allow_string_changes:
            # Includes reconnections whose AFTER refs no longer contain any
            # selected member, not just selected-note incident windows.
            touched={key for key in before_paths if before_paths[key]!=after_paths[key]}
        else:touched={key for key,path in before_paths.items()if set(changed)&set(path['refs'])}|{key for key,path in after_paths.items()if set(changed)&set(path['refs'])}
        neighborhood={ref for key in touched for ref in before_paths[key]['refs']+after_paths[key]['refs']}
        for key in sorted(touched):
            old,new=before_paths[key],after_paths[key]
            if old['reasons']or new['reasons']:issues.extend(old['reasons']+new['reasons']);continue
            if old['signature']==new['signature']:continue
            support=[path['refs']for path in before_paths.values()if not path['reasons']and path['signature']==new['signature']and not neighborhood.intersection(path['refs'])]
            if not support:issues.append('NO_INDEPENDENT_SOURCE_'+key[0].upper())
            else:witnesses.append(dict(kind=key[0],center=key[1],source_witness_refs=support))
        # Independent minimal vertical grid; every active occurrence is accounted,
        # with explicit percussion excluded but other unknown domains quarantined.
        if changed:
            start=min(nodes[r]['onset']for r in changed);stop=max(nodes[r]['onset']+nodes[r]['duration']for r in changed)
            points={start,stop}
            for n in nodes.values():
                if n['onset']<stop and n['onset']+n['duration']>start:points.update((max(start,n['onset']),min(stop,n['onset']+n['duration'])))
            from musical_tier2 import THEORY_FORMS
            def templates(pcs):return {(root,kind)for root in range(12)for kind,formula in THEORY_FORMS if {(root+step)%12 for step in formula}==pcs}
            for lo,hi in zip(sorted(points),sorted(points)[1:]):
                if hi<=lo:continue
                active=[n for n in nodes.values()if n['instrument']!=1024 and n['onset']<hi and n['onset']+n['duration']>lo]
                # A missing physical string on another pitched instrument does
                # not erase its independently known written pitch. Lane
                # ambiguity still quarantines incident lane paths above.
                if any(type(n['instrument'])is not int or not 0<=n['instrument']<=127 or set(n['reasons'])-{'UNKNOWN_STRING_LANE'}for n in active):issues.append('UNKNOWN_VERTICAL_PITCH_OR_EXECUTION');continue
                before_pcs={int(n['pitch']%12)for n in active};after_pcs={int(new_nodes[n['id']]['pitch']%12)for n in active}
                if before_pcs!=after_pcs or templates(before_pcs)!=templates(after_pcs):issues.append('VERTICAL_PC_OR_TEMPLATE_SET_CHANGED')
        return dict(status='PASS_INDEPENDENT_VOICING_CONTEXT'if not issues else'FAIL_INDEPENDENT_VOICING_CONTEXT',issues=sorted(set(issues)),changed_refs=changed,affected_paths=len(touched),excluded_neighborhood=sorted(neighborhood),witness_count=len(witnesses),witnesses=witnesses,scope='Exact source-observed fixed physical-lane written motion and nominal vertical invariance; not melody identity, performed harmony or artist preference')
    except Exception as error:
        return dict(status='FAIL_INDEPENDENT_VOICING_CONTEXT',issues=sorted(set(issues+[type(error).__name__+': '+str(error)])),changed_refs=changed,witness_count=len(witnesses))
