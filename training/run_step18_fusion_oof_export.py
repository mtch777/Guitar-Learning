#!/usr/bin/env python3
"""Train and export exactly the three Step-17 fold models for browser parity."""
import argparse
import json
import time
from pathlib import Path
import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from export_step18_fusion_models import export


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('vectors_json',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--smoke',action='store_true')
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    rows=json.loads(a.vectors_json.read_text())
    if len(rows)!=384:raise ValueError('Expected complete 384-row feature pool')
    y=np.asarray([r['string']-1 for r in rows],int)
    midis=np.asarray([r['midi'] for r in rows],int)
    X={name:np.asarray([r[name+'_features'] for r in rows],np.float32) for name in ('baseline','harmonic','mfcc')}
    targets=[m for m in sorted(set(midis)) if not a.smoke or 54<=m<=60]
    predictions=[];start=time.time()
    for fi,midi in enumerate(targets,1):
        tr=midis!=midi;te=np.flatnonzero(~tr)
        if a.smoke:te=np.asarray([i for i in te if 'normal' in rows[i]['file']],int)
        if not len(te):continue
        fold=a.out/f'midi_{midi}';fold.mkdir(exist_ok=True)
        probabilities={}
        for name in ('baseline','harmonic','mfcc'):
            sc=StandardScaler().fit(X[name][tr]);model=XGBClassifier(n_estimators=100,max_depth=3,learning_rate=.04,
                subsample=.85,colsample_bytree=.85,reg_lambda=2,objective='multi:softprob',
                num_class=8,random_state=42,n_jobs=8)
            model.fit(sc.transform(X[name][tr]),y[tr])
            probabilities[name]=model.predict_proba(sc.transform(X[name][te]))
            model_path=fold/(name+'_xgboost.json');scaler_path=fold/(name+'_scaler.joblib')
            model.save_model(model_path);joblib.dump(sc,scaler_path)
            (fold/(name+'.json')).write_text(json.dumps(export(model_path,scaler_path),separators=(',',':')))
            model_path.unlink();scaler_path.unlink()
        for j,index in enumerate(te):
            row=rows[index]
            predictions.append({'file':row['file'],'midi':int(midi),'string':row['string'],
                **{name+'_probabilities':probabilities[name][j].astype(float).tolist() for name in probabilities}})
        elapsed=time.time()-start
        print(f'FUSION OOF FOLD [{fi}/{len(targets)}] MIDI {midi} elapsed={elapsed/60:.1f}m ETA={elapsed/fi*(len(targets)-fi)/60:.1f}m',flush=True)
        (a.out/'python_oof_probabilities.json').write_text(json.dumps(predictions))
    print(f'WROTE {len(predictions)} held-out recordings',flush=True)

if __name__=='__main__':main()
