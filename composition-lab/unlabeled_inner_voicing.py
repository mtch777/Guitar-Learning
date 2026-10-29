"""Source inner patterns valid under EVERY retained chord assumption.

Conditional degrees constrain proposals. Existing musical owners and the
connected inverse alone realize them; no inferred true root or pitch backup.
"""
from copy import deepcopy
from fractions import Fraction as F
from harmonic_evidence import source_patterns,context
from harmonic_pattern_ledger import build as build_ledger
from inner_voicing import encoded,verify,PREVIEW_POLICY
from declared_degree_choices import sample
from voicing_frames import pitches
import musical_tier2 as music

POLICY='all_hypothesis_inner_preview'


def catalog(upper):
    c=source_patterns(upper)
    c['ledger']=build_ledger(c,c['harmonic_evidence'])
    c['owner_context']=context(upper)
    return c


def solve(c,row,layout):
    """Every conditional degree equation must produce the same occurrences."""
    units={u['id']:u for u in c['units']};support=layout['support']
    ids=[s['target_hypothesis_ref'] for s in support]
    if len(ids)!=len(set(ids)) or set(ids)!=set(row['all_hypothesis_refs']):raise ValueError('INCOMPLETE_ASSUMPTION_SUPPORT')
    solved=[]
    for s in support:
        u=units[s['target_hypothesis_ref']]
        if u['member_refs']!=row['member_refs']:raise ValueError('ASSUMPTION_OCCURRENCE_ORDER_CHANGED')
        if len(s['roles'])!=len(u['member_refs']):raise ValueError('INCOMPLETE_PROPOSED_DEGREES')
        solved.append(pitches(*u['family'][1:],s['roles']))
    if not solved or any(p!=solved[0] for p in solved):raise ValueError('ASSUMPTIONS_DISAGREE_ON_OUTPUT')
    if list(map(str,solved[0]))!=layout['pitches']:raise ValueError('STALE_RESOLVED_LAYOUT')
    return list(map(str,solved[0]))


def apply(upper,row,layout,prepared=None):
    """Solve into the existing owner; reuse its forward lift and inverse."""
    import voicing_families
    import declared_chord_ownership as declared
    c=catalog(upper) if prepared is None else prepared
    solved=solve(c,row,layout);ctx=c['owner_context'];core=deepcopy(ctx['core'])
    group=next(g for g in core['coattacks'] if g['id']==row['group_ref'])
    if [m['id'] for m in group['members']]!=row['member_refs']:raise ValueError('OWNER_OCCURRENCE_ORDER_CHANGED')
    anchor=group['bass_register_anchor']
    if min(map(F,solved))!=F(anchor):raise ValueError('PROTECTED_BASS_CHANGED')
    for m,p in zip(group['members'],solved):m['voicing_interval']=music.relation(anchor=anchor,pitch=p)['interval']
    # Recompute only derived views through the SAME existing analysis/equations.
    core=music.strip_lower(music.analyze(music.realize(core)))
    owner=upper['musical_relationships']
    if owner['schema']==declared.SCHEMA:
        core=declared.lift(core,ctx['labels'],ctx['capos'],profile=ctx['profile'])
    elif owner['schema']==voicing_families.SCHEMA:core=voicing_families.lift(core)
    elif owner['schema']!='musical-context-relations/2':raise ValueError('UNSUPPORTED_PITCH_OWNER')
    edited=deepcopy(upper);edited['musical_relationships']=core
    return edited


def degree_roundtrip(c,row,layout,actual_nodes):
    from chord_degree_relations import note_role
    hypotheses={h['id']:h for g in c['harmonic_evidence']['groups'] for h in g['hypotheses']}
    units={u['id']:u for u in c['units']};out=[]
    for s in layout['support']:
        u=units[s['target_hypothesis_ref']];h=hypotheses[u['id']];roles=[]
        for ref in row['member_refs']:
            r=note_role(actual_nodes[ref]['pitch'],h)['degree_relationships']
            if len(r)!=1:raise ValueError('INVERSE_DEGREE_AMBIGUITY')
            roles.append(dict(degree_token=r[0]['token'],relative_octaves=r[0]['relative_octaves']))
        if roles!=s['roles']:raise ValueError('INVERSE_DID_NOT_REALIZE_PROPOSED_DEGREES')
        out.append(dict(hypothesis_ref=u['id'],status='EXACT_PROPOSED_DEGREE_RECOVERY'))
    return out


def options(upper,target_ref,prepared=None):
    from connected_tier2 import realize
    from voicing_context_relations import graph
    import nominal_harmony as temporal
    c=catalog(upper) if prepared is None else prepared
    observed=next((g for g in c['harmonic_evidence']['groups'] if g['member_refs'] and g['member_refs'][0]==target_ref),None)
    if observed is None:raise ValueError('Unknown original source target')
    row=next((g for g in c['ledger']['groups'] if g['group_ref']==observed['group_ref']),None)
    if row is None:return dict(status='NO_EXACT_HARMONIC_ASSUMPTIONS',target_ref=target_ref,target=observed,all_hypothesis_refs=[],options=[],rejected=[])
    units={u['id']:u for u in c['units']};accepted=[];rejected=[]
    for layout in row['layouts']:
        option=deepcopy(layout)
        option['donor_refs']=sorted({g for s in layout['support'] for g in s['donor_group_refs']})
        if layout['support_class']!='ALL_ENUMERATED_TARGET_ASSUMPTIONS':
            rejected.append(dict(option,reason='NOT_SUPPORTED_UNDER_EVERY_RETAINED_ASSUMPTION'));continue
        try:
            solved=solve(c,row,layout)
            if layout['changed']:
                after=realize(apply(upper,row,layout,c));new=graph(after,typed_nominal=True)['nodes'];proof=[]
                for s in layout['support']:
                    target=units[s['target_hypothesis_ref']];donor=units[s['donor_hypothesis_refs'][0]]
                    proof.append(dict(hypothesis_ref=target['id'],checks=verify(c,after,target,donor,physical_policy=PREVIEW_POLICY)))
                roundtrip=degree_roundtrip(c,row,layout,new)
                if 'temporal_context' not in c:
                    tc=temporal.prepare(upper);c['temporal_context']=(tc,temporal.build(tc))
                changed=[r for r,p in zip(row['member_refs'],solved) if c['lane_graph']['nodes'][r]['pitch']!=p]
                tc,tv=c['temporal_context']
                option['relationship']=dict(status='PROVISIONAL_ALL_ASSUMPTION_INNER_RELATIONSHIPS',checks=proof,
                    degree_roundtrip=roundtrip,edited_set_context=temporal.edited_set_context(tc,tv,new,changed),
                    human_playability='UNVERIFIED',musical_fit='UNVERIFIED_FOR_THIS_CHANGE')
            else:option['relationship']=dict(status='UNCHANGED_INNER_COMPONENT')
            accepted.append(option)
        except (ValueError,KeyError,TypeError) as error:rejected.append(dict(option,reason=str(error)))
    return dict(status='SUPPORTED_ALL_ASSUMPTION_INNER_CHOICES' if any(o['changed'] for o in accepted) else 'NO_ADMITTED_CHANGED_INNER_COMPONENT',
                target_ref=target_ref,target=row,all_hypothesis_refs=row['all_hypothesis_refs'],options=accepted,rejected=rejected)


def intervene(upper,controls):
    from connected_tier2 import realize
    if controls.get('context_policy')!=POLICY or controls.get('register')!=0:raise ValueError('This scope requires its named policy and locked outer registers')
    realize(upper)
    if controls['voicing']==0:return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False)
    c=catalog(upper);evidence=options(upper,controls['target_ref'],c);chosen,report=sample(evidence,controls)
    report.update(evidence=evidence,physical_policy=PREVIEW_POLICY,human_playability='UNVERIFIED',musical_fit='UNVERIFIED_FOR_THIS_CHANGE')
    if report['changed']:report['status']='PROVISIONAL_ALL_ASSUMPTIONS_'+report['status']
    return (deepcopy(upper) if chosen is None else apply(upper,evidence['target'],chosen,c)),report
