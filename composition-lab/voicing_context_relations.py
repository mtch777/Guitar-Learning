"""Source-observed incident written-motion obligations, not artistic preference.

Replaces donor-context equality with checked target-context relationships in an
opt-in fixed-string spacing experiment. The established policy is unchanged.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import json

POLICY='source_lane_context'
JOINT_POLICY='source_joint_lane_context'
BASE_FIELDS=('part_id','instrument','member_pitch_classes','duration_q','meter','metrical_offset_q')


def token(v):return json.dumps(v,sort_keys=True,separators=(',',':'))


def graph(tier1,*,typed_nominal=False):
    if type(typed_nominal)is not bool:raise ValueError('Typed nominal permission must be bool')
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    from voicing_register import effect_reasons,notation
    docs=project_documents(tier1);lower=extract_documents(docs);nodes={};rest_rows=[]
    from source_semantics import rests,layout
    parts=[docs[k]for k in sorted((k for k in docs if k.startswith('track-')),key=lambda k:int(k[6:-5]))]
    headers,_=layout(parts);rest_bad=set()
    for part in parts:
        rows,warnings=rests(part,headers)
        rest_rows.extend(dict(part_id=part['partId'],**r)for r in rows)
        rest_bad.update((part['partId'],w['bar'])for w in warnings)
    bad_bars={w['bar']for k in ('layout_warnings','timing_warnings')for w in lower['source_coverage'][k]}
    for e in lower['events']:
        part,beat,note=notation(docs,e);s=note.get('string');reasons=effect_reasons(beat,note)
        if e['bar']in bad_bars:reasons.append('UNCERTAIN_SOURCE_CLOCK')
        if(e['part_id'],e['bar'])in rest_bad:reasons.append('CONFLICTING_SOURCE_REST')
        if e['pitch']is None or F(e['pitch']).denominator!=1:reasons.append('UNKNOWN_PITCH')
        if F(e['duration_q'])<=0:reasons.append('GRACE_OR_NONPOSITIVE_DURATION')
        if type(s)is not int or s<0:reasons.append('UNKNOWN_STRING_LANE')
        # Exact declarations are not interpreted as an acoustic attack/end.
        articulation=dict(note={k:v for k,v in note.items()if k not in ('fret','string','spn','tieOrigin','tieDestination')},
            beat={k:v for k,v in beat.items()if k not in ('notes','duration')})
        nodes[e['id']]=dict(id=e['id'],part_id=e['part_id'],voice=e['voice'],string=s,pitch=e['pitch'],
            onset_q=e['onset_q'],duration_q=e['duration_q'],bar=e['bar'],reasons=sorted(set(reasons)),articulation=articulation)
        if typed_nominal:
            nodes[e['id']]['nominal_dead_declaration']=dict(eligible=note.get('dead')is True and e['pitch']is None and note.get('spn')is None and note.get('courtesyAccidental')is not True and type(part.get('instrumentId'))is int and 0<=part['instrumentId']<=127 and type(s)is int and s>=0,
                fret=dict(present='fret'in note,type=type(note.get('fret')).__name__,value=deepcopy(note.get('fret'))))
    return dict(nodes=nodes,rests=rest_rows)


def paths(g,*,typed_nominal=False):
    """Every lane edge and center triple, including explicit song-lane boundaries."""
    if type(typed_nominal)is not bool:raise ValueError('Typed nominal permission must be bool')
    lanes=defaultdict(list);unknown=defaultdict(list);result={};rest_index=defaultdict(list)
    for r in g['rests']:rest_index[r['part_id'],r['voice']].append((F(r['onset_q']),F(r['onset_q'])+F(r['duration_q']),r))
    for n in g['nodes'].values():
        if type(n['string'])is not int or n['string']<0:unknown[n['part_id'],n['voice']].append(n)
        else:lanes[n['part_id'],n['voice'],n['string']].append(n)
    for lane,rows in lanes.items():
        rows.sort(key=lambda n:(F(n['onset_q']),n['id']))
        windows=[]
        for i,n in enumerate(rows):
            for kind,window in (('edge',rows[i:i+2]),('triple',rows[max(0,i-1):i+2])):
                if kind=='edge' and len(window)<2:window=[n,None]
                if kind=='triple':window=([None]if i==0 else[])+window+([None]if i==len(rows)-1 else[])
                windows.append((kind,n['id'],window))
        if typed_nominal:
            from nominal_event_incidence import spans,describe
            windows.extend(spans(rows))
        for kind,center,window in windows:
                reasons=[];present=[v for v in window if v is not None];rest_patterns=[]
                typed=describe(window) if typed_nominal else None
                if typed is not None:reasons.extend(typed['reasons'])
                else:
                    for v in present:reasons.extend(v['reasons'])
                for v in unknown[lane[:2]]:
                    at=F(v['onset_q']);lo=F(present[0]['onset_q']);hi=F(present[-1]['onset_q'])+F(present[-1]['duration_q'])
                    if(window[0]is None or at>=lo or at+F(v['duration_q'])>lo)and(window[-1]is None or at<hi):reasons.append('UNKNOWN_INTERVENING_LANE')
                for a,b in zip(window,window[1:]):
                    if a is None or b is None:rest_patterns.append(None);continue
                    gap=F(b['onset_q'])-F(a['onset_q'])-F(a['duration_q'])
                    if F(b['onset_q'])<=F(a['onset_q'])or gap<0:reasons.append('AMBIGUOUS_OR_OVERLAPPING_LANE')
                    selected=[r for start,stop,r in rest_index[lane[:2]]if start<F(b['onset_q'])and stop>F(a['onset_q'])]
                    rest_patterns.append(sorted([[str(F(r['onset_q'])-F(a['onset_q'])),r['duration_q'],r['source']]for r in selected]))
                pitches=[None if v is None or v['pitch']is None else F(v['pitch'])for v in window]
                motion=[None if a is None or b is None else str(b-a)for a,b in zip(pitches,pitches[1:])]
                times=[None if v is None else v['duration_q']for v in window]
                gaps=[None if a is None or b is None else str(F(b['onset_q'])-F(a['onset_q'])-F(a['duration_q']))for a,b in zip(window,window[1:])]
                key=token([kind,list(lane),[None if p is None else str(p%12)for p in pitches],motion,times,gaps,
                    [None if v is None else v['articulation']for v in window],rest_patterns])
                if typed is not None and typed['has_unpitched']:key=token([key,typed['slot_kinds'],typed['dead_fret_declarations'],typed['known_pitch_pairs']])
                result[kind,center]=dict(key=key,refs=[v['id']for v in present],reasons=sorted(set(reasons)))
                if typed is not None and typed['has_unpitched']:result[kind,center]['nominal_incidence']=typed
    return result


def evidence(g,*,typed_nominal=False):
    original=paths(g,typed_nominal=typed_nominal);index=defaultdict(list)
    for path in original.values():
        if not path['reasons']:index[path['key']].append(path['refs'])
    return original,index


def check_paths(g,target,realization,source_evidence=None,*,allow_string_changes=False,typed_nominal=False):
    """Evaluate actual after-neighborhoods using ONLY original source witnesses."""
    return check_many(g,[(target,realization)],source_evidence,allow_string_changes=allow_string_changes,typed_nominal=typed_nominal)


def check_many(g,choices,source_evidence=None,*,allow_string_changes=False,typed_nominal=False):
    """Same incident obligations for the UNION of simultaneous group choices."""
    if not choices or len({t['part_id'] for t,v in choices})!=1:raise ValueError('One part and nonempty choices required')
    part_id=choices[0][0]['part_id'];assignments={}
    for target,realization in choices:
        if len(target['member_refs'])!=len(realization['intervals']) or len(target['member_refs'])!=len(realization['strings']):raise ValueError('Complete group assignment required')
        for ref,interval,string in zip(target['member_refs'],realization['intervals'],realization['strings']):
            if ref in assignments or g['nodes'][ref]['part_id']!=part_id:raise ValueError('Overlapping or wrong-part assignment')
            assignments[ref]=(str(F(realization['anchor'])+F(interval)),string)
    # Lanes and their witnesses are explicitly part-local. Other parts remain in
    # independent vertical-cell checks; they cannot alter this part's adjacency.
    g=dict(nodes={r:n for r,n in g['nodes'].items()if n['part_id']==part_id},
        rests=[r for r in g['rests']if r['part_id']==part_id])
    before,index=evidence(g,typed_nominal=typed_nominal)if source_evidence is None else source_evidence
    before={k:p for k,p in before.items()if k[1]in g['nodes']}
    after_graph=deepcopy(g);changed=set()
    for ref,(p,string) in assignments.items():
        n=after_graph['nodes'][ref]
        if n['string']!=string and not allow_string_changes:return dict(status='REFUSED',reasons=['STRINGS_LOCKED'],witnesses=[])
        if p!=n['pitch']or n['string']!=string:changed.add(ref);n.update(pitch=p,string=string)
    if not changed:return dict(status='PASS_UNCHANGED_PITCH_RELATIONSHIPS',reasons=[],witnesses=[])
    after=paths(after_graph,typed_nominal=typed_nominal)
    old_lanes={(n['part_id'],n['voice'],n['string'])for n in g['nodes'].values()if type(n['string'])is int and n['string']>=0}
    new_lanes={(n['part_id'],n['voice'],n['string'])for n in after_graph['nodes'].values()if type(n['string'])is int and n['string']>=0}
    if old_lanes-new_lanes:return dict(status='REFUSED',reasons=['EMPTY_SOURCE_LANE_CREATED'],witnesses=[])
    if set(before)!=set(after):return dict(status='REFUSED',reasons=['UNRESOLVED_PATH_TOPOLOGY'],witnesses=[])
    # Include old-lane neighbor reconnections and new-lane split connections,
    # even when a resulting path no longer contains any selected occurrence.
    affected={k for k in before if before[k]!=after[k]}
    neighborhood={ref for k in affected for p in (before[k],after[k])for ref in p['refs']}
    reasons=[];witnesses=[]
    for k in sorted(affected):
        a,b=before[k],after[k]
        if a['reasons']or b['reasons']:reasons.extend(a['reasons']+b['reasons']);continue
        if a['key']==b['key']:continue
        options=[refs for refs in index.get(b['key'],[])if not neighborhood.intersection(refs)]
        if not options:reasons.append('NO_INDEPENDENT_SOURCE_'+k[0].upper());continue
        witnesses.append(dict(kind=k[0],center=k[1],after_refs=b['refs'],source_witness_refs=options))
    return dict(status='PASS_OBSERVED_INCIDENT_MOTION'if not reasons else'REFUSED',reasons=sorted(set(reasons)),
        changed_refs=sorted(changed),excluded_neighborhood=sorted(neighborhood),witnesses=witnesses,
        meaning='Exact source-observed fixed physical-lane written motion, not melody identity or artist preference')


def catalog(base,tier1,*,joint=False):
    result=deepcopy(base);g=graph(tier1)
    # These are source-linked analysis relationships, not a duplicate pitch owner.
    result['lane_relationships']=g
    result['joint_lane_reassignment']=joint
    source_paths,source_index=evidence(g)
    result['source_path_relations']=[dict(kind=k[0],center=k[1],**value)for k,value in source_paths.items()]
    result['source_path_index']=dict(source_index)
    pools=defaultdict(list)
    for row in result['units']:
        if row['refusal_reasons']:continue
        context=json.loads(row['family_context_key'])
        pools[token([context[k]for k in BASE_FIELDS])].append(row['id'])
    result['candidate_pools']=dict(pools)
    return result


def validate_actual(before,after,target,realization):
    """Same observed graph built from the ACTUAL inverse result, not proposal."""
    a,b=graph(before),graph(after)
    if a['rests']!=b['rests']or set(a['nodes'])!=set(b['nodes']):raise ValueError('Locked source topology/rests changed')
    changed=set(target['member_refs']);mapping=dict(zip(target['member_refs'],realization['intervals']))
    for ref,old in a['nodes'].items():
        new=b['nodes'][ref];expected=deepcopy(old)
        if ref in changed:
            expected['pitch']=str(F(realization['anchor'])+F(mapping[ref]))
            expected['string']=realization['strings'][target['member_refs'].index(ref)]
        if new!=expected:raise ValueError('Actual inverse violates literal note/time/lane/declaration locks')
        if old['pitch']is not None and F(old['pitch'])%12!=F(new['pitch'])%12:raise ValueError('Actual member PC changed')
    # Per-occurrence clocks/PCs imply equal vertical cells and template supports;
    # independent raw oracle separately partitions those cells before acceptance.
    joint=target['fixed_output_strings']!=realization['strings']
    relation=check_paths(a,target,realization,allow_string_changes=joint)
    if relation['status']=='REFUSED':raise ValueError('Actual inverse lacks incident source witnesses')
    return relation


def options(catalog,target_id):
    from family_policy import admissible
    target=next(r for r in catalog['units']if r['id']==target_id)
    if target['refusal_reasons']:return dict(status='REFUSED_TARGET',reasons=target['refusal_reasons'],options=[])
    a=json.loads(target['family_context_key']);original=dict(target['realization'],strings=target['fixed_output_strings'])
    choices={};rejected=[];g=catalog['lane_relationships'];source_evidence=None;donor_count=0;relations={}
    pool=catalog.get('candidate_pools',{}).get(token([a[k]for k in BASE_FIELDS]))
    by_id={r['id']:r for r in catalog['units']}
    donors=catalog['units']if pool is None else[by_id[ref]for ref in pool]
    for donor in donors:
        if donor['id']==target_id or donor['refusal_reasons']:continue
        b=json.loads(donor['family_context_key'])
        if any(a[k]!=b[k]for k in BASE_FIELDS):continue
        donor_count+=1;value,reason=admissible(target,donor);relation=None
        if reason is None and value['strings']!=target['fixed_output_strings']and not catalog.get('joint_lane_reassignment',False):reason='STRINGS_LOCKED'
        if reason is None and value!=original and a['execution_uncertainty']:reason='UNKNOWN_TARGET_OVERLAP_EXECUTION'
        if reason is None:
            if value==original:relation=dict(status='PASS_UNCHANGED_PITCH_RELATIONSHIPS',reasons=[],witnesses=[])
            else:
                key=token(value)
                if key not in relations:
                    if source_evidence is None:
                        source_evidence=({(p['kind'],p['center']):{k:v for k,v in p.items()if k not in ('kind','center')}for p in catalog['source_path_relations']},catalog['source_path_index'])if 'source_path_relations'in catalog else evidence(g)
                    relations[key]=check_paths(g,target,value,source_evidence,allow_string_changes=catalog.get('joint_lane_reassignment',False))
                relation=relations[key]
            if relation['status']=='REFUSED':reason=';'.join(relation['reasons'])
        if reason:
            rejected.append(dict(level='checked_target_relationships',donor_ref=donor['id'],reason=reason,realization=value));continue
        key=token(value);choices.setdefault(key,dict(realization=value,donor_refs=[],relationship_witnesses=relation))['donor_refs'].append(donor['id'])
    values=[choices[k]for k in sorted(choices)]
    alternative=any(v['realization']!=original for v in values)
    levels=[dict(level='checked_target_relationships',donor_units=donor_count,distinct_realizations=len(values),physically_feasible_realizations=len(values),has_alternative=alternative)]
    return dict(status='SUPPORTED_EMPIRICAL_ALTERNATIVES'if alternative else'OBSERVED_SINGLE_REALIZATION'if values else'NO_ELIGIBLE_ALTERNATIVE',target_ref=target_id,
        context_level='checked_target_relationships',levels=levels,options=values,rejected=rejected)
