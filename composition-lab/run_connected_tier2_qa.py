"""Frozen full-source integration QA; no source or expected answers in worker."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from source_fact_tier1 import extract
from check_complete_source_facts import check
from connected_tier2 import analyze,strip_lower,validate
from technique_tier2 import comparable_to_baseline
from qa_isolation_harness import execute
from check_technique_connections import check as check_connections


def bundle(root):
    names=('source_fact_tier1','source_field_registry','technique_observation_relations','musical_tier2','chord_degree_definitions','chord_degree_relations','contextual_note_roles','contextual_chord_motion','contextual_passage_roles','execution_dependencies','voicing_register','connected_tier2')
    code='import sys,types\n'
    hashes={}
    for name in names:
        source=(root/(name+'.py')).read_text(encoding='utf-8-sig')
        hashes[name]=hashlib.sha256(source.encode()).hexdigest()
        # Exact module source, not a hand-maintained reverse implementation.
        code+=f"_m=types.ModuleType({name!r});sys.modules[{name!r}]=_m\nexec(compile({source!r},{name!r},'exec'),_m.__dict__)\n"
    # Frozen function ASTs from the existing parser, not a second parser.
    api=root/'songsterr_automation/songsterr_api'
    sources={}
    sources['source_semantics']=(api/'source_semantics.py').read_text(encoding='utf-8-sig')
    parsed=ast.parse((api/'analyze_relationships.py').read_text(encoding='utf-8-sig'))
    selected=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in ('pitch','occurrences','hopo') or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('NOTE_FIELDS','BEAT_FIELDS') for t in n.targets)]
    sources['analyze_relationships']='from fractions import Fraction as F\nfrom collections import defaultdict\nfrom source_semantics import layout,marker_text,whole_measure_rest\n'+ast.unparse(ast.Module(body=selected,type_ignores=[]))
    parsed=ast.parse((root/'technique_analysis.py').read_text(encoding='utf-8-sig'))
    selected=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name=='classify_group']
    sources['technique_analysis']=ast.unparse(ast.Module(body=selected,type_ignores=[]))
    for name in ('source_slides','source_timing_regions','source_relationship_details'):
        sources[name]=(api/(name+'.py')).read_text(encoding='utf-8-sig')
    parser=ast.parse((root/'run_reversible_tier_qa.py').read_text(encoding='utf-8-sig'))
    function=next(n for n in parser.body if isinstance(n,ast.FunctionDef) and n.name=='extract_documents')
    sources['run_reversible_tier_qa']='import sys\nfrom pathlib import Path\nfrom fractions import Fraction as F\n'+ast.unparse(function)
    # Exact existing pure context adapters, not hand-written inverse copies.
    for name,dependency in (('source_key_tier1','from fractions import Fraction as F\nfrom run_reversible_tier_qa import extract_documents as extract_written_documents\n'),
                            ('source_tie_tier1','from source_key_tier1 import extract_documents as extract_context_documents\n')):
        tree=ast.parse((root/(name+'.py')).read_text(encoding='utf-8-sig'))
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='extract_documents')
        sources[name]=dependency+ast.unparse(function)
    for name,source in sources.items():
        code+=f"_m=types.ModuleType({name!r});_m.__file__={str(root/(name+'.py'))!r};sys.modules[{name!r}]=_m\nexec(compile({source!r},{name!r},'exec'),_m.__dict__)\n"
        hashes[name]=hashlib.sha256(source.encode()).hexdigest()
    return code+'reconstruct=sys.modules[\'connected_tier2\'].reconstruct\n',hashes


def run(output,baselines):
    output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
    code,hashes=bundle(root);cases=[]
    for folder in baselines:
        data=json.loads((folder/'result.json').read_text(encoding='utf-8'))
        for record in data['records']:cases.append((folder,record))
    # Include all retained source modules and pure adapters, not just inverse code.
    files=list(root.glob('*.py'))+list((root/'songsterr_automation/songsterr_api').glob('*.py'))+[Path(r['capture'])/p for _,r in cases for p in ['metadata.json']+[x.name for x in Path(r['capture']).glob('track-*.json')]]
    files += [p for folder,record in cases for p in (folder/'result.json',folder/record['file'])]
    frozen={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (output/'freeze.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
    results=[]
    for i,(folder,record) in enumerate(cases):
        capture=Path(record['capture']);directory=output/str(i);directory.mkdir()
        baseline_path=folder/record['file']
        if hashlib.sha256(baseline_path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Frozen baseline changed')
        lower=extract(capture);upper=analyze(lower)
        if upper['unsupported']:
            result=dict(capture=str(capture),status='FAIL_UNSUPPORTED',unsupported=upper['unsupported'])
        else:
            restored=validate(upper);source=check(capture,restored)
            # Old retained reports are checker-only, never inverse inputs.
            parity=comparable_to_baseline(upper['derived_views']['techniques'],json.loads(baseline_path.read_text(encoding='utf-8')))
            isolated=execute(code,strip_lower(upper),dict(variation=0),lower,directory/'isolated',timeout=120)
            actual=json.loads((directory/'isolated/worker/output.json').read_text(encoding='utf-8')) if isolated['status']=='PASS' else None
            independent=check(capture,actual) if actual is not None else dict(status='FAIL')
            documents={p.name:json.loads(p.read_text(encoding='utf-8-sig')) for p in [capture/'metadata.json']+sorted(capture.glob('track-*.json'))}
            connections=check_connections(documents,upper)
            (directory/'source-contrast-review.json').write_text(json.dumps(connections,indent=2),encoding='utf-8')
            result=dict(source_relationship_check=connections['status'],capture=str(capture),status='PASS' if connections['status']=='PASS_SOURCE_BACKED_RELATIONSHIPS' and parity and source['status']==independent['status']=='PASS_COMPLETE_CAPTURED_JSON_FACTS' and isolated['status']=='PASS' else 'FAIL',all_source_facts=len(lower['facts']),fret_relationships=len(upper['owned_parameters']['physical_positions']),registered_technique_groups=len(upper['owned_parameters']['technique_declarations']['groups']),retained_exact_parity=parity,source_check=source,isolated=isolated,independent_worker_output_check=independent,derived_harmonic_and_technique_cache_checked=True)
        (directory/'tier2.json').write_text(json.dumps(upper),encoding='utf-8')
        (directory/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');results.append(result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('source_check','isolated','independent_worker_output_check')}),flush=True)
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
    report=dict(status='PASS_FULL_DECLARED_SOURCE_BOUNDARY' if unchanged and all(r['status']=='PASS' for r in results) else 'FAIL',unchanged=unchanged,exact_module_sources=hashes,results=results,gate3='SOURCE_CONTRASTS_EXECUTED_PLANNER_FINAL_REVIEW_PENDING',scope='All captured source JSON typed facts; meaningful existing technique/harmonic relationships; no performed-audio or new-generation claim')
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('baselines',nargs='+',type=Path);a=p.parse_args();report=run(a.output,a.baselines);raise SystemExit(0 if report['status']=='PASS_FULL_DECLARED_SOURCE_BOUNDARY' else 1)
