#!/usr/bin/env python3
"""Step 6: compare classifiers on the same Abeßer 48D representation.

Reuses the Step-5 extractor without rerunning any completed prior experiment.
Evaluation remains leave-one-entire-MIDI-out. Hyperparameter selection is
3-fold GroupKFold by MIDI inside each outer fold. Five post-transition frames
are aggregated per recording, then the physical candidate mask is applied.
"""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.ensemble import ExtraTreesClassifier,RandomForestClassifier,HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score,f1_score,confusion_matrix
from sklearn.model_selection import GroupKFold,GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from run_abesser_reproduction import OPEN,RX,extract_record,possible

def models(smoke):
    if smoke:
        return {
          "random_forest":(RandomForestClassifier(random_state=42,n_jobs=-1),{"clf__n_estimators":[40],"clf__max_depth":[None]}),
          "extra_trees":(ExtraTreesClassifier(random_state=42,n_jobs=-1),{"clf__n_estimators":[40],"clf__max_depth":[None]}),
          "hist_gradient_boosting":(HistGradientBoostingClassifier(random_state=42),{"clf__max_iter":[40],"clf__learning_rate":[.1]}),
          "logistic":(LogisticRegression(max_iter=1500),{"clf__C":[1.0]}),
        }
    return {
      "random_forest":(RandomForestClassifier(random_state=42,n_jobs=-1),{"clf__n_estimators":[200,500],"clf__max_depth":[None,8,16],"clf__min_samples_leaf":[1,2]}),
      "extra_trees":(ExtraTreesClassifier(random_state=42,n_jobs=-1),{"clf__n_estimators":[200,500],"clf__max_depth":[None,8,16],"clf__min_samples_leaf":[1,2]}),
      "hist_gradient_boosting":(HistGradientBoostingClassifier(random_state=42),{"clf__max_iter":[100,200],"clf__learning_rate":[.05,.1],"clf__max_leaf_nodes":[15,31],"clf__l2_regularization":[0,1]}),
      "logistic":(LogisticRegression(max_iter=2000),{"clf__C":[.1,1,10]}),
    }

def build_dataset(wav_dir,order,smoke,out):
    meta=[]
    for p in sorted(wav_dir.glob("*.wav")):
        m=RX.fullmatch(p.name)
        if m:
            s,f=int(m[1]),int(m[2]); meta.append({"file":p.name,"path":p,"string":s,"fret":f,"strength":m[3].lower(),"midi":OPEN[s]+f})
    full=pd.DataFrame(meta); assert len(full)==384
    if smoke:
        df=full[(full.strength=="normal")&(full.midi>=54)&(full.midi<=60)].copy().reset_index(drop=True)
        assert len(df)>=20 and df.midi.nunique()>=5 and df.string.nunique()>=4
    else: df=full.reset_index(drop=True)
    X=[];diag=[];start=time.time()
    for i,r in df.iterrows():
        z=extract_record(r.path,int(r.midi),order)
        if z is None: feats=np.full((5,48),np.nan); tstar=-1;npart=0
        else: feats,tstar,npart=z
        X.append(feats);diag.append({"file":r.file,"tstar":tstar,"observable_partials":npart})
        if (i+1)%24==0 or i+1==len(df):
            elapsed=time.time()-start; eta=elapsed/(i+1)*(len(df)-i-1)
            print(f"EXTRACT [{i+1}/{len(df)}] elapsed {elapsed/60:.1f}m ETA {eta/60:.1f}m",flush=True)
    arr=np.asarray(X,float); assert arr.shape[1:]==(5,48) and np.isfinite(arr).any()
    pd.DataFrame(diag).to_csv(out/"diagnostics.csv",index=False)
    return df,arr

def evaluate(name,base,grid,df,X,out):
    truth=df.string.to_numpy(int); pred=np.zeros(len(df),int); conf=np.zeros(len(df)); rows=[]
    midis=sorted(df.midi.unique()); start=time.time()
    for fi,midi in enumerate(midis,1):
        test=np.where(df.midi.to_numpy()==midi)[0]; train=np.where(df.midi.to_numpy()!=midi)[0]
        Xt=[];yt=[];groups=[]
        for ridx in train:
            for frame in X[ridx]:
                if np.isfinite(frame).any():
                    Xt.append(frame);yt.append(truth[ridx]);groups.append(int(df.iloc[ridx].midi))
        Xt=np.asarray(Xt);yt=np.asarray(yt);groups=np.asarray(groups)
        pipe=Pipeline([("imp",SimpleImputer(strategy="median",keep_empty_features=True)),("scale",StandardScaler()),("clf",base)])
        splits=list(GroupKFold(3).split(Xt,yt,groups))
        gs=GridSearchCV(pipe,grid,cv=splits,scoring="f1_macro",n_jobs=-1)
        gs.fit(Xt,yt); model=gs.best_estimator_; classes=model.named_steps["clf"].classes_
        for ridx in test:
            valid=np.asarray([f for f in X[ridx] if np.isfinite(f).any()])
            probs=model.predict_proba(valid).sum(axis=0)
            allowed=set(possible(int(df.iloc[ridx].midi)))
            probs=np.array([v if int(c) in allowed else 0. for c,v in zip(classes,probs)])
            j=int(np.argmax(probs));pred[ridx]=int(classes[j]);conf[ridx]=float(probs[j]/max(probs.sum(),1e-12))
            rows.append({"model":name,"file":df.iloc[ridx].file,"midi":int(midi),"string":int(truth[ridx]),"predicted_string":int(pred[ridx]),"confidence":conf[ridx],"correct":bool(pred[ridx]==truth[ridx]),"best_params":json.dumps(gs.best_params_,sort_keys=True)})
        elapsed=time.time()-start;eta=elapsed/fi*(len(midis)-fi)
        print(f"{name} FOLD [{fi}/{len(midis)}] MIDI {midi} | elapsed {elapsed/60:.1f}m ETA {eta/60:.1f}m",flush=True)
        pd.DataFrame(rows).to_csv(out/f"predictions_{name}.csv",index=False)
    acc=float(accuracy_score(truth,pred));macro=float(f1_score(truth,pred,average="macro"))
    pd.DataFrame(confusion_matrix(truth,pred,labels=range(1,9)),index=range(1,9),columns=range(1,9)).to_csv(out/f"confusion_{name}.csv")
    return {"model":name,"accuracy":acc,"macro_f1":macro,"correct":int((pred==truth).sum()),"errors":int((pred!=truth).sum())}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("wav_dir",type=Path);ap.add_argument("--out",type=Path,required=True);ap.add_argument("--order",type=int,default=32);ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    df,X=build_dataset(a.wav_dir,a.order,a.smoke,a.out)
    results=[]
    for i,(name,(model,grid)) in enumerate(models(a.smoke).items(),1):
        print(f"START MODEL [{i}/{len(models(a.smoke))}] {name}",flush=True)
        r=evaluate(name,model,grid,df,X,a.out);results.append(r)
        (a.out/"summary.json").write_text(json.dumps({"ar_order":a.order,"smoke":a.smoke,"results":results},indent=2))
        print(f"DONE {name}: {r['accuracy']:.4%} macro-F1={r['macro_f1']:.4f}",flush=True)
    print(json.dumps(results,indent=2),flush=True)
if __name__=="__main__": main()
