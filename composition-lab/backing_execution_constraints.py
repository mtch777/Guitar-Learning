"""Existing execution endpoints and written string occupancy for one pitch owner.

This is a validator, not a detector or note selector. Numeric distances may
change. No original pitch/fret payload or performed ringing duration is stored.
"""
from copy import deepcopy
from bisect import bisect_left
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import json
import re

SCHEMA='backing-execution-constraints/1'
FIELDS={'id','kind','status','member_refs','source_fact_ref','origin_ref','destination_ref','candidate_destination_ref','tied_member_refs','direction','context','slide_type','pitch_effects_present','timing_eligible','crossed_section','reason'}
TOP={'schema','owned_refs','part_ids','obligations','unresolved_outside_neighborhood','written_string_occupancy'}
OCCUPANCY={'kind':'owned_written_string_exclusivity','clock':'half_open_written_intervals','all_voices':True,'sounding_ring_end':'not_inferred'}


def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def address(ref):
    if type(ref)is not str or not re.fullmatch(r'event:(?:0|[1-9]\d*)(?::(?:0|[1-9]\d*)){5}',ref):raise ValueError('Canonical execution occurrence required')
    return tuple(map(int,ref.split(':')[1:]))
def ordered(refs):return sorted(refs,key=address)
def _refs(refs):
    if type(refs)is not list or not refs or len(set(refs))!=len(refs):raise ValueError('Unique nonempty execution ownership required')
    return ordered(refs)
def identity(row):return 'execution:'+hashlib.sha256(encoded({k:v for k,v in row.items()if k!='id'}).encode()).hexdigest()


def _record(edge):
    s=edge['semantics']
    row=dict(kind=edge['kind'],status=edge['status'],member_refs=ordered(edge['member_refs']),
             source_fact_ref=s.get('source_fact_ref'),origin_ref=s.get('origin'),destination_ref=s.get('destination'),
             candidate_destination_ref=s.get('candidate_destination'),tied_member_refs=ordered(s.get('tied_members',[])),
             direction=s.get('direction'),context=s.get('context'),slide_type=s.get('type'),
             pitch_effects_present=s.get('pitch_effects_present'),timing_eligible=s.get('timing_eligible'),
             crossed_section=s.get('crossed_section'),reason=s.get('reason'))
    row['id']=identity(row)
    return row


@lru_cache(maxsize=2)
def _snapshot(serialized):
    # Bounded ephemeral optimization only. The exact entire current T1 is the
    # key; fresh isolated inverse workers have no source cache or hidden input.
    from source_fact_tier1 import project_documents
    import execution_dependencies
    t1=json.loads(serialized);graph=execution_dependencies.build(t1)
    docs=project_documents(t1)
    from source_semantics import layout
    from analyze_relationships import occurrences
    parts=[docs[n]for n in sorted((n for n in docs if n.startswith('track-')),key=lambda n:int(n[6:-5]))]
    headers,shared=layout(parts);nodes={};uncertain=[]
    for part in parts:
        pid=part['partId'];rows,grace,_,warnings=occurrences(part,headers)
        if warnings or shared:uncertain.append(pid)
        grace_ids={r['occurrence']for r in grace}
        for r in rows+grace:
            ref=f"event:{docs['metadata.json']['songId']}:{r['occurrence']}"
            if ref in nodes:raise ValueError('Duplicate execution occurrence')
            nodes[ref]=dict(ref=ref,part=pid,voice=r['voice'],string=r['string'],string_valid=type(r['string'])is int and 0<=r['string']<len(part.get('tuning')or[]),onset=F(r['onset_q']),duration=F(r['duration_q']),grace=r['occurrence']in grace_ids,tie_destination=r['tie_destination'],pitch=r['midi'],fret=r['fret'],bar=r['bar'],beat=r['beat'],note=r['note'],occurrence=r['occurrence'])
    return dict(records=[_record(e)for e in graph['edges']],nodes=nodes,uncertain_parts=uncertain)


def _parts(row):
    result={address(ref)[1]for ref in row['member_refs']}
    if row['source_fact_ref']:
        match=re.match(r'track-(\d+)\.json#',row['source_fact_ref'])
        if match:result.add(int(match.group(1)))
    return result


def _neighborhood(row,nodes):
    """The exact input set of the approved HP/slide successor lookup.

    This does not identify new endpoints: it follows the inputs consulted by
    analyze_relationships.hopo / source_slides.resolve_slides, including their
    early exits, sorting and failed tie-prefix check. Values are ephemeral.
    """
    result=set(row['member_refs'])
    for ref in result:
        if ref not in nodes:raise ValueError('Execution dependency outside written occurrence inventory')
    hp=row['kind']=='hopo' and row['status']=='unresolved'
    slide=row['kind']=='slide' and row['slide_type']in('shift','legato')
    if slide and row['status']in('grace_origin_order_unresolved','unknown_string','origin_tie_requires_chain','excluded_for_timing'):
        slide=False
    origin=row['origin_ref']
    if not(hp or slide)or origin is None or origin not in nodes:return result
    focal=nodes[origin]
    if focal['string']is None:return result
    lane=[r for r in nodes.values()if (r['part'],r['voice'],r['string'])==(focal['part'],focal['voice'],focal['string'])and not r['grace']]
    lane.sort(key=(lambda r:(r['onset'],r['occurrence']))if hp else(lambda r:(r['onset'],r['bar'],r['beat'],r['note'])))
    positions=[i for i,r in enumerate(lane)if r['ref']==origin]
    if not positions:return result
    end=focal['onset']+focal['duration']
    for candidate in lane[positions[0]+1:]:
        # The failed next-note check itself is a consulted input; notes after
        # it are not, even when they also carry literal tie markers.
        result.add(candidate['ref'])
        follows=(candidate['tie_destination']and candidate['onset']==end and
                 candidate['pitch']==focal['pitch']and candidate['fret']==focal['fret'])
        if slide and focal['pitch']is None:follows=False
        if not follows:break
        end+=candidate['duration']
    return result


def _occupancy_index(nodes):
    """Ephemeral bounds over the current written contacts, never saved state.

    Grace contacts are points, including a point exactly at an owned onset.
    Positive written intervals ending exactly there may remain candidates;
    the unchanged half-open predicate below rejects those boundary contacts.
    """
    parts={}
    for ordinal,(ref,node) in enumerate(nodes.items()):
        if not node['grace'] and node['duration']<=0:continue
        parts.setdefault(node['part'],[]).append((ordinal,ref,node))
    index={}
    for part,rows in parts.items():
        rows.sort(key=lambda row:row[2]['onset'])
        onsets=[];ends=[];maximum=None
        for _,_,node in rows:
            onset=node['onset'];end=onset if node['grace'] else onset+node['duration']
            maximum=end if maximum is None else max(maximum,end)
            onsets.append(onset);ends.append(maximum)
        index[part]=(rows,onsets,ends)
    return index


def _occupancy(nodes,refs):
    index=None
    for ref in refs:
        a=nodes[ref]
        if a['grace']or a['duration']<=0 or not a['string_valid']:
            raise ValueError('UNVERIFIED_OWNED_WRITTEN_CONTACT')
        if index is None:index=_occupancy_index(nodes)
        rows,onsets,ends=index[a['part']]
        first=bisect_left(ends,a['onset'])
        stop=bisect_left(onsets,a['onset']+a['duration'])
        # Bounds only prune impossible contacts. Preserve source insertion
        # order and every original predicate, including the first refusal.
        for _,other,b in sorted(rows[first:stop],key=lambda row:row[0]):
            if ref==other or a['part']!=b['part']:continue
            if b['grace']:
                if a['onset']<=b['onset']<a['onset']+a['duration']:
                    raise ValueError('UNVERIFIED_GRACE_CONTACT_ORDER: no performed duration inferred')
                continue
            if b['duration']<=0:continue
            if max(a['onset'],b['onset'])>=min(a['onset']+a['duration'],b['onset']+b['duration']):continue
            if not b['string_valid']:raise ValueError('UNVERIFIED_OVERLAPPING_STRING')
            if a['string']==b['string']:
                raise ValueError(f'WRITTEN_STRING_COLLISION: {ref} overlaps {other}')


def build(tier1,owned_refs):
    refs=_refs(owned_refs);parts=sorted({address(ref)[1]for ref in refs});data=_snapshot(encoded(tier1));nodes=data['nodes']
    if not set(refs)<=set(nodes):raise ValueError('Dangling execution owner')
    if set(parts)&set(data['uncertain_parts']):raise ValueError('UNVERIFIED_EXECUTION_CLOCK: existing parser reports timing uncertainty')
    _occupancy(nodes,refs)
    known=[];unknown=[]
    for row in data['records']:
        if not set(parts)&_parts(row):continue
        resolved=(row['kind']=='hopo'and row['status']=='source_transition_candidate')or(row['kind']=='slide'and row['status']=='resolved_written_target')
        if resolved:
            known.append(deepcopy(row))
        else:
            if set(refs)&_neighborhood(row,nodes):
                raise ValueError('UNRESOLVED_AFFECTED_EXECUTION: '+row['kind']+'/'+row['status'])
            unknown.append(deepcopy(row))
    return dict(schema=SCHEMA,owned_refs=refs,part_ids=parts,obligations=sorted(known,key=lambda r:r['id']),
                unresolved_outside_neighborhood=sorted(unknown,key=lambda r:r['id']),written_string_occupancy=deepcopy(OCCUPANCY))


def shape(scope,owned_refs):
    refs=_refs(owned_refs)
    if type(scope)is not dict or set(scope)!=TOP or scope['schema']!=SCHEMA or scope['owned_refs']!=refs or scope['part_ids']!=sorted({address(ref)[1]for ref in refs}) or encoded(scope['written_string_occupancy'])!=encoded(OCCUPANCY):raise ValueError('Complete execution obligations required')
    ids=[]
    for field in ('obligations','unresolved_outside_neighborhood'):
        rows=scope[field]
        if type(rows)is not list:raise ValueError('Typed execution obligations required')
        for row in rows:
            if type(row)is not dict or set(row)!=FIELDS or row['id']!=identity(row):raise ValueError('Execution identity mismatch or forbidden old note payload')
            if row['member_refs']!=ordered(row['member_refs']) or row['tied_member_refs']!=ordered(row['tied_member_refs']):raise ValueError('Canonical execution references required')
            ids.append(row['id'])
        if rows!=sorted(rows,key=lambda r:r['id']):raise ValueError('Canonical execution obligation order required')
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate execution obligation')


def validate(scope,tier1,owned_refs):
    """SAME current-source endpoint and occupancy predicate in either direction."""
    shape(scope,owned_refs)
    current=build(tier1,owned_refs)
    if encoded(current)!=encoded(scope):raise ValueError('EXECUTION_OBLIGATIONS_CHANGED: endpoint, kind, context or unknown neighborhood differs')


def proposed(scope,before,owned_refs,edits):
    validate(scope,before,owned_refs)
    if type(edits)is not dict or not set(edits)<=set(owned_refs):raise ValueError('Bounded proposed physical edits required')
    changed=dict(before,facts=list(before['facts']));index={r['id']:i for i,r in enumerate(changed['facts'])}
    for ref,values in edits.items():
        if type(values)is not dict or set(values)!={'string','fret'}or any(type(v)is not int or v<0 for v in values.values()):raise ValueError('Explicit integral written contacts required')
        _,pid,bar,voice,beat,note=address(ref);pointer=f'track-{pid}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}/notes/{note}'
        for key,value in values.items():
            fact=pointer+'/'+key
            if fact not in index or changed['facts'][index[fact]]['type']!='integer':raise ValueError('Existing integer contact owner required')
            changed['facts'][index[fact]]=dict(changed['facts'][index[fact]],value=value)
    validate(scope,changed,owned_refs)
