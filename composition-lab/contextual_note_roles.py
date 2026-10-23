"""Conditional musical roles, checked against the SAME reconstructed source.

No file access, label-driven note repair, separate pitch owner or role-to-note
generator. A role is evidence under an explicit reference and feasible chord
path; it is never a claim about the composer's intention.
"""
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
from source_fact_tier1 import project_documents,validate
import musical_tier2 as music

VERSION='conditional-passing-neighbor/1'
PACKAGE_VERSION='conditional-musical-context/2'
QUERY_KINDS={VERSION:'passing_neighbor','conditional-chord-voice-motion/1':'chord_voice_motion'}
MAX_REQUESTS=32
MAX_WINDOW_Q=32


def partial_path_possibilities(evidence,queries):
    """Conservative possibility across ALL terminal-reachable optimal edges.

    A vector stores only one witness. Its clean witness cannot exclude another
    path with the same memberships and incomplete supporting pitch evidence.
    This union may over-refuse a vector; it never certifies it from one witness.
    """
    if evidence['status']!='SCORED_NOT_MUSICAL_TRUTH':return [True]*len(queries)
    points=list(map(F,evidence['partition_points_q']));reachable={len(points)-1};pending=list(reachable)
    while pending:
        for begin in evidence['optimal_predecessors'][pending.pop()]:
            if begin not in reachable:reachable.add(begin);pending.append(begin)
    result=[]
    for query in queries:
        at=F(query['at_q'])
        result.append(any(points[begin]<=at<points[stop] and any(F(o['start_q'])<points[stop] and F(o['end_q'])>points[begin] for o in evidence['unknown_pitch_overlays'])
                          for stop in reachable for begin in evidence['optimal_predecessors'][stop]))
    return result


def role_predicate(shape,adjacent,memberships,*,eligible=True,partial=False):
    """Definition shared by forward analysis and reverse validation."""
    if not eligible or partial or adjacent!=[True,True]:return []
    if memberships!=['chord_member','nonmember','chord_member']:return []
    return ['passing_like'] if shape=='strictly_monotonic' else ['neighbor_like'] if shape=='departure_and_return' else []


def source_refusals(documents,events,refs):
    """Actual declarations, not inferred picked attacks or sounding endpoints."""
    reasons=[]
    for ident in refs:
        event=events[ident];part=documents[f"track-{event['part_id']}.json"]
        beat=part['measures'][event['bar']-1]['voices'][event['voice']]['beats'][event['beat']]
        note=beat['notes'][event['note']]
        if 'tie' in note and note['tie'] is not False and note['tie'] is not None:reasons.append('written_tie_continuation_or_unsupported_tie')
        for field in ('bend','slide','harmonic','harmonicFret','vibrato','leftHandVibrato','wideVibrato','dead'):
            # A zero harmonic fret is still a declaration. Empty curves are
            # unsupported expression, not evidence of an ordinary picked note.
            if field in note and note[field] is not False and note[field] is not None:reasons.append('unresolved_sounding_pitch_'+field)
        for field in ('tremoloBar','vibrato','leftHandVibrato','wideVibrato','vibratoWithTremoloBar','harmonic'):
            if field in beat and beat[field] is not False and beat[field] is not None:reasons.append('unresolved_sounding_pitch_beat_'+field)
        if note.get('graceNote') or beat.get('graceNote'):reasons.append('source_grace_declaration')
    return list(dict.fromkeys(reasons))


def evaluate(tier1,requests):
    """Only complete preceding-tier input; no source/cache or expected results."""
    validate(tier1)
    if type(requests) is not list or not 1<=len(requests)<=MAX_REQUESTS:raise ValueError('One to32 explicit role requests required')
    from source_tie_tier1 import extract_documents
    documents=project_documents(tier1);observed=extract_documents(documents)
    upper=music.strip_lower(music.analyze(observed));events={e['id']:e for e in observed['events']}
    index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']}
    results=[];packages={}
    for request in requests:
        if type(request) is not dict or request.get('version') not in QUERY_KINDS:raise ValueError('Registered typed context request required')
        if QUERY_KINDS[request['version']]=='chord_voice_motion':
            from contextual_chord_motion import evaluate_query
            row,evidence=evaluate_query(upper,documents,events,request)
            digest=None if evidence is None else hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            if digest is not None:packages[digest]=evidence
            row['harmonic_evidence_ref']=digest;results.append(row);continue
        if type(request) is not dict or set(request)!={'version','occurrence_refs','candidate_ref','harmonic_request'} or request['version']!=VERSION:raise ValueError('Typed versioned role request required')
        refs=request['occurrence_refs'];harmonic=request['harmonic_request']
        if type(harmonic) is not dict or set(harmonic)!={'start_q','end_q','part_id'}:raise ValueError('Explicit harmonic time/part scope required')
        a=music.fraction(harmonic['start_q']);b=music.fraction(harmonic['end_q'])
        if not 0<b-a<=MAX_WINDOW_Q:raise ValueError('Role harmonic window outside declared bound')
        motion=music.collection_motion_context(upper,refs,request['candidate_ref'])
        reasons=source_refusals(documents,events,refs)+motion['source_motion']['refusal_reasons']
        queries=[dict(occurrence_ref=ref,at_q=index[ref][0]['onset_q']) for ref in refs]
        if any(not a<=F(q['at_q'])<b for q in queries):raise ValueError('Role occurrence outside harmonic request')
        # Refused topology has no defensible three-attack harmonic query (e.g.
        # zero-duration grace). Do not turn an invalid query into missing data.
        evidence=None if reasons else music.harmonic_span_evidence(upper,**harmonic,max_edges=2048)
        joint=None if reasons else music.joint_reference_harmonic_context(upper,evidence,queries,request['candidate_ref'])
        alternatives=[]
        if joint is not None and joint['joint_membership'] is not None:
            membership=joint['joint_membership']
            partial_possibilities=partial_path_possibilities(evidence,queries)
            for vector in membership['feasible_membership_vectors']:
                partial=any(partial_possibilities)
                roles=role_predicate(motion['source_motion']['motion']['shape'] if motion['source_motion']['motion'] else None,
                    [p['adjacent_degree_movement'] for p in motion['pairs']],vector['memberships'],eligible=not reasons,partial=partial)
                alternatives.append(dict(**deepcopy(vector),conditional_roles=roles,partial_pitch_evidence=partial,
                    all_optimal_path_partial_possibilities=partial_possibilities))
        qualifying=sum(bool(row['conditional_roles']) for row in alternatives)
        status='SOURCE_SEQUENCE_REFUSED' if reasons else 'HARMONIC_RESOURCE_OR_EVIDENCE_UNAVAILABLE' if not alternatives else 'CONDITIONAL_ROLE_ALL_MEMBERSHIP_VECTORS' if qualifying==len(alternatives) else 'CONDITIONAL_ROLE_SOME_MEMBERSHIP_VECTORS' if qualifying else 'NO_QUALIFYING_ROLE'
        digest=None if evidence is None else hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        if digest is not None:packages[digest]=evidence
        results.append(dict(request=deepcopy(request),status=status,source_refusals=list(dict.fromkeys(reasons)),
            reference_motion=motion,harmonic_evidence_ref=digest,joint_context=joint,alternatives=alternatives,
            meaning='Stepwise chord-member to nonmember to chord-member motion under explicit key-reference and jointly feasible chord paths',
            limitations=['Conditional evidence, not established key, mode, intended function or emotional meaning',
                        'Written base pitches and nominal note intervals, not acoustic sustain',
                        'Diatonic passing/neighbor only; chromatic ornaments and other roles remain unclassified']))
    return dict(version=PACKAGE_VERSION,pitch_domains=music.occurrence_pitch_domains(upper),harmonic_evidence=packages,results=results)


def attach(upper,requests):
    """Checked derived assertions; preserve a single existing pitch authority."""
    from connected_tier2 import strip_lower,realize
    if 'contextual_constraints' in upper:raise ValueError('Attach once; never silently replace assertions')
    source=realize(strip_lower(upper));result=deepcopy(upper)
    result['contextual_constraints']=evaluate(source,requests)
    return result


def verify(tier1,constraints):
    if type(constraints) is not dict or set(constraints)!={'version','pitch_domains','harmonic_evidence','results'} or constraints['version'] not in (VERSION,PACKAGE_VERSION):raise ValueError('Versioned contextual assertions required')
    expected=evaluate(tier1,[row['request'] for row in constraints['results']])
    # Preserve the existing role-only request/package decoder. Its stored
    # derived assertions are still checked, never used to repair source notes.
    if constraints['version']==VERSION:
        if any(r['request']['version']!=VERSION for r in constraints['results']):raise ValueError('Legacy package cannot contain new query kinds')
        expected['version']=VERSION
    if json.dumps(expected,sort_keys=True)!=json.dumps(constraints,sort_keys=True):raise ValueError('Stale or contradictory contextual relationship')
    return expected
