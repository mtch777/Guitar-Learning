#!/usr/bin/env python3
"""Fit final three models on JS raw-input features; no in-sample accuracy claim."""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from export_step18_fusion_models import export


def main():
    ap=argparse.ArgumentParser();ap.add_argument('js_features',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    rows=json.loads(a.js_features.read_text())
    if len(rows)!=384:raise ValueError('Expected 384 training recordings')
    y=np.asarray([r['string']-1 for r in rows],int)
    for name,size in [('baseline',107),('harmonic',214),('mfcc',26)]:
        X=np.asarray([r[name+'_features'] for r in rows],np.float32)
        if X.shape!=(384,size):raise ValueError(f'{name}: {X.shape}')
        sc=StandardScaler().fit(X)
        model=XGBClassifier(n_estimators=100,max_depth=3,learning_rate=.04,
          subsample=.85,colsample_bytree=.85,reg_lambda=2,objective='multi:softprob',
          num_class=8,random_state=42,n_jobs=8)
        model.fit(sc.transform(X),y)
        mp=a.out/(name+'_xgboost.json');sp=a.out/(name+'_scaler.joblib')
        model.save_model(mp);joblib.dump(sc,sp)
        (a.out/(name+'.json')).write_text(json.dumps(export(mp,sp),separators=(',',':')))
        print(f'FINAL JS-RAW {name}: {size} features, 800 trees',flush=True)

if __name__=='__main__':main()
