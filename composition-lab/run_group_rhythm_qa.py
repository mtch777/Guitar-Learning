"""Repeatable whole-source development/frozen QA of complete-group rhythm."""
import argparse
import hashlib
import json
import traceback
from collections import Counter
from pathlib import Path
from source_fact_tier1 import extract
from connected_tier2 import analyze,strip_lower,validate,realize
from check_complete_source_facts import check
from run_connected_tier2_qa import bundle
from run_voicing_register_qa import save_capture
from qa_isolation_harness import execute
import local_group_rhythm as rhythm


def dump(path,data):path.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(capture,output,freeze=None):
    output.mkdir(parents=True,exist_ok=False)
    sources={str(p.resolve()):sha(p)for p in capture.glob('*.json')}
    hashes=dict(sources)
    if freeze is not None:
        frozen=json.loads(freeze.read_bytes());hashes.update(frozen['code_hashes']);hashes.update(frozen.get('native_hashes',{}))
        if frozen['policy']!=rhythm.POLICY and not(frozen['policy']=='parallel_rhythm_melody'and rhythm.POLICY in frozen.get('lever_policies',[])):raise ValueError('Rhythm-specific or declared shared freeze required')
        if frozen['policy']=='parallel_rhythm_melody'and(frozen['controls']['rhythm_seeds']!=list(range(64))or frozen['controls']['strengths']!=[0,50,100]):raise ValueError('Fixed draw protocol differs')
    dump(output/'plan.json',dict(source_hashes=sources,freeze=str(freeze)if freeze else None,seeds=list(range(64)),strengths=[0,50,100],
        selection='All complete groups, including exclusions. First source-ordered supported changed draw at100. No reroll. Development unless a preceding random freeze is linked.'))
    try:
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen input/code changed')
        before=extract(capture);upper=analyze(before,rhythm_groups=True,note_accent_slots=True)
        if validate(upper)!=before:raise ValueError('Forward/reverse verification failed')
        stripped=strip_lower(upper);dump(output/'stripped-tier2.json',stripped);code,modules=bundle(Path(__file__).parent)
        zero=execute(code,stripped,{'variation':0},before,output/'zero-isolated',timeout=600)
        if zero['status']!='PASS':raise ValueError(zero)
        actual=json.loads((output/'zero-isolated/worker/output.json').read_bytes());raw=check(capture,actual);dump(output/'source-comparison.json',raw)
        if raw['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError(raw)
        save_capture(actual,output/'zero-capture');view=rhythm.inventory(before);dump(output/'inventory.json',view)
        counts=Counter();rates={str(s):Counter()for s in(0,50,100)};demo=None;no_choice=None
        with(output/'choices.jsonl').open('w',encoding='utf-8')as f:
            for row in view['groups']:
                evidence=rhythm.options(before,row['id'],view);f.write(json.dumps(evidence)+'\n')
                counts['groups']+=1;counts['eligible']+=not bool(row['reasons']);counts['with_changed_choices']+=any(o['changed']for o in evidence['options'])
                if no_choice is None and not evidence['options']:no_choice=row
                for strength in(0,50,100):
                    for seed in range(64):
                        c=dict(context_policy=rhythm.POLICY,rhythm=strength,seed=seed,target_ref=row['id'])
                        choice,decision=rhythm.sample(evidence,c);rate=rates[str(strength)]
                        rate['draws']+=1;rate['released']+=decision['released'];rate['changed']+=decision['changed']
                        if demo is None and strength==100 and decision['changed']:
                            demo=dict(target=row,chosen=choice,controls=c,decision=decision,clip=dict(first=max(1,row['bar']-1),last=row['bar']+1,part=row['part_id']))
        workers=[dict(case='zero',status=zero['status'])]
        if no_choice is not None:
            c=dict(context_policy=rhythm.POLICY,rhythm=100,seed=0,target_ref=no_choice['id'])
            report=execute(code,stripped,c,before,output/'no-choice-isolated',timeout=600,purpose='local_group_rhythm_intervention')
            if report['status']!='PASS':raise ValueError(report)
            workers.append(dict(case='no-choice',status=report['status']))
        if demo:
            edited,decision=rhythm.intervene(stripped,demo['controls']);expected=realize(edited)
            changed=execute(code,stripped,demo['controls'],expected,output/'changed-isolated',timeout=600,purpose='local_group_rhythm_intervention')
            if changed['status']!='PASS':raise ValueError(changed)
            actual=json.loads((output/'changed-isolated/worker/output.json').read_bytes())
            effect=rhythm.verify_effect(before,actual,demo['target'],demo['chosen']['shares'])
            demo.update(decision=decision,actual_worker_scope_check=effect);dump(output/'demonstration.json',demo);save_capture(actual,output/'changed-capture')
            workers.append(dict(case='changed',status=changed['status']))
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen input/code changed during run')
        result=dict(status='PASS_SOURCE_GROUP_RHYTHM_CHANGE'if demo else'PASS_SOURCE_GROUP_RHYTHM_NO_CHOICE',facts=len(before['facts']),counts=dict(counts),
            rates={k:dict(v)for k,v in rates.items()},workers=workers,modules=modules,source_hashes_unchanged=True,
            qa1='Development reuse, not fresh.'if freeze is None else'Requires independent preceding random selection receipt.',
            qa2='Complete original captured data exact; actual source-denied same-relationship workers.',
            qa3='Complete source rhythmic groups with relative duration, fixed span and matching-context alternatives. No inferred phrase intent, acoustic sustain or artist-style claim.',
            independent_review='PENDING',native_audio='PENDING',full_rhythm_lever='OPEN')
    except Exception as exc:result=dict(status='FAIL_RETAINED',error=str(exc),traceback=traceback.format_exc())
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('--freeze',type=Path);a=p.parse_args()
    r=run(a.capture,a.output,a.freeze);print(json.dumps({k:v for k,v in r.items()if k not in('modules',)},indent=2));raise SystemExit(r['status']=='FAIL_RETAINED')
