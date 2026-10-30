"""One time authority: group span * shares, with prefix sums for attacks.

Both source notation and musical event time are solutions of this relation.
There is no stored original duration vector or lower-tier reconstruction cache.
"""
from copy import deepcopy
from fractions import Fraction as F
import musical_tier2 as music

SCHEMA='source-group-rhythm/1'
VIEWS=('ensemble_coattacks','nominal_written_spans','tonal_evidence','temporal_tonal_evidence')


def coordinate(value):
    if type(value)is not str or str(F(value))!=value:raise ValueError('Canonical rational coordinate required')
    return F(value)


def relation(*,start_q,span_q,shares=None,durations_q=None):
    """SAME duration=span*share equation; inverse share=duration/span."""
    start=coordinate(start_q);span=coordinate(span_q)
    if start<0 or span<=0 or(shares is None)==(durations_q is None):raise ValueError('Positive span and exactly one relationship side required')
    if durations_q is not None:
        if type(durations_q)is not list:raise ValueError('Duration sequence required')
        shares=[str(coordinate(d)/span)for d in durations_q]
    if type(shares)is not list or len(shares)<2:raise ValueError('Complete repeated group required')
    weights=[coordinate(s)for s in shares]
    if any(s<=0 for s in weights)or sum(weights,F(0))!=1:raise ValueError('Positive shares must sum exactly to one')
    durations=[span*s for s in weights];pos=start;onsets=[]
    for d in durations:onsets.append(str(pos));pos+=d
    return dict(shares=list(shares),durations_q=list(map(str,durations)),onsets_q=onsets)


def body_of(pitch):
    if pitch.get('schema')in('source-voicing-families/1','source-declared-chord-degrees/1'):return pitch['core']
    if pitch.get('schema')=='musical-context-relations/2':return pitch
    raise ValueError('Unregistered pitch relationship')


def refresh(body):
    for g in body['coattacks']:g['interpretation']=music.interpreted(g)
    groups=body['coattacks']
    body.update(ensemble_coattacks=music.ensemble(groups),nominal_written_spans=music.written_spans(groups),
                tonal_evidence=music.tonal_evidence(groups),temporal_tonal_evidence=music.temporal_tonal_evidence(groups,body['measure_geometry']))
    return body


def lift(tier1,pitch,prepared=None):
    from source_rhythm_groups import inventory
    evidence=inventory(tier1)if prepared is None else prepared
    result=deepcopy(pitch);body=body_of(result);facts={r['id']:r for r in tier1['facts']};groups=[]
    index={m['id']:(g,m)for g in body['coattacks']for m in g['members']}
    for row in evidence['groups']:
        if row['reasons']:continue
        pairs=[index[ref]for ref in row['occurrence_refs']]
        if any(len(g['members'])!=1 for g,m in pairs):continue
        durations=[m['duration_q']for g,m in pairs]
        solved=relation(start_q=row['start_q'],span_q=row['span_q'],durations_q=durations)
        if solved['onsets_q']!=[g['onset_q']for g,m in pairs]or solved['shares']!=row['shares']:raise ValueError('Source group and musical clock disagree')
        members=[]
        for ref,beat_ref,(g,m) in zip(row['occurrence_refs'],row['beat_refs'],pairs):
            scale=facts[beat_ref+'/duration/0']['value']
            members.append(dict(occurrence_ref=ref,coattack_ref=g['id'],beat_ref=beat_ref,fraction_scale=scale))
            del g['onset_q'];del m['duration_q']
        groups.append(dict(id=row['id'],part_id=row['part_id'],bar=row['bar'],voice=row['voice'],start_q=row['start_q'],span_q=row['span_q'],shares=solved['shares'],members=members))
    for view in VIEWS:body.pop(view,None)
    for g in body['coattacks']:g.pop('interpretation',None)
    return dict(schema=SCHEMA,pitch_relationships=result,groups=groups)


def expand(shared):
    from source_rhythm_groups import TYPES
    if type(shared)is not dict or set(shared)!={'schema','pitch_relationships','groups'}or shared['schema']!=SCHEMA:raise ValueError('Unknown rhythm owner payload')
    if type(shared['groups'])is not list:raise ValueError('Ordered group list required')
    pitch=deepcopy(shared['pitch_relationships']);body=body_of(pitch)
    if 'input'in body or any(k in body for k in VIEWS)or any('interpretation'in g for g in body['coattacks']):raise ValueError('Hidden lower/derived timing payload')
    idx={m['id']:(g,m)for g in body['coattacks']for m in g['members']};seen=set();seen_ids=set();values={}
    for group in shared['groups']:
        if type(group)is not dict or set(group)!={'id','part_id','bar','voice','start_q','span_q','shares','members'}:raise ValueError('Unknown group parameters')
        if type(group['id'])is not str or any(type(group[k])is not int or group[k]<0 for k in('part_id','voice'))or type(group['bar'])is not int or group['bar']<1 or type(group['members'])is not list:raise ValueError('Typed group address required')
        if group['id']in seen_ids:raise ValueError('Duplicate group')
        seen_ids.add(group['id'])
        members=group['members'];solved=relation(start_q=group['start_q'],span_q=group['span_q'],shares=group['shares'])
        if len(members)!=len(solved['shares']):raise ValueError('Group cardinality conflict')
        if group['id']!='source-beam:'+members[0]['beat_ref']+'|'+members[-1]['beat_ref']:raise ValueError('Source bracket identity conflict')
        previous=None
        for member,onset,duration in zip(members,solved['onsets_q'],solved['durations_q']):
            if type(member)is not dict or set(member)!={'occurrence_ref','coattack_ref','beat_ref','fraction_scale'}:raise ValueError('Unknown member parameters')
            if any(type(member[k])is not str for k in('occurrence_ref','coattack_ref','beat_ref')):raise ValueError('Typed occurrence references required')
            ref=member['occurrence_ref'];g,m=idx[ref]
            expected=f"track-{g['part_id']}.json#/measures/{m['bar']-1}/voices/{m['voice']}/beats/{m['beat']}"
            if ref in seen or g['id']!=member['coattack_ref']or len(g['members'])!=1 or g['part_id']!=group['part_id']or m['bar']!=group['bar']or m['voice']!=group['voice']or m['note']!=0 or member['beat_ref']!=expected:raise ValueError('Rhythm occurrence/source ownership conflict')
            if previous is not None and m['beat']!=previous+1:raise ValueError('Noncontiguous source group')
            previous=m['beat'];seen.add(ref)
            if 'onset_q'in g or 'duration_q'in m:raise ValueError('Duplicate original timing authority')
            typ=F(4)/F(duration);scale=member['fraction_scale']
            if typ.denominator!=1 or int(typ)not in TYPES or type(scale)is not int or scale<=0:raise ValueError('Unsupported flat duration encoding')
            g['onset_q']=onset;m['duration_q']=duration
            for tail,val in (('/type',int(typ)),('/duration/0',scale),('/duration/1',scale*int(typ))):
                key=expected+tail
                if key in values:raise ValueError('Duplicate notation owner')
                values[key]=val
    # Missing times and coattack collisions are subsequently rejected by the
    # existing pitch/core validation, including all source-frame comparisons.
    if pitch.get('schema')=='musical-context-relations/2':refresh(body);music.validate(pitch)
    return pitch,values


def validate_source_groups(shared,tier1):
    """Recheck admissibility against reconstructed source, not stored claims."""
    from source_rhythm_groups import inventory
    rows={r['id']:r for r in inventory(tier1)['groups']}
    for g in shared['groups']:
        r=rows.get(g['id'])
        if r is None or r['reasons']or any(g[k]!=r[k]for k in('part_id','bar','voice','start_q','span_q','shares'))or [m['occurrence_ref']for m in g['members']]!=r['occurrence_refs']:raise ValueError('Rhythm group not supported by reconstructed source')
