"""Complete frozen-source, component-conditioned tempo experiment QA."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import argparse,hashlib,json,traceback
from source_fact_tier1 import extract,extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,validate
from check_complete_source_facts import check as check_source_capture
from run_connected_tier2_qa import bundle
from run_voicing_register_qa import save_capture
from qa_isolation_harness import execute
import local_step_tempos as tempo


def dump(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_answer(before,target,chosen):
    """Parent-only expected output from original JSON paths, never the tempo owner."""
    if chosen is None:return deepcopy(before)
    docs=project_documents(before);bpm=F(chosen['quarter_bpm'])
    if bpm.denominator!=1 or bpm<=0:raise ValueError('Positive integer source BPM required')
    for ref in target['bpm_refs']:
        name,pointer=ref.split('#',1);parts=[s.replace('~1','/').replace('~0','~')for s in pointer[1:].split('/')];value=docs[name]
        for key in parts[:-1]:value=value[int(key)]if type(value)is list else value[key]
        key=parts[-1];key=int(key)if type(value)is list else key
        if type(value[key])is not int:raise ValueError('Original BPM must retain its integer source type')
        value[key]=bpm.numerator
    return extract_documents(docs)


def clip_for(target,view,before):
    docs=project_documents(before);last=max((len(v.get('measures',[]))for name,v in docs.items()if name.startswith('track-')),default=target['bar'])
    following=next((r for r in view['clock']['global_events']if r['onset_q']==target['end_q']),None)
    return dict(first=max(1,target['bar']-1),last=min(last,following['bar']+1)if following else last,
        part=int(target['component_ref'].split(':')[1]),source_interval_q=[target['onset_q'],target['end_q']])


def run(capture,output,freeze=None):
    output.mkdir(parents=True,exist_ok=False);seeds=list(range(32));strengths=[0,50,100]
    source_hashes={str(p.resolve()):sha(p)for p in capture.glob('*.json')};hashes=dict(source_hashes)
    try:
        if freeze is not None:
            frozen=json.loads(freeze.read_bytes());hashes.update(frozen['code_hashes']);hashes.update(frozen.get('native_hashes',{}))
            if frozen['policy']!=tempo.POLICY and tempo.POLICY not in frozen.get('lever_policies',[]):raise ValueError('Declared tempo policy freeze required')
            controls=frozen['controls']
            if controls['strengths']!=strengths or controls.get('tempo_seeds',controls.get('seeds'))!=seeds:raise ValueError('Frozen percentage/seed protocol differs')
    except Exception as exc:
        result=dict(status='FAIL_RETAINED',phase='frozen_protocol',error=str(exc),traceback=traceback.format_exc())
        dump(output/'result.json',result);return result
    dump(output/'plan.json',dict(policy=tempo.POLICY,source_hashes=source_hashes,hashes=hashes,freeze=str(freeze)if freeze else None,seeds=seeds,strengths=strengths,
        selection='Every original global-event/part/voice component and all source alternatives. First source-ordered actual BPM change at100. No replacement source or manually chosen figure.',
        evidence_label='PARTIAL',native_execution_and_human_fit='Separate verification required.'))
    try:
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen source/code changed')
        before=extract(capture);full=analyze(before,step_tempos=True,palm_mute_slots=True,note_accent_slots=True,rhythm_groups=True,rhythm_group_profile='written_time')
        if validate(full)!=before:raise ValueError('Full forward/reverse mismatch')
        upper=strip_lower(full);dump(output/'stripped-tier2.json',upper);code,modules=bundle(Path(__file__).parent)
        view=tempo.inventory(before);dump(output/'inventory.json',view)
        rows=view['choices']['A_passage_speed']['components']
        first=rows[0]if rows else None
        zero_controls=dict(variation=0)if first is None else dict(context_policy=tempo.POLICY,tempo=0,target_ref=first['event_id'],component_ref=tempo.component_id(first['part_id'],first['voice']),seed=0)
        zero=execute(code,upper,zero_controls,before,output/'zero-isolated',timeout=900,purpose='exact_zero'if first is None else'local_step_tempo_intervention')
        if zero['status']!='PASS':raise ValueError(zero)
        actual=json.loads((output/'zero-isolated/worker/output.json').read_bytes());parity=check_source_capture(capture,actual);dump(output/'source-comparison.json',parity)
        if parity['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError(parity)
        save_capture(actual,output/'zero-capture')
        counts=Counter();rates={str(s):Counter()for s in strengths};demo=None;no_choice=None
        with(output/'choices.jsonl').open('w',encoding='utf-8')as handle,(output/'draws.jsonl').open('w',encoding='utf-8')as draw_handle:
            for row in rows:
                ref=tempo.component_id(row['part_id'],row['voice']);evidence=tempo.options(before,row['event_id'],ref,view);handle.write(json.dumps(evidence)+'\n')
                counts['components']+=1;counts[evidence['status']]+=1;counts['with_choices']+=bool(evidence['options'])
                if no_choice is None and not evidence['options']:no_choice=(row['event_id'],ref)
                draws=[]
                for strength in strengths:
                    for seed in seeds:
                        controls=dict(context_policy=tempo.POLICY,tempo=strength,target_ref=row['event_id'],component_ref=ref,seed=seed)
                        chosen,decision=tempo.sample(evidence,controls);rate=rates[str(strength)]
                        rate['draws']+=1;rate['released']+=decision['released'];rate['changed']+=decision['changed']
                        draws.append(dict(strength=strength,seed=seed,chosen_index=evidence['options'].index(chosen)if chosen is not None else None,decision=decision))
                        if demo is None and strength==100 and decision['changed']:
                            demo=dict(target=evidence['target'],chosen=chosen,controls=controls,decision=decision,
                                clip=clip_for(evidence['target'],view,before),evidence_label='PARTIAL')
                draw_handle.write(json.dumps(dict(target_ref=row['event_id'],component_ref=ref,draws=draws))+'\n')
        workers=[dict(case='zero',status=zero['status'])]
        if no_choice is not None:
            controls=dict(context_policy=tempo.POLICY,tempo=100,target_ref=no_choice[0],component_ref=no_choice[1],seed=0)
            receipt=execute(code,upper,controls,before,output/'no-choice-isolated',timeout=900,purpose='local_step_tempo_intervention')
            if receipt['status']!='PASS':raise ValueError(receipt)
            workers.append(dict(case='no-choice',status=receipt['status']))
        if demo is not None:
            evidence=tempo.options(before,demo['controls']['target_ref'],demo['controls']['component_ref'],view);variants=[]
            for strength,name in((50,'half-isolated'),(100,'changed-isolated')):
                controls=dict(demo['controls'],tempo=strength);chosen,decision=tempo.sample(evidence,controls)
                expected=raw_answer(before,demo['target'],chosen)
                receipt=execute(code,upper,controls,expected,output/name,timeout=900,purpose='local_step_tempo_intervention')
                if receipt['status']!='PASS':raise ValueError(receipt)
                actual=json.loads((output/name/'worker/output.json').read_bytes())
                if actual!=expected:raise ValueError('Actual isolated output differs from raw source expectation')
                from check_step_tempo_artifacts import check_source
                independent=check_source(before,actual,dict(target=demo['target'],chosen=chosen))if chosen is not None else dict(status='EXACT_UNRELEASED_SOURCE',same=actual==before)
                if independent['status']not in('PASS_INDEPENDENT_STEP_TEMPO_SOURCE_SCOPE','EXACT_UNRELEASED_SOURCE'):raise ValueError(independent)
                variants.append(dict(strength=strength,controls=controls,decision=decision,source_comparison='PASS_ALL_TYPED_SOURCE_FACTS',independent_source_check=independent))
                workers.append(dict(case=name,status=receipt['status']))
                if strength==100:save_capture(actual,output/'changed-capture')
            demo['variants']=variants;dump(output/'demonstration.json',demo)
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen input/code changed during run')
        result=dict(status='PASS_PARTIAL_SOURCE_COMPONENT_TEMPO_CHANGE'if demo else'PASS_SOURCE_TEMPO_NO_CHOICE',facts=len(before['facts']),counts=dict(counts),
            rates={k:dict(v)for k,v in rates.items()},workers=workers,modules=modules,source_hashes_unchanged=True,
            qa1='Fixed-source development only.'if freeze is None else'Requires independently checked preceding random-selection receipt.',
            qa2='Actual source-denied policy workers; full captured JSON parity. Changed expectation uses raw source paths, not the tempo owner.',
            qa3='PARTIAL source rhythm-conditioned speed evidence; all other written facts locked. Full-band consensus, transition suitability and whole-lifetime fit are not established.',
            independent_all_options_review='PENDING',native_gp_midi_audio='PENDING',human_fit='NOT_ESTABLISHED',full_tempo_lever='OPEN')
    except Exception as exc:result=dict(status='FAIL_RETAINED',error=str(exc),traceback=traceback.format_exc())
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('--freeze',type=Path);a=p.parse_args()
    result=run(a.capture,a.output,a.freeze);print(json.dumps({k:v for k,v in result.items()if k!='modules'},indent=2));raise SystemExit(result['status']=='FAIL_RETAINED')
