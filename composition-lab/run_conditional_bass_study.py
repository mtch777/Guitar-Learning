"""Private controlled incremental bass evidence study; source inputs != labels.

Verified clean-refit PC models are fixed controls for the incremental factor.
This study measures ONE added conditional relationship, not guitar key accuracy.
"""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
from conditional_bass_factor import fit,update,validate_feature
from ordered_tonal_factor import infer
from run_tonal_source_stream_audit import score,aggregate


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_clean_models(clean,study):
    report_path=study/'result.json';plan_path=study/'plan-before-fitting.json';selection_path=study/'selection-before-test.json'
    report=json.loads(report_path.read_text());plan=json.loads(plan_path.read_text())
    if report['status']!='COMPLETED_CLEAN_SOURCE_REFIT' or report['unchanged'] is not True:raise ValueError('Successful clean source refit required')
    if set(report['model_sha256'])!={'ordered','marginal','shuffled_predecessor'}:raise ValueError('Complete clean model inventory required')
    required={str((clean/'manifest.json').resolve()),str(Path(__file__).with_name('ordered_tonal_factor.py').resolve()),str(Path(__file__).with_name('run_clean_tonal_study.py').resolve())}
    if not required<=set(plan['frozen']):raise ValueError('Complete clean dependency provenance required')
    if sha(clean/'manifest.json')!=report['clean_manifest_sha256'] or sha(selection_path)!=report['selection_sha256']:raise ValueError('Clean model dataset/selection provenance differs')
    if not all(sha(Path(p))==h for p,h in plan['frozen'].items()):raise ValueError('Clean refit frozen dependencies changed')
    for kind,digest in report['model_sha256'].items():
        if sha(study/(kind+'-research-model.json'))!=digest:raise ValueError('Clean refit model changed')
    return [report_path,plan_path,selection_path]


def adjusted(prediction,observed,features,model,alpha):
    index={r['id']:r for r in observed};out=[]
    if len(index)!=len(observed) or set(index)!=set(features):raise ValueError('Exact complete source input/feature join required')
    if len(prediction['rows'])!=len(observed):raise ValueError('Incomplete base inference')
    seen=set()
    for row in prediction['rows']:
        ident=row['observation_ref']
        if ident in seen:raise ValueError('Duplicate base inference identity')
        seen.add(ident);source=index[ident];feature=features[ident]
        if feature['observation_ref']!=ident or (feature['start_q'],feature['end_q'])!=(row['start_q'],row['end_q']) or (row['start_q'],row['end_q'])!=(source['start_q'],source['end_q']):raise ValueError('Conditional feature clock/identity mismatch')
        result=update(model,row['posterior'],source['mask'],feature,alpha);prob=result['posterior']
        out.append(dict(observation_ref=ident,start_q=row['start_q'],end_q=row['end_q'],posterior=prob,
                        marginal_map_state=max(range(24),key=lambda s:prob[s]),bass_evidence_status=result['status']))
    return dict(rows=out,scope='Query-local bass likelihood times unchanged PC posterior; not a joint all-bass sequence posterior')


def evaluated(piece,prediction):
    result=score(piece,prediction['rows']);index={r['observation_ref']:r for r in prediction['rows']}
    bins=[dict(duration_q=0.,correct_q=0.,confidence_q=0.) for _ in range(10)]
    for target in piece['rows']:
        if target['quarantine_reasons']:continue
        row=index[target['id']];weight=float(F(target['duration_q']));confidence=max(row['posterior'])
        bucket=bins[min(9,int(confidence*10))];bucket['duration_q']+=weight
        bucket['correct_q']+=weight*(row['marginal_map_state']==target['target']['state']);bucket['confidence_q']+=weight*confidence
    return dict(result,calibration_bins=bins)


def combined(rows):
    result=aggregate(rows);bins=[{k:sum(r['calibration_bins'][i][k] for r in rows) for k in ('duration_q','correct_q','confidence_q')} for i in range(10)]
    result['calibration_ece']=sum(abs(b['correct_q']-b['confidence_q']) for b in bins)/result['duration_q']
    result['calibration_bins']=bins;return result


def run(clean,study,output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private output required')
    output.mkdir(parents=True);manifest_path=clean/'manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    records=manifest['records'];partitions=defaultdict(list);features={};paths=[manifest_path,Path(__file__)]+verify_clean_models(clean,study)
    root=Path(__file__).parent
    paths += [root/n for n in ('conditional_bass_factor.py','tonal_source_stream.py','ordered_tonal_factor.py','tonal_context_observations.py','run_tonal_source_stream_audit.py')]
    work_splits={}
    for record in records:
        source_path=clean/record['source_file'];teacher_path=Path(record['teacher_file'])
        if sha(source_path)!=record['source_sha256'] or sha(teacher_path)!=record['teacher_sha256']:raise ValueError('Frozen source/teacher artifact changed')
        source=json.loads(source_path.read_text(encoding='utf-8'));piece=json.loads(teacher_path.read_text(encoding='utf-8'))
        if piece['piece']!=record['piece'] or piece['split']!=record['split']:raise ValueError('Frozen piece identity/split mismatch')
        if piece['work'] in work_splits and work_splits[piece['work']]!=piece['split']:raise ValueError('Whole-work leakage')
        work_splits[piece['work']]=piece['split'];piece['source_observations']=source['observations'];partitions[piece['split']].append(piece)
        inventory={r['observation_ref']:r for r in source['features']}
        if len(inventory)!=len(source['features']) or set(inventory)!={r['id'] for r in source['observations']}:raise ValueError('Complete source-only features required')
        for row in source['observations']:
            feature=inventory[row['id']];validate_feature(feature,row['mask'])
            if feature['piece']!=piece['piece'] or (feature['start_q'],feature['end_q'])!=(row['start_q'],row['end_q']):raise ValueError('Source feature join differs')
        features[piece['piece']]=inventory;paths.extend([source_path,teacher_path])
    if set(partitions)!={'train','validation','test'}:raise ValueError('Three frozen partitions required')
    models={kind:json.loads((study/(kind+'-research-model.json')).read_text()) for kind in ('ordered','marginal')}
    paths += [study/(kind+'-research-model.json') for kind in models]
    frozen={str(p.resolve()):sha(p) for p in paths};grid=(1,10,100)
    plan=dict(frozen=frozen,alpha_grid=grid,selection='Validation duration-weighted NLL; deterministic smallest-alpha tie; seal BEFORE test',
        scope='Previously inspected Mozart piano works, exploratory incremental bass experiment. Separately refitted PC models use clean source contexts and training-only teacher joins.',
        labels='Only TRAIN current eligible targets fit bass. ALL source-only cells infer. Evaluation target availability never selects inference rows.',
        control='TRAIN bass permuted within whole work and exact absolute PC mask; fixed seed9427; availability neutral',
        no_guitar_or_seven_mode_accuracy_claim=True,whole_work_splits=work_splits,
        license='Private noncommercial research only; no annotation or fitted weights publication')
    (output/'plan-before-fitting.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    factors={};selections={};validation={};test={};base_predictions={}
    for control in ('actual','shuffled'):
        factor,training_rows=fit(partitions['train'],features,shuffle=control=='shuffled',seed=9427);factors[control]=factor
        (output/(control+'-bass-research-model.json')).write_text(json.dumps(factor),encoding='utf-8')
        (output/(control+'-training-provenance.json')).write_text(json.dumps(training_rows),encoding='utf-8')
    for kind,base in models.items():
        for piece in partitions['validation']:
            base_predictions[kind,piece['piece']]=infer(base,piece['source_observations'])
        selections[kind]={};validation[kind]={}
        for control,factor in factors.items():
            candidates=[]
            for alpha in grid:
                scores=[evaluated(p,adjusted(base_predictions[kind,p['piece']],p['source_observations'],features[p['piece']],factor,alpha)) for p in partitions['validation']]
                candidates.append(dict(alpha=alpha,metrics=combined(scores)))
            chosen=min(candidates,key=lambda r:(r['metrics']['key_label_nll'],r['alpha']))
            selections[kind][control]=chosen['alpha'];validation[kind][control]=candidates
    seal=output/'selection-before-test.json';seal.write_text(json.dumps(dict(selected=selections,validation=validation),indent=2),encoding='utf-8');seal_hash=sha(seal)
    for kind,base in models.items():
        scores=defaultdict(list);works=defaultdict(lambda:defaultdict(list));predictions=defaultdict(list)
        for piece in partitions['test']:
            original=infer(base,piece['source_observations']);variants={'base':original}
            for control,factor in factors.items():variants[control]=adjusted(original,piece['source_observations'],features[piece['piece']],factor,selections[kind][control])
            for variant,prediction in variants.items():
                metric=evaluated(piece,prediction);scores[variant].append(metric);works[variant][piece['work']].append(metric)
                predictions[variant].append(dict(piece=piece['piece'],prediction=prediction))
        test[kind]=dict(aggregate={v:combined(s) for v,s in scores.items()},per_work={v:{w:combined(s) for w,s in bywork.items()} for v,bywork in works.items()})
        for variant,rows in predictions.items():(output/(kind+'-'+variant+'-test-predictions.json')).write_text(json.dumps(rows),encoding='utf-8')
        print(json.dumps(dict(stage='test',kind=kind,metrics={v:{k:m[k] for k in ('key_label_nll','brier','top_key_agreement','calibration_ece')} for v,m in test[kind]['aggregate'].items()})),flush=True)
    unchanged=all(sha(Path(p))==h for p,h in frozen.items()) and sha(seal)==seal_hash
    comparisons={}
    for kind,result in test.items():
        a=result['aggregate'];harm=[w for w in result['per_work']['base'] if result['per_work']['actual'][w]['key_label_nll']>result['per_work']['base'][w]['key_label_nll']]
        comparisons[kind]=dict(actual_minus_base_nll=a['actual']['key_label_nll']-a['base']['key_label_nll'],actual_minus_shuffled_nll=a['actual']['key_label_nll']-a['shuffled']['key_label_nll'],harmed_works=harm,
            promotion='REJECT_INCONSISTENT_OR_UNPROVEN' if harm or a['actual']['key_label_nll']>=min(a['base']['key_label_nll'],a['shuffled']['key_label_nll']) else 'EXPLORATORY_SUPPORT_ONLY_REQUIRES_NEW_DOMAIN_VALIDATION')
    report=dict(status='COMPLETED_CONTROLLED_BASS_STUDY' if unchanged else 'FAIL_CHANGED',unchanged=unchanged,selected=selections,test=test,comparisons=comparisons,
                limits=plan['scope'],qa_scope='Incremental musical evidence study, not full-source inverse or fresh-song gates; those retained separately')
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('clean',type=Path);p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=run(a.clean,a.study,a.output)
    print(json.dumps(dict(status=r['status'],unchanged=r['unchanged'],comparisons=r['comparisons'])));raise SystemExit(0 if r['unchanged'] else 1)
