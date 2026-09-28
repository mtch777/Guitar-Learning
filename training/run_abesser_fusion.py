#!/usr/bin/env python3
"""Step 7: test whether preserved Abeßer predictions add useful fusion evidence.

No base model is retrained. Every input is an out-of-fold prediction preserved
from completed experiments. Learned calibration/fusion is fit leave-one-entire-
MIDI-out so the held-out pitch never trains its own fusion rule.
"""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

KEY=["file","string","midi"]
STRONG=["baseline","harmonic","mfcc"]
ALL=STRONG+["abesser"]

def load(a):
    def one(path,name):
        d=pd.read_csv(path).copy()
        d[f"{name}_correct"]=d.predicted_string.eq(d.string)
        return d.rename(columns={"predicted_string":f"{name}_pred","confidence":f"{name}_conf"})
    b=one(a.baseline,"baseline"); h=one(a.harmonic,"harmonic")
    c=pd.read_csv(a.confirmation); c=c[c.config.eq("mfcc_cum_0_120")].copy()
    c["mfcc_correct"]=c.predicted_string.eq(c.string)
    c=c.rename(columns={"predicted_string":"mfcc_pred","confidence":"mfcc_conf"})
    ab=one(a.abesser,"abesser")
    d=b[KEY+["baseline_pred","baseline_conf","baseline_correct"]]
    d=d.merge(h[KEY+["harmonic_pred","harmonic_conf","harmonic_correct"]],on=KEY,validate="one_to_one")
    d=d.merge(c[KEY+["mfcc_pred","mfcc_conf","mfcc_correct"]],on=KEY,validate="one_to_one")
    d=d.merge(ab[KEY+["abesser_pred","abesser_conf","abesser_correct"]],on=KEY,validate="one_to_one")
    assert len(d)==384 and d.file.nunique()==384
    return d

def overlap(d):
    out={"individual":{},"abesser_error_overlap":{}}
    for m in ALL:
        out["individual"][m]={"correct":int(d[f"{m}_correct"].sum()),"errors":int((~d[f"{m}_correct"]).sum()),"accuracy":float(d[f"{m}_correct"].mean())}
    for m in STRONG:
        out["abesser_error_overlap"][m]=int((~d.abesser_correct & ~d[f"{m}_correct"]).sum())
    out["abesser_unique_save_vs_three_strong"]=int((d.abesser_correct & ~d.baseline_correct & ~d.harmonic_correct & ~d.mfcc_correct).sum())
    out["oracle_three_strong"]={"correct":int(d[[f"{m}_correct" for m in STRONG]].any(axis=1).sum())}
    out["oracle_four_models"]={"correct":int(d[[f"{m}_correct" for m in ALL]].any(axis=1).sum())}
    return out

def calibrated_correctness(train,test,models,kind):
    scores={}
    for m in models:
        x=train[f"{m}_conf"].to_numpy(float); y=train[f"{m}_correct"].astype(int).to_numpy(); xt=test[f"{m}_conf"].to_numpy(float)
        if kind=="isotonic":
            cal=IsotonicRegression(out_of_bounds="clip",y_min=0,y_max=1).fit(x,y); scores[m]=cal.predict(xt)
        else:
            cal=LogisticRegression(C=1,max_iter=1000).fit(x.reshape(-1,1),y); scores[m]=cal.predict_proba(xt.reshape(-1,1))[:,1]
    return scores

def choose(test,scores,models):
    a=np.column_stack([scores[m] for m in models]); ix=a.argmax(axis=1)
    pred=np.array([int(test.iloc[i][f"{models[j]}_pred"]) for i,j in enumerate(ix)])
    return pred,a.max(axis=1),np.array([models[j] for j in ix])

def meta_features(d,models):
    conf=np.column_stack([d[f"{m}_conf"].to_numpy(float) for m in models])
    agree=[]
    for i in range(len(models)):
        for j in range(i+1,len(models)):
            agree.append((d[f"{models[i]}_pred"]==d[f"{models[j]}_pred"]).astype(float).to_numpy())
    return np.column_stack([conf]+agree)

def eval_fusion(d,out,smoke):
    # Smoke traverses the entire fitting/calibration/output cycle on a real subset.
    mids=sorted(d.midi.unique())
    if smoke:
        mids=[m for m in mids if 54<=m<=60]
        work=d[d.midi.isin(mids)].copy()
    else: work=d.copy()
    rows=[]; start=time.time(); total=len(mids)
    for n,midi in enumerate(mids,1):
        te=work[work.midi.eq(midi)].copy()
        # Real run trains fusion on every other MIDI. Smoke uses its small real subset.
        tr=work[~work.midi.eq(midi)].copy()
        if tr.midi.nunique()<3: raise RuntimeError("not enough training MIDI groups")
        truth=te.string.to_numpy(int)
        methods={}
        for models,label in ((STRONG,"three"),(ALL,"four")):
            for kind in ("logistic","isotonic"):
                sc=calibrated_correctness(tr,te,models,kind)
                methods[f"{label}_calibrated_{kind}"]=choose(te,sc,models)
            Xtr=meta_features(tr,models); Xte=meta_features(te,models); ps=[]
            for m in models:
                y=tr[f"{m}_correct"].astype(int)
                clf=LogisticRegression(C=1,max_iter=1000,class_weight="balanced").fit(Xtr,y)
                ps.append(clf.predict_proba(Xte)[:,1])
            parr=np.column_stack(ps); ix=parr.argmax(axis=1)
            pred=np.array([int(te.iloc[i][f"{models[j]}_pred"]) for i,j in enumerate(ix)])
            methods[f"{label}_meta_logistic"]=(pred,parr.max(axis=1),np.array([models[j] for j in ix]))
        for method,(pred,score,selected) in methods.items():
            for i,(_,r) in enumerate(te.iterrows()):
                rows.append({"method":method,"file":r.file,"midi":int(r.midi),"string":int(r.string),"predicted_string":int(pred[i]),"score":float(score[i]),"selected_model":str(selected[i]),"correct":bool(pred[i]==truth[i])})
        elapsed=time.time()-start; eta=elapsed/n*(total-n)
        print(f"FUSION FOLD [{n}/{total}] MIDI {midi} | elapsed {elapsed:.1f}s ETA {eta:.1f}s",flush=True)
        pd.DataFrame(rows).to_csv(out/"fusion_predictions.csv",index=False)
    p=pd.DataFrame(rows); results={}
    for method,g in p.groupby("method"):
        results[method]={"correct":int(g.correct.sum()),"errors":int((~g.correct).sum()),"accuracy":float(g.correct.mean()),"abesser_selected":int(g.selected_model.eq("abesser").sum())}
    return results,work

def main():
    ap=argparse.ArgumentParser()
    for x in ("baseline","harmonic","confirmation","abesser"): ap.add_argument(f"--{x}",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True); ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    d=load(a); ov=overlap(d)
    results,work=eval_fusion(d,a.out,a.smoke)
    summary={"step":7,"smoke":a.smoke,"protocol":"preserved out-of-fold base predictions; leave-one-entire-MIDI-out fusion fitting","recordings":len(work),"overlap_full_dataset":ov,"fusion":results}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__": main()
