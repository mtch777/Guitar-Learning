"""Frozen-model replay with source-only inputs and a SEPARATE evaluation mask.

Historical models/parameters stay unchanged. Earlier results may exploit where
evaluation annotations were available; this measures that input-boundary defect.
"""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
from tonal_source_stream import project_source_cells,observations
from ordered_tonal_factor import infer,public_observations


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def score(piece,predictions):
    index={r['observation_ref']:r for r in predictions}
    if len(index)!=len(predictions):raise ValueError('Duplicate inference identity')
    total=nll=brier=correct=0.;count=0
    for row in piece['rows']:
        if row['quarantine_reasons']:continue
        pred=index[row['id']]
        if (pred['start_q'],pred['end_q'])!=(row['start_q'],row['end_q']):raise ValueError('Evaluation clock differs from inference')
        state=row['target']['state'];weight=float(F(row['duration_q']));prob=pred['posterior']
        if type(state) is not int or not 0<=state<24 or weight<=0:raise ValueError('Typed evaluation target/weight required')
        if len(prob)!=24 or any(not math.isfinite(p) or p<0 or p>1 for p in prob) or abs(math.fsum(prob)-1)>1e-10:raise ValueError('Invalid fixed posterior')
        total+=weight;nll-=weight*math.log(max(prob[state],1e-300));brier+=weight*sum((p-int(i==state))**2 for i,p in enumerate(prob));correct+=weight*(pred['marginal_map_state']==state);count+=1
    return dict(duration_q=total,nll_sum=nll,brier_sum=brier,correct_q=correct,evaluation_cells=count)


def aggregate(rows):
    duration=sum(r['duration_q'] for r in rows)
    return dict(duration_q=duration,key_label_nll=sum(r['nll_sum'] for r in rows)/duration,
                brier=sum(r['brier_sum'] for r in rows)/duration,top_key_agreement=sum(r['correct_q'] for r in rows)/duration,
                evaluation_cells=sum(r['evaluation_cells'] for r in rows))


def run(study,output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private output required')
    output.mkdir(parents=True);root=Path(__file__).parent
    original_freeze=json.loads((study/'freeze.json').read_text(encoding='utf-8'))
    for name,digest in original_freeze.items():
        if sha(Path(name))!=digest:raise ValueError('Original fixed-study support/code changed')
    manifest_path=Path(next(p for p in original_freeze if p.endswith('manifest.json')));manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    support={Path(p).parent.name:(Path(p),h) for p,h in manifest['source_sha256'].items()}
    records=[r for r in manifest['records'] if r['split']=='test']
    files=[Path(__file__),root/'tonal_source_stream.py',root/'ordered_tonal_factor.py',root/'tonal_context_observations.py',manifest_path]
    files+=list(study.glob('*.json'))+[manifest_path.parent/r['file'] for r in records]+[support[Path(r['file']).stem][0] for r in records]
    frozen={str(p.resolve()):sha(p) for p in files}
    (output/'plan-before-inference.json').write_text(json.dumps(dict(frozen=frozen,
        selection='ALL frozen test pieces; original works previously inspected, no new benchmark claim',
        correction='Source-context-only eligibility/clocks/masks/previous/sequences; unknown annotation cells remain in inference; labels used only in separate unchanged evaluation mask',
        original_models_unchanged=True,no_fitting_or_retuning=True),indent=2),encoding='utf-8')
    models={k:json.loads((study/(k+'-research-model.json')).read_text()) for k in ('ordered','marginal','shuffled_predecessor')}
    saved={k:{p['piece']:p['prediction'] for p in json.loads((study/(k+'-test.json')).read_text())['predictions']} for k in models}
    inputs=[];predicted=defaultdict(list);legacy_scores=defaultdict(list);clean_scores=defaultdict(list);bywork=defaultdict(lambda:defaultdict(list))
    for record in records:
        piece=json.loads((manifest_path.parent/record['file']).read_text(encoding='utf-8'));path,digest=support[piece['piece']]
        if sha(path)!=digest:raise ValueError('Original source-context support changed')
        raw=json.loads(path.read_text(encoding='utf-8'));pure=observations(project_source_cells(raw));source_rows=pure['observations']
        old_rows=public_observations(piece['rows']);oldids={r['id'] for r in old_rows};newids={r['id'] for r in source_rows}
        if not oldids<=newids:raise ValueError('Previously scored cell lost from source-only inference')
        oldindex={r['id']:r for r in old_rows};newindex={r['id']:r for r in source_rows}
        info=dict(piece=piece['piece'],work=piece['work'],source_cells=len(raw),legacy_inference_cells=len(old_rows),source_only_inference_cells=len(source_rows),
                  annotation_only_removed_cells=sorted(newids-oldids),changed_predecessor_or_sequence_ids=[i for i in sorted(oldids) if oldindex[i]!=newindex[i]])
        (output/(piece['piece']+'-source-input.json')).write_text(json.dumps(pure),encoding='utf-8');inputs.append(info)
        for kind,model in models.items():
            baseline=infer(model,old_rows)
            if baseline!=saved[kind][piece['piece']]:raise ValueError('Original legacy baseline does not replay exactly')
            clean=infer(model,source_rows);a=score(piece,baseline['rows']);b=score(piece,clean['rows'])
            legacy_scores[kind].append(a);clean_scores[kind].append(b);bywork[kind][piece['work']].append(dict(legacy=a,source_only=b))
            oldpred={p['observation_ref']:p for p in baseline['rows']};newpred={p['observation_ref']:p for p in clean['rows']}
            info.setdefault('models',{})[kind]=dict(legacy=a,source_only=b,changed_map_on_scored_cells=sum(oldpred[i]['marginal_map_state']!=newpred[i]['marginal_map_state'] for i in oldids),
                maximum_posterior_change=max((abs(x-y) for i in oldids for x,y in zip(oldpred[i]['posterior'],newpred[i]['posterior'])),default=0))
            predicted[kind].append(dict(piece=piece['piece'],prediction=clean))
    unchanged=all(sha(Path(p))==h for p,h in frozen.items())
    for kind,rows in predicted.items():(output/(kind+'-source-only-predictions.json')).write_text(json.dumps(rows),encoding='utf-8')
    results={kind:dict(legacy=aggregate(legacy_scores[kind]),source_only=aggregate(clean_scores[kind]),
        per_work={work:{scope:aggregate([r[scope] for r in rows]) for scope in ('legacy','source_only')} for work,rows in bywork[kind].items()}) for kind in models}
    report=dict(status='COMPLETED_SOURCE_ONLY_INPUT_AUDIT' if unchanged else 'FAIL_CHANGED',unchanged=unchanged,pieces=inputs,models=results,
                source_valid_annotation_only_removed_cells=sum(len(r['annotation_only_removed_cells']) for r in inputs),
                limitations=['Historical key results used annotation-dependent inference availability and require qualification','Fixed preinspected test works; no retuning, fresh accuracy or guitar/mode claim','Source-only observation proof, not complete-source musical inverse'])
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=run(a.study,a.output)
    print(json.dumps({k:v for k,v in r.items() if k!='pieces'}));raise SystemExit(0 if r['unchanged'] else 1)
