"""Frozen-source role QA with complete denominators and an audited inverse."""
import argparse
from collections import Counter,defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
from source_fact_tier1 import extract,project_documents
from connected_tier2 import analyze,strip_lower,reconstruct
from contextual_note_roles import VERSION,attach,source_refusals
from run_connected_tier2_qa import bundle
from qa_isolation_harness import execute
from check_complete_source_facts import check
import musical_tier2 as music


def inventory(lower,normalized):
    """Every consecutive source-voice triple; no result-driven selection."""
    docs=project_documents(lower);events={e['id']:e for e in normalized['events']};voices=defaultdict(list)
    for e in events.values():voices[(e['part_id'],e['voice'])].append(e)
    rows=[]
    for lane,notes in sorted(voices.items()):
        notes.sort(key=lambda e:(e['bar'],e['beat'],e['note']))
        onset_counts=Counter(e['onset_q'] for e in notes)
        for i in range(len(notes)-2):
            triple=notes[i:i+3];refs=[e['id'] for e in triple];reasons=source_refusals(docs,events,refs)
            starts=[F(e['onset_q']) for e in triple];durations=[F(e['duration_q']) for e in triple]
            if any(onset_counts[e['onset_q']]!=1 for e in triple):reasons.append('ambiguous_same_voice_simultaneity')
            if any(d<=0 for d in durations):reasons.append('zero_duration_or_grace_occurrence')
            if any(e['pitch'] is None for e in triple):reasons.append('unknown_pitch_occurrence')
            if any(starts[j+1]!=starts[j]+durations[j] for j in (0,1)):reasons.append('noncontiguous_written_intervals')
            a=min(starts);b=max(t+d for t,d in zip(starts,durations))
            if any(e['id'] not in refs and F(e['onset_q'])<b and F(e['onset_q'])+F(e['duration_q'])>a for e in notes):reasons.append('ambiguous_same_voice_overlap')
            if not 0<b-a<=32:reasons.append('outside_role_window_bound')
            rows.append(dict(occurrence_refs=refs,part_id=lane[0],voice=lane[1],start_q=str(a),end_q=str(b),refusals=list(dict.fromkeys(reasons))))
    return rows


def necessary_requests(eligible,events,references):
    """Exhaustive necessary degree-motion test, before any harmonic outcomes."""
    requests=[];counts=Counter()
    for row in eligible:
        for reference in references:
            try:
                degrees=[music.collection_degree_relation(reference['tonic_pc'],reference['reference_intervals'],pitch=events[i]['pitch'])['diatonic_coordinate'] for i in row['occurrence_refs']]
            except ValueError:counts['unmapped_reference']+=1;continue
            if not all(abs(degrees[i+1]-degrees[i])==1 for i in (0,1)):
                counts['not_adjacent_degrees']+=1;continue
            counts['requires_harmonic_test']+=1
            requests.append(dict(version=VERSION,occurrence_refs=row['occurrence_refs'],candidate_ref=reference['id'],harmonic_request=dict(start_q=row['start_q'],end_q=row['end_q'],part_id=None)))
    return requests,dict(counts)


def run(capture,baseline,output,selection='spaced'):
    output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
    paths=list(root.glob('*.py'))+list((root/'songsterr_automation/songsterr_api').glob('*.py'))+list(capture.glob('*.json'))+[baseline]
    frozen={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    plan=dict(source_capture=str(capture.resolve()),selection=selection,
              selection_definition='Six evenly spaced eligible triples' if selection=='spaced' else 'ALL eligible triples/reference pairs satisfying necessary adjacent-degree motion; remaining pairs mathematically cannot satisfy this bounded role definition',
              candidate_reference='Unique KrumhanslSchmuckler global score maximum and parallel major/minor; uncalibrated reference selection, not established key',
              role_window='Exact extent of selected three written occurrences; ensemble harmonic scope',max_queries=12,
              domain='Conditional diatonic passing/neighbor only',frozen=frozen)
    (output/'plan-before-analysis.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    lower=extract(capture);upper=analyze(lower)
    if upper['unsupported']:
        report=dict(status='FAIL_UNSUPPORTED',unsupported=upper['unsupported']);(output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
    normalized=music.reconstruct(upper['musical_relationships'],dict(variation=0));rows=inventory(lower,normalized)
    (output/'whole-song-triple-inventory.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    eligible=[r for r in rows if not r['refusals']]
    candidates=[c for s in upper['musical_relationships']['tonal_evidence']['scopes'] if s['id']=='song-pooled' for c in s['candidates'] if c['family']=='KrumhanslSchmuckler' and c['score'] is not None]
    best=max(c['score'] for c in candidates);winners=[c for c in candidates if abs(c['score']-best)<=1e-12]
    if len(winners)!=1:
        report=dict(status='INCONCLUSIVE_AMBIGUOUS_QUERY_REFERENCE',winners=winners)
        (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
    winner=winners[0];parallel=next(c for c in candidates if c['tonic_pc']==winner['tonic_pc'] and c['quality']!=winner['quality'])
    chosen=sorted({round(i*(len(eligible)-1)/max(1,min(6,len(eligible))-1)) for i in range(min(6,len(eligible)))})
    requests=[dict(version=VERSION,occurrence_refs=eligible[i]['occurrence_refs'],candidate_ref=c['id'],harmonic_request=dict(start_q=eligible[i]['start_q'],end_q=eligible[i]['end_q'],part_id=None)) for i in chosen for c in (winner,parallel)]
    census=None
    if selection=='necessary':requests,census=necessary_requests(eligible,{e['id']:e for e in normalized['events']},(winner,parallel))
    if not requests or len(requests)>32:
        report=dict(status='INCONCLUSIVE_NO_QUERIES_OR_RESOURCE_BOUND',queries_required=len(requests),necessary_condition_census=census)
        (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
    (output/'requests-before-role-results.json').write_text(json.dumps(requests,indent=2),encoding='utf-8')
    upper=attach(upper,requests);bare=strip_lower(upper)
    (output/'tier2.json').write_text(json.dumps(upper),encoding='utf-8')
    code,hashes=bundle(root);worker=execute(code,bare,dict(variation=0),lower,output/'isolated',timeout=240)
    restored=json.loads((output/'isolated/worker/output.json').read_text(encoding='utf-8')) if worker['status']=='PASS' else None
    exact=check(capture,restored) if restored is not None else dict(status='FAIL_WORKER')
    previous=json.loads(baseline.read_text(encoding='utf-8'))
    detector_parity=upper['derived_views']['techniques']==previous['derived_views']['techniques']
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
    report=dict(status='PASS_BOUNDED_CONTEXT_AND_FULL_SOURCE' if worker['status']=='PASS' and exact['status']=='PASS_COMPLETE_CAPTURED_JSON_FACTS' and detector_parity and unchanged else 'FAIL',
        whole_source_facts=len(lower['facts']),source_occurrences=len(normalized['events']),source_voice_triples=len(rows),topology_eligible_triples=len(eligible),
        refusal_counts=dict(Counter(r for row in rows for r in row['refusals'])),selected_queries=len(requests),explicit_references=[winner,parallel],
        conditional_results=dict(Counter(r['status'] for r in upper['contextual_constraints']['results'])),
        selection=selection,necessary_condition_census=census,
        exact=exact,worker=worker,retained_detector_parity=detector_parity,unchanged=unchanged,module_hashes=hashes,
        gates=dict(gate1='SAME_FROZEN_NEW_SONG_RERUN_AFTER_REGISTERED_FLOAT_DISPLAY_FIX',gate2='ACTUAL_STRIPPED_COMPLETE_SOURCE_WORKER',gate3='BOUNDED_CONDITIONAL_RELATIONSHIPS_ONLY_PLANNER_REVIEW_PENDING'),
        limitations=['Harmonic queries are bounded; selection and necessary conditions disclosed','No established key, seven-mode inference, artist intent, audible fidelity or generation claim'])
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('baseline',type=Path);p.add_argument('output',type=Path);p.add_argument('--selection',choices=('spaced','necessary'),default='spaced');a=p.parse_args()
    report=run(a.capture,a.baseline,a.output,a.selection);print(json.dumps(report));raise SystemExit(0 if report['status']=='PASS_BOUNDED_CONTEXT_AND_FULL_SOURCE' else 1)
