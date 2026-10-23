"""Refit unchanged tonal kernel using source-only inputs and separate teachers."""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
from ordered_tonal_factor import fit,infer
from run_conditional_bass_study import evaluated,combined


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def training_join(piece,observed):
    """Teacher gaps reset supervised transitions, NEVER source predecessors."""
    teachers={r['id']:r for r in piece['rows']};rows=[]
    if len(teachers)!=len(piece['rows']):raise ValueError('Duplicate teacher identity')
    for source in observed:
        teacher=teachers[source['id']]
        if (source['start_q'],source['end_q'],source['mask'])!=(teacher['start_q'],teacher['end_q'],teacher['mask']):raise ValueError('Source/teacher clock or pitch differs')
        eligible=not teacher['quarantine_reasons']
        rows.append(dict(source,duration_q=str(F(source['end_q'])-F(source['start_q'])),target=teacher['target'] if eligible else None,
                         quarantine_reasons=[] if eligible else ['TRAINING_ONLY_NO_CURRENT_TEACHER']))
    expected={r['id'] for r in piece['rows'] if not r['quarantine_reasons']}
    if not expected<={r['id'] for r in rows}:raise ValueError('Teacher cannot create source observations')
    return dict(piece=piece['piece'],work=piece['work'],split=piece['split'],rows=rows)


def evaluate(model,pieces):
    scores=[];works=defaultdict(list);predictions=[]
    for piece in pieces:
        prediction=infer(model,piece['source_observations']);metric=evaluated(piece,prediction)
        scores.append(metric);works[piece['work']].append(metric);predictions.append(dict(piece=piece['piece'],prediction=prediction))
    return dict(aggregate=combined(scores),per_work={w:combined(s) for w,s in works.items()},predictions=predictions)


def run(clean,plan_path,output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private output required')
    output.mkdir(parents=True);manifest_path=clean/'manifest.json';manifest=json.loads(manifest_path.read_text());plan=json.loads(plan_path.read_text());partitions=defaultdict(list);works={}
    paths=[Path(__file__),manifest_path,plan_path]+[Path(__file__).with_name(n) for n in ('ordered_tonal_factor.py','tonal_context_observations.py','run_conditional_bass_study.py','conditional_bass_factor.py','tonal_source_stream.py','run_tonal_source_stream_audit.py')]
    for record in manifest['records']:
        source_path=clean/record['source_file'];teacher_path=Path(record['teacher_file'])
        if sha(source_path)!=record['source_sha256'] or sha(teacher_path)!=record['teacher_sha256']:raise ValueError('Frozen source/teacher changed')
        source=json.loads(source_path.read_text());piece=json.loads(teacher_path.read_text());piece['source_observations']=source['observations']
        if piece['piece']!=record['piece'] or piece['split']!=record['split'] or piece['work']!=record['work']:raise ValueError('Source/teacher identity differs')
        if piece['work'] in works and works[piece['work']]!=piece['split']:raise ValueError('Whole-work leakage')
        works[piece['work']]=piece['split'];partitions[piece['split']].append(piece);paths.extend([source_path,teacher_path])
    if set(partitions)!={'train','validation','test'}:raise ValueError('Three frozen partitions required')
    frozen={str(p.resolve()):sha(p) for p in paths}
    (output/'plan-before-fitting.json').write_text(json.dumps(dict(frozen=frozen,original_grid=plan,
        correction='Source-only predecessors/sequences; TRAIN teacher join resets supervised transition bookkeeping at missing targets; all source-only cells infer',
        scope='Previously inspected Mozart works; repeat study not fresh accuracy, no guitar or seven-mode claim',license='Private noncommercial only'),indent=2),encoding='utf-8')
    train=[training_join(p,p['source_observations']) for p in partitions['train']];models={};selection={}
    for kind in plan['models']:
        base=fit(train,kind,seed=plan['shuffle_seed']);grid=[]
        for alpha in plan['emission_backoff_strengths']:
            for tau in plan['key_transition_dirichlet_strengths']:
                result=evaluate(dict(base,alpha=alpha,tau=tau),partitions['validation'])
                grid.append(dict(alpha=alpha,tau=tau,metrics=result['aggregate']))
        chosen=min(grid,key=lambda r:(r['metrics']['key_label_nll'],r['alpha'],r['tau']))
        models[kind]=dict(base,alpha=chosen['alpha'],tau=chosen['tau']);selection[kind]=dict(selected=chosen,validation_grid=grid)
        print(json.dumps(dict(stage='selected',kind=kind,alpha=chosen['alpha'],tau=chosen['tau'],nll=chosen['metrics']['key_label_nll'])),flush=True)
    seal=output/'selection-before-test.json';seal.write_text(json.dumps(selection,indent=2),encoding='utf-8');seal_hash=sha(seal);test={}
    for kind,model in models.items():
        (output/(kind+'-research-model.json')).write_text(json.dumps(model),encoding='utf-8');result=evaluate(model,partitions['test']);test[kind]={k:v for k,v in result.items() if k!='predictions'}
        (output/(kind+'-test.json')).write_text(json.dumps(result),encoding='utf-8')
        print(json.dumps(dict(stage='test',kind=kind,metrics={k:result['aggregate'][k] for k in ('key_label_nll','brier','top_key_agreement','calibration_ece')})),flush=True)
    unchanged=all(sha(Path(p))==h for p,h in frozen.items()) and sha(seal)==seal_hash
    report=dict(status='COMPLETED_CLEAN_SOURCE_REFIT' if unchanged else 'FAIL_CHANGED',unchanged=unchanged,test=test,
                clean_manifest_sha256=sha(manifest_path),model_sha256={kind:sha(output/(kind+'-research-model.json')) for kind in models},
                selection_sha256=seal_hash,
                source_input_cells={s:sum(len(p['source_observations']) for p in ps) for s,ps in partitions.items()},
                teacher_cells={s:sum(sum(not r['quarantine_reasons'] for r in p['rows']) for p in ps) for s,ps in partitions.items()},
                scope='Corrected source-input provenance with unchanged kernel/grid/worksplit, not established musical truth or fresh guitar validation')
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('clean',type=Path);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=run(a.clean,a.plan,a.output)
    print(json.dumps(dict(status=r['status'],unchanged=r['unchanged'])));raise SystemExit(0 if r['unchanged'] else 1)
