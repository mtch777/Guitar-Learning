#!/usr/bin/env python3
"""Leakage-safe fusion evaluation from preserved out-of-fold predictions.

No base model is retrained. For each held-out MIDI, confidence calibration and
fusion are fitted only on predictions from other MIDIs, then evaluated on the
held-out MIDI.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression

KEY=["file","string","fret","midi","strength"]
MODELS=["baseline","harmonic","mfcc"]

def load_inputs(a):
    def load(p,prefix):
        d=pd.read_csv(p); d[f"{prefix}_correct"]=d.predicted_string==d.string
        return d.rename(columns={"predicted_string":f"{prefix}_pred","confidence":f"{prefix}_conf"})
    b=load(a.baseline,"baseline"); h=load(a.harmonic,"harmonic")
    c=pd.read_csv(a.confirmation); c=c[c.config=="mfcc_cum_0_120"].copy()
    c["mfcc_correct"]=c.predicted_string==c.string
    c=c.rename(columns={"predicted_string":"mfcc_pred","confidence":"mfcc_conf"})
    m=b[KEY+["baseline_pred","baseline_conf","baseline_correct"]]
    m=m.merge(h[KEY+["harmonic_pred","harmonic_conf","harmonic_correct"]],on=KEY,validate="one_to_one")
    m=m.merge(c[KEY+["mfcc_pred","mfcc_conf","mfcc_correct"]],on=KEY,validate="one_to_one")
    assert len(m)==384
    return m

def calibrated_scores(train,test,method):
    out={}
    for model in MODELS:
        x=train[f"{model}_conf"].to_numpy(float); y=train[f"{model}_correct"].astype(int).to_numpy()
        xt=test[f"{model}_conf"].to_numpy(float)
        if method=="logistic":
            cal=LogisticRegression(C=1.0,max_iter=1000).fit(x.reshape(-1,1),y)
            out[model]=cal.predict_proba(xt.reshape(-1,1))[:,1]
        else:
            cal=IsotonicRegression(out_of_bounds="clip",y_min=0,y_max=1).fit(x,y)
            out[model]=cal.predict(xt)
    return out

def choose(test,scores):
    arr=np.column_stack([scores[m] for m in MODELS])
    ix=arr.argmax(axis=1)
    return np.array([test.iloc[i][f"{MODELS[j]}_pred"] for i,j in enumerate(ix)],dtype=int),arr.max(axis=1)

def meta_features(d):
    # Only preserved predictions/confidences and physically known MIDI/fret candidate context.
    conf=np.column_stack([d[f"{m}_conf"].to_numpy(float) for m in MODELS])
    agree=np.column_stack([
      (d.baseline_pred==d.harmonic_pred).astype(float),
      (d.baseline_pred==d.mfcc_pred).astype(float),
      (d.harmonic_pred==d.mfcc_pred).astype(float)])
    return np.column_stack([conf,agree])

def main():
    ap=argparse.ArgumentParser()
    for x in ("baseline","harmonic","confirmation"): ap.add_argument(f"--{x}",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    d=load_inputs(a); rows=[]
    total=len(d.midi.unique()); start=pd.Timestamp.now()
    for n,midi in enumerate(sorted(d.midi.unique()),1):
        tr=d[d.midi!=midi].copy(); te=d[d.midi==midi].copy()
        print(f"START [{n}/{total}] held-out MIDI {midi} ({len(te)} recordings)",flush=True)
        methods={}
        for method in ("logistic","isotonic"):
            scores=calibrated_scores(tr,te,method); pred,score=choose(te,scores)
            methods[f"calibrated_{method}"]=(pred,score)
        # Meta-classifier predicts which base model will be correct. One classifier/model.
        Xtr=meta_features(tr); Xte=meta_features(te); ps=[]
        for model in MODELS:
            y=tr[f"{model}_correct"].astype(int)
            clf=LogisticRegression(C=1.0,max_iter=1000,class_weight="balanced").fit(Xtr,y)
            ps.append(clf.predict_proba(Xte)[:,1])
        parr=np.column_stack(ps); ix=parr.argmax(axis=1)
        pred=np.array([te.iloc[i][f"{MODELS[j]}_pred"] for i,j in enumerate(ix)],dtype=int)
        methods["meta_logistic"]=(pred,parr.max(axis=1))
        truth=te.string.to_numpy(int)
        for method,(pred,score) in methods.items():
            for i,(_,r) in enumerate(te.iterrows()):
                rows.append({"method":method,"file":r.file,"midi":int(r.midi),"string":int(r.string),
                  "predicted_string":int(pred[i]),"score":float(score[i]),"correct":bool(pred[i]==truth[i])})
        elapsed=(pd.Timestamp.now()-start).total_seconds()
        print(f"DONE  [{n}/{total}] MIDI {midi} | elapsed {elapsed:.1f}s",flush=True)
        pd.DataFrame(rows).to_csv(a.out/"fusion_predictions.csv",index=False)

    p=pd.DataFrame(rows); summary={}
    for method,g in p.groupby("method"):
        summary[method]={"correct":int(g.correct.sum()),"errors":int((~g.correct).sum()),"accuracy":float(g.correct.mean())}
    # Non-learned references, computed from preserved predictions.
    maj=[]
    raw=[]
    for _,r in d.iterrows():
        preds=[int(r[f"{m}_pred"]) for m in MODELS]
        vals,counts=np.unique(preds,return_counts=True)
        if counts.max()>=2: maj.append(int(vals[counts.argmax()]))
        else: maj.append(int(r[f"{MODELS[int(np.argmax([r[f'{m}_conf'] for m in MODELS]))]}_pred"]))
        k=MODELS[int(np.argmax([r[f"{m}_conf"] for m in MODELS]))]; raw.append(int(r[f"{k}_pred"]))
    for name,pred in (("majority_vote",maj),("raw_highest_confidence",raw)):
        ok=np.asarray(pred)==d.string.to_numpy(int)
        summary[name]={"correct":int(ok.sum()),"errors":int((~ok).sum()),"accuracy":float(ok.mean())}
    (a.out/"summary.json").write_text(json.dumps({"protocol":"leave-one-entire-MIDI-out fusion fitting","recordings":len(d),"results":summary},indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__": main()
