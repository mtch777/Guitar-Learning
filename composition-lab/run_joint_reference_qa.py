"""Frozen source test of conditional scale/chord relationships; no true-key claim."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
from musical_tier2 import analyze, strip_lower, harmonic_span_evidence, joint_reference_harmonic_context
from qa_isolation_harness import execute


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def study(upper, tolerance, max_edges):
    import math
    from fractions import Fraction as F
    scope = next(s for s in upper['tonal_evidence']['scopes'] if s['id'] == 'song-pooled')
    pool = [c for c in scope['candidates'] if c['family'] == 'KrumhanslSchmuckler' and c['score'] is not None and math.isfinite(c['score'])]
    maximum = max((c['score'] for c in pool), default=None)
    winners = [c for c in pool if maximum-c['score'] <= tolerance]
    candidate = winners[0]['id'] if len(winners) == 1 else None
    index = {m['id']: (g, m) for g in upper['coattacks'] for m in g['members']}
    rows = []
    for part in range(upper['source_quality']['tracks']):
        voices = sorted({m['voice'] for g, m in index.values() if g['part_id'] == part})
        for voice in voices or [None]:
            refs = sorted((i for i, (g, m) in index.items() if g['part_id'] == part and m['voice'] == voice), key=lambda i: tuple(index[i][1][k] for k in ('bar', 'beat', 'note')))
            chosen = refs[:3]
            positives = [i for i in chosen if F(index[i][1]['duration_q']) > 0]
            queries = [dict(occurrence_ref=i, at_q=str(F(index[i][0]['onset_q'])+F(index[i][1]['duration_q'])/2)) for i in positives]
            row = dict(part_id=part, voice=voice, owned_occurrences=len(refs), occurrence_refs=chosen, unqueryable_zero_duration=[i for i in chosen if i not in positives], queries=queries, harmonic=None, context=None)
            if not chosen:
                row['status'] = 'NO_OWNED_NOTE_OCCURRENCES_IN_PART'
            elif not queries:
                row['status'] = 'NO_POSITIVE_DURATION_QUERY'
            elif candidate is None:
                row['status'] = 'NO_UNIQUE_MODEL_QUERY_REFERENCE'
            else:
                start = min(F(index[i][0]['onset_q']) for i in positives)
                end = max(F(index[i][0]['onset_q'])+F(index[i][1]['duration_q']) for i in positives)
                row['harmonic'] = harmonic_span_evidence(upper, str(start), str(end), max_edges=max_edges)
                row['context'] = joint_reference_harmonic_context(upper, row['harmonic'], queries, candidate)
                row['status'] = row['context']['status']
            rows.append(row)
    return dict(candidate_ref=candidate, tied_maxima=[dict(candidate_ref=c['id'], score=c['score']) for c in winners], tolerance=tolerance, max_edges=max_edges, rows=rows, claim='Explicit model query reference only; no established key, mode, function or listening claim')


def source_check(capture, upper, result):
    from check_reversible_source import source_expectation
    from check_collection_degrees import native_reference
    from check_harmonic_span_source import check
    raw, _ = source_expectation(capture)
    population = [(int(i.split(':')[2]), int(i.split(':')[3]), n['pitch'], n['onset_q'], n['duration_q']) for i, n in raw.items()]
    errors, oracles, expected = [], [], []
    for part in range(upper['source_quality']['tracks']):
        voices = sorted({int(i.split(':')[4]) for i in raw if int(i.split(':')[2]) == part})
        for voice in voices or [None]:
            refs = [i for i in raw if int(i.split(':')[2]) == part and int(i.split(':')[4]) == voice]
            expected.append((part, voice, len(refs), refs[:3]))
    if [(r['part_id'], r['voice'], r['owned_occurrences'], r['occurrence_refs']) for r in result['rows']] != expected:
        errors.append('Raw all-part/owned-voice first-three denominator differs')
    pool = next(s['candidates'] for s in upper['tonal_evidence']['scopes'] if s['id'] == 'song-pooled')
    finite = [c for c in pool if c['family'] == 'KrumhanslSchmuckler' and c['score'] is not None and __import__('math').isfinite(c['score'])]
    top = max((c['score'] for c in finite), default=None)
    ties = [c for c in finite if abs(c['score']-top) <= result['tolerance']]
    if result['tied_maxima'] != [dict(candidate_ref=c['id'], score=c['score']) for c in ties] or result['candidate_ref'] != (ties[0]['id'] if len(ties) == 1 else None):
        errors.append('Reference selection differs')
    candidate = ties[0] if len(ties) == 1 else None
    degrees = native_reference(candidate['tonic_pc'], candidate['quality'])[0] if candidate else None
    for row in result['rows']:
        selected = row['occurrence_refs']
        positives = [i for i in selected if F(raw[i]['duration_q']) > 0]
        queries = [dict(occurrence_ref=i, at_q=str(F(raw[i]['onset_q'])+F(raw[i]['duration_q'])/2)) for i in positives]
        if row['queries'] != queries or row['unqueryable_zero_duration'] != [i for i in selected if i not in positives]:
            errors.append('Raw query clock or unqueryable population differs')
        context, harmonic = row['context'], row['harmonic']
        if not queries or candidate is None:
            expected_status = 'NO_OWNED_NOTE_OCCURRENCES_IN_PART' if not selected else 'NO_POSITIVE_DURATION_QUERY' if not queries else 'NO_UNIQUE_MODEL_QUERY_REFERENCE'
            if context is not None or harmonic is not None or row['status'] != expected_status:
                errors.append('Unqueryable case replaced or interpreted')
            continue
        request = dict(start_q=str(min(F(raw[i]['onset_q']) for i in positives)), end_q=str(max(F(raw[i]['onset_q'])+F(raw[i]['duration_q']) for i in positives)), part_id=None, max_edges=result['max_edges'])
        if harmonic['request'] != request:
            errors.append('Raw full query extent or frozen cap differs')
        digest = hashlib.sha256(json.dumps(harmonic, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        if context['harmonic_evidence_ref']['sha256'] != digest or context['harmonic_evidence_ref']['request'] != request:
            errors.append('Stored complete harmonic package reference differs')
        if context['reference']['candidate_ref'] != candidate['id'] or len(context['queries']) != len(queries):
            errors.append('Reference or query population differs')
        scored = harmonic['status'] == 'SCORED_NOT_MUSICAL_TRUTH'
        if harmonic['status'] in ('SCORED_NOT_MUSICAL_TRUTH', 'NOT_RUN_RESOURCE_LIMIT'):
            oracles.append(check(population, harmonic, context['joint_membership'], raw))
        elif harmonic['status'] != 'NOT_RUN_SOURCE_TIMING_UNCERTAIN':
            errors.append('Unexplained non-run outcome')
        if row['status'] != ('CONDITIONAL_JOINT_CONTEXT' if scored else 'HARMONIC_ANALYSIS_NOT_RUN'):
            errors.append('Query status differs')
        for query, note in zip(queries, context['queries']):
            p = raw[query['occurrence_ref']]['pitch']; pitch = None if p is None else F(p)
            degree = degrees[int(pitch) % 12] if pitch is not None and pitch.denominator == 1 else None
            state = 'unknown' if pitch is None or pitch.denominator != 1 else 'in_reference_collection' if degree is not None else 'outside_reference_collection'
            coordinate = note['reference_coordinates']
            if note['occurrence_ref'] != query['occurrence_ref'] or note['at_q'] != query['at_q'] or note['reference_membership'] != state:
                errors.append('Native/raw reference state differs')
            if pitch is None:
                if coordinate is not None: errors.append('Unknown gained coordinates')
            elif coordinate is None or coordinate['reference_collection_degree'] != degree or coordinate['relative_octaves'] != int((pitch-candidate['tonic_pc'])//12):
                errors.append('Native degree or source register differs')
            marginal = note['marginal_harmonic_context']
            if scored:
                cell = next(c for c in harmonic['all_optimal_path_cell_consensus'] if F(c['start_q']) <= F(query['at_q']) < F(c['end_q']))
                labels = [dict(c, note_membership='unknown' if pitch is None or pitch.denominator != 1 else 'chord_member' if int(pitch-c['root_pc']) % 12 in c['formula'] else 'nonmember') for c in cell['candidate_labels']]
                if marginal['labels'] != labels or marginal['cell_span_q'] != [cell['start_q'], cell['end_q']] or marginal['no_pitched_evidence_possibility'] != cell['no_pitched_evidence_possibility']:
                    errors.append('Complete marginal source membership differs')
            elif marginal is not None: errors.append('Non-run invented marginal')
        combined = [] if not scored else [[dict(occurrence_ref=q['occurrence_ref'], at_q=q['at_q'], reference_membership=q['reference_membership'], chord_membership=v) for q, v in zip(context['queries'], vector['memberships'])] for vector in context['joint_membership']['feasible_membership_vectors']]
        if context['combined_membership_vectors'] != combined or any(context[k] is not None for k in ('established_key', 'established_mode', 'harmonic_function', 'chord_mode')):
            errors.append('Joint vector changed or unsupported interpretation asserted')
    return dict(status='PASS' if not errors and all(o['status'] == 'PASS' for o in oracles) else 'FAIL', errors=errors, harmonic_source_oracles=oracles, scope='Raw denominator/clocks + native explicit-reference degrees + independent complete harmonic DAG and feasible vectors; not key accuracy')


def run(fresh, output):
    from source_tie_tier1 import extract
    from check_reversible_source import check, check_tie_relations
    from check_tonal_profiles import check as tonal_check
    from run_written_tie_context_qa import raw_declarations, exact_fields
    from three_gate_qa import portability
    import check_collection_degrees, check_harmonic_span_source
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root/'songsterr_automation/songsterr_api'))
    importlib.import_module('source_semantics'); importlib.import_module('analyze_relationships')
    import music21.scale, music21.pitch
    capture, selection, plan_path = fresh/'capture', fresh/'selection.json', fresh/'jointreference-plan.json'
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    if sha(selection) != plan['selection_sha256']: raise ValueError('Frozen selection changed')
    output.mkdir(parents=True, exist_ok=False)
    modules = sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None) and Path(m.__file__).suffix == '.py' and root in Path(m.__file__).resolve().parents and 'local-artifacts' not in Path(m.__file__).parts} | {Path(__file__).resolve()})
    frozen = {str(p): sha(p) for p in modules+[selection, plan_path]+list(capture.glob('*.json'))}
    write(output/'freeze.json', frozen)
    for p in modules:
        target = output/'frozen-code'/p.relative_to(root); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(p.read_bytes())
    lower = extract(capture); upper = analyze(lower)
    result = study(strip_lower(upper), plan['ks_tie_tolerance'], plan['max_edges']); write(output/'study.json', result)
    source = source_check(capture, upper, result)
    raw = check(capture, [{k: e[k] for k in ('id', 'pitch', 'onset_q', 'duration_q')} for e in lower['events']])
    tonal = tonal_check(capture, upper)
    ties = check_tie_relations(capture, upper['written_ties']['links'], upper['written_ties']['unresolved'])
    declarations = exact_fields(raw_declarations(capture), lower['tie_notation'])
    code = (root/'musical_tier2.py').read_text(encoding='utf-8')
    wrapper = '\n'+inspect.getsource(study)+'''
_exact_reconstruct=reconstruct
def reconstruct(package,controls):
    if set(package)!={'upper','tolerance','max_edges'}:raise ValueError('Declared source-independent query metadata only')
    return dict(tier1=_exact_reconstruct(package['upper'],controls),study=study(package['upper'],package['tolerance'],package['max_edges']))
'''
    isolated = execute(code+wrapper, dict(upper=strip_lower(upper), tolerance=plan['ks_tie_tolerance'], max_edges=plan['max_edges']), dict(variation=0), dict(tier1=lower, study=result), output/'isolated', timeout=240)
    unchanged = all(sha(Path(p)) == digest for p, digest in frozen.items())
    verdict = unchanged and declarations and raw['status'] == 'pass_declared_raw_source_fields' and ties['status'] == 'pass_declared_written_tie_relations' and all(r['status'] == 'PASS' for r in (source, tonal, isolated))
    selected = portability(capture, selection); verdict = verdict and selected['status'] == 'PASS'
    report = dict(technical_status='PASS' if verdict else 'FAIL', code_and_source_unchanged=unchanged, fresh_selection=selected, raw_source=raw, source_ties=ties, exact_declarations=declarations, source_context=source, tonal_source=tonal, isolated_same_relations=isolated, candidate_ref=result['candidate_ref'], outcomes=[dict(part_id=r['part_id'], voice=r['voice'], status=r['status']) for r in result['rows']], musical_acceptance='PENDING_PLANNER; conditional collection/chord meaning only, no established key/mode/function or listening claim')
    write(output/'result.json', report); print(json.dumps(report, indent=2)); return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('fresh',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    raise SystemExit(0 if run(args.fresh,args.output)['technical_status']=='PASS' else 1)
