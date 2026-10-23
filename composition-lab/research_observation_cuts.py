"""Research adapter: remove ONLY explicitly experiment-created support cuts.

Original source boundaries are never coalesced. No attack is inferred from a
boundary, and no model parameter, musical score or product interface is changed.
"""
from copy import deepcopy
from fractions import Fraction as F
from diagnose_tonal_subdivision import check_rows


SCHEMA='research-source-support-cuts/1'


def validate_support(refs):
    if type(refs) is not list or any(type(r) is not str or not r for r in refs) or len(refs)!=len(set(refs)):
        raise ValueError('Unique exact source-support refs required')


def prepare(observations,supports,boundary_events=None):
    """Split supported nonempty cells; retain rest/empty-support cells intact."""
    check_rows(observations)
    if set(supports)!={r['id'] for r in observations}:raise ValueError('Complete source-support inventory required')
    boundary_events={} if boundary_events is None else boundary_events
    if set(boundary_events)-set(supports):raise ValueError('Unknown original boundary')
    children=[];membership=[];unsplit=[]
    for i,row in enumerate(observations):
        refs=supports[row['id']];validate_support(refs)
        original_events=deepcopy(boundary_events.get(row['id'],[]))
        if type(original_events) is not list or any(type(x)is not str for x in original_events):raise ValueError('Typed boundary-event witnesses required')
        split=bool(refs) and row['mask']!=0
        midpoint=str((F(row['start_q'])+F(row['end_q']))/2)
        cuts=[(row['start_q'],midpoint),(midpoint,row['end_q'])] if split else [(row['start_q'],row['end_q'])]
        ids=[]
        for j,(a,b) in enumerate(cuts):
            ident=f'research-cut:{i}:{j}';ids.append(ident)
            child=dict(row,id=ident,start_q=a,end_q=b,previous_mask=row['previous_mask'] if j==0 else row['mask'])
            children.append(dict(observation=child,support_refs=deepcopy(refs),boundary_kind='original_source_boundary' if j==0 else 'experiment_created_cut',boundary_events=original_events if j==0 else []))
        membership.append(dict(parent_ref=row['id'],child_refs=ids))
        if not split:unsplit.append(dict(parent_ref=row['id'],reason='REST_OR_EMPTY_SUPPORT_NOT_SUBDIVIDED'))
    return dict(schema=SCHEMA,children=children,membership=membership),unsplit


def canonicalize(packet):
    if set(packet)!={'schema','children','membership'} or packet['schema']!=SCHEMA:raise ValueError('Typed experiment-cut packet required')
    children=packet['children'];rows=[c['observation'] for c in children];check_rows(rows)
    index={r['observation']['id']:r for r in children};used=[];parents=set();observations=[];witnesses=[];supports=[]
    for link in packet['membership']:
        if set(link)!={'parent_ref','child_refs'} or type(link['parent_ref']) not in (int,str) or link['parent_ref'] in parents or not link['child_refs']:raise ValueError('Invalid original boundary membership')
        parents.add(link['parent_ref']);group=[index[i] for i in link['child_refs']];first=group[0];base=first['observation'];refs=first['support_refs'];validate_support(refs)
        if len(group)>1 and (not refs or base['mask']==0):raise ValueError('Rest/empty-support cuts cannot coalesce')
        witness=[]
        for j,c in enumerate(group):
            if set(c)!={'observation','support_refs','boundary_kind','boundary_events'}:raise ValueError('Unexpected cut payload')
            row=c['observation'];used.append(row['id']);validate_support(c['support_refs'])
            if c['support_refs']!=refs or row['mask']!=base['mask'] or row['sequence']!=base['sequence']:raise ValueError('Changed note support/rest/sequence cannot coalesce')
            expected='original_source_boundary' if j==0 else 'experiment_created_cut'
            if c['boundary_kind']!=expected or type(c['boundary_events']) is not list or any(type(e)is not str for e in c['boundary_events']):raise ValueError('Original event boundary cannot be erased')
            if j and (c['boundary_events'] or group[j-1]['observation']['end_q']!=row['start_q']):raise ValueError('Source event or gap at experiment cut')
            witness.append(dict(child_ref=row['id'],start_q=row['start_q'],end_q=row['end_q'],boundary_kind=c['boundary_kind'],boundary_events=deepcopy(c['boundary_events'])))
        observations.append(dict(base,id=link['parent_ref'],end_q=group[-1]['observation']['end_q']))
        witnesses.append(dict(parent_ref=link['parent_ref'],children=witness));supports.append(dict(parent_ref=link['parent_ref'],source_note_refs=deepcopy(refs)))
    if used!=[r['id'] for r in rows]:raise ValueError('Missing/duplicate/reordered child membership')
    check_rows(observations)
    return dict(schema='research-canonical-observations/1',observations=observations,source_support=supports,subdivision_witnesses=witnesses)


def restore(canonical):
    if set(canonical)!={'schema','observations','source_support','subdivision_witnesses'} or canonical['schema']!='research-canonical-observations/1':raise ValueError('Typed canonical experiment required')
    check_rows(canonical['observations']);obs={r['id']:r for r in canonical['observations']};supports={r['parent_ref']:r['source_note_refs'] for r in canonical['source_support']}
    if len(supports)!=len(canonical['source_support']) or set(supports)!=set(obs):raise ValueError('Source-support denominator differs')
    children=[];membership=[];seen=[]
    for w in canonical['subdivision_witnesses']:
        if set(w)!={'parent_ref','children'} or not w['children']:raise ValueError('Invalid cut witness')
        parent=w['parent_ref'];row=obs[parent];seen.append(parent);ids=[]
        if w['children'][0]['start_q']!=row['start_q'] or w['children'][-1]['end_q']!=row['end_q']:raise ValueError('Lost original span')
        for j,c in enumerate(w['children']):
            if set(c)!={'child_ref','start_q','end_q','boundary_kind','boundary_events'}:raise ValueError('Unexpected structural witness')
            ids.append(c['child_ref']);child=dict(row,id=c['child_ref'],start_q=c['start_q'],end_q=c['end_q'],previous_mask=row['previous_mask'] if j==0 else row['mask'])
            children.append(dict(observation=child,support_refs=deepcopy(supports[parent]),boundary_kind=c['boundary_kind'],boundary_events=deepcopy(c['boundary_events'])))
        membership.append(dict(parent_ref=parent,child_refs=ids))
    if seen!=[r['id'] for r in canonical['observations']]:raise ValueError('Original boundary inventory differs')
    packet=dict(schema=SCHEMA,children=children,membership=membership)
    if canonicalize(packet)!=canonical:raise ValueError('Canonical witness conflict')
    return packet
