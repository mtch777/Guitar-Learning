"""Authored diagnostic only: no inferred key, reference accuracy or generation."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
from musical_tier2 import analyze,strip_lower
from test_tonal_order_blindspot import counterexample,query
from qa_isolation_harness import execute
from check_harmonic_span_source import check


def run(output):
    root=Path(__file__).resolve().parent
    paths=[Path(__file__),root/'test_tonal_order_blindspot.py',root/'musical_tier2.py',root/'check_harmonic_span_source.py',root/'qa_isolation_harness.py']
    hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    output.mkdir(parents=True,exist_ok=False)
    code=(root/'musical_tier2.py').read_text(encoding='utf-8')+'\n'+inspect.getsource(query)+'''
_exact_reconstruct=reconstruct
def reconstruct(upper,controls):
    return dict(tier1=_exact_reconstruct(upper,controls),query=query(upper))
'''
    rows=[]
    for reverse in (False,True):
        lower=counterexample(reverse);upper=strip_lower(analyze(lower));result=query(upper)
        raw=[tuple(e[k] for k in ('part_id','bar','pitch','onset_q','duration_q')) for e in lower['events']]
        oracle=check(raw,result['harmonic'])
        isolated=execute(code,upper,dict(variation=0),dict(tier1=lower,query=result),output/str(int(reverse)),timeout=60)
        rows.append(dict(authored_order='Cmajor E7 Aminor' if reverse else 'Aminor E7 Cmajor',query=result,independent_harmonic_arithmetic=oracle,isolated_same_relations=isolated))
    equal={k:rows[0]['query'][k]==rows[1]['query'][k] for k in ('histogram','global_scores','raw_temporal','smoothed_temporal')}
    changed=rows[0]['query']['harmonic']['all_optimal_path_cell_consensus'][0]['candidate_labels']!=rows[1]['query']['harmonic']['all_optimal_path_cell_consensus'][0]['candidate_labels']
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in hashes.items())
    passed=unchanged and all(equal.values()) and changed and all(r[k]['status']=='PASS' for r in rows for k in ('independent_harmonic_arithmetic','isolated_same_relations'))
    report=dict(status='PASS_DIAGNOSTIC' if passed else 'FAIL',frozen_code=hashes,unchanged=unchanged,tonal_invariances=equal,harmonic_direction_distinguished=changed,rows=rows,conclusion='Current global and within-measure temporal key evidence cannot distinguish these different ordered harmonies. Full harmonic context DOES retain the difference. No true key or preferred order is asserted; no learned repair or musical-quality result.')
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();raise SystemExit(0 if run(a.output)['status']=='PASS_DIAGNOSTIC' else 1)
