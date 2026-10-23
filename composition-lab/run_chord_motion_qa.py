"""New frozen-source two-context study; preserve failures and all denominators."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from source_fact_tier1 import extract,project_documents
from connected_tier2 import analyze,strip_lower
from contextual_note_roles import attach
from contextual_chord_motion import VERSION
from run_contextual_role_qa import inventory
from run_connected_tier2_qa import bundle
from qa_isolation_harness import execute
from check_complete_source_facts import check
from freeze_technique_baseline import retained
from technique_tier2 import comparable_to_baseline
import musical_tier2 as music


def run(capture,output):
    output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
    paths=list(root.glob('*.py'))+list((root/'songsterr_automation/songsterr_api').glob('*.py'))+list(capture.glob('*.json'))
    frozen={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    plan=dict(selection='Every source-voice consecutive pair counted; six evenly spaced preliminary topology-eligible pairs, explicit top global Krumhansl reference and parallel collection each',
        harmonic_scope='Ensemble; exact written pair extent; all compatible label pairs retained',reference='Uncalibrated explicit hypotheses, NOT established key/mode',frozen=frozen)
    (output/'plan-before-analysis.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    lower=extract(capture);docs=project_documents(lower)
    baseline=retained(docs);(output/'retained-before-context.json').write_text(json.dumps(baseline),encoding='utf-8')
    upper=analyze(lower)
    if upper['unsupported']:
        report=dict(status='FAIL_UNSUPPORTED_RETAINED',unsupported=upper['unsupported']);(output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
    normalized=music.reconstruct(upper['musical_relationships'],dict(variation=0));events={e['id']:e for e in normalized['events']}
    rows=inventory(lower,normalized,2);eligible=[r for r in rows if not r['refusals']]
    (output/'whole-song-pair-inventory.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    candidates=[c for s in upper['musical_relationships']['tonal_evidence']['scopes'] if s['id']=='song-pooled' for c in s['candidates'] if c['family']=='KrumhanslSchmuckler' and c['score'] is not None]
    maximum=max((c['score'] for c in candidates),default=None);winners=[c for c in candidates if maximum is not None and abs(c['score']-maximum)<=1e-12]
    if len(winners)!=1 or not eligible:
        report=dict(status='INCONCLUSIVE_REFERENCE_OR_NO_ELIGIBLE_PAIRS',source_pairs=len(rows),eligible=len(eligible),winners=winners)
        (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
    winner=winners[0];parallel=next(c for c in candidates if c['tonic_pc']==winner['tonic_pc'] and c['quality']!=winner['quality'])
    count=min(6,len(eligible));indices=sorted({round(i*(len(eligible)-1)/max(1,count-1)) for i in range(count)})
    requests=[dict(version=VERSION,occurrence_refs=eligible[i]['occurrence_refs'],at_qs=[events[r]['onset_q'] for r in eligible[i]['occurrence_refs']],candidate_ref=c['id'],
        harmonic_request=dict(start_q=eligible[i]['start_q'],end_q=eligible[i]['end_q'],part_id=None)) for i in indices for c in (winner,parallel)]
    (output/'requests-before-results.json').write_text(json.dumps(requests,indent=2),encoding='utf-8')
    upper=attach(upper,requests);(output/'tier2.json').write_text(json.dumps(upper),encoding='utf-8')
    code,hashes=bundle(root);worker=execute(code,strip_lower(upper),dict(variation=0),lower,output/'isolated',timeout=300)
    restored=json.loads((output/'isolated/worker/output.json').read_text(encoding='utf-8')) if worker['status']=='PASS' else None
    exact=check(capture,restored) if restored is not None else dict(status='FAIL_WORKER')
    parity=comparable_to_baseline(upper['derived_views']['techniques'],json.loads(json.dumps(baseline)))
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
    contexts=upper['contextual_constraints'];results=contexts['results']
    report=dict(status='PASS_BOUNDED_CHORD_MOTION_SOURCE' if worker['status']=='PASS' and exact['status']=='PASS_COMPLETE_CAPTURED_JSON_FACTS' and parity and unchanged else 'FAIL',
        source_occurrences=len(events),source_pairs=len(rows),preliminary_eligible_pairs=len(eligible),refusal_counts=dict(Counter(r for row in rows for r in row['refusals'])),
        queries=len(requests),query_results=dict(Counter(r['status'] for r in results)),pair_counts=[len(r['alternatives']) for r in results],
        pitch_domains=dict(Counter(r['domain'] for r in contexts['pitch_domains'])),exact=exact,worker=worker,retained_detector_parity=parity,unchanged=unchanged,module_hashes=hashes,
        gates=dict(gate1='FRESH_FROZEN_SONG',gate2='ACTUAL_STRIPPED_COMPLETE_SOURCE',gate3='CONDITIONAL_RELATIONSHIPS_PENDING_INDEPENDENT_PLANNER_REVIEW'),
        limitations=['Only preselected bounded queries received joint harmonic analysis','No inference accuracy, established key, mode, function, temporary tonic or audio claim'])
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    report=run(a.capture,a.output);print(json.dumps(report));raise SystemExit(0 if report['status']=='PASS_BOUNDED_CHORD_MOTION_SOURCE' else 1)
