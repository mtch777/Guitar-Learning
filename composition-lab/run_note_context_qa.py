"""Frozen-source conditional note-context QA; no annotated note-role claim."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import importlib
import json
from pathlib import Path
import sys

from musical_tier2 import analyze, strip_lower, harmonic_span_evidence, note_motion_evidence, harmonic_membership_evidence
from qa_isolation_harness import execute


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def study(upper, request, sequences):
    harmonic = harmonic_span_evidence(upper, **request)
    index = {m['id']: (g, m) for g in upper['coattacks'] for m in g['members']}
    rows = []
    for sequence in sequences:
        refs = sequence['first_three_refs']
        row = dict(sequence=sequence)
        if len(refs) != 3:
            row.update(status='FEWER_THAN_THREE_RETAINED', motion=None, membership=None)
        else:
            motion = note_motion_evidence(upper, refs)
            row['motion'] = motion
            # Membership is a note/time relationship, not a melodic-line claim.
            # Keep the exact frozen triple; retain grace as unqueryable, never
            # replace it with a later occurrence to manufacture coverage.
            queries=[]; unqueryable=[]
            for ident in refs:
                group,member=index[ident]
                if F(member['duration_q'])>0:queries.append(dict(occurrence_ref=ident,at_q=group['onset_q']))
                else:unqueryable.append(dict(occurrence_ref=ident,reason='zero_duration_has_no_half_open_interior'))
            row['unqueryable_memberships']=unqueryable
            row['membership']=harmonic_membership_evidence(upper,harmonic,queries) if queries and harmonic['status']=='SCORED_NOT_MUSICAL_TRUTH' else None
            if motion['eligibility'] != 'eligible_owned_written_sequence':
                row.update(status='MELODIC_INTERPRETATION_REFUSED')
            elif harmonic['status'] != 'SCORED_NOT_MUSICAL_TRUTH':
                row.update(status='HARMONIC_ANALYSIS_NOT_RUN')
            else:
                row.update(status='CONDITIONAL_MEMBERSHIP_ONLY')
        rows.append(row)
    return dict(harmonic=harmonic, sequences=rows)


def independent_queries(raw, sequences, result):
    """Raw-source arithmetic, no calls to musical analysis or inverse helpers.

    Checks every motion coordinate and every returned joint-label witness.
    Exhaustive completeness is separately checked on small analytical cases.
    """
    errors = []; vectors = 0; labels_checked = 0
    points = list(map(F, result['harmonic'].get('partition_points_q', [])))
    reachable={len(points)-1};pending=list(reachable)
    while pending:
        stop=pending.pop()
        for begin in result['harmonic'].get('optimal_predecessors',[[]])[stop]:
            if begin not in reachable:reachable.add(begin);pending.append(begin)
    forms = {'major': (0, 4, 7), 'dominant-seventh': (0, 4, 7, 10), 'minor': (0, 3, 7),
             'diminished-seventh': (0, 3, 6, 9), 'half-diminished-seventh': (0, 3, 6, 10), 'diminished': (0, 3, 6)}
    for sequence, row in zip(sequences, result['sequences']):
        refs = sequence['first_three_refs']
        if row['sequence'] != sequence: errors.append('Changed frozen sequence')
        if len(refs) != 3:
            if row['status'] != 'FEWER_THAN_THREE_RETAINED': errors.append('Lost short sequence')
            continue
        notes = [raw[i] for i in refs]; motion = row['motion']
        clocks = [dict(occurrence_ref=i, onset_q=n['onset_q'], duration_q=n['duration_q']) for i, n in zip(refs, notes)]
        gaps = [str(F(notes[j+1]['onset_q'])-F(notes[j]['onset_q'])-F(notes[j]['duration_q'])) for j in (0, 1)]
        if motion['clocks'] != clocks or motion['gaps_q'] != gaps: errors.append('Source motion clocks differ')
        pitches = [None if n['pitch'] is None else F(n['pitch']) for n in notes]
        if all(p is not None for p in pitches):
            a, b = pitches[1]-pitches[0], pitches[2]-pitches[1]
            shape = 'strictly_monotonic' if a*b>0 else 'departure_and_return' if a!=0 and pitches[0]==pitches[2] else 'contains_repetition' if a==0 or b==0 else 'direction_change_without_register_return'
            expected = dict(approach_semitones=str(a), departure_semitones=str(b), register_return=pitches[0]==pitches[2], shape=shape, diatonic_step=None)
            if motion['motion'] != expected: errors.append('Source pitch motion differs')
        elif motion['motion'] is not None: errors.append('Unknown pitch received motion')
        # Re-derive same-voice simultaneity/overlap directly from raw IDs.
        part, voice = sequence['part_id'], sequence['voice']
        owned = [i for i in raw if int(i.split(':')[2])==part and int(i.split(':')[4])==voice]
        start = owned.index(refs[0]); reasons = []
        if owned[start:start+3] != refs: reasons.append('not_consecutive_owned_occurrences')
        if any(sum(raw[i]['onset_q']==n['onset_q'] for i in owned)!=1 for n in notes): reasons.append('ambiguous_same_voice_simultaneity')
        if any(F(n['duration_q'])==0 for n in notes): reasons.append('zero_duration_or_grace_occurrence')
        if any(p is None for p in pitches): reasons.append('unknown_pitch_occurrence')
        left=min(F(n['onset_q']) for n in notes); right=max(F(n['onset_q'])+F(n['duration_q']) for n in notes)
        if any(i not in refs and F(raw[i]['onset_q'])<right and F(raw[i]['onset_q'])+F(raw[i]['duration_q'])>left for i in owned): reasons.append('ambiguous_same_voice_overlap')
        if any(F(g)!=0 for g in gaps): reasons.append('noncontiguous_written_intervals')
        actual_reasons = set(motion['refusal_reasons'])-{'source_timing_uncertain'}
        if actual_reasons != set(reasons): errors.append('Source melodic refusal differs')
        if any(motion[k] is not None for k in ('passing_tone','neighbor_tone')): errors.append('Unsupported function claim')
        membership = row['membership']
        expected_queries=[dict(occurrence_ref=i,at_q=n['onset_q']) for i,n in zip(refs,notes) if F(n['duration_q'])>0]
        expected_unqueryable=[dict(occurrence_ref=i,reason='zero_duration_has_no_half_open_interior') for i,n in zip(refs,notes) if F(n['duration_q'])==0]
        if row['unqueryable_memberships']!=expected_unqueryable:errors.append('Grace query exclusion changed')
        if membership is not None and membership['queries']!=expected_queries:errors.append('Frozen queried occurrences replaced')
        if expected_queries and result['harmonic']['status']=='SCORED_NOT_MUSICAL_TRUTH' and membership is None:errors.append('Eligible membership query omitted')
        if membership is None: continue
        alternatives=membership['feasible_membership_vectors']
        signatures=[tuple(v['memberships']) for v in alternatives]
        if not alternatives or len(signatures)!=len(set(signatures)):errors.append('Empty or duplicate membership inventory')
        if any(len(v)!=len(expected_queries) for v in signatures):errors.append('Wrong membership vector length')
        for vector in membership['feasible_membership_vectors']:
            vectors += 1; witness = vector['one_valid_path_and_label_witness']; actual = []
            if not witness or witness[0]['begin']!=0 or witness[-1]['stop']!=len(points)-1 or any(a['stop']!=b['begin'] for a,b in zip(witness,witness[1:])): errors.append('Non-contiguous witness')
            for edge in witness:
                a, b = edge['begin'], edge['stop']; weights=[0]*12
                if not 0<=a<b<len(points) or b not in reachable or a not in result['harmonic']['optimal_predecessors'][b]:errors.append('Witness edge outside globally optimal boundary DAG')
                for note in raw.values():
                    p = None if note['pitch'] is None else F(note['pitch'])
                    if p is None or p.denominator!=1: continue
                    for at in points[a:b]:
                        if F(note['onset_q'])<=at<F(note['onset_q'])+F(note['duration_q']): weights[int(p)%12]+=1
                candidates=[]
                for root in range(12):
                    for kind, formula in forms.items():
                        pcs={(root+x)%12 for x in formula}
                        score=sum(w if pc in pcs else -w for pc,w in enumerate(weights))-sum(weights[pc]==0 for pc in pcs)
                        candidates.append((score,root,kind,list(formula)))
                label=edge['label']
                if not any(weights):
                    if label is not None: errors.append('No-evidence label invented')
                elif label is None or (max(x[0] for x in candidates),label['root_pc'],label['kind'],label['formula']) not in candidates: errors.append('Witness label not independently optimal')
                labels_checked+=1
            for query in membership['queries']:
                note=raw[query['occurrence_ref']]; at=F(query['at_q']); pitch=None if note['pitch'] is None else F(note['pitch'])
                if not F(note['onset_q'])<=at<F(note['onset_q'])+F(note['duration_q']): errors.append('Query outside source interval')
                edge=next(e for e in witness if points[e['begin']]<=at<points[e['stop']]); label=edge['label']
                actual.append('unknown' if pitch is None or pitch.denominator!=1 or label is None else 'chord_member' if (pitch-label['root_pc'])%12 in label['formula'] else 'nonmember')
            if actual != vector['memberships']: errors.append('Joint source membership differs')
    if len(result['sequences'])!=len(sequences): errors.append('Sequence denominator changed')
    return dict(status='PASS' if not errors else 'FAIL',sequences=len(sequences),vectors_checked=vectors,witness_edge_labels_checked=labels_checked,errors=errors,
                scope='Raw motion/refusals and all returned witnesses; exhaustive vector completeness separately tested on small cases')


def run(fresh, output):
    from source_key_tier1 import extract
    from check_reversible_source import source_expectation, check
    from check_harmonic_span_source import check as harmonic_check
    from three_gate_qa import portability
    root=Path(__file__).resolve().parent
    sys.path.insert(0,str(root/'songsterr_automation/songsterr_api'))
    importlib.import_module('source_semantics'); importlib.import_module('analyze_relationships')
    output.mkdir(parents=True,exist_ok=False)
    paths=[fresh/n for n in ('selection.json','notecontext-plan.json','denominator.json')]+list((fresh/'capture').glob('*.json'))
    modules=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).suffix=='.py' and root in Path(m.__file__).resolve().parents and 'local-artifacts' not in Path(m.__file__).parts}|{Path(__file__).resolve()})
    frozen={str(p):sha(p) for p in paths+modules};write(output/'freeze.json',frozen)
    for module in modules:
        target=output/'frozen-code'/module.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(module.read_bytes())
    plan=json.loads((fresh/'notecontext-plan.json').read_text(encoding='utf-8')); denominator=json.loads((fresh/'denominator.json').read_text(encoding='utf-8'))
    if plan['selection_sha256']!=sha(fresh/'selection.json') or denominator['source_plan_sha256']!=sha(fresh/'notecontext-plan.json'):raise ValueError('Frozen plan changed')
    sequences=denominator['sequences']; request=plan['harmonic_request'];capture=fresh/'capture'
    selection=portability(capture,fresh/'selection.json'); lower=extract(capture)
    source=check(capture,[{k:e[k] for k in ('id','pitch','onset_q','duration_q')} for e in lower['events']])
    raw,_=source_expectation(capture);topology=source_expectation(capture,include_topology=True)
    # Derive denominator again from ALL declared raw voices, including empty ones.
    keys=sorted({(int(v['id'].split(':')[2]),int(v['id'].split(':')[4])) for v in topology['voices']})
    expected=[]
    for part,voice in keys:
        refs=[i for i,n in raw.items() if int(i.split(':')[2])==part and int(i.split(':')[4])==voice and F(request['start_q'])<=F(n['onset_q'])<F(request['end_q'])]
        expected.append(dict(part_id=part,voice=voice,owned_occurrences_in_window=len(refs),first_three_refs=refs[:3],denominator_status='query_first_three_no_replacement' if len(refs)>=3 else 'fewer_than_three_retained'))
    if sequences!=expected:raise ValueError('Frozen source denominator differs; do not replace')
    upper=analyze(lower); result=study(upper,request,sequences);write(output/'study.json',result)
    harmonic_raw=[(int(i.split(':')[2]),int(i.split(':')[3]),n['pitch'],n['onset_q'],n['duration_q']) for i,n in raw.items()]
    oracle=harmonic_check(harmonic_raw,result['harmonic']);queries=independent_queries(raw,sequences,result)
    code=(root/'musical_tier2.py').read_text(encoding='utf-8')
    # SAME functions, numeric zero controls. Only the return envelope is adapted.
    function_source=__import__('inspect').getsource(study)
    wrapper='\n'+function_source+'''
_exact_reconstruct = reconstruct
def reconstruct(package, controls):
    if set(package)!={'upper','request','sequences'}:raise ValueError('Declared query metadata only')
    upper=package['upper']
    return dict(tier1=_exact_reconstruct(upper,controls),study=study(upper,package['request'],package['sequences']))
'''
    isolated=execute(code+wrapper,dict(upper=strip_lower(upper),request=request,sequences=sequences),dict(variation=0),dict(tier1=lower,study=result),output/'isolated',timeout=180)
    unchanged=all(sha(Path(p))==digest for p,digest in frozen.items())
    passed=unchanged and selection['status']=='PASS' and source['status']=='pass_declared_raw_source_fields' and all(x['status']=='PASS' for x in (oracle,queries,isolated))
    report=dict(technical_status='PASS' if passed else 'FAIL',code_and_source_unchanged=unchanged,fresh_selection=selection,source_oracle=source,harmonic_source_oracle=oracle,note_query_source_oracle=queries,isolated_same_relations=isolated,sequence_outcomes=dict(Counter(r['status'] for r in result['sequences'])),musical_acceptance='PENDING_PROJECTPLANNER_REVIEW; no annotated note-role accuracy or full GP claim')
    write(output/'result.json',report);print(json.dumps(report,indent=2));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('fresh',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    raise SystemExit(0 if run(args.fresh,args.output)['technical_status']=='PASS' else 1)
