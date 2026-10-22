"""Exact rational chord-boundary diagnostics on frozen analysis artifacts.

Chord identity is root + relative pitch-class formula. Inversion/function/key
label changes alone do not create a different chord for this metric.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path


def compare(reference_spans,evidence):
    gold=set();prior=None
    for row in reference_spans:
        identity=(row['reference_root_pc'],tuple(row['reference_formula']))
        if prior is not None and identity!=prior:gold.add(F(row['start_q']))
        prior=identity
    points=list(map(F,evidence['partition_points_q']))
    predicted={F(row['start_q']) for row in evidence['canonical_display_path'][1:]}
    mandatory={points[i] for i in evidence['mandatory_boundary_indices'] if i not in (0,len(points)-1)}
    def metrics(given):
        correct=given&gold
        return dict(exact_hits=len(correct),predicted=len(given),reference=len(gold),precision=len(correct)/len(given) if given else None,recall=len(correct)/len(gold) if gold else None,
                    matched_q=list(map(str,sorted(correct))),extra_q=list(map(str,sorted(given-gold))),missed_q=list(map(str,sorted(gold-given))))
    return dict(canonical_display_cuts=metrics(predicted),all_path_mandatory_cuts=metrics(mandatory),
                rule='Exact rational boundary equality; root+formula change, no timing tolerance or label-driven path choice',
                claim='Boundary agreement on qualified reference labels, NOT key changes or definitive harmonic truth')


def run(artifact,output):
    if output.exists():raise ValueError('Fresh diagnostic output required')
    rows=[];hashes={str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for directory in sorted(artifact.glob('riemenschneider*')):
        files=[directory/'result.json',directory/'harmonic.json']
        for p in files:hashes[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
        result,evidence=[json.loads(p.read_text(encoding='utf-8')) for p in files]
        rows.append(dict(reference=directory.name,diagnostic=compare(result['annotated_evaluation']['reference_spans'],evidence)))
    report=dict(inputs=hashes,results=rows,metric_defined_in='check_harmonic_boundaries.py before executing these diagnostics; no model refit')
    output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(rows,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.artifact,a.output)
