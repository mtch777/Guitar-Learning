"""Complete bounded written-note roles on the existing optimal harmonic DAG.

All roles are template conditioned. No preferred key, function, emotion or
authored spelling is inferred, and no source notes are repaired from labels.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import json
import musical_tier2 as music
from chord_degree_relations import note_role
from contextual_chord_motion import observed_sonority,compare_sonority,reference_coordinate
from contextual_note_roles import source_refusals,partial_path_possibilities,role_predicate

VERSION='conditional-passage-note-roles/1'
MAX_OCCURRENCES=128
MAX_ASSIGNMENTS=100000


def interval_theory_compatibility(edge,selected,domains,budget,reference=None):
    """Unscored PC-superset definitions over an ALREADY selected graph edge."""
    observed={i for i,n in enumerate(edge['pitch_class_note_cell_weights']) if n}
    result=dict(scope='Written PCs across this existing scored interval, NOT simultaneous overlap or a chord prediction',
                observed_pitch_classes=sorted(observed),partial_evidence=edge['partial_known_pitch_evidence'],
                exact_templates=[],incomplete_compatible_templates=[],physical_technique_classification=None)
    if len(observed)<2:return dict(result,status='INSUFFICIENT_DISTINCT_PC_EVIDENCE'),0
    refs=[e for e in selected if domains[e['id']]!='explicit_nonpitched' and F(e['duration_q'])>0 and F(e['onset_q'])<F(edge['end_q']) and F(e['onset_q'])+F(e['duration_q'])>F(edge['start_q'])]
    used=0
    for kind,formula in music.THEORY_FORMS:
        for root in range(12):
            template={(root+i)%12 for i in formula}
            if not observed<=template:continue
            used+=len(refs)
            if used>budget:return None,used
            label=dict(root_pc=root,kind=kind,formula=list(formula));missing=sorted(template-observed)
            row=dict(
                label=label,root_observed_in_interval=root in observed,unobserved_template_pitch_classes=missing,
                known_note_roles=[dict(occurrence_ref=e['id'],role=note_role(e['pitch'] if domains[e['id']]=='pitched' else None,label)) for e in refs])
            if reference is not None:
                in_collection=lambda pc:(pc-reference['tonic_pc'])%12 in reference['reference_intervals']
                row['conditional_reference_comparison']=dict(reference_candidate_ref=reference['id'],root_coordinate=reference_coordinate(reference,str(root)),
                    template_pitch_classes_outside_reference=sorted(pc for pc in template if not in_collection(pc)),
                    unobserved_pitch_classes_in_reference=[pc for pc in missing if in_collection(pc)],
                    unobserved_pitch_classes_outside_reference=[pc for pc in missing if not in_collection(pc)])
            result['exact_templates' if not missing else 'incomplete_compatible_templates'].append(row)
    return dict(result,status='UNSCORED_THEORY_COMPATIBILITY',meaning='Missing tones distinguish unresolved interpretations; no notes added and no ranking, probability or cross-edge coherence inferred'),used


def optimal_edges(evidence,events,domains):
    points=list(map(F,evidence['partition_points_q']));reachable={len(points)-1};pending=list(reachable)
    while pending:
        for i in evidence['optimal_predecessors'][pending.pop()]:
            if i not in reachable:reachable.add(i);pending.append(i)
    prefix=[[0]*12]
    for cell in evidence['minimal_cells']:
        counts=[0]*12
        for ref in cell['occurrence_refs']:counts[int(F(events[ref]['pitch'])%12)]+=1
        prefix.append([a+b for a,b in zip(prefix[-1],counts)])
    edges=[]
    for stop in sorted(reachable-{0}):
        for begin in evidence['optimal_predecessors'][stop]:
            weights=[b-a for a,b in zip(prefix[begin],prefix[stop])]
            scores=music.harmonic_template_scores(weights) if any(weights) else []
            best=max((r['score'] for r in scores),default=0)
            labels=[{k:r[k] for k in ('root_pc','kind','formula')} for r in scores if r['score']==best] or [None]
            unknown=[r['occurrence_ref'] for r in evidence['unknown_pitch_overlays'] if F(r['start_q'])<points[stop] and F(r['end_q'])>points[begin]]
            unknown_domain=sorted({ref for c in evidence['minimal_cells'][begin:stop] for ref in c['occurrence_refs'] if domains[ref]=='unknown'})
            edges.append(dict(id=f'edge:{begin}:{stop}',begin=begin,stop=stop,start_q=str(points[begin]),end_q=str(points[stop]),
                              labels=labels,pitch_class_note_cell_weights=weights,unknown_pitch_overlay_refs=unknown,
                              unknown_instrument_domain_refs=unknown_domain,partial_known_pitch_evidence=bool(unknown or unknown_domain)))
    return edges


def feasible_held_pairs(edges,boundary_index):
    """Adjacent minimal cells: one spanning edge OR two edges sharing boundary."""
    candidates=[]
    for edge in edges:
        if edge['begin']<boundary_index<edge['stop']:
            candidates.extend((label,label,[edge['id']]) for label in edge['labels'])
    before=[e for e in edges if e['stop']==boundary_index];after=[e for e in edges if e['begin']==boundary_index]
    for left in before:
        for right in after:
            candidates.extend((a,b,[left['id'],right['id']]) for a in left['labels'] for b in right['labels'])
    unique={}
    index={e['id']:e for e in edges}
    for a,b,witness in candidates:
        key=json.dumps([a,b],sort_keys=True,separators=(',',':'))
        partial=any(index[ref]['partial_known_pitch_evidence'] for ref in witness)
        if key not in unique:unique[key]=dict(labels=[a,b],one_feasible_edge_witness=witness,any_feasible_witness_has_partial_evidence=partial)
        else:unique[key]['any_feasible_witness_has_partial_evidence']|=partial
    return [unique[k] for k in sorted(unique)]


def signature(role):
    if role['status'] not in ('TEMPLATE_CHORD_TONE','TEMPLATE_NONMEMBER'):return None
    return role['status'],tuple((d['degree'],d['alteration']) for d in role['degree_relationships'])


def evaluate_query(upper,documents,events,request):
    if type(request) is not dict or set(request)!={'version','harmonic_request','reference_candidate_ref'} or request['version']!=VERSION:raise ValueError('Typed complete-passage role request required')
    harmonic=request['harmonic_request']
    if type(harmonic) is not dict or set(harmonic)!={'start_q','end_q','part_id'}:raise ValueError('Exact passage time/part scope required')
    start=music.fraction(harmonic['start_q']);end=music.fraction(harmonic['end_q'])
    if not 0<end-start<=12:raise ValueError('Passage must fit twelve quarter notes')
    if harmonic['part_id'] is not None and harmonic['part_id'] not in {e['part_id'] for e in events.values()}:raise ValueError('Unknown passage part')
    domains={r['occurrence_ref']:r['domain'] for r in music.occurrence_pitch_domains(upper)}
    reference=request['reference_candidate_ref'];reference_definition=None;reference_context=None
    if reference is not None:
        found=[(s,c) for s in upper['tonal_evidence']['scopes'] for c in s['candidates'] if c['id']==reference]
        allowed={'song-pooled'}|({f"part:{harmonic['part_id']}"} if harmonic['part_id'] is not None else set())
        if type(reference) is not str or len(found)!=1 or found[0][0]['id'] not in allowed:raise ValueError('One explicit in-scope reference candidate required')
        scope,reference_definition=found[0]
        collection={(reference_definition['tonic_pc']+i)%12 for i in reference_definition['reference_intervals']}
        equivalents=[dict(candidate_ref=c['id'],tonic_pc=c['tonic_pc'],reference_collection=c['reference_collection']) for c in scope['candidates'] if {(c['tonic_pc']+i)%12 for i in c['reference_intervals']}==collection]
        reference_context=dict(candidate_ref=reference,tonic_pc=reference_definition['tonic_pc'],reference_collection=reference_definition['reference_collection'],
                               reference_intervals=reference_definition['reference_intervals'],score=reference_definition['score'],score_type=reference_definition['score_type'],
                               collection_equivalent_candidates=equivalents,
                               status='EXPLICIT_PROVISIONAL_REFERENCE_NOT_ESTABLISHED_KEY_OR_MODE',
                               limitation='Collection equivalence does not establish center; existing candidates do not exhaust all modal centers')
    selected=[e for e in events.values() if (harmonic['part_id'] is None or e['part_id']==harmonic['part_id']) and (start<=F(e['onset_q'])<end if F(e['duration_q'])==0 else F(e['onset_q'])<end and F(e['onset_q'])+F(e['duration_q'])>start)]
    selected.sort(key=lambda e:(e['part_id'],e['bar'],e['voice'],e['beat'],e['note']))
    inventory=[dict(occurrence_ref=e['id'],domain=domains[e['id']],source_expression_declarations=source_refusals(documents,events,[e['id']]),
                    status='EXCLUDED_EXPLICIT_NONPITCHED' if domains[e['id']]=='explicit_nonpitched' else 'ZERO_DURATION_WRITTEN_OCCURRENCE' if F(e['duration_q'])==0 else 'UNKNOWN_PITCHED_DOMAIN' if domains[e['id']]=='unknown' else 'UNKNOWN_WRITTEN_PITCH' if e['pitch'] is None or F(e['pitch']).denominator!=1 else 'KNOWN_WRITTEN_BASE_PITCH') for e in selected]
    for row,e in zip(inventory,selected):row['conditional_reference_coordinate']=None if reference_definition is None or domains[e['id']]!='pitched' else reference_coordinate(reference_definition,e['pitch'])
    result=dict(request=deepcopy(request),occurrence_inventory=inventory,provisional_reference=reference_context,
                limitations=['Template definitions are not authored spelling or harmonic function','Written base pitch/nominal overlap, not acoustic execution','Graph edge/label dependence retained; no independent marginal combinations','Reference collection is explicit and provisional; no established key or mode'])
    if len(selected)>MAX_OCCURRENCES:return dict(result,status='NOT_RUN_OCCURRENCE_RESOURCE_LIMIT',required_occurrences=len(selected)),None
    evidence=music.harmonic_span_evidence(upper,**harmonic,max_edges=2048)
    if evidence['status']!='SCORED_NOT_MUSICAL_TRUTH':return dict(result,status='HARMONIC_RESOURCE_OR_EVIDENCE_UNAVAILABLE'),evidence
    edges=optimal_edges(evidence,events,domains);points=list(map(F,evidence['partition_points_q']));assignments=[];snapshots={};count=0
    for edge in edges:
        for label_index,label in enumerate(edge['labels']):
            notes=[]
            for e in selected:
                if domains[e['id']]=='explicit_nonpitched':continue
                a=max(F(e['onset_q']),F(edge['start_q']));b=min(F(e['onset_q'])+F(e['duration_q']),F(edge['end_q']))
                if not a<b:continue
                count+=1
                if count>MAX_ASSIGNMENTS:return dict(result,status='NOT_RUN_ROLE_RESOURCE_LIMIT',role_limit=MAX_ASSIGNMENTS),evidence
                clock=str(a)
                if clock not in snapshots:snapshots[clock]=observed_sonority(upper,clock,harmonic['part_id'])
                role=note_role(e['pitch'] if domains[e['id']]=='pitched' else None,label)
                notes.append(dict(occurrence_ref=e['id'],span_q=[str(a),str(b)],role=role,observed_sonority_ref=clock,
                                  template_against_observation=None if label is None else compare_sonority(snapshots[clock],label)))
            assignments.append(dict(edge_ref=edge['id'],label_index=label_index,notes=notes,supporting_edge_partial_known_pitch_evidence=edge['partial_known_pitch_evidence']))
    for edge in edges:
        compatibility,used=interval_theory_compatibility(edge,selected,domains,MAX_ASSIGNMENTS-count,reference_definition)
        count+=used
        if compatibility is None:return dict(result,status='NOT_RUN_ROLE_RESOURCE_LIMIT',role_limit=MAX_ASSIGNMENTS),evidence
        edge['unscored_theory_compatibility']=compatibility
    changes=[]
    for i,t in enumerate(points[1:-1],1):
        pairs=feasible_held_pairs(edges,i)
        for e in selected:
            if domains[e['id']]!='pitched' or not F(e['onset_q'])<t<F(e['onset_q'])+F(e['duration_q']):continue
            alternatives=[]
            for pair in pairs:
                roles=[note_role(e['pitch'],label) for label in pair['labels']];keys=[signature(r) for r in roles]
                alternatives.append(dict(**pair,roles=roles,role_changed=None if None in keys else keys[0]!=keys[1]))
            count+=len(alternatives)
            if count>MAX_ASSIGNMENTS:return dict(result,status='NOT_RUN_ROLE_RESOURCE_LIMIT',role_limit=MAX_ASSIGNMENTS),evidence
            changes.append(dict(occurrence_ref=e['id'],boundary_q=str(t),alternatives=alternatives,
                                dependence='Same edge must use same label; adjacent retained optimal edges may choose their own labels'))
    patterns=[];lanes=defaultdict(list)
    for e in selected:lanes[e['part_id'],e['voice']].append(e)
    for lane in sorted(lanes):
        ordered=lanes[lane]
        for triple in zip(ordered,ordered[1:],ordered[2:]):
            refs=[e['id'] for e in triple];reasons=source_refusals(documents,events,refs)
            if any(domains[r]!='pitched' for r in refs):reasons.append('not_all_declared_pitched_occurrences')
            if any(not start<=F(e['onset_q'])<end for e in triple):reasons.append('source_onset_outside_passage')
            if reference is None:
                patterns.append(dict(occurrence_refs=refs,status='NOT_EVALUATED_NO_REFERENCE',source_refusals=reasons));continue
            motion=music.collection_motion_context(upper,refs,reference)
            motion['source_motion']['attack_and_tie_status']='Complete source tie/expression declarations checked by passage wrapper; no acoustic attack claim'
            reasons+=motion['source_motion']['refusal_reasons'];alternatives=[]
            if not reasons:
                queries=[dict(occurrence_ref=r,at_q=events[r]['onset_q']) for r in refs]
                joint=music.joint_reference_harmonic_context(upper,evidence,queries,reference)
                partial=any(partial_path_possibilities(evidence,queries))
                for vector in joint['joint_membership']['feasible_membership_vectors']:
                    roles=role_predicate(motion['source_motion']['motion']['shape'] if motion['source_motion']['motion'] else None,
                                         [p['adjacent_degree_movement'] for p in motion['pairs']],vector['memberships'],eligible=True,partial=partial)
                    alternatives.append(dict(**vector,conditional_roles=roles,partial_pitch_evidence=partial))
            patterns.append(dict(occurrence_refs=refs,status='SOURCE_SEQUENCE_REFUSED' if reasons else 'CONDITIONAL_PATTERN_EVIDENCE',
                                 source_refusals=list(dict.fromkeys(reasons)),reference_motion=motion,alternatives=alternatives))
    return dict(result,status='COMPLETE_CONDITIONAL_PASSAGE_ROLES',optimal_edges=edges,edge_label_role_assignments=assignments,
                observed_sonorities=snapshots,held_note_role_changes=changes,passing_neighbor_analysis=patterns),evidence
