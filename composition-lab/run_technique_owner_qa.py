"""Complete Tier1 + retained forward parity + bounded typed-owner inverse QA.

Unlifted source facts remain visible; this runner cannot label them a full inverse.
"""
import argparse
import ast
import hashlib
import inspect
import json
from pathlib import Path
import sys
from source_fact_tier1 import extract,ownership_ledger
from check_complete_source_facts import check
from technique_tier2 import analyze,comparable_to_baseline
from technique_observation_relations import realize
from qa_isolation_harness import execute


def run(baselines,output):
    output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
    cases=[]
    for folder in baselines:
        manifest=json.loads((folder/'result.json').read_text(encoding='utf-8'))
        if manifest['status']!='FROZEN_RETAINED_BASELINE':raise ValueError('Retained baseline did not seal')
        for row in manifest['records']:cases.append((folder,row))
    modules=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).suffix=='.py' and root in Path(m.__file__).resolve().parents and 'local-artifacts' not in Path(m.__file__).parts}|{Path(__file__).resolve()})
    files=modules+[p for _,row in cases for p in Path(row['capture']).glob('*.json')]+[folder/row['file'] for folder,row in cases]
    frozen={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (output/'freeze.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
    # Only the lower-Tier validator import is omitted from the executable bundle;
    # all relationship/realization function ASTs are unchanged. No files staged.
    original=(root/'technique_observation_relations.py').read_text(encoding='utf-8')
    parsed=ast.parse(original);parsed.body=[n for n in parsed.body if not isinstance(n,ast.ImportFrom) or n.module!='source_fact_tier1']
    bundle=ast.unparse(parsed)
    before={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
    after={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(bundle).body if isinstance(n,ast.FunctionDef)}
    if before!=after:raise ValueError('Bundled SAME relationship functions changed')
    bundle+='''
def reconstruct(model,controls):
    if controls!={'variation':0} or type(controls['variation']) not in (int,float):raise ValueError('Explicit locked controls required')
    return realize(model)
'''
    results=[]
    for ordinal,(folder,row) in enumerate(cases):
        directory=output/str(ordinal);directory.mkdir();capture=Path(row['capture'])
        baseline_path=folder/row['file']
        if hashlib.sha256(baseline_path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Frozen retained output changed')
        lower=extract(capture);source=check(capture,lower);upper=analyze(lower)
        parity=comparable_to_baseline(upper,json.loads(baseline_path.read_text(encoding='utf-8')))
        model=upper['technique_observations'];actual=realize(model);owned={r['id'] for r in actual}
        expected=[r for r in lower['facts'] if r['id'] in owned]
        exact=json.dumps(actual,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False)
        isolated=execute(bundle,model,dict(variation=0),expected,directory/'isolated',timeout=120)
        ledger=ownership_ledger(lower)
        for item in ledger:
            if item['fact_ref'] in owned:item.update(owner='T2:registered_technique_observations',disposition='same_typed_source_unit_relationship')
        (directory/'ownership-ledger.json').write_text(json.dumps(ledger,indent=2),encoding='utf-8')
        # The source is nested ONCE. Relationship output excludes full legacy rows.
        (directory/'tier2.json').write_text(json.dumps(upper,indent=2),encoding='utf-8')
        result=dict(capture=str(capture),complete_tier1_source=source,exact_retained_forward_parity=parity,registered_owner_exact_inverse=exact,registered_owner_isolated_inverse=isolated,total_source_facts=len(lower['facts']),lifted_technique_facts=len(owned),unlifted_source_facts=len(lower['facts'])-len(owned),unsupported_technique_structures=model['unsupported'],registered_technique_groups=len(model['groups']),full_tier1_inverse='NOT_COMPLETE_UNLIFTED_OWNERS_REMAIN')
        result['bounded_status']='PASS' if source['status']=='PASS_COMPLETE_CAPTURED_JSON_FACTS' and parity and exact and isolated['status']=='PASS' else 'FAIL'
        (directory/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');results.append(result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('registered_owner_isolated_inverse','complete_tier1_source')}),flush=True)
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
    report=dict(status='PASS_BOUNDED_TECHNIQUE_OWNERS' if unchanged and all(r['bounded_status']=='PASS' for r in results) else 'FAIL',unchanged=unchanged,results=results,same_function_asts=True,full_integration='INCOMPLETE_OTHER_SOURCE_OWNERS_AND_UNIFIED_MUSICAL_CONTEXT_PENDING',gate3='PENDING_PLANNER_SOURCE_CONTRAST_REVIEW')
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('baselines',nargs='+',type=Path);a=p.parse_args();run(a.baselines,a.output)
