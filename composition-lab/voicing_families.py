"""Shared source spacing owners; lowest written pitch is not an inferred root.

Pitch = bass anchor + slot interval. Definitions own intervals once; occurrences
own their choice/permutation. Existing musical relations derive all context views.
"""
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
import musical_tier2 as music

SCHEMA='source-voicing-families/1'
VIEWS=('ensemble_coattacks','nominal_written_spans','tonal_evidence','temporal_tonal_evidence')
GROUP={'id','part_id','bar','timing_uncertain','onset_q','scope_type','bass_register_anchor','members'}


def identifier(intervals):
    return 'spacing:'+hashlib.sha256(json.dumps(intervals,separators=(',',':')).encode()).hexdigest()


def eligible(group):
    return len(group['members'])>=2 and group['bass_register_anchor'] is not None and all(m.get('voicing_interval') is not None for m in group['members'])


def slot_order(group):
    return sorted(range(len(group['members'])),key=lambda i:(F(group['members'][i]['voicing_interval'])%12,F(group['members'][i]['voicing_interval']),group['members'][i]['id']))


def lift(core):
    if 'input' in core:raise ValueError('Remove lower payload before family analysis')
    music.validate(core)
    body=deepcopy(core);definitions={}
    for field in VIEWS:body.pop(field)
    for group in body['coattacks']:
        group.pop('interpretation')
        if not eligible(group):continue
        permutation=slot_order(group)
        intervals=[group['members'][i]['voicing_interval'] for i in permutation]
        ref=identifier(intervals);definitions[ref]=dict(id=ref,intervals=intervals)
        group.update(spacing_ref=ref,member_permutation=permutation)
        for member in group['members']:member.pop('voicing_interval')
    return dict(schema=SCHEMA,core=body,spacings=[definitions[k] for k in sorted(definitions)])


def realize(shared):
    if type(shared)is not dict or set(shared)!={'schema','core','spacings'} or shared['schema']!=SCHEMA:raise ValueError('Undeclared family payload')
    body=deepcopy(shared['core']);definitions={};used=set()
    if 'input' in body or any(k in body for k in VIEWS):raise ValueError('Lower or derived cache in family owner')
    for definition in shared['spacings']:
        if type(definition)is not dict or set(definition)!={'id','intervals'}:raise ValueError('Undeclared spacing owner')
        intervals=definition['intervals']
        if type(intervals)is not list or len(intervals)<2 or any(type(v)is not str or str(F(v))!=v or F(v)<0 for v in intervals) or min(map(F,intervals))!=0:raise ValueError('Invalid spacing coordinates')
        if sorted(intervals,key=lambda v:(F(v)%12,F(v)))!=intervals:raise ValueError('Noncanonical spacing slots')
        ref=definition['id']
        if ref!=identifier(intervals) or ref in definitions:raise ValueError('Duplicate/stale spacing identity')
        definitions[ref]=intervals
    if list(definitions)!=sorted(definitions):raise ValueError('Noncanonical spacing registry')
    for group in body['coattacks']:
        factored='spacing_ref' in group or 'member_permutation' in group
        if set(group)!=GROUP|({'spacing_ref','member_permutation'} if factored else set()):raise ValueError('Undeclared group owner')
        if not factored:
            if eligible(group):raise ValueError('Eligible intervals must have one shared owner')
            continue
        ref=group.pop('spacing_ref');permutation=group.pop('member_permutation');members=group['members']
        if ref not in definitions:raise ValueError('Missing spacing definition')
        intervals=definitions[ref]
        if type(permutation)is not list or len(intervals)!=len(members) or len(permutation)!=len(members) or any(type(i)is not int for i in permutation) or sorted(permutation)!=list(range(len(members))):raise ValueError('Nonbijective source-member permutation')
        for member in members:
            if set(member)!=music.MEMBER_FIELDS-{'voicing_interval'}:raise ValueError('Duplicate or hidden interval owner')
        for source_index,value in zip(permutation,intervals):members[source_index]['voicing_interval']=value
        if not eligible(group) or slot_order(group)!=permutation:raise ValueError('Noncanonical family member correspondence')
        used.add(ref)
    if used!=set(definitions):raise ValueError('Unused spacing owner')
    for group in body['coattacks']:group['interpretation']=music.interpreted(group)
    groups=body['coattacks']
    body.update(ensemble_coattacks=music.ensemble(groups),nominal_written_spans=music.written_spans(groups),tonal_evidence=music.tonal_evidence(groups),temporal_tonal_evidence=music.temporal_tonal_evidence(groups,body['measure_geometry']))
    music.validate(body)
    return body


def validate(shared):
    core=realize(shared)
    if lift(core)!=shared:raise ValueError('Noncanonical family ownership')
    return core


def choose(shared,member_refs,intervals):
    """Select a source definition; never manufacture a new interval owner."""
    result=deepcopy(shared);wanted=set(member_refs)
    group=next(g for g in result['core']['coattacks'] if {m['id'] for m in g['members']}==wanted)
    ref=identifier(intervals)
    if ref not in {d['id'] for d in result['spacings']}:raise ValueError('Choice has no observed spacing definition')
    if 'spacing_ref' not in group:raise ValueError('Choice outside family-owned scope')
    by_ref=dict(zip(member_refs,intervals));indices={m['id']:i for i,m in enumerate(group['members'])}
    ordered=sorted(member_refs,key=lambda r:(F(by_ref[r])%12,F(by_ref[r]),r))
    group['spacing_ref']=ref;group['member_permutation']=[indices[r] for r in ordered]
    used={g['spacing_ref'] for g in result['core']['coattacks'] if 'spacing_ref' in g}
    result['spacings']=[d for d in result['spacings'] if d['id'] in used]
    validate(result)
    return result
