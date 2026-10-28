"""Observed whole chord-degree placement, solved by the existing inverse.

This release keeps chord root/formula/doubling/bass and actual strings fixed.
It does not identify melody, infer stylistic preference, or generate new pitches.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from fractions import Fraction as F
import json
import random

POLICY='declared_degree_allocation'
NOMINAL_POLICY='declared_degree_nominal_slots'


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def catalog(upper,*,typed_nominal=False):
    from connected_tier2 import realize
    from source_fact_tier1 import project_documents
    from declared_chord_ownership import label_values,capo_values,validate
    from chord_symbol_lexicon import parse,LEGACY_PROFILE
    from voicing_context_relations import graph
    from voicing_register import notation,tie_relationships
    from source_tie_tier1 import extract_documents
    from execution_dependencies import build
    shared=upper['musical_relationships']
    if shared.get('schema')!='source-declared-chord-degrees/1':raise ValueError('Declared degree owners required')
    before=realize(upper);docs=project_documents(before);context=extract_documents(docs)
    labels=label_values(upper['owned_parameters']['source_choices'],upper['source_structure']['facts'])
    capos=capo_values(upper['owned_parameters']['source_choices'],upper['source_structure']['facts'])
    core=validate(shared,labels,capos);groups={g['id']:g for g in core['coattacks']}
    nodes=graph(before,typed_nominal=typed_nominal);ties=tie_relationships(context);execution=build(before)
    pinned=set(execution['pinned_members'])|{r for e in ties['links'] for r in (e['origin'],e['destination'])}|{e['destination'] for e in ties['unresolved']}
    events={e['id']:e for e in context['events']};units=[]
    for g in shared['core']['coattacks']:
        if 'declared_chord_ref' not in g:continue
        refs=[m['id'] for m in g['members']];rows=[nodes['nodes'][r] for r in refs]
        h=parse(labels[g['declared_chord_ref']],profile=shared.get('admission_profile',LEGACY_PROFILE))['interpretations'][0]
        reasons={r for row in rows for r in row['reasons']}
        if pinned.intersection(refs):reasons.add('PINNED_EXECUTION')
        strings=[row['string'] for row in rows]
        if any(type(s)is not int or s<0 for s in strings) or len(set(strings))!=len(strings):reasons.add('NONUNIQUE_OR_UNKNOWN_STRING')
        if len({row['duration_q'] for row in rows})!=1:reasons.add('NONUNIFORM_WRITTEN_CHORD_DURATION')
        pitches=[F(groups[g['id']]['bass_register_anchor'])+F(m['voicing_interval']) for m in groups[g['id']]['members']]
        for ref in refs:
            part,beat,note=notation(docs,events[ref])
            if type(part.get('instrumentId'))is not int or not 24<=part['instrumentId']<=39:reasons.add('OUTSIDE_GUITAR_SCOPE')
            if any(b.get('sustainPedal')is True for measure in part.get('measures',[]) for voice in measure.get('voices',[]) for b in voice.get('beats',[])):reasons.add('UNKNOWN_PEDAL_SOUNDING_END')
            if set(beat.get('chord',{}))-{'text','width'}:reasons.add('UNINTERPRETED_CHORD_DIAGRAM')
            if note.get('spn')is not None or note.get('courtesyAccidental')is True:reasons.add('UNCOUPLED_SOURCE_PITCH_SPELLING')
            if any(k in note for k in ('leftFinger','rightFinger','fingering')):reasons.add('UNCOUPLED_FINGER_DECLARATION')
            fret=F(str(note['fret']));limit=part.get('frets')
            if fret<0 or fret.denominator!=1 or type(limit)is int and limit>0 and fret>limit:reasons.add('INVALID_SOURCE_FRET')
        roles=[dict(degree_token=m['degree_token'],relative_octaves=m['relative_octaves']) for m in g['members']]
        key=encoded([g['part_id'],h['root_pc'],h['kind'],len(refs),sorted(Counter(m['degree_token'] for m in g['members']).items()),str(min(pitches)),sorted(strings)])
        units.append(dict(id=refs[0],group_ref=g['id'],part_id=g['part_id'],member_refs=refs,strings=strings,roles=roles,pitches=list(map(str,pitches)),key=key,reasons=sorted(reasons)))
    return dict(before=before,documents=docs,units=units,lane_graph=nodes,typed_nominal=typed_nominal)


def apply(upper,target,roles):
    """Only owned degree/register parameters change; the existing inverse solves frets."""
    if len(roles)!=len(target['member_refs']):raise ValueError('Complete observed allocation required')
    edited=deepcopy(upper);group=next(g for g in edited['musical_relationships']['core']['coattacks'] if g['id']==target['group_ref'])
    if [m['id'] for m in group['members']]!=target['member_refs']:raise ValueError('Allocation occurrence mismatch')
    for member,role in zip(group['members'],roles):
        if set(role)!={'degree_token','relative_octaves'}:raise ValueError('Undeclared degree parameter')
        member.update(role)
    return edited


def verify(before,after,target,donor,lanes,*,typed_nominal=False):
    from source_fact_tier1 import project_documents
    from voicing_context_relations import check_paths,graph
    from freeze_technique_baseline import retained
    from technique_analysis import classify_group
    from execution_dependencies import build
    from voicing_register import tie_relationships
    from source_tie_tier1 import extract_documents
    allowed={f"track-{int(r.split(':')[2])}.json#/measures/{int(r.split(':')[3])-1}/voices/{r.split(':')[4]}/beats/{r.split(':')[5]}/notes/{r.split(':')[6]}/fret" for r in target['member_refs']}
    if encoded({k:v for k,v in before.items() if k!='facts'})!=encoded({k:v for k,v in after.items() if k!='facts'}):raise ValueError('Source envelope changed')
    if len(before['facts'])!=len(after['facts']):raise ValueError('Source inventory changed')
    for a,b in zip(before['facts'],after['facts']):
        if encoded(a)==encoded(b):continue
        if a['id'] not in allowed or encoded({k:v for k,v in a.items() if k!='value'})!=encoded({k:v for k,v in b.items() if k!='value'}):raise ValueError('Locked source fact changed')
    after_graph=graph(after,typed_nominal=typed_nominal);old=lanes['nodes'];new=after_graph['nodes'];refs=target['member_refs']
    docs=project_documents(before);after_docs=project_documents(after)
    if encoded(build(before)['signature'])!=encoded(build(after)['signature']):raise ValueError('Execution relationships changed')
    if encoded(tie_relationships(extract_documents(docs)))!=encoded(tie_relationships(extract_documents(after_docs))):raise ValueError('Tie relationships changed')
    source={s:p for s,p in zip(donor['strings'],donor['pitches'])}
    pitches=[F(new[r]['pitch']) for r in refs]
    if [str(p) for p in pitches]!=[source[s] for s in target['strings']]:raise ValueError('No observed whole fixed-string allocation')
    if Counter(p%12 for p in pitches)!=Counter(F(old[r]['pitch'])%12 for r in refs) or min(pitches)!=min(F(old[r]['pitch']) for r in refs):raise ValueError('Chord doubling or bass changed')
    for ref in refs:
        n=new[ref]
        if n['string']!=old[ref]['string']:raise ValueError('String changed')
        for other in new.values():
            if other['id']!=ref and other['part_id']==n['part_id'] and other['string']==n['string'] and F(other['onset_q'])<F(n['onset_q'])+F(n['duration_q']) and F(other['onset_q'])+F(other['duration_q'])>F(n['onset_q']):raise ValueError('Occupied output string')
    # Equal target contribution preserves its union with ANY unchanged outside
    # pitch set. Outside uncertainty remains unknown; it is never guessed away.
    lo=min(F(old[r]['onset_q']) for r in refs);hi=max(F(old[r]['onset_q'])+F(old[r]['duration_q']) for r in refs);points={lo,hi}
    outside_unknown=[]
    for ref,n in old.items():
        if ref in refs:
            if n['pitch']is None or new[ref]['pitch']is None or n['reasons'] or new[ref]['reasons']:raise ValueError('Unknown selected pitch or execution')
            for node in (n,new[ref]):points.update((F(node['onset_q']),F(node['onset_q'])+F(node['duration_q'])))
        else:
            if encoded(n)!=encoded(new[ref]):raise ValueError('Outside musical projection changed')
            if F(n['onset_q'])<hi and F(n['onset_q'])+F(n['duration_q'])>lo and n['reasons']:outside_unknown.append(dict(ref=ref,reasons=n['reasons']))
    for start,end in zip(sorted(points),sorted(points)[1:]):
        def contribution(nodes):return Counter(F(nodes[r]['pitch'])%12 for r in refs if F(nodes[r]['onset_q'])<end and F(nodes[r]['onset_q'])+F(nodes[r]['duration_q'])>start)
        if contribution(old)!=contribution(new):raise ValueError('Target written pitch-class contribution changed')
    def classes(values):return classify_group([dict(midi=int(p),string=s) for p,s in zip(values,target['strings'])])
    if classes(pitches)!=classes([F(old[r]['pitch']) for r in refs]):raise ValueError('Coattack technique classification changed')
    realization=dict(anchor=str(min(pitches)),intervals=[str(p-min(pitches)) for p in pitches],strings=target['strings'])
    motion=check_paths(lanes,target,realization,typed_nominal=typed_nominal)
    if motion['status']=='REFUSED':raise ValueError(dict(incident_motion=motion))
    motion['written_vertical_invariance']=dict(target_contribution='EXACT_PER_TIME_PC_MULTISET',outside_projection='EXACT_UNCHANGED',unchanged_outside_uncertainty=outside_unknown,acoustic_harmony_verified=False)
    a=retained(docs);b=retained(after_docs)
    if encoded([t['approved_pedal_phrases'] for t in a['tracks']])!=encoded([t['approved_pedal_phrases'] for t in b['tracks']]):raise ValueError('Approved pedal interpretation changed')
    return motion


def options(upper,target_ref,prepared=None,*,typed_nominal=False):
    from connected_tier2 import realize
    c=catalog(upper,typed_nominal=typed_nominal) if prepared is None else prepared
    if c.get('typed_nominal',False)!=typed_nominal:raise ValueError('Prepared path model differs from requested evidence')
    target=next((u for u in c['units'] if u['id']==target_ref),None)
    if target is None:raise ValueError('Target has no declared degree ownership')
    if target['reasons']:return dict(status='REFUSED_TARGET',target=target,options=[],rejected=[],reasons=target['reasons'])
    candidates=defaultdict(list)
    for donor in c['units']:
        if donor['key']!=target['key'] or donor['reasons']:continue
        roles=dict(zip(donor['strings'],donor['roles']));mapped=[roles[s] for s in target['strings']]
        candidates[encoded(mapped)].append(donor)
    accepted=[];rejected=[]
    for key,donors in sorted(candidates.items()):
        roles=json.loads(key);changed=roles!=target['roles']
        try:
            if changed:
                edited=apply(upper,target,roles);after=realize(edited)
                motion=verify(c['before'],after,target,donors[0],c['lane_graph'],typed_nominal=typed_nominal)
            else:motion=dict(status='PASS_UNCHANGED_PITCH_RELATIONSHIPS')
            accepted.append(dict(roles=roles,donor_refs=[d['id'] for d in donors],changed=changed,motion=motion))
        except (ValueError,KeyError,TypeError) as error:rejected.append(dict(roles=roles,donor_refs=[d['id'] for d in donors],reason=str(error)))
    return dict(status='SUPPORTED_ALLOCATION_CHOICES' if any(v['changed'] for v in accepted) else 'NO_ADMITTED_CHANGED_ALLOCATION',target=target,options=accepted,rejected=rejected)


def sample(evidence,controls):
    rng=random.Random(controls['seed']);released=rng.random()<controls['voicing']/100
    if not released:return None,dict(status='REFERENCE_RETAINED',released=False,changed=False)
    population=[o for o in evidence['options'] for _ in o['donor_refs']]
    if not population:return None,dict(status='NO_ADMITTED_CHOICE',released=True,changed=False)
    chosen=deepcopy(rng.choice(population))
    return chosen,dict(status='SOURCE_SUPPORTED_DEGREE_ALLOCATION' if chosen['changed'] else 'OBSERVED_COINCIDENCE',released=True,changed=chosen['changed'],chosen=chosen)


def intervene(upper,controls):
    from connected_tier2 import realize
    if controls.get('register')!=0:raise ValueError('This release locks bass register')
    realize(upper)
    if controls['voicing']==0:return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False)
    evidence=options(upper,controls['target_ref'],typed_nominal=controls.get('context_policy')==NOMINAL_POLICY);chosen,report=sample(evidence,controls)
    report['evidence']=evidence
    return (deepcopy(upper) if chosen is None else apply(upper,evidence['target'],chosen['roles'])),report
