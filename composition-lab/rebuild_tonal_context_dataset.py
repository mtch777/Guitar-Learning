"""Reproduce frozen private research rows from hashed source-support cells.

No fitting, resplitting, test retuning, copied features or public corpus output.
Original feature rows are opened only AFTER regeneration for an equality check.
"""
import argparse
import hashlib
import json
from pathlib import Path
from tonal_context_observations import target_cells


def run(dataset,output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private output required')
    manifest_path=dataset/'manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));output.mkdir(parents=True)
    support={Path(p).parent.name:(Path(p),digest) for p,digest in manifest['source_sha256'].items()}
    results=[];works={}
    for record in manifest['records']:
        piece=Path(record['file']).stem;work=record['work'];split=record['split']
        if work in works and works[work]!=split:raise ValueError('Whole-work partition conflict')
        works[work]=split;path,digest=support[piece]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Frozen support input changed')
        regenerated=dict(work=work,piece=piece,split=split,rows=target_cells(json.loads(path.read_text(encoding='utf-8'))))
        destination=output/record['file'];destination.write_text(json.dumps(regenerated,separators=(',',':')),encoding='utf-8')
        original_path=dataset/record['file']
        if hashlib.sha256(original_path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Frozen original rows changed')
        matches=regenerated==json.loads(original_path.read_text(encoding='utf-8'))
        results.append(dict(piece=piece,rows=len(regenerated['rows']),exact_structured_equality=matches))
    report=dict(status='PASS_REGENERATED_FROM_SUPPORT' if all(r['exact_structured_equality'] for r in results) else 'FAIL',
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),results=results,
        cells=sum(r['rows'] for r in results),scope='Research data reproducibility only; not song inverse or inferred-key accuracy')
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('dataset',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=run(a.dataset,a.output)
    print(json.dumps({k:v for k,v in r.items() if k!='results'}));raise SystemExit(0 if r['status']=='PASS_REGENERATED_FROM_SUPPORT' else 1)
