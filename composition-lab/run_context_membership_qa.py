"""One frozen capture: exact inverse plus a deterministic optional context lock.

Retains no eligible lock and failures; never substitutes another song or claims
an audible change. Reuses the existing complete-source gate and isolated worker.
"""
import argparse,json,traceback
from fractions import Fraction as F
from pathlib import Path
from run_declared_chord_qa import run as exact,sha,dump
from run_connected_tier2_qa import bundle
from qa_isolation_harness import execute
from check_complete_source_facts import check as source_check
from check_nominal_harmony import check as context_check
from check_context_membership import check as lock_check
import context_membership as locks
import nominal_harmony as nominal


def run(capture,output,freeze):
    output.mkdir(exist_ok=False,parents=True);frozen=json.loads(freeze.read_text());attempts=[]
    inputs={str(p.resolve()):sha(p)for p in capture.glob('*.json')}
    dump(output/'input-hashes.json',inputs)
    try:
        hashes={**inputs,**frozen['code_hashes'],**frozen.get('native_hashes',{})}
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen input/code drift')
        zero=exact(capture,output/'exact',freeze)
        if zero['status']!='PASS_DECLARED_WRITTEN_CHORD_QA':raise ValueError(zero)
        upper=json.loads((output/'exact/stripped-tier2.json').read_text())
        tier1=json.loads((output/'exact/zero-isolated/worker/output.json').read_text())
        c=nominal.prepare_tier1(tier1);view=nominal.build(c)
        audit=context_check(tier1,view);dump(output/'independent-context.json',audit)
        if audit['status']!='PASS_INDEPENDENT_NOMINAL_HARMONY':raise ValueError(audit)
        selected=None
        for event in sorted(c['events'].values(),key=lambda e:(F(e['onset_q']),e['part_id'],e['id'])):
            request=dict(edited_refs=[event['id']],scope='ensemble_minus_edited')
            result=locks.from_context(c,view,request)
            attempts.append(dict(request=request,status=result['status'],reasons=result['reasons']))
            if result['status']=='SUPPORTED':selected=result['packet'];break
        dump(output/'attempts.json',attempts)
        base=dict(song_id=zero['song_id'],title=zero['title'],notes=zero['note_occurrences'],facts=zero['source_facts'],
            qa1='Fresh only with preregistered selection; unchanged code, no replacement',
            qa2='PASS_ACTUAL_COMPLETE_SOURCE_AND_PAIR_INVERSE',
            qa3='Conditional written support membership; no selected root/key/function or artist-fit claim',
            musical_change=False,creative_gateway='NOT_PASSED')
        if selected is None:
            result=dict(base,status='PASS_EXACT_NO_AVAILABLE_MEMBERSHIP_LOCK',queries=len(attempts))
        else:
            upper['membership_lock']=selected;dump(output/'locked-tier2.json',upper)
            code,modules=bundle(Path(__file__).parent)
            actual=execute(code,upper,dict(variation=0),tier1,output/'locked-isolated',timeout=300)
            if actual['status']!='PASS':raise ValueError(actual)
            rebuilt=json.loads((output/'locked-isolated/worker/output.json').read_text())
            raw=source_check(capture,rebuilt);independent=lock_check(tier1,rebuilt,selected,locks.assess(rebuilt,selected))
            dump(output/'raw-source.json',raw);dump(output/'independent-lock.json',independent)
            if raw['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS' or independent['status']!='PASS_INDEPENDENT_CONTEXT_MEMBERSHIP':raise ValueError(dict(raw=raw,independent=independent))
            result=dict(base,status='PASS_BOUNDED_MEMBERSHIP_LOCK_QA',queries=len(attempts),
                selected_request=selected['request'],contexts=len(selected['contexts']),modules=modules,
                removed=['Tier0 files','Tier1 input','derived views','source/cache access','expected answers'])
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen inputs changed during execution')
    except Exception as exc:
        dump(output/'attempts.json',attempts)
        result=dict(status='FAIL_RETAINED',error=str(exc),traceback=traceback.format_exc())
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args()
    r=run(a.capture,a.output,a.freeze);print(json.dumps({k:v for k,v in r.items()if k not in ('modules','traceback')},indent=2))
    raise SystemExit(1 if r['status']=='FAIL_RETAINED'else 0)
