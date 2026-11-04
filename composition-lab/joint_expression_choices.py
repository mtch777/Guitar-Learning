"""Finite simultaneous expression choices measured on the final output.

The caller owns musical eligibility and native playback formulas. This solver
receives primitive rank/accent/descendant-velocity values, never change counts.
It counts frozen original attacks and signed region differences itself. No IO,
source observations, dynamic constants, or performed-velocity formula live here.
``descendant_ids`` are current written occurrence identities, not asserted native
callbacks. Their aligned performed entries are measured velocities or None when
an occurrence has no independent callback/evidence; no fake callback is created.
"""
from copy import deepcopy
from itertools import product

from output_change_targets import target_count

FEATURES=('base_dynamic','accent','performed','adjacent_dynamic_difference')
LOCAL=FEATURES[:3]


def _name(value):return type(value)is str and bool(value)
def _rank(value):return value is None or type(value)is int
def _accent(value):return value is None or type(value)is int and value in (0,1,2)


def _performed(value,count):
    return (type(value)is list and len(value)==count and
            all(v is None or type(v)is int and v>=0 for v in value))


def _input(regions,attacks,edges,requests,max_nodes):
    if (type(regions)is not dict or not regions or any(not _name(ref)for ref in regions)
            or type(attacks)is not dict or not attacks or any(not _name(ref)for ref in attacks)
            or type(edges)is not dict or any(not _name(ref)for ref in edges)
            or type(requests)is not dict or set(requests)!=set(FEATURES)
            or type(max_nodes)is not int or max_nodes<0):
        raise ValueError('Explicit frozen regions, attacks, edges, four targets and search budget required')
    for name,value in requests.items():
        if name=='performed'and value is None:continue
        target_count(0,value)
    membership={ref:[]for ref in regions};tables={};descendants=set()
    for ref,attack in attacks.items():
        if (type(attack)is not dict or set(attack)!={'region_ref','descendant_ids','baseline','current','performed_table'}
                or attack['region_ref']not in regions or type(attack['descendant_ids'])is not list
                or not attack['descendant_ids']or any(not _name(v)for v in attack['descendant_ids'])
                or len(set(attack['descendant_ids']))!=len(attack['descendant_ids'])
                or descendants&set(attack['descendant_ids'])):
            raise ValueError('One original attack must own unique stable written descendant occurrences')
        descendants.update(attack['descendant_ids']);count=len(attack['descendant_ids'])
        membership[attack['region_ref']].append(ref)
        for side in ('baseline','current'):
            state=attack[side]
            if (type(state)is not dict or set(state)!={'rank','accent','performed'}
                    or not _rank(state['rank'])or not _accent(state['accent'])
                    or not _performed(state['performed'],count)):
                raise ValueError('Closed baseline/current rank, accent and aligned performed values required')
        rows=attack['performed_table'];table={}
        if type(rows)is not list:raise ValueError('Explicit performed table required')
        for row in rows:
            if (type(row)is not dict or set(row)!={'rank','accent','performed'}
                    or type(row['rank'])is not int or row['accent']is None or not _accent(row['accent'])
                    or not _performed(row['performed'],count)):
                raise ValueError('Exact rank/accent tuple and descendant performed vector required')
            key=(row['rank'],row['accent'])
            if key in table:raise ValueError('Duplicate performed tuple')
            table[key]=tuple(row['performed'])
        current=attack['current'];key=(current['rank'],current['accent'])
        if None not in key and table.get(key)!=tuple(current['performed']):
            raise ValueError('Current performed state disagrees with its declared context table')
        tables[ref]=table
    ranks={}
    for region,refs in membership.items():
        if not refs:raise ValueError('Every region must retain its declared original attack population')
        ranks[region]={}
        for side in ('baseline','current'):
            values={attacks[ref][side]['rank']for ref in refs}
            if len(values)!=1:raise ValueError('One region cannot contain conflicting baseline/current base ranks')
            ranks[region][side]=next(iter(values))
        candidates=regions[region]
        if type(candidates)is not list:raise ValueError('Finite ordered region candidates required')
        identities=set();realizations=set()
        for candidate in candidates:
            if (type(candidate)is not dict or set(candidate)!={'id','marking','rank','accents'}
                    or not _name(candidate['id'])or candidate['id']in identities
                    or not _name(candidate['marking'])or type(candidate['rank'])is not int
                    or type(candidate['accents'])is not dict or set(candidate['accents'])!=set(refs)
                    or any(v is None or not _accent(v)for v in candidate['accents'].values())):
                raise ValueError('Candidate must assign exactly its complete original-attack membership')
            identities.add(candidate['id'])
            realized=(candidate['rank'],tuple(candidate['accents'][ref]for ref in refs))
            if realized in realizations:raise ValueError('Duplicate final expression choices are not alternatives')
            realizations.add(realized)
            for ref in refs:
                if (candidate['rank'],candidate['accents'][ref])not in tables[ref]:
                    raise ValueError('Candidate lacks an explicit performed-context tuple')
    for edge in edges.values():
        if (type(edge)is not dict or set(edge)!={'from_region','to_region','baseline_difference','current_difference'}
                or edge['from_region']not in regions or edge['to_region']not in regions):
            raise ValueError('Closed adjacency relationship between declared regions required')
        for side in ('baseline','current'):
            left=ranks[edge['from_region']][side];right=ranks[edge['to_region']][side]
            expected=None if left is None or right is None else right-left
            if edge[side+'_difference']!=expected or not _rank(edge[side+'_difference']):
                raise ValueError('Signed adjacency difference disagrees with declared region ranks')
    return membership,tables,len(descendants)


def _unknown(attacks,edges,requests):
    result={name:[]for name in FEATURES}
    for ref,attack in attacks.items():
        for name,field in zip(LOCAL,('rank','accent','performed')):
            value=attack['current'if requests[name]==0 else'baseline'][field]
            if (value is None or name=='performed'and None in value or
                    name=='performed'and requests[name]is None and None in attack['current']['performed']):
                result[name].append(ref)
    side='current_difference'if requests[FEATURES[3]]==0 else'baseline_difference'
    result[FEATURES[3]]=[ref for ref,edge in edges.items()if edge[side]is None]
    return result


def _choices(regions,attacks,membership,tables,requests):
    options={};unknown=[];rejected=[]
    for region,candidates in regions.items():
        options[region]=[]
        for index,candidate in enumerate(candidates):
            counts=[0,0,0];reason=None;uncertain=False
            for ref in membership[region]:
                base=attacks[ref]['baseline'];current=attacks[ref]['current']
                rank=candidate['rank'];accent=candidate['accents'][ref]
                for offset,(name,field,value)in enumerate((('base_dynamic','rank',rank),('accent','accent',accent))):
                    if requests[name]==0:
                        if value!=current[field]:reason='CURRENT_LOCK'
                    else:counts[offset]+=int(value!=base[field])
                performed=tables[ref][rank,accent]
                if requests['performed']is None:continue
                if None in performed:uncertain=True;continue
                if requests['performed']==0:
                    if performed!=tuple(current['performed']):reason='CURRENT_LOCK'
                else:
                    counts[2]+=int(performed!=tuple(base['performed']))
                    if requests['performed']==100 and any(a==b for a,b in zip(performed,base['performed'])):
                        reason='UNCHANGED_DESCENDANT_AT_100'
            row=dict(region_ref=region,candidate_id=candidate['id'])
            if reason:rejected.append(dict(row,reason=reason))
            elif uncertain:unknown.append(row)
            else:options[region].append(dict(index=index,rank=candidate['rank'],counts=tuple(counts)))
    return options,unknown,rejected


def _bounds(assigned,options,edges,requests,targets):
    for offset,name in enumerate(LOCAL):
        if requests[name]is None:continue
        low=high=sum(choice['counts'][offset]for choice in assigned.values())
        for region,values in options.items():
            if region in assigned:continue
            if not values:return False
            amounts=[choice['counts'][offset]for choice in values]
            low+=min(amounts);high+=max(amounts)
        if not low<=targets[name]<=high:return False
    low=high=0;name=FEATURES[3]
    for edge in edges.values():
        a,b=edge['from_region'],edge['to_region']
        if a==b:steps={0}
        else:
            left=[assigned[a]]if a in assigned else options[a]
            right=[assigned[b]]if b in assigned else options[b]
            steps={y['rank']-x['rank']for x,y in product(left,right)}
        if not steps:return False
        if requests[name]==0:
            if edge['current_difference']not in steps:return False
        else:
            changed={int(step!=edge['baseline_difference'])for step in steps}
            low+=min(changed);high+=max(changed)
    return low<=targets[name]<=high


def _measure(regions,attacks,edges,tables,requests,targets,chosen):
    output={};values={name:{}for name in FEATURES};all_changed=[]
    for ref,attack in attacks.items():
        candidate=regions[attack['region_ref']][chosen[attack['region_ref']]['index']]
        rank=candidate['rank'];accent=candidate['accents'][ref]
        performed=tables[ref][rank,accent]
        values['base_dynamic'][ref]=rank;values['accent'][ref]=accent;values['performed'][ref]=list(performed)
        if (None not in performed and None not in attack['baseline']['performed']and
                all(a!=b for a,b in zip(performed,attack['baseline']['performed']))):all_changed.append(ref)
    for ref,edge in edges.items():
        values[FEATURES[3]][ref]=chosen[edge['to_region']]['rank']-chosen[edge['from_region']]['rank']
    for name in FEATURES:
        comparison='current'if requests[name]==0 else'baseline';changed=[];unchanged=[];unknown=[]
        for ref,value in values[name].items():
            if name==FEATURES[3]:baseline=edges[ref][comparison+'_difference']
            else:baseline=attacks[ref][comparison][{'base_dynamic':'rank','accent':'accent','performed':'performed'}[name]]
            if value is None or baseline is None or name=='performed'and(None in value or None in baseline):
                unknown.append(ref)
            else:(unchanged if value==baseline else changed).append(ref)
        total=len(values[name]);satisfied=None if requests[name]is None else not unknown and len(changed)==targets[name]
        if name=='performed'and requests[name]==100:satisfied=satisfied and len(all_changed)==total
        output[name]=dict(comparison=comparison,requested_percent=requests[name],target_count=targets[name],
            total_count=total,changed_count=len(changed),changed_ids=changed,unchanged_ids=unchanged,
            unknown_ids=unknown,final_values=values[name],satisfied=satisfied,
            status='MEASURE_ONLY_UNVERIFIED'if requests[name]is None else'SATISFIED'if total else'NOT_APPLICABLE')
        if name=='performed':output[name]['all_descendants_changed_ids']=all_changed
    return output


def solve(regions,attacks,edges,requests,*,max_nodes=100000):
    """First feasible caller-ordered region choices; no musical-preference claim.

    Positive percentages compare FINAL values to the frozen baseline. Zero
    locks supplied CURRENT values. Counts use original attack IDs, not regions
    or callback multiplicity. Performed100 additionally changes every aligned
    written descendant with an independently observed native value. The playback table is explicit caller-supplied data;
    its current tuple must agree with current measurements. Final native
    verification is still the caller's obligation. An explicit performed=None
    is diagnostic only: preserve and measure every performed unit, impose no
    performed target, and return FEASIBLE_UNVERIFIED_PERFORMANCE rather than a
    combined success. It cannot certify unknown performed values.
    """
    membership,tables,descendant_count=_input(regions,attacks,edges,requests,max_nodes)
    totals={name:len(edges)if name==FEATURES[3]else len(attacks)for name in FEATURES}
    targets={name:None if requests[name]is None else target_count(totals[name],requests[name])for name in FEATURES}
    unknown=_unknown(attacks,edges,requests)
    options,unknown_options,rejected=({},[],[])
    examined=0;assigned={};status=None
    if any(ids for name,ids in unknown.items()if requests[name]is not None):status='UNKNOWN_MEASUREMENTS'
    elif any(not totals[name]and requests[name]is not None and requests[name]>0 for name in FEATURES):status='NOT_APPLICABLE'
    else:
        options,unknown_options,rejected=_choices(regions,attacks,membership,tables,requests)
        order={ref:i for i,ref in enumerate(regions)}
        sequence=sorted(regions,key=lambda ref:(len(options[ref]),order[ref]))
        if not _bounds(assigned,options,edges,requests,targets):status='INFEASIBLE'
        else:
            frames=[0];depth=0
            while depth>=0:
                region=sequence[depth];assigned.pop(region,None)
                if frames[depth]>=len(options[region]):
                    frames.pop();depth-=1;continue
                if examined>=max_nodes:status='SEARCH_BUDGET_EXHAUSTED';break
                choice=options[region][frames[depth]];frames[depth]+=1;examined+=1
                assigned[region]=choice
                if not _bounds(assigned,options,edges,requests,targets):continue
                if depth==len(sequence)-1:status='FEASIBLE';break
                depth+=1;frames.append(0)
            if status is None:status='INFEASIBLE'
        if status=='INFEASIBLE'and unknown_options:status='UNKNOWN_MEASUREMENTS'
    measurements=(_measure(regions,attacks,edges,tables,requests,targets,assigned)
                  if status=='FEASIBLE'else None)
    if measurements is not None and not all(row['satisfied']for name,row in measurements.items()if requests[name]is not None):
        raise AssertionError('Search result does not satisfy independently recomputed output counts')
    feasible=status=='FEASIBLE'
    if feasible and requests['performed']is None:status='FEASIBLE_UNVERIFIED_PERFORMANCE'
    return dict(status=status,assignment={ref:deepcopy(regions[ref][assigned[ref]['index']])for ref in regions}
                if feasible else None,measurements=measurements,
        target_counts=targets,total_counts=totals,region_attack_counts={r:len(ids)for r,ids in membership.items()},
        descendant_count=descendant_count,examined_choices=examined,max_nodes=max_nodes,
        decision_complete=feasible or status=='INFEASIBLE',combined_targets_verified=status=='FEASIBLE',
        exhaustive_contradiction=status=='INFEASIBLE',
        unknown_measurements=unknown,unknown_candidates=unknown_options,rejected_candidates=rejected,
        selection='First feasible caller-ordered finite choices; not preference or rank optimum')
