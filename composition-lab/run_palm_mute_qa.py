"""Whole-source palm-mute policy QA; keep failures and no-choice cases."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import argparse,hashlib,json,traceback
from source_fact_tier1 import extract,extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,validate
from check_complete_source_facts import check as check_source_capture
from check_palm_mute_artifacts import check_source,source_beat
from run_connected_tier2_qa import bundle
from run_voicing_register_qa import save_capture
from qa_isolation_harness import execute
import local_palm_mutes as mute


def dump(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_answer(before,target,chosen):
    """Parent-only expected output from captured declarations, never the owner."""
    if chosen is None:return deepcopy(before)
    docs=project_documents(before)
    for ref,state in zip(target['beat_refs'],chosen['states']):
        beat=source_beat(docs,ref)
        if state=={'kind':'absent'}:beat.pop('palmMute',None)
        else:beat['palmMute']=state['value']
    return extract_documents(docs)


def run(capture,output,freeze=None):
    output.mkdir(parents=True,exist_ok=False);seeds=list(range(32));strengths=[0,50,100]
    source_hashes={str(p.resolve()):sha(p)for p in capture.glob('*.json')};hashes=dict(source_hashes)
    try:
        if freeze is not None:
            frozen=json.loads(freeze.read_bytes());hashes.update(frozen['code_hashes']);hashes.update(frozen.get('native_hashes',{}))
            if frozen['policy']!=mute.POLICY and mute.POLICY not in frozen.get('lever_policies',[]):raise ValueError('Declared palm-mute policy freeze required')
            controls=frozen['controls']
            if controls['strengths']!=strengths or controls.get('palm_mute_seeds',controls.get('seeds'))!=seeds:raise ValueError('Frozen percentage/seed protocol differs')
    except Exception as exc:
        result=dict(status='FAIL_RETAINED',phase='frozen_protocol',error=str(exc),traceback=traceback.format_exc())
        dump(output/'result.json',result);return result
    dump(output/'plan.json',dict(policy=mute.POLICY,source_hashes=source_hashes,hashes=hashes,freeze=str(freeze)if freeze else None,seeds=seeds,strengths=strengths,
        selection='All original coattacks and source alternatives. First source-ordered on/off changed draw at100. No alternative source search or note selection.'))
    try:
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen source/code changed')
        before=extract(capture);full=analyze(before,palm_mute_slots=True,note_accent_slots=True,rhythm_groups=True,rhythm_group_profile='written_time')
        if validate(full)!=before:raise ValueError('Full forward/reverse mismatch')
        upper=strip_lower(full);dump(output/'stripped-tier2.json',upper);code,modules=bundle(Path(__file__).parent)
        view=mute.inventory(before);dump(output/'inventory.json',view)
        zero_controls=dict(variation=0)if not view['coattacks']else dict(context_policy=mute.POLICY,palm_mute=0,target_ref=view['coattacks'][0]['coattack_ref'],seed=0)
        zero_purpose='exact_zero'if not view['coattacks']else'local_palm_mute_intervention'
        zero=execute(code,upper,zero_controls,before,output/'zero-isolated',timeout=900,purpose=zero_purpose)
        if zero['status']!='PASS':raise ValueError(zero)
        actual=json.loads((output/'zero-isolated/worker/output.json').read_bytes());parity=check_source_capture(capture,actual);dump(output/'source-comparison.json',parity)
        if parity['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError(parity)
        save_capture(actual,output/'zero-capture')
        counts=Counter();rates={str(s):Counter()for s in strengths};demo=None;no_choice=None
        with(output/'choices.jsonl').open('w',encoding='utf-8')as handle,(output/'draws.jsonl').open('w',encoding='utf-8')as draw_handle:
            for row in view['coattacks']:
                evidence=mute.options(before,row['coattack_ref'],view);handle.write(json.dumps(evidence)+'\n')
                counts['coattacks']+=1;counts['eligible']+=not bool(row['reasons']);counts[evidence['status']]+=1
                counts['with_on_off_choices']+=any(o['mute_changed']for o in evidence['options'])
                if no_choice is None and not evidence['options']:no_choice=row
                draws=[]
                for strength in strengths:
                    for seed in seeds:
                        controls=dict(context_policy=mute.POLICY,palm_mute=strength,target_ref=row['coattack_ref'],seed=seed)
                        chosen,decision=mute.sample(evidence,controls);rate=rates[str(strength)]
                        rate['draws']+=1;rate['released']+=decision['released'];rate['changed']+=decision['changed'];rate['mute_changed']+=decision['mute_changed']
                        draws.append(dict(strength=strength,seed=seed,chosen_index=evidence['options'].index(chosen)if chosen is not None else None,decision=decision))
                        if demo is None and strength==100 and decision['mute_changed']:
                            demo=dict(target=row,chosen=chosen,controls=controls,decision=decision,
                                clip=dict(first=max(1,min(int(r.split(':')[3])for r in row['member_refs'])-1),last=max(int(r.split(':')[3])for r in row['member_refs'])+1,part=row['part_id']))
                draw_handle.write(json.dumps(dict(target_ref=row['coattack_ref'],draws=draws))+'\n')
        workers=[dict(case='zero',status=zero['status'])]
        if no_choice is not None:
            controls=dict(context_policy=mute.POLICY,palm_mute=100,target_ref=no_choice['coattack_ref'],seed=0)
            receipt=execute(code,upper,controls,before,output/'no-choice-isolated',timeout=900,purpose='local_palm_mute_intervention')
            if receipt['status']!='PASS':raise ValueError(receipt)
            workers.append(dict(case='no-choice',status=receipt['status']))
        if demo is not None:
            evidence=mute.options(before,demo['target']['coattack_ref'],view);variant_receipts=[]
            for strength,name in((50,'half-isolated'),(100,'changed-isolated')):
                controls=dict(demo['controls'],palm_mute=strength);chosen,decision=mute.sample(evidence,controls)
                expected=raw_answer(before,demo['target'],chosen)
                receipt=execute(code,upper,controls,expected,output/name,timeout=900,purpose='local_palm_mute_intervention')
                if receipt['status']!='PASS':raise ValueError(receipt)
                actual=json.loads((output/name/'worker/output.json').read_bytes())
                independent=check_source(before,actual,dict(target=demo['target'],chosen=chosen))if chosen else dict(status='EXACT_UNRELEASED_SOURCE',same=actual==before)
                if independent['status']not in('PASS_INDEPENDENT_PALM_MUTE_SOURCE_SCOPE','EXACT_UNRELEASED_SOURCE'):raise ValueError(independent)
                variant_receipts.append(dict(strength=strength,controls=controls,decision=decision,source_check=independent))
                workers.append(dict(case=name,status=receipt['status']))
                if strength==100:save_capture(actual,output/'changed-capture');demo['independent_source_check']=independent
            demo['variants']=variant_receipts;dump(output/'demonstration.json',demo)
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen input/code changed during run')
        result=dict(status='PASS_SOURCE_PALM_MUTE_CHANGE'if demo else'PASS_SOURCE_PALM_MUTE_NO_CHOICE',facts=len(before['facts']),counts=dict(counts),
            rates={k:dict(v)for k,v in rates.items()},workers=workers,modules=modules,source_hashes_unchanged=True,
            qa1='Fixed-source development only.'if freeze is None else'Requires independently checked preceding random-selection receipt.',
            qa2='Actual source-denied policy workers; complete captured JSON parity and independent actual changed-source scope.',
            qa3='Source-observed complete-coattack muting alternatives with all other written facts locked; no artist preference claim.',
            independent_all_options_review='PENDING',native_gp_midi_audio='PENDING',authentic_muted_timbre='NOT_ESTABLISHED',full_palm_mute_lever='OPEN')
    except Exception as exc:result=dict(status='FAIL_RETAINED',error=str(exc),traceback=traceback.format_exc())
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('--freeze',type=Path);a=p.parse_args()
    result=run(a.capture,a.output,a.freeze);print(json.dumps({k:v for k,v in result.items()if k!='modules'},indent=2));raise SystemExit(result['status']=='FAIL_RETAINED')
