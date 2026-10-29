"""Complete source inventories, source-only choices, and isolated same inverse."""
import argparse,hashlib,json,traceback
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from source_fact_tier1 import extract
from connected_tier2 import analyze,strip_lower,validate,realize
from check_complete_source_facts import check as raw_check
from check_local_accents import Oracle
from run_connected_tier2_qa import bundle
from run_declared_chord_qa import dump,sha
from run_voicing_register_qa import save_capture
from qa_isolation_harness import execute
import local_accents as accents

SEEDS=list(range(32));STRENGTHS=(0,50,100)


def run(capture,output,freeze):
    output.mkdir(parents=True,exist_ok=False);frozen=json.loads(freeze.read_text());inputs={str(p.resolve()):sha(p)for p in capture.glob('*.json')}
    dump(output/'plan.json',dict(policy=accents.POLICY,seeds=SEEDS,strengths=STRENGTHS,source_hashes=inputs,freeze=str(freeze.resolve()),
        selection='Every original note/context and option checked. First source-time-ordered changed sound-level draw at100%, seeds0..31. One adjacent source bar each side. No song replacement; no-choice retained.'))
    try:
        if frozen['policy']!=accents.POLICY:raise ValueError('Frozen accent policy required')
        hashes={**inputs,**frozen['code_hashes'],**frozen.get('native_hashes',{})}
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen dependencies drifted')
        before=extract(capture);upper=analyze(before,note_accent_slots=True)
        if validate(upper)!=before:raise ValueError('Forward/backward pair failed')
        stripped=strip_lower(upper);code,modules=bundle(Path(__file__).parent)
        dump(output/'stripped-tier2.json',stripped)
        zero=execute(code,stripped,{'variation':0},before,output/'zero-and-pair/zero-isolated',timeout=600)
        if zero['status']!='PASS':raise ValueError(zero)
        actual=json.loads((output/'zero-and-pair/zero-isolated/worker/output.json').read_text())
        raw=raw_check(capture,actual);dump(output/'complete-source-check.json',raw)
        if raw['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError(raw)
        save_capture(actual,output/'zero-capture')
        view=accents.inventory(before);oracle=Oracle(before);dump(output/'inventory.json',view)
        if view!=oracle.inventory():raise ValueError('Complete independent source inventory differs')
        counts=Counter();rates={str(s):Counter()for s in STRENGTHS};draw_hash=hashlib.sha256();demo=None;no_choice=None
        rows=sorted(view['occurrences'],key=lambda r:(r['bar'],F(r['position_q']),r['part_id'],r['voice'],r['beat'],r['note']))
        with(output/'choices.jsonl').open('w',encoding='utf-8')as choices:
            for row in rows:
                ref=row['occurrence_ref'];evidence=accents.options(before,ref,view)
                if evidence!=oracle.options(ref):raise ValueError('Independent option inventory differs: '+ref)
                choices.write(json.dumps(evidence,allow_nan=False)+'\n')
                counts['note_objects']+=1;counts['qualified_notes']+=not bool(row['reasons'])
                counts['options']+=len(evidence['options']);counts['targets_with_changed_notation']+=any(o['changed']for o in evidence['options'])
                counts['targets_with_changed_sound_level']+=any(o['sound_level']!=row['sound_level']for o in evidence['options'])
                if no_choice is None and not evidence['options']:no_choice=row
                for strength in STRENGTHS:
                    for seed in SEEDS:
                        c=dict(context_policy=accents.POLICY,accents=strength,target_ref=ref,seed=seed)
                        chosen,decision=accents.sample(evidence,c)
                        audit=oracle.check_sample(ref,c,chosen,decision)
                        if audit['status']!='PASS_INDEPENDENT_LOCAL_ACCENT_SAMPLE':raise ValueError(audit)
                        rates[str(strength)]['draws']+=1;rates[str(strength)]['released']+=decision['released'];rates[str(strength)]['changed_notation']+=decision['changed']
                        rates[str(strength)]['changed_sound_level']+=bool(chosen is not None and chosen['sound_level']!=row['sound_level'])
                        draw_hash.update((json.dumps(dict(controls=c,decision=decision),sort_keys=True,separators=(',',':'))+'\n').encode())
                        if demo is None and strength==100 and chosen is not None and chosen['sound_level']!=row['sound_level']:
                            from source_fact_tier1 import project_documents
                            doc=project_documents(before)[f"track-{row['part_id']}.json"]
                            demo=dict(target=row,chosen=chosen,controls=c,decision=decision,clip=dict(first=max(1,row['bar']-1),last=min(len(doc['measures']),row['bar']+1),part=row['part_id']))
        actual_reports=[]
        for name,row,strength in [('explicit-zero',rows[0]if rows else None,0),('no-choice',no_choice,100)]:
            if row is None:continue
            c=dict(context_policy=accents.POLICY,accents=strength,target_ref=row['occurrence_ref'],seed=0)
            edited,decision=accents.intervene(stripped,c);expected=realize(edited)
            if expected!=before:raise ValueError('Zero/no-choice changed source')
            result=execute(code,stripped,c,before,output/(name+'-isolated'),timeout=600,purpose='local_accents_intervention')
            if result['status']!='PASS':raise ValueError(result)
            actual_reports.append(dict(case=name,status=result['status']))
        if demo:
            edited,decision=accents.intervene(stripped,demo['controls']);expected=realize(edited)
            audit=oracle.check(expected,demo['target']['occurrence_ref'],demo['chosen']['donor_refs'],decision)
            if audit['status']!='PASS_INDEPENDENT_LOCAL_ACCENTS':raise ValueError(audit)
            changed=execute(code,stripped,demo['controls'],expected,output/'changed-isolated',timeout=600,purpose='local_accents_intervention')
            if changed['status']!='PASS':raise ValueError(changed)
            actual=json.loads((output/'changed-isolated/worker/output.json').read_text())
            audit=oracle.check(actual,demo['target']['occurrence_ref'],demo['chosen']['donor_refs'],decision)
            if audit['status']!='PASS_INDEPENDENT_LOCAL_ACCENTS':raise ValueError(audit)
            demo.update(decision=decision,actual_worker_audit=audit);dump(output/'demonstration.json',demo);save_capture(actual,output/'changed-capture')
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Dependencies changed during run')
        metadata=json.loads((capture/'metadata.json').read_text(encoding='utf-8-sig'))
        result=dict(status='PASS_SYMBOLIC_LOCAL_ACCENTS_CHANGE'if demo else'PASS_LOCAL_ACCENTS_NO_CHANGE',song_id=metadata['songId'],title=metadata.get('title'),
            facts=len(before['facts']),counts=dict(counts),rates={k:dict(v)for k,v in rates.items()},draw_ledger_sha256=draw_hash.hexdigest(),actual_workers=actual_reports,modules=modules,
            qa1='Fresh only when independently linked to preregistered selection; development reuse is not fresh.',
            qa2='Complete facts/order exact via actual isolated inverse; actual zero/no-choice and changed worker when available.',
            qa3='Source-observed attack emphasis conditioned on part/voice/dynamic/meter/position/duration; explicit interaction exclusions. No phrase intent, artist or emotional claim.',
            native_audio='PENDING',creative_gateway='NOT_PASSED',listening_judgment=None)
    except Exception as exc:result=dict(status='FAIL_RETAINED',error=str(exc),traceback=traceback.format_exc())
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args()
    r=run(a.capture,a.output,a.freeze);print(json.dumps({k:v for k,v in r.items()if k not in('modules','traceback')},indent=2));raise SystemExit(r['status']=='FAIL_RETAINED')
