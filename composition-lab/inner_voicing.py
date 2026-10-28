"""Source-supported inner degree components, with protected literal boundaries.

No melodic voice is inferred. The existing degree inverse remains authoritative.
"""
from collections import defaultdict
from bisect import bisect_left,bisect_right
from copy import deepcopy
from fractions import Fraction as F
import json
from declared_degree_choices import catalog as degree_catalog,apply,sample,encoded
from voicing_context_relations import paths,graph,check_paths

POLICY='source_inner_degree_component'
PREVIEW_POLICY='provisional_contact_inner_preview'


def notation(docs,ref):
    pid,bar,voice,beat,note=map(int,ref.split(':')[2:]);p=docs[f'track-{pid}.json']
    return p,p['measures'][bar-1]['voices'][voice]['beats'][beat]['notes'][note]


def overlaps(nodes,refs):
    selected=set(refs);rows=[nodes[r] for r in refs];part=rows[0]['part_id']
    lo=min(F(n['onset_q']) for n in rows);hi=max(F(n['onset_q'])+F(n['duration_q']) for n in rows)
    return sorted(r for r,n in nodes.items() if r not in selected and n['part_id']==part and ((F(n['duration_q'])>0 and F(n['onset_q'])<hi and F(n['onset_q'])+F(n['duration_q'])>lo) or (F(n['duration_q'])==0 and lo<=F(n['onset_q'])<hi)))


def overlap_index(nodes):
    result=defaultdict(lambda:[[],[],[]])
    for n in nodes.values():
        a,d=F(n['onset_q']),F(n['duration_q']);entry=result[n['part_id']]
        if d>0:entry[0].append(a);entry[1].append(a+d)
        elif d==0:entry[2].append(a)
    return {p:[sorted(v) for v in entry] for p,entry in result.items()}


def outside_overlap(index,nodes,refs):
    rows=[nodes[r] for r in refs];lo=min(F(n['onset_q']) for n in rows);hi=max(F(n['onset_q'])+F(n['duration_q']) for n in rows)
    if hi<=lo:return bool(overlaps(nodes,refs))
    starts,ends,points=index[rows[0]['part_id']]
    count=bisect_left(starts,hi)-bisect_right(ends,lo)+bisect_left(points,hi)-bisect_left(points,lo)
    own=sum((F(n['duration_q'])>0 and F(n['onset_q'])<hi and F(n['onset_q'])+F(n['duration_q'])>lo) or (F(n['duration_q'])==0 and lo<=F(n['onset_q'])<hi) for n in rows)
    return count>own


def geometry(docs,nodes,refs,pinned,index=None):
    rows=[nodes[r] for r in refs];reasons={r for n in rows for r in n['reasons']}
    if pinned.intersection(refs):reasons.add('PINNED_EXECUTION')
    strings=[n['string'] for n in rows]
    if any(type(s)is not int or s<0 for s in strings) or len(set(strings))!=len(strings):reasons.add('NONUNIQUE_OR_UNKNOWN_STRING')
    if len({n['duration_q'] for n in rows})!=1 or any(F(n['duration_q'])<=0 for n in rows):reasons.add('NONUNIFORM_OR_NONPOSITIVE_DURATION')
    if (overlaps(nodes,refs) if index is None else outside_overlap(index,nodes,refs)):reasons.add('OUTSIDE_PART_NOMINAL_OVERLAP')
    p,_=notation(docs,refs[0]);instrument=p.get('instrumentId');tuning=p.get('tuning');capo=p.get('capo')
    if type(instrument)is not int or not 24<=instrument<=39:reasons.add('OUTSIDE_GUITAR_SCOPE')
    if any(b.get('sustainPedal')is True for m in p.get('measures',[]) for v in m.get('voices',[]) for b in v.get('beats',[])):reasons.add('UNKNOWN_PEDAL_SOUNDING_END')
    if capo is not None and type(capo)not in (int,float):reasons.add('UNKNOWN_CAPO')
    if type(tuning)is not list or any(type(v)not in (int,float) for v in tuning):reasons.add('UNKNOWN_TUNING')
    for ref in refs:
        _,raw=notation(docs,ref)
        if raw.get('spn')is not None or raw.get('courtesyAccidental')is True:reasons.add('UNCOUPLED_SOURCE_PITCH_SPELLING')
        if any(k in raw for k in ('leftFinger','rightFinger','fingering')):reasons.add('UNCOUPLED_FINGER_DECLARATION')
        pid,bar,voice,beat,_=map(int,ref.split(':')[2:]);b=docs[f'track-{pid}.json']['measures'][bar-1]['voices'][voice]['beats'][beat]
        if isinstance(b.get('chord'),dict) and set(b['chord'])-{'text','width'}:reasons.add('UNINTERPRETED_CHORD_DIAGRAM')
    if reasons:return dict(id=refs[0],member_refs=refs,reasons=sorted(reasons),key=None)
    frets={};capo=F(str(capo or 0));limit=p.get('frets')
    for n in rows:
        _,raw=notation(docs,n['id']);s=n['string']
        if type(raw.get('fret'))not in (int,float):
            reasons.add('UNKNOWN_FRET');continue
        fret=F(str(raw['fret']))
        if fret<0 or fret.denominator!=1 or type(limit)is int and limit>0 and fret>limit:reasons.add('INVALID_FRET')
        if not 0<=s<len(tuning) or n['pitch']is None or F(str(tuning[s]))+capo+fret!=F(n['pitch']):reasons.add('PHYSICAL_EQUATION_CONFLICT')
        frets[s]=fret
    if reasons:return dict(id=refs[0],member_refs=refs,reasons=sorted(reasons),key=None)
    ordered=sorted(frets);base=min(frets.values())
    key=encoded([instrument,list(map(lambda v:str(F(str(v))),tuning)),str(capo),ordered,[str(frets[s]-base) for s in ordered],[frets[s]==0 for s in ordered]])
    return dict(id=refs[0],member_refs=refs,reasons=sorted(reasons),key=key if not reasons else None)


def decorate(c):
    from source_tie_tier1 import extract_documents
    from voicing_register import tie_relationships
    from execution_dependencies import build
    nodes=c['lane_graph']['nodes']
    index=overlap_index(nodes)
    ties=tie_relationships(extract_documents(c['documents']));execution=build(c['before'])
    pinned=set(execution['pinned_members'])|{r for e in ties['links'] for r in (e['origin'],e['destination'])}|{e['destination'] for e in ties['unresolved']}
    pp=paths(c['lane_graph'],typed_nominal=True);byref=defaultdict(set)
    for path in pp.values():
        for ref in path['refs']:byref[ref].update(path['refs'])
    for u in c['units']:
        pitches=list(map(F,u['pitches']));lo,hi=min(pitches),max(pitches)
        u['base_reasons']=u['reasons'][:];u['family']=json.loads(u['key'])[:3]
        u['outer_refs']=[r for r,p in zip(u['member_refs'],pitches) if p in (lo,hi)]
        u['inner_refs']=[r for r,p in zip(u['member_refs'],pitches) if lo<p<hi]
        u['inner_strings']=[nodes[r]['string'] for r in u['inner_refs']]
        u['excluded_neighborhood']=sorted(set(u['member_refs'])|{r for ref in u['member_refs'] for r in byref[ref]})
        if not u['inner_refs']:u['reasons'].append('NO_INNER_OCCURRENCE')
        if outside_overlap(index,nodes,u['member_refs']):u['reasons'].append('OUTSIDE_PART_NOMINAL_OVERLAP')
        u['reasons']=sorted(set(u['reasons']))
    groups=defaultdict(list)
    for r,n in nodes.items():groups[n['part_id'],n['onset_q']].append(r)
    c['geometries']=[geometry(c['documents'],nodes,refs,pinned,index) for refs in groups.values()]
    c['pinned']=pinned;c['overlap_index']=index
    return c


def catalog(upper):
    return decorate(degree_catalog(upper,typed_nominal=True))


def component_links(c,target):
    """All software-enumerated component donors, before candidate validation."""
    result=[];excluded=set(target['excluded_neighborhood']);selected=set(target['inner_strings'])
    if target['reasons']:return result
    for donor in c['units']:
        if donor['base_reasons'] or donor['family']!=target['family'] or excluded.intersection(donor['member_refs']):continue
        if not selected<=set(donor['inner_strings']):continue
        source=dict(zip(donor['strings'],donor['roles']));roles=[deepcopy(source[s] if r in target['inner_refs'] else role) for r,s,role in zip(target['member_refs'],target['strings'],target['roles'])]
        result.append(dict(donor=donor,roles=roles,changed=roles!=target['roles']))
    return result


def verify(c,after,target,donor,*,physical_policy=POLICY):
    if physical_policy not in (POLICY,PREVIEW_POLICY):raise ValueError('Unknown physical evidence policy')
    from source_fact_tier1 import project_documents
    from execution_dependencies import build
    from source_tie_tier1 import extract_documents
    from voicing_register import tie_relationships
    from technique_analysis import classify_group
    from freeze_technique_baseline import retained
    before=c['before'];refs=target['member_refs'];selected=set(target['inner_refs']);old=c['lane_graph']['nodes'];newgraph=graph(after,typed_nominal=True);new=newgraph['nodes'];docs=project_documents(after)
    allowed={f"track-{int(r.split(':')[2])}.json#/measures/{int(r.split(':')[3])-1}/voices/{r.split(':')[4]}/beats/{r.split(':')[5]}/notes/{r.split(':')[6]}/fret" for r in selected}
    if encoded({k:v for k,v in before.items() if k!='facts'})!=encoded({k:v for k,v in after.items() if k!='facts'}):raise ValueError('SOURCE_ENVELOPE_CHANGED')
    if len(before['facts'])!=len(after['facts']):raise ValueError('SOURCE_INVENTORY_CHANGED')
    for a,b in zip(before['facts'],after['facts']):
        if encoded(a)==encoded(b):continue
        if a['id']not in allowed or encoded({k:v for k,v in a.items() if k!='value'})!=encoded({k:v for k,v in b.items() if k!='value'}):raise ValueError('OUTSIDE_INNER_FRET_FACT_CHANGED')
    if set(old)!=set(new):raise ValueError('OCCURRENCE_INVENTORY_CHANGED')
    if encoded(build(before)['signature'])!=encoded(build(after)['signature']):raise ValueError('EXECUTION_CHANGED')
    if encoded(tie_relationships(extract_documents(c['documents'])))!=encoded(tie_relationships(extract_documents(docs))):raise ValueError('TIES_CHANGED')
    if selected.intersection(c['pinned']):raise ValueError('PINNED_EXECUTION')
    lo,hi=min(F(old[r]['pitch']) for r in refs),max(F(old[r]['pitch']) for r in refs)
    source=dict(zip(donor['strings'],donor['pitches']))
    for r in selected:
        if not lo<F(new[r]['pitch'])<hi:raise ValueError('INNER_PITCH_OUTSIDE_PROTECTED_ENVELOPE')
        if new[r]['pitch']!=source[old[r]['string']]:raise ValueError('NO_COUPLED_SOURCE_COMPONENT')
    for a in selected:
        for b in selected:
            if (F(old[a]['pitch'])-F(old[b]['pitch']))*(F(new[a]['pitch'])-F(new[b]['pitch']))<0:raise ValueError('INNER_STRING_PITCH_ORDER_REVERSED')
    # Uniform target durations make this set identity pointwise over the span.
    if {F(old[r]['pitch'])%12 for r in refs}!={F(new[r]['pitch'])%12 for r in refs}:raise ValueError('CHORD_FORMULA_SUPPORT_CHANGED')
    shape=geometry(docs,new,refs,c['pinned'],c['overlap_index'])
    if shape['reasons']:raise ValueError(dict(geometry=shape['reasons']))
    excluded=set(target['excluded_neighborhood'])
    witnesses=[g for g in c['geometries'] if not g['reasons'] and g['key']==shape['key'] and not excluded.intersection(g['member_refs'])]
    contact=None
    if physical_policy==POLICY:
        if not witnesses:raise ValueError('NO_INDEPENDENT_WHOLE_GEOMETRY')
    else:
        from fretting_contacts import analyze
        required=[dict(string=new[r]['string'],fret=int(F(str(notation(docs,r)[1]['fret'])))) for r in refs]
        contact=analyze(required)
        if contact['status']!='COVERED':raise ValueError(dict(contact_model=contact))
    oldpaths=paths(c['lane_graph'],typed_nominal=True);newpaths=paths(newgraph,typed_nominal=True)
    if set(oldpaths)!=set(newpaths):raise ValueError('PATH_TOPOLOGY_CHANGED')
    changed={r for r in selected if old[r]['pitch']!=new[r]['pitch']}
    for key,a in oldpaths.items():
        b=newpaths[key]
        if changed.intersection(a['refs']+b['refs']) and (a['reasons'] or b['reasons']):raise ValueError(dict(incident_execution=sorted(set(a['reasons']+b['reasons']))))
    def classes(table):return classify_group([dict(midi=int(F(table[r]['pitch'])),string=table[r]['string']) for r in refs])
    if classes(old)!=classes(new):raise ValueError('TECHNIQUE_CLASS_CHANGED')
    if encoded([t['approved_pedal_phrases'] for t in retained(c['documents'])['tracks']])!=encoded([t['approved_pedal_phrases'] for t in retained(docs)['tracks']]):raise ValueError('APPROVED_PEDAL_CHANGED')
    pitches=[F(new[r]['pitch']) for r in refs]
    context=check_paths(c['lane_graph'],target,dict(anchor=str(lo),intervals=[str(p-lo) for p in pitches],strings=target['strings']),typed_nominal=True)
    result=dict(status='PASS_INNER_COMPONENT_RELATIONSHIPS',geometry_witness_refs=[g['member_refs'] for g in witnesses],context_observation=context,
        protection='Exact literal outer occurrences, complete chord PC set, unchanged outside facts; doubling may change',melody_identity='UNKNOWN',artist_fit='UNVERIFIED',physical_evidence='Observed whole fret geometry, not human playability verification')
    if contact is not None:
        result.update(status='PROVISIONAL_INNER_CONTACT_RELATIONSHIPS',physical_policy=PREVIEW_POLICY,contact_coverage=contact,
            physical_evidence='Bounded contact coverage only; reach, posture, clean tone and movement remain unverified',human_playability='UNVERIFIED')
    return result


def options(upper,target_ref,prepared=None,*,physical_policy=POLICY):
    if physical_policy not in (POLICY,PREVIEW_POLICY):raise ValueError('Unknown physical evidence policy')
    from connected_tier2 import realize
    c=catalog(upper) if prepared is None else prepared;target=next(u for u in c['units'] if u['id']==target_ref)
    if target['reasons']:return dict(status='REFUSED_TARGET',target=target,reasons=target['reasons'],options=[],rejected=[])
    buckets=defaultdict(list)
    for link in component_links(c,target):buckets[encoded(link['roles'])].append(link)
    accepted=[];rejected=[]
    for key,links in sorted(buckets.items()):
        roles=json.loads(key);changed=roles!=target['roles'];donors=[r['donor']['id'] for r in links]
        try:
            relation=verify(c,realize(apply(upper,target,roles)),target,links[0]['donor'],physical_policy=physical_policy) if changed else dict(status='UNCHANGED_INNER_COMPONENT')
            accepted.append(dict(roles=roles,donor_refs=donors,changed=changed,relationship=relation))
        except (ValueError,KeyError,TypeError) as error:rejected.append(dict(roles=roles,donor_refs=donors,reason=str(error)))
    return dict(status='SUPPORTED_INNER_CHOICES' if any(o['changed'] for o in accepted) else 'NO_ADMITTED_CHANGED_INNER_COMPONENT',target=target,options=accepted,rejected=rejected)


def intervene(upper,controls):
    from connected_tier2 import realize
    if controls.get('register')!=0:raise ValueError('This scope locks literal outer registers')
    policy=controls.get('context_policy',POLICY)
    if policy not in (POLICY,PREVIEW_POLICY):raise ValueError('Unknown inner-voicing policy')
    realize(upper)
    if controls['voicing']==0:return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False)
    evidence=options(upper,controls['target_ref'],physical_policy=policy);chosen,report=sample(evidence,controls);report['evidence']=evidence
    if policy==PREVIEW_POLICY:
        report.update(physical_policy=policy,human_playability='UNVERIFIED')
        if report['changed']:report['status']='PROVISIONAL_'+report['status']
    return (deepcopy(upper) if chosen is None else apply(upper,evidence['target'],chosen['roles'])),report
