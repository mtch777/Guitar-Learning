"""Frozen full-source/all-assumptions proposal and actual intervention gates.

No caller pitches, source-label invention, preferred harmonic root or artist
claim. A resource stop is incomplete, never a successful creative gate.
"""
import argparse,json,shutil,traceback
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from run_declared_chord_qa import run as exact_qa,sha,dump
from run_connected_tier2_qa import bundle
from run_voicing_register_qa import save_capture
from connected_tier2 import realize
from source_fact_tier1 import extract
from check_complete_source_facts import check as check_source
from check_harmonic_evidence import check as check_harmonic
from check_harmonic_pattern_ledger import check as check_ledger
from check_unlabeled_inner import Oracle
from unlabeled_inner_voicing import catalog,options,apply,POLICY
from declared_degree_choices import sample
from qa_isolation_harness import execute

SEEDS=list(range(32))
def run(capture,output,freeze,*,max_targets=None):
    capture=Path(capture);output=Path(output);freeze=Path(freeze)
    if max_targets is not None and(type(max_targets)is not int or max_targets<1):raise ValueError('Positive declared resource bound required')
    output.mkdir(parents=True,exist_ok=False);frozen=json.loads(freeze.read_text());source_hashes={str(p.resolve()):sha(p)for p in capture.glob('*.json')}
    plan=dict(policy=POLICY,seeds=SEEDS,source_hashes=source_hashes,max_targets=max_targets,
        selection='All source groups in rational onset/part/id order; first changed draw in fixed0..31 batch at100%; every outcome retained',
        scope='Conditional finite-vocabulary universal source patterns; contact coverage provisional, no key/voice/artist inference')
    dump(output/'plan.json',plan);ledger=[];audits=[];denominators=[];counts=Counter();demo=None;untested=[]
    try:
        dependencies={**frozen['code_hashes'],**frozen.get('native_hashes',{})}
        if any(sha(Path(p))!=h for p,h in {**source_hashes,**dependencies}.items()):raise ValueError('Initial source/code/native drift')
        original=output/'original-capture';original.mkdir()
        for p in capture.glob('*.json'):shutil.copyfile(p,original/p.name)
        zero=exact_qa(capture,output/'zero-and-pair',freeze)
        if zero['status']!='PASS_DECLARED_WRITTEN_CHORD_QA':raise ValueError('Complete source/pair gate failed; retained')
        upper=json.loads((output/'zero-and-pair/stripped-tier2.json').read_text());before=json.loads((output/'zero-and-pair/zero-isolated/worker/output.json').read_text())
        if check_source(capture,before)['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError('Actual zero does not match complete raw capture')
        save_capture(before,output/'zero-capture')
        c=catalog(upper);raw_catalog=dict(units=c['units'],geometries=c['geometries'],component_scope_refusals=c['component_scope_refusals'])
        native=check_harmonic(before,c['harmonic_evidence'],raw_catalog,profile=c['profile']);dump(output/'independent-harmonic.json',native)
        if native['status']!='PASS_NATIVE_HARMONIC_EVIDENCE':raise ValueError(native)
        checked_ledger=check_ledger(raw_catalog,c['harmonic_evidence'],c['ledger']);dump(output/'independent-ledger.json',checked_ledger)
        if checked_ledger['status']!='PASS_INDEPENDENT_PATTERN_LEDGER':raise ValueError(checked_ledger)
        oracle=Oracle(before);inventory=oracle.inventory();dump(output/'independent-inventory.json',inventory)
        dump(output/'harmonic-evidence.json',c['harmonic_evidence']);dump(output/'catalog.json',raw_catalog);dump(output/'pattern-ledger.json',c['ledger'])
        groups=sorted(c['harmonic_evidence']['groups'],key=lambda g:(F(g['onset_q']),g['part_id'],g['member_refs'][0]));native_groups={g['id']:g for g in inventory['groups']}
        if len(groups)!=len(native_groups)or{g['member_refs'][0]for g in groups}!=set(native_groups):raise ValueError('Complete source target inventory differs')
        for g in groups:
            expected=native_groups[g['member_refs'][0]]
            if g['member_refs']!=expected['member_refs']or [h['id']for h in g['hypotheses']]!=[h['id']for h in expected['hypotheses']]:raise ValueError('Source target/hypothesis membership differs')
        code,_=bundle(Path(__file__).parent.resolve());zero_ref=groups[0]['member_refs'][0]if groups else'event:unused-exact-zero-target'
        preview_zero=execute(code,upper,dict(voicing=0,register=0,target_ref=zero_ref,seed=0,context_policy=POLICY),before,output/'preview-zero-isolated',timeout=600,purpose='voicing_register_intervention')
        if preview_zero['status']!='PASS':raise ValueError(preview_zero)
        selected=None
        for index,g in enumerate(groups):
            if max_targets is not None and index>=max_targets:
                untested=[r['member_refs'][0]for r in groups[index:]];break
            target_ref=g['member_refs'][0];proposal=options(upper,target_ref,c)
            independent=oracle.check_options(target_ref,proposal);denominators.append(dict(target_ref=target_ref,result=independent))
            if independent['status']!='PASS_INDEPENDENT_UNLABELED_OPTIONS':raise ValueError(dict(target_ref=target_ref,independent=independent))
            labeled=bool(g['declarations']);counts['targets']+=1;counts['labeled_targets'if labeled else'unlabeled_targets']+=1
            counts['targets_with_exact_fits']+=bool(g['hypotheses']);counts['admitted_changed_layouts']+=sum(o['changed']for o in proposal['options']);counts['rejected_layouts']+=len(proposal['rejected'])
            eligible=proposal['target'].get('eligible_target_hypothesis_refs',[])
            counts['component_eligible_targets']+=bool(eligible)
            counts['universally_eligible_targets']+=bool(proposal['all_hypothesis_refs'])and set(eligible)==set(proposal['all_hypothesis_refs'])
            counts['retained_hypotheses']+=len(proposal['all_hypothesis_refs'])
            counts['targets_with_admitted_changes']+=any(o['changed']for o in proposal['options'])
            counts['rejected_changed_layouts']+=sum(o['changed']for o in proposal['rejected'])
            counts['labeled_changed_layouts'if labeled else'unlabeled_changed_layouts']+=sum(o['changed']for o in proposal['options'])
            counts['unique_donor_group_links']+=sum(len(o['donor_refs'])for o in proposal['options'])
            for choice in proposal['options']:
                if not choice['changed']:continue
                after=realize(apply(upper,proposal['target'],choice,c));audit=oracle.check(after,g['member_refs'],choice)
                audits.append(dict(target_ref=target_ref,pitches=choice['pitches'],result=audit))
                if audit['status']!='PASS_PROVISIONAL_ALL_ASSUMPTIONS_INNER':raise ValueError(audits[-1])
                counts['independently_checked_changed_layouts']+=1
            control=dict(voicing=100,register=0,target_ref=target_ref,context_policy=POLICY);draws=[]
            for seed in SEEDS:
                chosen,decision=sample(proposal,dict(control,seed=seed));draws.append(dict(seed=seed,decision=decision))
                if selected is None and chosen is not None and chosen['changed']:selected=(g,proposal,chosen,dict(control,seed=seed))
            ledger.append(dict(target_ref=target_ref,proposal=proposal,draws=draws))
            if len(ledger)%25==0:
                dump(output/'choices-partial.json',ledger);dump(output/'progress.json',dict(processed=len(ledger),total=len(groups),counts=dict(counts)))
        dump(output/'choices.json',ledger);dump(output/'independent-options.json',denominators);dump(output/'independent-changes.json',audits);dump(output/'untested-targets.json',untested)
        if selected is not None:
            g,proposal,chosen,controls=selected;expected=realize(apply(upper,proposal['target'],chosen,c))
            changed_worker=execute(code,upper,controls,expected,output/'changed-isolated',timeout=600,purpose='voicing_register_intervention')
            if changed_worker['status']!='PASS':raise ValueError(changed_worker)
            actual=json.loads((output/'changed-isolated/worker/output.json').read_text());audit=oracle.check(actual,g['member_refs'],chosen)
            if audit['status']!='PASS_PROVISIONAL_ALL_ASSUMPTIONS_INNER':raise ValueError(audit)
            save_capture(actual,output/'changed-capture')
            source_groups={row['group_ref']:row for row in c['harmonic_evidence']['groups']};units={u['id']:u for u in c['units']}
            first=units[chosen['support'][0]['target_hypothesis_ref']]
            target=dict(id=g['member_refs'][0],group_ref=g['group_ref'],part_id=g['part_id'],member_refs=g['member_refs'],outer_refs=first['outer_refs'],inner_refs=first['inner_refs'],strings=first['strings'],
                all_hypothesis_refs=proposal['all_hypothesis_refs'],conditional_roles_before=[dict(hypothesis_ref=s['target_hypothesis_ref'],roles=units[s['target_hypothesis_ref']]['roles'])for s in chosen['support']])
            frequencies=[]
            for strength in (0,50,100):
                decisions=[sample(proposal,dict(controls,voicing=strength,seed=seed))[1]for seed in range(1000)]
                frequencies.append(dict(strength=strength,trials=1000,released=sum(d['released']for d in decisions),changed=sum(d['changed']for d in decisions)))
            demo=dict(schema='all-assumptions-inner-preview/1',status='PROVISIONAL_AUDIBLE_ARTIFACT_NOT_YET_BUILT',controls=controls,target=target,chosen=chosen,
                donor_source_refs=[source_groups[r]['member_refs'][0]for r in chosen['donor_refs']],donor_source_bars=sorted({int(source_groups[r]['member_refs'][0].split(':')[3])for r in chosen['donor_refs']}),
                target_has_source_label=bool(g['declarations']),actual_worker_audit=audit,isolated=changed_worker,frequencies=frequencies,human_playability='UNVERIFIED',listening_judgment=None,
                role_display_scope='Every conditional hypothesis retained; no single declared or inferred true root selected')
            dump(output/'demonstration.json',demo)
        if any(sha(Path(p))!=h for p,h in {**source_hashes,**dependencies}.items()):raise ValueError('Final source/code/native drift')
        status='INCOMPLETE_RETAINED_RESOURCE_LIMIT'if untested else'PASS_PROVISIONAL_UNLABELED_INNER_QA'if demo else'PASS_UNLABELED_INNER_QA_NO_CHANGE'
        result=dict(status=status,policy=POLICY,song_id=zero['song_id'],title=zero['title'],notes=zero['note_occurrences'],facts=zero['source_facts'],counts=dict(counts),
            independent_population_counts=inventory['counts'],
            total_source_targets=len(groups),tested_targets=len(ledger),untested_targets=len(untested),changed_demonstration=demo is not None,demonstration_has_source_label=demo['target_has_source_label']if demo else None,
            creative_gateway='NOT_PASSED',human_playability='UNVERIFIED',listening_judgment=None,
            qa1='Fresh status requires separate preregistered selection; no-fit and resource stops retained',
            qa2='Actual complete-source/degree-pair/explicit-policy zero; actual changed worker when available. Same existing owners, no second pitch stream.',
            qa3='All retained finite-vocabulary assumptions support the same source-derived layout; every changed option independently audited; no true harmony, key, melodic identity or artist-fit claim')
    except Exception as exc:
        dump(output/'choices.json',ledger);dump(output/'independent-options.json',denominators);dump(output/'independent-changes.json',audits)
        result=dict(status='FAIL_RETAINED',error=str(exc),counts=dict(counts),tested_targets=len(ledger));(output/'traceback.txt').write_text(traceback.format_exc())
    dump(output/'result.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);p.add_argument('--max-targets',type=int);a=p.parse_args()
    result=run(a.capture,a.output,a.freeze,max_targets=a.max_targets);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status'].startswith('PASS_')else 1)
