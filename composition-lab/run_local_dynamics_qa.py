"""Complete source palettes, measured releases and actual shared-inverse edits."""
import argparse,json,traceback
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from run_declared_chord_qa import run as exact,sha,dump
from run_connected_tier2_qa import bundle
from run_voicing_register_qa import save_capture
from qa_isolation_harness import execute
from check_complete_source_facts import check as raw_check
from check_local_dynamics import Oracle
from connected_tier2 import realize
from source_fact_tier1 import project_documents
from run_reversible_tier_qa import extract_documents
import local_dynamics as dynamics

SEEDS=list(range(32))
STRENGTHS=(0,50,100)


def review_scope(target,events,docs):
    """Bound preview length only; never remove a source candidate or its effects."""
    refs=target['influence_refs'];part=target['part_id']
    if not refs or any(r not in events for r in refs):return None
    if type(docs[f'track-{part}.json'].get('instrumentId'))is not int or not 0<=docs[f'track-{part}.json']['instrumentId']<128:return None
    first=min(target['bar'],min(events[r]['bar']for r in refs));last=max(events[r]['bar']for r in refs)
    if last-first>6:return None
    return dict(first=max(1,first-1),last=min(len(docs[f'track-{part}.json']['measures']),last+1),part=part)


def run(capture,output,freeze):
    output.mkdir(parents=True,exist_ok=False);frozen=json.loads(freeze.read_text());ledger=[]
    inputs={str(p.resolve()):sha(p)for p in capture.glob('*.json')}
    dump(output/'plan.json',dict(policy=dynamics.POLICY,seeds=SEEDS,strengths=STRENGTHS,source_hashes=inputs,
        selection='Complete declarations/options; first changed fixed draw in onset/part/ref order whose entire pitched influence fits seven source bars, plus one context bar each side. Review selection only; no source candidate dropped. No song replacement.'))
    try:
        hashes={**inputs,**frozen['code_hashes'],**frozen.get('native_hashes',{})}
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen code/native/input drift')
        zero=exact(capture,output/'zero-and-pair',freeze)
        if zero['status']!='PASS_DECLARED_WRITTEN_CHORD_QA':raise ValueError(zero)
        upper=json.loads((output/'zero-and-pair/stripped-tier2.json').read_text())
        before=json.loads((output/'zero-and-pair/zero-isolated/worker/output.json').read_text())
        save_capture(before,output/'zero-capture')
        view=dynamics.inventory(before);native=Oracle(before);dump(output/'inventory.json',view)
        if view!=native.inventory():raise ValueError('Independent complete dynamic inventory disagrees')
        docs=project_documents(before);events={e['id']:e for e in extract_documents(docs)['events']}
        def order(d):
            times=[F(events[r]['onset_q'])for r in d['influence_refs']if r in events]
            return (min(times)if times else F(10**12),d['part_id'],d['fact_ref'])
        counts=Counter();rates={str(s):Counter()for s in STRENGTHS};demonstration=None
        for target in sorted(view['declarations'],key=order):
            ref=target['fact_ref'];evidence=dynamics.options(before,ref,view);expected=native.choices(ref)
            if evidence['options']!=expected['options']:raise ValueError('Independent dynamic palette differs: '+ref)
            counts['declarations']+=1;counts['eligible_declarations']+=not bool(target['reasons'])
            counts['source_options']+=len(evidence['options']);counts['changed_source_options']+=sum(o['changed']for o in evidence['options'])
            counts['declarations_with_change']+=any(o['changed']for o in evidence['options'])
            clip=review_scope(target,events,docs);draws=[]
            for strength in STRENGTHS:
                for seed in SEEDS:
                    controls=dict(context_policy=dynamics.POLICY,dynamics=strength,target_ref=ref,seed=seed)
                    chosen,decision=dynamics.sample(evidence,controls)
                    rates[str(strength)]['draws']+=1;rates[str(strength)]['released']+=decision['released'];rates[str(strength)]['changed']+=decision['changed']
                    draws.append(dict(strength=strength,seed=seed,decision=decision))
                    if demonstration is None and strength==100 and chosen is not None and chosen['changed'] and clip:
                        demonstration=dict(target=target,chosen=chosen,controls=controls,decision=decision,clip=clip)
            ledger.append(dict(target_ref=ref,evidence=evidence,draws=draws))
        dump(output/'choices.json',ledger)
        code,modules=bundle(Path(__file__).parent)
        explicit_zero=None
        if view['declarations']:
            controls=dict(context_policy=dynamics.POLICY,dynamics=0,target_ref=view['declarations'][0]['fact_ref'],seed=0)
            explicit_zero=execute(code,upper,controls,before,output/'dynamic-zero-isolated',timeout=600,purpose='local_dynamics_intervention')
            if explicit_zero['status']!='PASS':raise ValueError(explicit_zero)
        if demonstration:
            edited,decision=dynamics.intervene(upper,demonstration['controls']);expected=realize(edited)
            audit=native.check(expected,demonstration['target']['fact_ref'],demonstration['chosen']['donor_refs'],decision)
            if audit['status']!='PASS_INDEPENDENT_LOCAL_DYNAMICS':raise ValueError(audit)
            changed=execute(code,upper,demonstration['controls'],expected,output/'changed-isolated',timeout=600,purpose='local_dynamics_intervention')
            if changed['status']!='PASS':raise ValueError(changed)
            actual=json.loads((output/'changed-isolated/worker/output.json').read_text())
            independent=native.check(actual,demonstration['target']['fact_ref'],demonstration['chosen']['donor_refs'],decision)
            if independent['status']!='PASS_INDEPENDENT_LOCAL_DYNAMICS':raise ValueError(independent)
            save_capture(actual,output/'changed-capture')
            demonstration.update(decision=decision,actual_worker_audit=independent)
            dump(output/'demonstration.json',demonstration)
        if raw_check(capture,before)['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError('Source/zero mismatch')
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen dependencies changed during run')
        result=dict(status='PASS_SYMBOLIC_LOCAL_DYNAMICS_CHANGE'if demonstration else'PASS_LOCAL_DYNAMICS_NO_REVIEWABLE_CHANGE',
            song_id=zero['song_id'],title=zero['title'],notes=zero['note_occurrences'],facts=zero['source_facts'],counts=dict(counts),
            rates={k:dict(v)for k,v in rates.items()},explicit_zero=explicit_zero['status']if explicit_zero else'NO_SOURCE_DECLARATION',
            actual_changed=demonstration is not None,modules=modules,
            qa1='Fresh only when linked to preregistered selection; failures/no-choice retained',
            qa2='Actual whole-source/pair/exact-zero and changed inverse when available; no lower/source/cache input',
            qa3='Source declaration influence and observed same-part/voice/scope palette; not intended expression or artist taste',
            native_audio='PENDING',creative_gateway='NOT_PASSED',listening_judgment=None)
    except Exception as exc:
        dump(output/'choices.json',ledger);result=dict(status='FAIL_RETAINED',error=str(exc),traceback=traceback.format_exc())
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args()
    r=run(a.capture,a.output,a.freeze);print(json.dumps({k:v for k,v in r.items()if k not in ('modules','traceback')},indent=2));raise SystemExit(r['status']=='FAIL_RETAINED')
