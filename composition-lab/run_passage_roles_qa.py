"""Frozen first-source-measure musical-role and complete-source inverse QA."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from source_fact_tier1 import extract,project_documents
from connected_tier2 import analyze,strip_lower
from contextual_note_roles import attach
from contextual_passage_roles import VERSION
from run_connected_tier2_qa import bundle
from qa_isolation_harness import execute
from check_complete_source_facts import check
from freeze_technique_baseline import retained
from technique_tier2 import comparable_to_baseline


def run(capture,output):
    output.mkdir(parents=True,exist_ok=False);root=Path(__file__).parent
    files=list(root.glob('*.py'))+list((root/'songsterr_automation/songsterr_api').glob('*.py'))+list(capture.glob('*.json'))
    frozen={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (output/'plan-before-analysis.json').write_text(json.dumps(dict(frozen=frozen,
        selection='FIRST original source measure in full, all tracks/voices/occurrences; no easier replacement',
        reference='Unique highest global Krumhansl candidate if available, explicitly uncalibrated; otherwise no reference and ornament evidence not evaluated',
        scope='Template-conditioned degree/hold/passing-neighbor evidence, not inferred key/function/emotion'),indent=2),encoding='utf-8')
    lower=extract(capture);documents=project_documents(lower);baseline=retained(documents)
    (output/'retained-before-context.json').write_text(json.dumps(baseline),encoding='utf-8')
    upper=analyze(lower)
    if upper['unsupported']:
        report=dict(status='FAIL_UNSUPPORTED_RETAINED',unsupported=upper['unsupported']);(output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
    music=upper['derived_views']['harmonic_context'];first=music['measure_geometry']['frames'][0]
    from fractions import Fraction as F
    candidates=[c for s in music['tonal_evidence']['scopes'] if s['id']=='song-pooled' for c in s['candidates'] if c['family']=='KrumhanslSchmuckler' and c['score'] is not None]
    maximum=max((c['score'] for c in candidates),default=None);winners=[c for c in candidates if maximum is not None and abs(c['score']-maximum)<=1e-12]
    request=dict(version=VERSION,harmonic_request=dict(start_q=first['start_q'],end_q=str(F(first['start_q'])+F(first['duration_q'])),part_id=None),
                 reference_candidate_ref=winners[0]['id'] if len(winners)==1 else None)
    (output/'request-before-context.json').write_text(json.dumps(request,indent=2),encoding='utf-8')
    upper=attach(upper,[request]);(output/'tier2.json').write_text(json.dumps(upper),encoding='utf-8')
    row=upper['contextual_constraints']['results'][0]
    code,hashes=bundle(root);worker=execute(code,strip_lower(upper),dict(variation=0),lower,output/'isolated',timeout=300)
    actual=json.loads((output/'isolated/worker/output.json').read_text(encoding='utf-8')) if worker['status']=='PASS' else None
    exact=check(capture,actual) if actual is not None else dict(status='FAIL_WORKER')
    parity=comparable_to_baseline(upper['derived_views']['techniques'],json.loads(json.dumps(baseline)))
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
    ok=worker['status']=='PASS' and exact['status']=='PASS_COMPLETE_CAPTURED_JSON_FACTS' and parity and unchanged and row['status']=='COMPLETE_CONDITIONAL_PASSAGE_ROLES'
    report=dict(status='PASS_BOUNDED_PASSAGE_SOURCE' if ok else 'FAIL_RETAINED',unchanged=unchanged,request=request,passage_status=row['status'],
                occurrence_inventory_counts=dict(Counter(r['status'] for r in row['occurrence_inventory'])),
                optimal_edges=len(row.get('optimal_edges',[])),edge_label_role_assignments=len(row.get('edge_label_role_assignments',[])),
                held_note_boundaries=len(row.get('held_note_role_changes',[])),
                ornament_status_counts=dict(Counter(r['status'] for r in row.get('passing_neighbor_analysis',[]))),
                exact=exact,worker=worker,retained_detector_parity=parity,module_hashes=hashes,
                gate3='PENDING_INDEPENDENT_SOURCE_MUSICAL_REVIEW',limitations=row['limitations'])
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('capture',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    result=run(args.capture,args.output);print(json.dumps(result));raise SystemExit(0 if result['status']=='PASS_BOUNDED_PASSAGE_SOURCE' else 1)
