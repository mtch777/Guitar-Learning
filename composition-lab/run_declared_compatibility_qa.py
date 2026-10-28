"""Replay ACTUAL old upper/pair inputs under current code; no reanalysis repair."""
import argparse
import json
from pathlib import Path
import traceback
from run_declared_chord_qa import sha,dump,PAIR_RECONSTRUCTOR
from run_connected_tier2_qa import bundle
from qa_isolation_harness import execute
from check_complete_source_facts import check as facts_check
from check_declared_chord_ownership import check as degree_check,_Capture
from connected_tier2 import validate


def run(previous,output,freeze):
    output.mkdir(parents=True,exist_ok=False)
    frozen=json.loads(freeze.read_text());sources=json.loads((previous/'source-hashes.json').read_text())
    paths=[previous/'stripped-tier2.json',previous/'pair-isolated/worker/input.json',
           previous/'zero-isolated/worker/output.json',previous/'pair-isolated/worker/output.json',
           previous/'zero-isolated/worker/input.json',previous/'zero-isolated/freeze.json',previous/'pair-isolated/freeze.json']
    hashes={**sources,**{str(p.resolve()):sha(p) for p in paths},**frozen['code_hashes']}
    dump(output/'tested-hashes.json',hashes)
    try:
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen input/code hash conflict')
        upper=json.loads(paths[0].read_text());pair_input=json.loads(paths[1].read_text())['upper']
        if json.loads(paths[4].read_text())['upper']!=upper:raise ValueError('Historical whole worker input differs from saved upper')
        expected=json.loads(paths[2].read_text());pair_expected=json.loads(paths[3].read_text())
        if pair_input['musical_relationships']!=upper['musical_relationships']:raise ValueError('Historical pair/whole input disagreement')
        validate(upper)
        code,modules=bundle(Path(__file__).parent.resolve())
        zero=execute(code,upper,{'variation':0},expected,output/'zero-isolated',timeout=180)
        pair=execute(code+PAIR_RECONSTRUCTOR,pair_input,{'variation':0},pair_expected,output/'pair-isolated',timeout=180)
        if zero['status']!='PASS' or pair['status']!='PASS':raise ValueError(dict(zero=zero,pair=pair))
        actual=json.loads((output/'zero-isolated/worker/output.json').read_text())
        docs={Path(p).name:json.loads(Path(p).read_text(encoding='utf-8-sig')) for p in sources}
        raw=facts_check(_Capture(docs),actual);independent=degree_check(docs,upper,actual)
        dump(output/'raw-source-check.json',raw);dump(output/'independent-degree-check.json',independent)
        if raw['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS' or independent['issues']:raise ValueError(dict(raw=raw,independent=independent))
        if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen input/code changed during replay')
        result=dict(status='PASS_ACTUAL_SAVED_REPRESENTATION',previous=str(previous),counts=independent['counts'],zero=zero,pair=pair,modules=modules)
    except Exception as error:result=dict(status='FAIL_RETAINED',error=str(error),traceback=traceback.format_exc())
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('previous',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args()
    r=run(a.previous,a.output,a.freeze)
    print(json.dumps({k:v[:600] if k=='error' else v for k,v in r.items() if k in ('status','counts','error')}),flush=True)
    raise SystemExit(0 if r['status']=='PASS_ACTUAL_SAVED_REPRESENTATION' else 1)
