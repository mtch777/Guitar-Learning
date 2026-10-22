"""Recheck sealed producer artifacts with a corrected independent validator.

Does NOT rerun or claim to rerun the musical producer or isolated inverse.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from musical_tier2 import validate
from run_tied_harmonic_context_qa import source_queries
from run_written_tie_context_qa import exact_fields


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def study_hash(path):
    source=path.read_text(encoding='utf-8');node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='study')
    return hashlib.sha256(ast.get_source_segment(source,node).encode('utf-8')).hexdigest()


def run(producer,output):
    root=Path(__file__).resolve().parent;freeze=json.loads((producer/'freeze.json').read_text(encoding='utf-8'));original=json.loads((producer/'result.json').read_text(encoding='utf-8'))
    if output.exists():raise ValueError('Fresh validator result required')
    current_core=root/'musical_tier2.py';current_study=root/'run_tied_harmonic_context_qa.py';old_study=producer/'frozen-code/run_tied_harmonic_context_qa.py'
    hashes={str(p):sha(p) for p in (current_core,current_study,Path(__file__).resolve(),producer/'freeze.json',producer/'result.json',root/'check_harmonic_span_source.py',root/'check_reversible_source.py',root/'run_written_tie_context_qa.py')}
    unchanged_core=sha(current_core)==freeze[str(current_core)]
    unchanged_study=study_hash(current_study)==study_hash(old_study)
    sources={path:digest for path,digest in freeze.items() if 'local-artifacts' in Path(path).parts}
    source_integrity=all(sha(Path(path))==digest for path,digest in sources.items());hashes.update(sources)
    results=[]
    for ordinal,row in enumerate(original['results']):
        directory=producer/str(ordinal);study_path=directory/'study.json';stage=directory/'isolated/worker';upper_path=stage/'input.json';output_path=stage/'output.json';operator=stage/'relationships.py'
        for p in (study_path,upper_path,output_path,operator):hashes[str(p)]=sha(p)
        staged=json.loads((directory/'isolated/freeze.json').read_text(encoding='utf-8'))
        staged_integrity=all(sha(stage/name)==digest for name,digest in staged.items())
        upper=json.loads(upper_path.read_text(encoding='utf-8'))['upper']['upper'];validate(upper)
        study=json.loads(study_path.read_text(encoding='utf-8'));actual=json.loads(output_path.read_text(encoding='utf-8'))
        oracle=source_queries(Path(row['capture']),upper,study)
        matches=exact_fields(actual['study'],study)
        results.append(dict(case=ordinal,source_context=oracle,original_isolated_status=row['isolated_same_relations']['status'],staged_code_input_integrity=staged_integrity,saved_study_equals_original_worker_output=matches,status='PASS' if oracle['status']=='PASS' and staged_integrity and matches and row['status']=='PASS' else 'FAIL'))
    unchanged=all(sha(Path(path))==digest for path,digest in hashes.items())
    report=dict(status='PASS' if original['technical_status']=='PASS' and unchanged_core and unchanged_study and source_integrity and unchanged and all(r['status']=='PASS' for r in results) else 'FAIL',producer_run=str(producer),producer_verdict=original['technical_status'],musical_core_unchanged=unchanged_core,producer_study_function_unchanged=unchanged_study,original_sources_unchanged=source_integrity,validator_inputs_unchanged=unchanged,results=results,hashes=hashes,scope='Corrected validator re-audit of original frozen studies/upper/source; producer and isolated inverse NOT rerun; original verdict unmodified')
    output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ('hashes','results')},indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('producer',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    raise SystemExit(0 if run(a.producer,a.output)['status']=='PASS' else 1)
