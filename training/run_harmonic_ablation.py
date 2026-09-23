#!/usr/bin/env python3
"""Exhaustive harmonic-feature ablation for the ringing string classifier.

Uses the exact baseline + harmonic extraction in train_full_ringing.py, evaluates
with leave-one-pitch-out candidate masking, and writes ranked CSV/JSON results.
"""
from __future__ import annotations
import argparse, json, re, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from train_full_ringing import OPEN_MIDI, RX, extract, mask

def make_model(n):
    return XGBClassifier(
        n_estimators=n,max_depth=3,learning_rate=.04,subsample=.85,
        colsample_bytree=.85,reg_lambda=2,objective="multi:softprob",
        num_class=8,random_state=42,n_jobs=8)

def evaluate(X, df, cols, trees):
    truth=df.string.to_numpy()
    pred=np.zeros(len(df),dtype=int)
    for midi in sorted(df.midi.unique()):
        test=np.where(df.midi.to_numpy()==midi)[0]
        train=np.where(df.midi.to_numpy()!=midi)[0]
        scaler=StandardScaler().fit(X[train][:,cols])
        clf=make_model(trees).fit(scaler.transform(X[train][:,cols]),truth[train]-1)
        probs=clf.predict_proba(scaler.transform(X[test][:,cols]))
        for row_i,idx in enumerate(test):
            p=mask(probs[row_i],int(midi))
            pred[idx]=int(np.argmax(p))+1
    return int((truth==pred).sum()),float(accuracy_score(truth,pred))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("wav_dir",type=Path)
    ap.add_argument("--out",type=Path,default=Path("training/results/harmonic_ablation"))
    ap.add_argument("--screen-trees",type=int,default=20)
    ap.add_argument("--final-trees",type=int,default=100)
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)

    rows=[]; xs=[]; names=None
    print("Extracting features...")
    for path in sorted(a.wav_dir.glob("*.wav")):
        if "muted" in path.name.lower(): continue
        m=RX.fullmatch(path.name)
        if not m: continue
        s,f=int(m[1]),int(m[2])
        x,n=extract(path,s,f,"full")
        xs.append(x); names=n
        rows.append({"string":s,"fret":f,"strength":m[3].lower(),"file":path.name,
                     "midi":OPEN_MIDI[s]+f})
    if not rows: raise RuntimeError("No ringing WAVs found")
    X=np.vstack(xs); df=pd.DataFrame(rows)
    baseline=list(range(107))
    harmonic=list(range(107,len(names)))

    # Simple harmonic ratios and deltas only: exclude width/detune/contrast.
    ratios=[i for i in harmonic if "_db_vs_h1" in names[i]]
    deltas=[i for i in harmonic if "_delta_db" in names[i]]
    simple=ratios+deltas
    attack=[i for i in ratios if "harm_attack_" in names[i]]
    early=[i for i in ratios if "harm_early_" in names[i]]
    late=[i for i in ratios if "harm_late_" in names[i]]

    experiments=[
      ("baseline107",baseline),
      ("baseline+attack_ratios",baseline+attack),
      ("baseline+early_ratios",baseline+early),
      ("baseline+late_ratios",baseline+late),
      ("baseline+all_ratios",baseline+ratios),
      ("baseline+deltas",baseline+deltas),
      ("baseline+ratios+deltas",baseline+simple),
    ]

    # Rank each simple harmonic by candidate-restricted univariate separation:
    # between-position variance / within-position variance for the same MIDI.
    scores=[]
    for i in simple:
        between=[]; within=[]
        for midi,g in df.assign(_x=X[:,i]).groupby("midi"):
            means=g.groupby(["string","fret"])._x.mean()
            if len(means)<2: continue
            between.append(float(np.var(means)))
            for _,pg in g.groupby(["string","fret"]):
                if len(pg)>1: within.append(float(np.var(pg._x)))
        b=np.mean(between) if between else 0
        w=np.mean(within) if within else 0
        scores.append((b/(w+1e-9),i))
    ranked=[i for _,i in sorted(scores,reverse=True)]
    for k in (1,2,3,5,7,10,14,21,28,35):
        if k<=len(ranked):
            experiments.append((f"baseline+ranked_top_{k}",baseline+ranked[:k]))
    for i in ranked:
        experiments.append((f"baseline+single::{names[i]}",baseline+[i]))

    results=[]
    print(f"{len(df)} recordings, {len(names)} total features, {len(experiments)} screening experiments")
    for n,(label,cols) in enumerate(experiments,1):
        t=time.time(); correct,acc=evaluate(X,df,cols,a.screen_trees)
        row={"experiment":label,"features":len(cols),"trees":a.screen_trees,
             "correct":correct,"total":len(df),"accuracy":acc,
             "seconds":round(time.time()-t,2)}
        results.append(row)
        pd.DataFrame(results).sort_values(["accuracy","features"],ascending=[False,True]).to_csv(
            a.out/"screening_results.csv",index=False)
        print(f"[{n}/{len(experiments)}] {label}: {correct}/{len(df)} = {acc:.4%}")

    ranked_results=sorted(results,key=lambda r:(-r["accuracy"],r["features"]))
    # Confirm baseline + top five screening configurations at 100 trees.
    finalists=[next(r for r in results if r["experiment"]=="baseline107")]
    finalists += [r for r in ranked_results if r["experiment"]!="baseline107"][:5]
    final=[]
    lookup=dict(experiments)
    print("\n100-tree confirmation...")
    for r in finalists:
        label=r["experiment"]; cols=lookup[label]
        t=time.time(); correct,acc=evaluate(X,df,cols,a.final_trees)
        row={"experiment":label,"features":len(cols),"trees":a.final_trees,
             "correct":correct,"total":len(df),"accuracy":acc,
             "seconds":round(time.time()-t,2)}
        final.append(row)
        pd.DataFrame(final).sort_values(["accuracy","features"],ascending=[False,True]).to_csv(
            a.out/"final_results.csv",index=False)
        print(f"{label}: {correct}/{len(df)} = {acc:.4%}")

    summary={
      "recordings":len(df),"total_features":len(names),
      "screen_trees":a.screen_trees,"final_trees":a.final_trees,
      "best_screening":sorted(results,key=lambda r:(-r["accuracy"],r["features"]))[0],
      "best_final":sorted(final,key=lambda r:(-r["accuracy"],r["features"]))[0],
    }
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2))
    pd.DataFrame({"rank":range(1,len(ranked)+1),
                  "feature":[names[i] for i in ranked],
                  "separation_score":[dict((i,s) for s,i in scores)[i] for i in ranked]}).to_csv(
                      a.out/"harmonic_feature_ranking.csv",index=False)
    print("\n"+json.dumps(summary,indent=2))

if __name__=="__main__": main()
