"""Frozen real Songsterr written-observation ownership test, research only."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from source_tie_tier1 import extract
from source_written_sonority_cells import extract_cells
from research_observation_cuts import prepare,canonicalize,restore
from ordered_tonal_factor import infer
from qa_isolation_harness import execute


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def inverse_code(root):
    """Stage reviewed shared functions only; no model/data/source-file adapter."""
    chunks=['from copy import deepcopy','from fractions import Fraction as F']
    for filename,names in (('diagnose_tonal_subdivision.py',{'FIELDS','check_rows'}),
                           ('research_observation_cuts.py',{'SCHEMA','validate_support','canonicalize','restore'})):
        text=(root/filename).read_text(encoding='utf-8');tree=ast.parse(text)
        for node in tree.body:
            selected=isinstance(node,ast.FunctionDef) and node.name in names or isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets)
            if selected:chunks.append(ast.get_source_segment(text,node))
    chunks.append("def reconstruct(upper,controls):\n    if controls!={'variation':0}:raise ValueError('Locked observation scope required')\n    return restore(upper)")
    return '\n\n'.join(chunks)


def run(capture,study,output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private output required')
    output.mkdir(parents=True);root=Path(__file__).parent
    files=list(capture.glob('*.json'))+list(root.glob('*.py'))+list((root/'songsterr_automation/songsterr_api').glob('*.py'))
    files +=[study/(kind+'-research-model.json') for kind in ('ordered','marginal')]
    frozen={str(p.resolve()):digest(p) for p in files}
    (output/'plan-before-analysis.json').write_text(json.dumps(dict(frozen=frozen,scope='All nominal written cells; unknown pitch quarantined, original source boundaries preserved; no key accuracy or new source selection claim'),indent=2),encoding='utf-8')
    try:
        view=extract_cells(extract(capture));packet,unsplit=prepare(view['observations'],view['supports'],view['boundary_events']);canonical=canonicalize(packet)
        if canonical['observations']!=view['observations'] or restore(canonical)!=packet:raise ValueError('Observation ownership mismatch')
        (output/'source-view.json').write_text(json.dumps(view),encoding='utf-8')
        (output/'canonical.json').write_text(json.dumps(canonical),encoding='utf-8')
        worker=execute(inverse_code(root),canonical,dict(variation=0),packet,output/'isolated',timeout=60)
        models={}
        for kind in ('ordered','marginal'):
            model=json.loads((study/(kind+'-research-model.json')).read_text(encoding='utf-8'))
            baseline=infer(model,view['observations']);adapted=infer(model,canonical['observations'])
            if baseline!=adapted:raise ValueError('Fixed model inference changed after artificial-cut adapter')
            models[kind]=dict(exact_prediction_invariance=True,posterior_cells=len(baseline['rows']))
        unchanged=all(digest(Path(p))==h for p,h in frozen.items())
        report=dict(status='PASS_BOUNDED_SOURCE_CUT_QA' if worker['status']=='PASS' and unchanged else 'FAIL',unchanged=unchanged,
                    source_occurrences=view['source_occurrences'],source_cells=len(view['rows']),eligible_cells=len(view['observations']),
                    quarantined_cells=sum(bool(r['quarantine_reasons']) for r in view['rows']),source_span_q=view['span_q'],
                    artificial_child_cells=len(packet['children']),unsplit_rest_cells=len(unsplit),original_boundaries_preserved=True,
                    exact_observation_roundtrip=True,worker=worker,models=models,
                    limitations=['Written base pitch, not acoustic execution','Observation cut-packet inverse only; full-source inverse separately verified','No evaluation labels or guitar key/mode accuracy claim','Private research models not product deployment'])
    except Exception as exc:
        report=dict(status='FAIL_RETAINED',error=type(exc).__name__+': '+str(exc))
        (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');raise
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('capture',type=Path);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    result=run(args.capture,args.study,args.output);print(json.dumps(result));raise SystemExit(0 if result['status']=='PASS_BOUNDED_SOURCE_CUT_QA' else 1)
