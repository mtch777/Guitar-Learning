"""Frozen generic voicing policy tested on fresh captures; no adaptive retry."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import traceback

from source_fact_tier1 import extract,project_documents
from connected_tier2 import analyze,strip_lower,reconstruct
from voicing_register import inventory,empirical_options,sample_choice,intervene
from run_connected_tier2_qa import bundle
from run_voicing_register_qa import locked_diff,save_capture
from qa_isolation_harness import execute
from check_complete_source_facts import check
from check_technique_connections import check as source_relationships
from freeze_technique_baseline import retained
from technique_tier2 import comparable_to_baseline

POLICY='source_witnessed_fixed_strings'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path,data):path.write_text(json.dumps(data,indent=2),encoding='utf-8')


def raw_geometry(documents,refs):
    """Independent raw JSON witness checker; no producer inventory calls."""
    result=[];settings=None
    for ref in refs:
        _,sid,part,bar,voice,beat,note=ref.split(':')
        p=documents[f'track-{part}.json'];n=p['measures'][int(bar)-1]['voices'][int(voice)]['beats'][int(beat)]['notes'][int(note)]
        current=[p['instrumentId'],p['tuning'],p.get('capo') or 0]
        if settings is not None and current!=settings:raise ValueError('Mixed instrument witness')
        settings=current;s=n['string'];f=F(str(n['fret']))
        result.append([str(F(str(p['tuning'][s]))+F(str(p.get('capo') or 0))+f),s,str(f)])
    return dict(settings=settings,members=sorted(result))


def audit_choices(documents,catalog,policy=POLICY):
    issues=[];accepted=0;alternatives=0;rejections=Counter();selection=None;rows=[]
    by_id={r['id']:r for r in catalog['units']}
    for target in catalog['units']:
        if target['refusal_reasons']:continue
        evidence=empirical_options(catalog,target['id'],policy)
        rows.append(dict(target_ref=target['id'],status=evidence['status'],levels=evidence['levels'],rejected=evidence['rejected'],options=evidence['options']))
        rejections.update(r['reason'] for r in evidence['rejected'])
        if selection is None and evidence['status']=='SUPPORTED_EMPIRICAL_ALTERNATIVES':selection=target
        for choice in evidence['options']:
            realization=choice['realization'];raw=raw_geometry(documents,target['member_refs'])
            predicted=[]
            for ref,interval in zip(target['member_refs'],realization['intervals']):
                entry=raw_geometry(documents,[ref]);_,_,part,_,_,_,_=ref.split(':')
                s=realization['strings'][target['member_refs'].index(ref)] if policy=='joint_source_fingering' else entry['members'][0][1];p=documents[f'track-{part}.json'];pitch=F(realization['anchor'])+F(interval)
                predicted.append([str(pitch),s,str(pitch-F(str(p['tuning'][s]))-F(str(p.get('capo') or 0)))])
            predicted=dict(settings=raw['settings'],members=sorted(predicted))
            old_pcs=sorted(F(row[0])%12 for row in raw['members']);new_pcs=sorted(F(row[0])%12 for row in predicted['members'])
            if old_pcs!=new_pcs:issues.append('PC multiplicity mismatch:'+target['id'])
            for ref in choice['donor_refs']:
                accepted+=1;donor=by_id[ref]
                if ref==target['id'] or raw_geometry(documents,donor['member_refs'])!=predicted:issues.append('No independent joint witness:'+ref)
            original=dict(target['realization'],strings=target['fixed_output_strings']) if policy=='joint_source_fingering' else target['realization']
            alternatives+=realization!=original
    return dict(status='PASS_BOUNDED_SOURCE_WITNESSES' if not issues else 'FAIL',issues=issues,accepted_donor_links=accepted,
        alternative_choices=alternatives,rejected_donor_links=dict(rejections),rows=rows),selection


def run(capture,output,freeze):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private output required')
    frozen=json.loads(freeze.read_text(encoding='utf-8'))
    policy=frozen.get('policy',POLICY)
    if policy not in ('source_witnessed_fixed_strings','incident_dependencies','joint_source_fingering'):raise ValueError('Frozen declared policy required')
    if any(digest(Path(p))!=h for p,h in frozen['code_hashes'].items()):raise ValueError('Frozen logic changed; no fresh-test result permitted')
    output.mkdir(parents=True);result=dict(status='RUNNING',policy=policy)
    freeze_digest=digest(freeze)
    source_hashes={str(p.resolve()):digest(p) for p in capture.glob('*.json')}
    dump(output/'source-hashes-before.json',source_hashes)
    try:
        lower=extract(capture);documents=project_documents(lower);baseline=retained(documents);upper=analyze(lower)
        if upper['unsupported']:
            dump(output/'unsupported-source-owners.json',upper['unsupported'])
            raise ValueError(f"Unsupported source owners: {len(upper['unsupported'])}; see unsupported-source-owners.json")
        stripped=strip_lower(upper);dump(output/'stripped-tier2.json',stripped)
        code,modules=bundle(Path(__file__).parent)
        zero=execute(code,stripped,dict(variation=0),lower,output/'zero-isolated',timeout=300)
        actual=json.loads((output/'zero-isolated/worker/output.json').read_text(encoding='utf-8')) if zero['status']=='PASS' else None
        exact=check(capture,actual) if actual is not None else dict(status='FAIL_WORKER')
        connections=source_relationships(documents,upper);parity=comparable_to_baseline(upper['derived_views']['techniques'],json.loads(json.dumps(baseline)))
        catalog=inventory(lower,policy);dump(output/'catalog.json',catalog)
        meaning,target=audit_choices(documents,catalog,policy)
        from check_voicing_policy import check as independent_policy_check
        independent=independent_policy_check(documents,catalog,reported=meaning['rows'],policy=policy)
        dump(output/'independent-policy-audit.json',independent)
        meaning['independent_denominator_check']={k:v for k,v in independent.items() if k!='expected_rows'}
        if independent['status']!='PASS_INDEPENDENT_POLICY':meaning['status']='FAIL'
        if policy in ('incident_dependencies','joint_source_fingering'):
            from check_execution_dependencies import check as check_dependencies
            dependency_check=check_dependencies(lower,catalog['execution_dependencies'])
            dump(output/'independent-execution-audit.json',dependency_check)
            meaning['independent_execution_check']={k:v for k,v in dependency_check.items() if k not in ('expected','expected_graph')}
            if dependency_check['status']!='PASS_INDEPENDENT_EXECUTION_DEPENDENCIES':meaning['status']='FAIL'
        dump(output/'source-witness-audit.json',meaning)
        draws=[];changed_run=None;locks=None;decision=None
        # All source units were inventoried. First supported alternative is a
        # predeclared demonstration rule, not a quality or coverage estimate.
        if target is None:target=next((r for r in catalog['units'] if not r['refusal_reasons']),None)
        if target is not None:
            for voicing,register,physical in ([(s,s,s) for s in (0,50,100)]+[(100,0,0),(0,100,0),(0,0,100),(100,100,0)] if policy=='joint_source_fingering' else [(s,s,0) for s in (0,50,100)]+[(100,0,0),(0,100,0)]):
                seeds=range(9427,9447) if voicing==register and (policy!='joint_source_fingering' or physical==voicing) else [9427]
                for seed in seeds:
                    controls=dict(voicing=voicing,register=register,seed=seed,target_ref=target['id'],context_policy=policy)
                    if policy=='joint_source_fingering':controls['physical']=physical
                    _,choice=sample_choice(catalog,controls);draws.append(dict(controls=controls,decision=choice))
            demo=next((r for r in draws if r['decision']['changed']),None)
            if demo:
                edited,decision=intervene(stripped,demo['controls']);changed=reconstruct(edited,dict(variation=0))
                changed_run=execute(code,stripped,demo['controls'],changed,output/'changed-isolated',timeout=300,purpose='voicing_register_intervention')
                changed_actual=json.loads((output/'changed-isolated/worker/output.json').read_text(encoding='utf-8')) if changed_run['status']=='PASS' else None
                if changed_actual is not None and policy=='joint_source_fingering':
                    from check_joint_fingering import check as joint_locks
                    locks=joint_locks(lower,changed_actual,demo['controls'],decision)
                else:locks=locked_diff(lower,changed_actual,target['member_refs']) if changed_actual is not None else dict(status='FAIL_WORKER')
                if changed_actual is not None and policy in ('incident_dependencies','joint_source_fingering'):
                    from check_execution_dependencies import expected as expected_dependencies
                    from check_voicing_policy import _written_ties
                    from run_reversible_tier_qa import extract_documents as written_events
                    after_documents=project_documents(changed_actual)
                    semantic_locks=dict(execution_signatures_equal=expected_dependencies(lower)['signature']==expected_dependencies(changed_actual)['signature'],
                        written_ties_equal=_written_ties(documents,written_events(documents)['events'])==_written_ties(after_documents,written_events(after_documents)['events']))
                    locks['independent_semantic_locks']=semantic_locks
                    if not all(semantic_locks.values()):locks['status']='FAIL';locks['issues'].append('Independent execution/tie relationship changed')
                save_capture(actual,output/'zero-capture');save_capture(changed_actual,output/'changed-capture')
        dump(output/'ALL-control-draws.json',draws)
        unchanged=set(source_hashes)=={str(p.resolve()) for p in capture.glob('*.json')} and all(digest(Path(p))==h for p,h in source_hashes.items()) and all(digest(Path(p))==h for p,h in frozen['code_hashes'].items()) and digest(freeze)==freeze_digest
        passed=unchanged and zero['status']=='PASS' and exact['status']=='PASS_COMPLETE_CAPTURED_JSON_FACTS' and connections['status']=='PASS_SOURCE_BACKED_RELATIONSHIPS' and parity and meaning['status']=='PASS_BOUNDED_SOURCE_WITNESSES'
        if changed_run is not None:passed=passed and changed_run['status']=='PASS' and locks['status']=='PASS_LOCKED_DIMENSIONS'
        study_kind=frozen.get('study_kind','FRESH_FROZEN_TRIAL')
        pass_status='PASS_BOUNDED_REPAIR_AND_REVERSAL' if study_kind=='DEVELOPMENT_REPAIR_REPLAY_NOT_FRESH' else 'PASS_BOUNDED_PORTABILITY_AND_REVERSAL'
        result=dict(status=pass_status if passed else 'FAIL_RETAINED',study_kind=study_kind,policy=policy,unchanged=unchanged,
            song_id=documents['metadata.json']['songId'],title=documents['metadata.json'].get('title'),artist=documents['metadata.json'].get('artist'),
            source_occurrences=catalog['source_occurrences'],source_facts=len(lower['facts']),units=len(catalog['units']),eligible_units=sum(not r['refusal_reasons'] for r in catalog['units']),
            refusal_counts=catalog['refusal_counts'],qa1=dict(source_relationships=connections,technique_parity=parity),qa2=dict(zero=zero,independent_source=exact,changed=changed_run,locks=locks),
            qa3={k:v for k,v in meaning.items() if k!='rows'},target_ref=target['id'] if target else None,decision=decision,
            nonzero_acceptance='OPEN_GP_AUDIO_AND_HUMAN_REVIEW' if decision else 'OPEN_NO_SUPPORTED_CHANGED_DRAW',modules=modules,
            control_counts={str(s):dict(draws=sum(r['controls']['voicing']==r['controls']['register']==s and r['controls'].get('physical',s)==s for r in draws),changed=sum(r['controls']['voicing']==r['controls']['register']==s and r['controls'].get('physical',s)==s and r['decision']['changed'] for r in draws)) for s in (0,50,100)},
            freeze_sha256=freeze_digest,limits='Bounded notation/context/witness audit, not key/function/artist accuracy or certified human playability; no adaptive policy shopping')
    except Exception as error:
        result.update(status='FAIL_RETAINED',error=type(error).__name__+': '+str(error));(output/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8')
    dump(output/'result.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('capture',type=Path);parser.add_argument('output',type=Path);parser.add_argument('freeze',type=Path);args=parser.parse_args()
    result=run(args.capture,args.output,args.freeze)
    print(json.dumps({k:result.get(k) for k in ('status','song_id','title','source_occurrences','source_facts','eligible_units','qa3','control_counts','nonzero_acceptance','error')}))
    raise SystemExit(0 if result['status'] in ('PASS_BOUNDED_PORTABILITY_AND_REVERSAL','PASS_BOUNDED_REPAIR_AND_REVERSAL') else 1)
