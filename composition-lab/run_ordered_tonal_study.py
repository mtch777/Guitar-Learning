"""Frozen held-out-by-work study. Private noncommercial research artifacts only."""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
from ordered_tonal_factor import fit,infer,emission,public_observations


def evaluate(model,pieces,save_predictions=False):
    rows=[];predictions=[]
    for piece in pieces:
        observed=public_observations(piece['rows']);prediction=infer(model,observed);targets={r['id']:r for r in piece['rows'] if not r['quarantine_reasons']}
        duration=nll=brier=correct=emission_nll=unseen=0.;bins=[dict(duration=0.,correct=0.,confidence_sum=0.) for _ in range(10)]
        for p,o in zip(prediction['rows'],observed):
            target=targets[p['observation_ref']];state=target['target']['state'];weight=float(F(target['duration_q']));prob=p['posterior'];confidence=max(prob);prediction_state=p['marginal_map_state'];duration+=weight;nll-=weight*math.log(max(prob[state],1e-300));brier+=weight*sum((value-int(i==state))**2 for i,value in enumerate(prob));correct+=weight*(prediction_state==state)
            ep,backoff=emission(model,o['mask'],o['previous_mask'],state);emission_nll-=weight*math.log(ep);unseen+=weight*backoff
            bucket=bins[min(9,int(confidence*10))];bucket['duration']+=weight;bucket['correct']+=weight*(prediction_state==state);bucket['confidence_sum']+=weight*confidence
        rows.append(dict(piece=piece['piece'],work=piece['work'],duration_q=duration,key_label_nll_sum=nll,brier_sum=brier,correct_q=correct,emission_predictive_nll_sum=emission_nll,unseen_context_q=unseen,calibration_bins=bins,cells=len(observed)))
        if save_predictions:predictions.append(dict(piece=piece['piece'],prediction=prediction))
    def aggregate(group):
        d=sum(r['duration_q'] for r in group)
        return dict(duration_q=d,key_label_nll=sum(r['key_label_nll_sum'] for r in group)/d,brier=sum(r['brier_sum'] for r in group)/d,top_key_agreement=sum(r['correct_q'] for r in group)/d,emission_predictive_nll=sum(r['emission_predictive_nll_sum'] for r in group)/d,unseen_context_fraction=sum(r['unseen_context_q'] for r in group)/d,cells=sum(r['cells'] for r in group))
    bywork=defaultdict(list)
    for r in rows:bywork[r['work']].append(r)
    return dict(aggregate=aggregate(rows),works={w:aggregate(r) for w,r in sorted(bywork.items())},pieces=rows,predictions=predictions)


def run(dataset,output):
    if 'local-artifacts' not in output.resolve().parts or output.exists():raise ValueError('Fresh private research output required')
    output.mkdir(parents=True);manifest_path=dataset/'manifest.json';plan_path=dataset/'plan-before-fitting.json';manifest=json.loads(manifest_path.read_text());plan=json.loads(plan_path.read_text());partitions=defaultdict(list);bywork={};paths=[manifest_path,plan_path,Path(__file__),Path(__file__).with_name('ordered_tonal_factor.py'),Path(__file__).with_name('tonal_context_observations.py')]
    for record in manifest['records']:
        path=dataset/record['file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Frozen features changed')
        piece=json.loads(path.read_text());paths.append(path)
        if piece['work'] in bywork and bywork[piece['work']]!=piece['split']:raise ValueError('Whole-work leakage')
        bywork[piece['work']]=piece['split'];partitions[piece['split']].append(piece)
    frozen={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};(output/'freeze.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
    grids={};selected={};models={}
    for kind in plan['models']:
        base=fit(partitions['train'],kind,seed=plan['shuffle_seed']);grid=[]
        for alpha in plan['emission_backoff_strengths']:
            for tau in plan['key_transition_dirichlet_strengths']:
                model=dict(base,alpha=alpha,tau=tau);result=evaluate(model,partitions['validation']);grid.append(dict(alpha=alpha,tau=tau,validation=result['aggregate']))
        best=min(grid,key=lambda r:(r['validation']['key_label_nll'],r['alpha'],r['tau']));models[kind]=dict(base,alpha=best['alpha'],tau=best['tau']);selected[kind]=best;grids[kind]=grid
        print(json.dumps(dict(stage='validation_selected',kind=kind,selected=best)),flush=True)
    # Selection written and sealed BEFORE test inference; no choice uses test.
    selection=dict(plan_sha256=frozen[str(plan_path.resolve())],selected=selected,validation_grids=grids,split_works=bywork)
    (output/'selection-before-test.json').write_text(json.dumps(selection,indent=2),encoding='utf-8');selection_hash=hashlib.sha256((output/'selection-before-test.json').read_bytes()).hexdigest();tests={}
    for kind,model in models.items():
        (output/(kind+'-research-model.json')).write_text(json.dumps(model,separators=(',',':')),encoding='utf-8');test=evaluate(model,partitions['test'],save_predictions=True);tests[kind]=test
        (output/(kind+'-test.json')).write_text(json.dumps(test,separators=(',',':')),encoding='utf-8');print(json.dumps(dict(stage='test',kind=kind,result=test['aggregate'])),flush=True)
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items()) and selection_hash==hashlib.sha256((output/'selection-before-test.json').read_bytes()).hexdigest()
    ordered=tests['ordered']['aggregate'];comparisons={kind:dict(key_label_nll_difference=ordered['key_label_nll']-tests[kind]['aggregate']['key_label_nll'],agreement_difference=ordered['top_key_agreement']-tests[kind]['aggregate']['top_key_agreement']) for kind in ('marginal','shuffled_predecessor')}
    wins=all(c['key_label_nll_difference']<0 for c in comparisons.values())
    report=dict(status='COMPLETED_FIXED_RESEARCH_STUDY' if unchanged else 'FAIL_MUTATED_INPUT_OR_CODE',ordered_factor_operational_gate='PASS' if wins else 'REJECT_NOT_BETTER_THAN_BOTH_CONTROLS',unchanged=unchanged,selected=selected,test={k:v['aggregate'] for k,v in tests.items()},per_work={k:v['works'] for k,v in tests.items()},comparisons=comparisons,scope='Small previously inspected Mozart corpus, held-out-by-work analyst major/minor labels; no guitar/modal/function/generalization or calibrated product claim',license_scope=plan['license_scope'])
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('dataset',type=Path);parser.add_argument('output',type=Path);a=parser.parse_args();r=run(a.dataset,a.output);raise SystemExit(0 if r['status']=='COMPLETED_FIXED_RESEARCH_STUDY' else 1)
