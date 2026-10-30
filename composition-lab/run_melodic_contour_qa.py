"""One captured song: complete inverse and every local melodic opportunity."""
import argparse
import hashlib
import json
import traceback
from collections import Counter
from pathlib import Path
from source_fact_tier1 import extract
from connected_tier2 import analyze,strip_lower,validate,realize
from check_complete_source_facts import check as check_source
from run_connected_tier2_qa import bundle
from run_voicing_register_qa import save_capture
from qa_isolation_harness import execute
from check_melodic_contour_change import expected as raw_expected,check as independent_change
import melodic_contour_choices as choices
import melodic_contour_intervention as melody


def dump(path,data):path.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(capture,output,freeze=None):
    output.mkdir(parents=True,exist_ok=False)
    hashes={str(p.resolve()):sha(p)for p in capture.glob('*.json')}
    seeds=list(range(32));strengths=[0,50,100]
    if freeze is not None:
        frozen=json.loads(freeze.read_bytes());hashes.update(frozen['code_hashes']);hashes.update(frozen.get('native_hashes',{}))
        if frozen['policy']!='parallel_rhythm_melody'or choices.POLICY not in frozen.get('lever_policies',[]):raise ValueError('Declared shared random freeze required')
        if frozen['controls']['melody_seeds']!=seeds or frozen['controls']['strengths']!=strengths:raise ValueError('Fixed draw protocol differs')
    dump(output/'plan.json',dict(hashes=hashes,freeze=str(freeze)if freeze else None,seeds=seeds,strengths=strengths,
        selection='Every consecutive source triple, every qualifying donor and fixed draw; first source-ordered changed100% draw; no replacement for failure or no choice.'))
    try:
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen source/code changed')
        before=extract(capture);upper=analyze(before,rhythm_groups=True,note_accent_slots=True)
        if validate(upper)!=before:raise ValueError('Full inverse mismatch')
        upper=strip_lower(upper);dump(output/'stripped-tier2.json',upper);code,modules=bundle(Path(__file__).parent)
        zero=execute(code,upper,dict(variation=0),before,output/'zero-isolated',timeout=900)
        if zero['status']!='PASS':raise ValueError(zero)
        actual=json.loads((output/'zero-isolated/worker/output.json').read_bytes());raw=check_source(capture,actual);dump(output/'source-comparison.json',raw)
        if raw['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError(raw)
        save_capture(actual,output/'zero-capture');prepared=melody.prepare(upper);inventory=prepared['inventory'];dump(output/'inventory.json',inventory)
        counts=Counter();rates={str(s):Counter()for s in strengths};demo=None;no_choice=None
        # Source order is part, voice, raw beat order, established before testing.
        with(output/'choices.jsonl').open('w',encoding='utf-8')as handle:
            for row in inventory['neighborhoods']:
                evidence=melody.options(upper,row['target_ref'],prepared);handle.write(json.dumps(evidence)+'\n')
                counts['neighborhoods']+=1;counts['eligible']+=not bool(row['reasons'])
                counts['with_changed_choices']+=any(o['changed']for o in evidence['options']);counts[evidence['status']]+=1
                if no_choice is None and not evidence['options']:no_choice=row
                for strength in strengths:
                    for seed in seeds:
                        controls=dict(context_policy=choices.POLICY,melody=strength,target_ref=row['target_ref'],seed=seed)
                        selected,decision=choices.sample(evidence,controls);rate=rates[str(strength)]
                        rate['draws']+=1;rate['released']+=decision['released'];rate['changed']+=decision['changed']
                        if demo is None and strength==100 and decision['changed']:
                            demo=dict(target=row,chosen=selected,controls=controls,decision=decision,
                                membership_contract=melody.packet(prepared,row['target_ref'])['packet'])
        workers=[dict(case='zero',status=zero['status'])]
        if no_choice is not None:
            controls=dict(context_policy=choices.POLICY,melody=100,target_ref=no_choice['target_ref'],seed=0)
            result=execute(code,upper,controls,before,output/'no-choice-isolated',timeout=900,purpose='local_melodic_contour_intervention')
            if result['status']!='PASS':raise ValueError(result)
            workers.append(dict(case='no-choice',status=result['status']))
        if demo is not None:
            expected=raw_expected(before,demo['target']['target_ref'],demo['chosen']['donor_refs'][0])
            result=execute(code,upper,demo['controls'],expected,output/'changed-isolated',timeout=900,purpose='local_melodic_contour_intervention')
            if result['status']!='PASS':raise ValueError(result)
            actual=json.loads((output/'changed-isolated/worker/output.json').read_bytes())
            independent=independent_change(before,actual,demo['target'],demo['chosen'],demo['membership_contract'])
            if independent['status']!='PASS_INDEPENDENT_MIDDLE_NOTE_CHANGE':raise ValueError(independent)
            demo['independent_output_check']=independent;dump(output/'demonstration.json',demo);save_capture(actual,output/'changed-capture')
            workers.append(dict(case='changed',status=result['status']))
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen input/code changed during run')
        result=dict(status='PASS_SOURCE_MELODIC_CHANGE'if demo else'PASS_SOURCE_MELODIC_NO_CHOICE',facts=len(before['facts']),counts=dict(counts),
            rates={k:dict(v)for k,v in rates.items()},workers=workers,modules=modules,source_hashes_unchanged=True,
            qa1='Fixed-source development only.'if freeze is None else'Requires independent preceding random-selection receipt.',
            qa2='Actual isolated same-relationship inverse; original source JSON exactly compared outside worker.',
            qa3='Observed three-note contour and all retained chord-membership alternatives; no inferred phrase intention or musical quality claim.',
            independent_all_options_review='PENDING',native_audio='PENDING',full_melody_lever='OPEN')
    except Exception as exc:result=dict(status='FAIL_RETAINED',error=str(exc),traceback=traceback.format_exc())
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('--freeze',type=Path);a=p.parse_args()
    result=run(a.capture,a.output,a.freeze);print(json.dumps({k:v for k,v in result.items()if k!='modules'},indent=2));raise SystemExit(result['status']=='FAIL_RETAINED')
