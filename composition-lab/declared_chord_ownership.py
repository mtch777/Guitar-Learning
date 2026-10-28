"""Written chord degrees own supported notes; source labels remain conditional.

No chord duration, key, acoustic harmony or artistic intention is inferred.
Selected groups lose their old bass/interval owner. Both directions use the
existing chord-degree equation; unmatched groups keep their existing owner.
"""
from copy import deepcopy
from fractions import Fraction as F
import re
import musical_tier2 as music
from chord_degree_definitions import degree_definitions
from chord_degree_relations import note_role,pitch_from_degree
from chord_symbol_lexicon import parse,LEGACY_PROFILE,CURRENT_PROFILE
from voicing_families import GROUP,VIEWS

SCHEMA='source-declared-chord-degrees/1'
LABEL=re.compile(r'^track-(\d+)\.json#/measures/(\d+)/voices/(\d+)/beats/(\d+)/chord/text$')
CAPO=re.compile(r'^track-(\d+)\.json#/capo$')


def label_values(choices,facts):
    """Decode referenced declarations from their ONE existing scalar owner."""
    from technique_observation_relations import scalar_relation
    index={r['id']:r for r in facts};values={}
    for choice in choices:
        ref=choice['fact_ref']
        if LABEL.fullmatch(ref):
            if ref in values:raise ValueError('Duplicate chord literal owner')
            values[ref]=scalar_relation(index[ref]['type'],parameter=choice['parameter'])
    return values


def capo_values(choices,facts):
    from technique_observation_relations import scalar_relation
    index={r['id']:r for r in facts};values={}
    for choice in choices:
        ref=choice['fact_ref'];match=CAPO.fullmatch(ref)
        if match:
            pid=int(match[1])
            if pid in values:raise ValueError('Duplicate capo owner')
            values[pid]=scalar_relation(index[ref]['type'],parameter=choice['parameter'])
    return values


def attached(group,labels):
    addresses={(group['part_id'],m['bar']-1,m['voice'],m['beat']) for m in group['members']}
    return sorted(ref for ref in labels if (match:=LABEL.fullmatch(ref)) and tuple(map(int,match.groups())) in addresses)


def selection(group,labels,capos=None,*,profile=CURRENT_PROFILE):
    refs=attached(group,labels)
    if len(refs)!=1:return dict(status='NO_DECLARATION' if not refs else 'MULTIPLE_DECLARATIONS',declaration_refs=refs)
    addresses={(m['bar']-1,m['voice'],m['beat']) for m in group['members']}
    if len(addresses)!=1:return dict(status='MIXED_DECLARING_BEAT_SCOPE',declaration_refs=refs)
    capo=(capos or {}).get(group['part_id'])
    if capo is not None and not(type(capo) in (int,float) and capo==0):return dict(status='UNVERIFIED_CAPO_LABEL_CONVENTION',declaration_refs=refs)
    if any(F(m['duration_q'])<=0 for m in group['members']):return dict(status='GRACE_OR_NONPOSITIVE_DURATION',declaration_refs=refs)
    ref=refs[0];parsed=parse(labels[ref],profile=profile)
    if parsed['status']!='UNIQUE_LIBRARY_SYMBOL':return dict(status=parsed['status'],declaration_refs=refs)
    if group['timing_uncertain']:return dict(status='UNCERTAIN_SOURCE_CLOCK',declaration_refs=refs)
    pitches=[music.member_pitch(group,m) for m in group['members']]
    if not pitches or any(p is None or F(p).denominator!=1 for p in pitches):return dict(status='UNKNOWN_WRITTEN_PITCH',declaration_refs=refs)
    h=parsed['interpretations'][0];definitions=degree_definitions(h['kind']);formula=sorted({d['pitch_class'] for d in definitions})
    actual={int(F(p)%12) for p in pitches};expected={(h['root_pc']+d)%12 for d in formula}
    if len(actual)<2:return dict(status='NOT_MULTIPLE_PITCH_CLASSES',declaration_refs=refs)
    if actual!=expected:return dict(status='SYMBOL_PITCH_SET_MISMATCH',declaration_refs=refs,missing=sorted(expected-actual),outside=sorted(actual-expected))
    if h['explicit_bass_pc'] is not None and int(min(map(F,pitches))%12)!=h['explicit_bass_pc']:return dict(status='EXPLICIT_SLASH_BASS_MISMATCH',declaration_refs=refs)
    label=dict(root_pc=h['root_pc'],kind=h['kind'],formula=formula)
    roles=[note_role(p,label)['degree_relationships'] for p in pitches]
    if any(len(r)!=1 for r in roles):return dict(status='AMBIGUOUS_DEGREE_ASSIGNMENT',declaration_refs=refs)
    return dict(status='SUPPORTED_DECLARED_WRITTEN_CHORD',declaration_refs=refs,label=label,
        roles=[r[0] for r in roles],explicit_bass_pc=h['explicit_bass_pc'])


def inspect(core,labels,capos=None,*,profile=CURRENT_PROFILE):
    rows=[dict(group_ref=g['id'],onset_q=g['onset_q'],**selection(g,labels,capos,profile=profile)) for g in core['coattacks']]
    used={ref for r in rows for ref in r['declaration_refs']}
    return dict(groups=rows,unattached_declarations=sorted(set(labels)-used),
        declaration_count=len(labels),scope='Declaring beat/coattack only; conditional written chord, no implied label duration or acoustic truth')


def lift(core,labels,capos=None,*,profile=CURRENT_PROFILE):
    if profile not in (LEGACY_PROFILE,CURRENT_PROFILE):raise ValueError('Unknown immutable chord admission profile')
    if 'input' in core:raise ValueError('Remove previous-tier payload before degree ownership')
    music.validate(core);body=deepcopy(core)
    for field in VIEWS:body.pop(field)
    for group in body['coattacks']:
        group.pop('interpretation');selected=selection(group,labels,capos,profile=profile)
        if selected['status']!='SUPPORTED_DECLARED_WRITTEN_CHORD':continue
        group.pop('bass_register_anchor');group['declared_chord_ref']=selected['declaration_refs'][0]
        for member,role in zip(group['members'],selected['roles']):
            member.pop('voicing_interval');member.update(degree_token=role['token'],relative_octaves=role['relative_octaves'])
    output=dict(schema=SCHEMA,core=body)
    if profile!=LEGACY_PROFILE:output['admission_profile']=profile
    return output


def realize(shared,labels,capos=None):
    if type(shared)is not dict or set(shared) not in ({'schema','core'},{'schema','core','admission_profile'}) or shared['schema']!=SCHEMA:raise ValueError('Undeclared chord-degree payload')
    profile=shared.get('admission_profile',LEGACY_PROFILE)
    if profile not in (LEGACY_PROFILE,CURRENT_PROFILE):raise ValueError('Unknown immutable chord admission profile')
    if profile==LEGACY_PROFILE and 'admission_profile' in shared:raise ValueError('Legacy chord admission uses its historical field-free envelope')
    body=deepcopy(shared['core'])
    if 'input' in body or any(k in body for k in VIEWS):raise ValueError('Lower or derived cache in degree owner')
    for group in body['coattacks']:
        if 'declared_chord_ref' not in group:
            if set(group)!=GROUP or any(set(m)!=music.MEMBER_FIELDS for m in group['members']):raise ValueError('Undeclared fallback owner')
            continue
        if set(group)!=(GROUP-{'bass_register_anchor'})|{'declared_chord_ref'}:raise ValueError('Duplicate or hidden group pitch owner')
        ref=group.pop('declared_chord_ref')
        if ref not in labels or attached(group,labels)!=[ref]:raise ValueError('Chord declaration belongs to another group or is ambiguous')
        parsed=parse(labels[ref],profile=profile)
        if parsed['status']!='UNIQUE_LIBRARY_SYMBOL':raise ValueError('Declared chord no longer has a unique interpretation')
        h=parsed['interpretations'][0];defs={d['token']:d for d in degree_definitions(h['kind'])};pitches=[]
        for member in group['members']:
            if set(member)!=(music.MEMBER_FIELDS-{'voicing_interval'})|{'degree_token','relative_octaves'}:raise ValueError('Duplicate or hidden note pitch owner')
            token=member.pop('degree_token');octaves=member.pop('relative_octaves')
            if type(token)is not str or token not in defs or type(octaves)is not int:raise ValueError('Typed template degree/register required')
            pitches.append(pitch_from_degree(h['root_pc'],h['kind'],dict(defs[token],relative_octaves=octaves)))
        if not pitches:raise ValueError('Missing declared chord members')
        anchor=str(min(map(F,pitches)));group['bass_register_anchor']=anchor
        for member,pitch in zip(group['members'],pitches):member['voicing_interval']=music.relation(anchor=anchor,pitch=pitch)['interval']
        if selection(group,labels,capos,profile=profile)['status']!='SUPPORTED_DECLARED_WRITTEN_CHORD':raise ValueError('Actual degree realization no longer supports the source declaration')
    for group in body['coattacks']:group['interpretation']=music.interpreted(group)
    groups=body['coattacks']
    body.update(ensemble_coattacks=music.ensemble(groups),nominal_written_spans=music.written_spans(groups),
        tonal_evidence=music.tonal_evidence(groups),temporal_tonal_evidence=music.temporal_tonal_evidence(groups,body['measure_geometry']))
    music.validate(body)
    return body


def validate(shared,labels,capos=None):
    core=realize(shared,labels,capos)
    if lift(core,labels,capos,profile=shared.get('admission_profile',LEGACY_PROFILE))!=shared:raise ValueError('Noncanonical or missed declared-chord ownership')
    return core
