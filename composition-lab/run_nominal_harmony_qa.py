"""Actual isolated whole-source inverse and written-context recomputation."""
import argparse
import hashlib
import json
from pathlib import Path
from connected_tier2 import analyze,strip_lower
from source_fact_tier1 import extract
from check_complete_source_facts import check as check_source
from nominal_harmony import analyze as context,prepare
from check_nominal_harmony import check
from qa_isolation_harness import execute
from run_connected_tier2_qa import bundle as existing_bundle


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,v):path.write_text(json.dumps(v,indent=2),encoding='utf-8')


def bundle(root):
    code,hashes=existing_bundle(root)
    for name in ('harmonic_evidence','nominal_harmony'):
        source=(root/(name+'.py')).read_text(encoding='utf-8-sig')
        code+=f"_m=types.ModuleType({name!r});sys.modules[{name!r}]=_m\nexec(compile({source!r},{name!r},'exec'),_m.__dict__)\n"
        hashes[name]=hashlib.sha256(source.encode()).hexdigest()
    code+='''
def reconstruct(upper,controls):
 if controls != {'variation':0}:raise ValueError('No creative activation in this gate')
 return sys.modules['nominal_harmony'].analyze(upper)
'''
    return code,hashes


def run(capture,output,freeze,upper_path=None):
    output.mkdir(parents=True,exist_ok=False);frozen=json.loads(freeze.read_text());root=Path(__file__).parent
    inputs={str(p.resolve()):sha(p) for p in capture.glob('*.json')}
    if upper_path:inputs[str(upper_path.resolve())]=sha(upper_path)
    dump(output/'input-hashes.json',inputs)
    try:
        hashes={**frozen['code_hashes'],**frozen.get('native_hashes',{})}
        if any(sha(p)!=h for p,h in hashes.items()):raise ValueError('Frozen code/native dependency drift')
        lower=extract(capture);upper=json.loads(upper_path.read_text()) if upper_path else strip_lower(analyze(lower,declared_chords=True))
        c=prepare(upper)
        if check_source(capture,c['before'])['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError('Existing owner differs from actual source')
        view=context(upper);independent=check(lower,view)
        dump(output/'native.json',independent);dump(output/'stripped-tier2.json',upper);dump(output/'context.json',view)
        if independent['status']!='PASS_INDEPENDENT_NOMINAL_HARMONY':raise ValueError(independent)
        zero_code,_=existing_bundle(root);zero=execute(zero_code,upper,dict(variation=0),lower,output/'zero-isolated',timeout=300)
        if zero['status']!='PASS':raise ValueError(zero)
        actual=json.loads((output/'zero-isolated/worker/output.json').read_text())
        raw=check_source(capture,actual);dump(output/'raw-source-check.json',raw)
        if raw['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError('Actual zero differs from source')
        code,modules=bundle(root);pair=execute(code,upper,dict(variation=0),view,output/'context-isolated',timeout=300)
        if pair['status']!='PASS':raise ValueError(pair)
        rebuilt=json.loads((output/'context-isolated/worker/output.json').read_text())
        independent_rebuilt=check(actual,rebuilt);dump(output/'independent-worker-check.json',independent_rebuilt)
        if independent_rebuilt['status']!='PASS_INDEPENDENT_NOMINAL_HARMONY':raise ValueError(independent_rebuilt)
        if any(sha(p)!=h for p,h in {**inputs,**hashes}.items()):raise ValueError('Source/code drift during gate')
        result=dict(status='PASS_BOUNDED_NOMINAL_HARMONY_QA',source_facts=len(lower['facts']),counts=view['counts'],
            qa1='Development replay unless linked to preregistered fresh selection',
            qa2=dict(whole_source=zero['status'],same_context=pair['status'],actual_raw_source=raw['status']),
            qa3=dict(independent_native=independent_rebuilt['status'],scope='Written simultaneous populations and conditional note roles; no selected chord path, key, mode, intent or creative permission'),
            modules=modules,removed=['Tier0 source files','Tier1 payload','Derived context caches','Expected answers','Source/cache filesystem access'],
            retained='Existing stripped Tier2 owners; no second note stream. Conditional hypotheses are recomputed, not claimed sufficient alone for exact recovery.')
    except Exception as exc:result=dict(status='FAIL_RETAINED',error=repr(exc))
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);p.add_argument('--upper',type=Path);a=p.parse_args()
    r=run(a.capture,a.output,a.freeze,a.upper);print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='PASS_BOUNDED_NOMINAL_HARMONY_QA' else 1)
