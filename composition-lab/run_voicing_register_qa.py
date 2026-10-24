"""Frozen-source scoped intervention, exact inverse and independent lock audit."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
from source_fact_tier1 import extract,project_documents
from connected_tier2 import analyze,strip_lower,reconstruct
from contextual_note_roles import attach
from voicing_register import inventory,select_target,sample_choice,intervene
from run_connected_tier2_qa import bundle
from qa_isolation_harness import execute
from check_complete_source_facts import check
from freeze_technique_baseline import retained
from technique_tier2 import comparable_to_baseline


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def locked_diff(before,after,member_refs):
    a={r['id']:r for r in before['facts']};b={r['id']:r for r in after['facts']};issues=[]
    if list(a)!=list(b):issues.append('Source identities/order changed')
    from run_reversible_tier_qa import extract_documents
    before_events=extract_documents(project_documents(before))['events'];after_events=extract_documents(project_documents(after))['events']
    old={e['id']:e for e in before_events};new={e['id']:e for e in after_events}
    allowed=set();changed=[]
    for ref in member_refs:
        event=old[ref];allowed.add(f"track-{event['part_id']}.json#/measures/{event['bar']-1}/voices/{event['voice']}/beats/{event['beat']}/notes/{event['note']}/fret")
        if event['pitch'] is None or new[ref]['pitch'] is None or F(event['pitch'])%12!=F(new[ref]['pitch'])%12:issues.append('Selected member pitch class changed')
    for ident in set(a)|set(b):
        if a.get(ident)!=b.get(ident):
            changed.append(ident)
            if ident not in allowed:issues.append('Locked source fact changed: '+ident)
    for ref,event in old.items():
        if ref not in member_refs and new.get(ref)!=event:issues.append('Unselected musical occurrence changed')
    return dict(status='PASS_LOCKED_DIMENSIONS' if not issues else 'FAIL',changed_source_paths=sorted(changed),allowed_paths=sorted(allowed),issues=issues,
                meaning='Only selected fret values differ; selected note PCs and all source timing/identity/string/technique/dynamic/other-part facts exact')


def save_capture(tier1,path):
    path.mkdir(parents=True,exist_ok=False)
    for name,value in project_documents(tier1).items():(path/name).write_text(json.dumps(value),encoding='utf-8')


def run(capture,output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private output required')
    output.mkdir(parents=True);root=Path(__file__).parent
    files=[p for p in root.glob('*.py') if not p.name.startswith('test_')]+list((root/'songsterr_automation/songsterr_api').glob('*.py'))+list(capture.glob('*.json'))
    frozen={str(p.resolve()):sha(p) for p in files};code,modules=bundle(root)
    (output/'plan-before-execution.json').write_text(json.dumps(dict(frozen=frozen,modules=modules,seeds=list(range(9427,9447)),strengths=[0,50,100],
        scope='Weak same-part/PCmultiplicity/duration pooling; source-declared geometry only; HUMAN_EXECUTION_UNVERIFIED',
        source='Previously frozen random capture, development-inspected; not untouched accuracy benchmark',
        selection='First eligible source unit by onset/part/identity; first changed of FIXED batch for demonstration; retain every draw'),indent=2),encoding='utf-8')
    lower=extract(capture);catalog=inventory(lower);selection=select_target(catalog,'pooled_declared_geometry')
    (output/'catalog.json').write_text(json.dumps(catalog),encoding='utf-8');(output/'selection.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
    if selection.get('target_ref') is None:
        result=dict(status='NO_ELIGIBLE_ALTERNATIVE_RETAINED',selection=selection);(output/'result.json').write_text(json.dumps(result),encoding='utf-8');return result
    target=next(r for r in catalog['units'] if r['id']==selection['target_ref']);baseline=retained(project_documents(lower));upper=analyze(lower)
    if upper['unsupported']:raise ValueError('Complete inverse blocked by unsupported source owners: '+str(upper['unsupported']))
    frame=upper['derived_views']['harmonic_context']['measure_geometry']['frames'][target['bar']-1]
    request=dict(version='conditional-passage-note-roles/1',harmonic_request=dict(start_q=frame['start_q'],end_q=str(F(frame['start_q'])+F(frame['duration_q'])),part_id=None),reference_candidate_ref=None)
    upper=attach(upper,[request]);(output/'tier2.json').write_text(json.dumps(upper),encoding='utf-8');stripped=strip_lower(upper)
    draws=[]
    for strength in (0,50,100):
        for seed in range(9427,9447):
            controls=dict(voicing=strength,register=strength,target_ref=target['id'],seed=seed,context_policy='pooled_declared_geometry')
            realization,decision=sample_choice(catalog,controls);draws.append(dict(controls=controls,decision=decision,realization=realization))
    for voicing,register in ((100,0),(0,100)):
        controls=dict(voicing=voicing,register=register,target_ref=target['id'],seed=9427,context_policy='pooled_declared_geometry')
        realization,decision=sample_choice(catalog,controls);draws.append(dict(controls=controls,decision=decision,realization=realization))
    (output/'ALL-control-draws.json').write_text(json.dumps(draws,indent=2),encoding='utf-8')
    demo=next((r for r in draws if r['decision']['changed']),None)
    zero=execute(code,stripped,dict(variation=0),lower,output/'zero-isolated',timeout=300)
    actual_zero=json.loads((output/'zero-isolated/worker/output.json').read_text()) if zero['status']=='PASS' else None
    zero_source=check(capture,actual_zero) if actual_zero is not None else dict(status='FAIL_WORKER')
    if actual_zero is not None:save_capture(actual_zero,output/'zero-capture')
    parity=comparable_to_baseline(upper['derived_views']['techniques'],json.loads(json.dumps(baseline)))
    if demo is None:
        result=dict(status='NO_CHANGED_DRAW_RETAINED',zero=zero,zero_source=zero_source,draws=len(draws));(output/'result.json').write_text(json.dumps(result),encoding='utf-8');return result
    edited,decision=intervene(stripped,demo['controls']);changed=reconstruct(edited,dict(variation=0));lock_check=locked_diff(lower,changed,target['member_refs'])
    (output/'changed-tier2.json').write_text(json.dumps(edited),encoding='utf-8')
    changed_run=execute(code,stripped,demo['controls'],changed,output/'changed-isolated',timeout=300,purpose='voicing_register_intervention')
    actual_changed=json.loads((output/'changed-isolated/worker/output.json').read_text()) if changed_run['status']=='PASS' else None
    changed_lock=locked_diff(lower,actual_changed,target['member_refs']) if actual_changed is not None else dict(status='FAIL_WORKER')
    if actual_changed is not None:save_capture(actual_changed,output/'changed-capture')
    zero_controls=dict(demo['controls'],voicing=0,register=0)
    zero_named=reconstruct(stripped,zero_controls)==lower
    unchanged=all(sha(Path(p))==h for p,h in frozen.items())
    success=zero['status']==changed_run['status']=='PASS' and zero_source['status']=='PASS_COMPLETE_CAPTURED_JSON_FACTS' and lock_check['status']==changed_lock['status']=='PASS_LOCKED_DIMENSIONS' and zero_named and parity and unchanged
    result=dict(status='PASS_EXACT_AND_SCOPED_SYMBOLIC_INTERVENTION' if success else 'FAIL_RETAINED',unchanged=unchanged,target_ref=target['id'],part_id=target['part_id'],target_bar=target['bar'],request=request,
        source_occurrences=catalog['source_occurrences'],all_source_facts=len(lower['facts']),catalog_units=len(catalog['units']),eligible_units=sum(not r['refusal_reasons'] for r in catalog['units']),
        zero=zero,zero_source=zero_source,named_zero_controls_exact=zero_named,retained_detector_parity=parity,changed_worker=changed_run,locked=changed_lock,decision=decision,demo_controls=demo['controls'],
        control_counts={str(s):dict(draws=20,changed=sum(r['decision']['changed'] for r in draws if r['controls']['voicing']==r['controls']['register']==s),statuses=dict(Counter(r['decision']['status'] for r in draws if r['controls']['voicing']==r['controls']['register']==s))) for s in (0,50,100)},
        separate_locks=[r for r in draws if r['controls']['voicing']!=r['controls']['register']],gate3='PENDING_INDEPENDENT_SOURCE_REVIEW',gp_audio='PENDING',physical_acceptance='OPEN_TEN_FRET_SPAN_NOT_VERIFIED',
        scope='Complete-source exact0 and same-equation scoped nonzero, not a finished creative lever or artist/musical suitability claim')
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=run(a.capture,a.output)
    print(json.dumps({k:r.get(k) for k in ('status','unchanged','target_ref','source_occurrences','all_source_facts','control_counts','physical_acceptance')}));raise SystemExit(0 if r['status']=='PASS_EXACT_AND_SCOPED_SYMBOLIC_INTERVENTION' else 1)
