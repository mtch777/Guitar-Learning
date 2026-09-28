#!/usr/bin/env python3
"""Step 14: calibration/personalization experiment.

Question: can a small amount of guitar/player-specific labeled calibration
improve physical-string identification enough to justify the user effort?

The acoustic representation is deliberately the proven lightweight one:
three independent 40 ms MFCC frames over 0-120 ms. Evaluation remains
leave-one-entire-MIDI-out. Calibration examples are selected only from the
training MIDIs for each fold, so no held-out MIDI contributes to its own
personalization.

Methods:
  base       - global 3x40 ms MFCC XGBoost probabilities
  prototype  - blend global probabilities with per-string standardized-feature
               prototype similarity learned from a limited calibration budget
  prior      - lightweight per-string reliability prior from calibration data

Budgets are explicit anchor frets. A budget contributes at most one normal-pick
recording per string/fret where available, keeping user effort interpretable.
"""
from __future__ import annotations
import argparse,json,re,time
from pathlib import Path
import librosa,numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

OPEN={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63}
RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$",re.I)
BUDGETS={"minimal":[0,12],"medium":[0,5,7,12,17,19,24]}
SR=22050

def feat(path):
    y,_=librosa.load(path,sr=SR,mono=True); y,_=librosa.effects.trim(y,top_db=50)
    out=[]
    for a,b in ((0,.04),(.04,.08),(.08,.12)):
        seg=y[int(a*SR):min(len(y),int(b*SR))]
        if len(seg)<128: seg=np.pad(seg,(0,max(0,128-len(seg))))
        m=librosa.feature.mfcc(y=seg,sr=SR,n_mfcc=13)
        for i in range(13): out += [float(m[i].mean()),float(m[i].std())]
    return np.asarray(out,np.float32)

def model():
    return XGBClassifier(n_estimators=100,max_depth=3,learning_rate=.04,subsample=.85,
      colsample_bytree=.85,reg_lambda=2,objective="multi:softprob",num_class=8,
      random_state=42,n_jobs=8)

def mask(p,midi):
    q=p.copy()
    for i,s in enumerate(range(1,9)):
        if not OPEN[s]<=midi<=OPEN[s]+24:q[i]=0
    return q/q.sum() if q.sum() else q

def cal_indices(df,train,frets):
    # one normal recording per string/fret; deterministic fallback to any strength
    z=[]
    for s in range(1,9):
        for f in frets:
            q=[i for i in train if df.iloc[i].string==s and df.iloc[i].fret==f]
            if not q: continue
            normal=[i for i in q if df.iloc[i].strength=="normal"]
            z.append(normal[0] if normal else q[0])
    return np.array(sorted(set(z)),int)

def proto_probs(Zcal,ycal,query):
    centers={}
    for s in range(1,9):
        q=Zcal[ycal==s]
        if len(q):centers[s]=q.mean(axis=0)
    p=np.zeros(8)
    for s,c in centers.items():
        d=np.mean((query-c)**2)
        p[s-1]=np.exp(-d/2)
    return p/p.sum() if p.sum() else p

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--data",type=Path,default=Path("training/data/ringing_384"))
    ap.add_argument("--out",type=Path,required=True);ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    rows=[];xs=[];files=[]
    for p in sorted(a.data.glob("*.wav")):
        m=RX.fullmatch(p.name)
        if m: files.append((p,int(m[1]),int(m[2]),m[3].lower()))
    if a.smoke:
        # Whole pipeline on a small but multi-string/multi-MIDI real subset.
        files=[x for x in files if x[2] in (0,5,12,17,24) and x[3]=="normal"]
    print(f"CAL EXTRACT recordings={len(files)} smoke={a.smoke}",flush=True)
    t=time.time()
    for i,(p,s,f,st) in enumerate(files,1):
        xs.append(feat(p));rows.append(dict(file=p.name,string=s,fret=f,strength=st,midi=OPEN[s]+f))
        if i==1 or i%25==0 or i==len(files):
            e=time.time()-t;print(f"EXTRACT [{i}/{len(files)}] elapsed={e:.1f}s ETA={e/i*(len(files)-i):.1f}s",flush=True)
    X=np.vstack(xs);df=pd.DataFrame(rows);truth=df.string.to_numpy();midis=df.midi.to_numpy()
    budgets={"minimal":BUDGETS["minimal"],"medium":BUDGETS["medium"]}
    methods=["base"]+[f"{b}_{m}" for b in budgets for m in ("prototype","prior")]
    pred={m:np.zeros(len(df),int) for m in methods}; conf={m:np.zeros(len(df)) for m in methods}
    unique=sorted(df.midi.unique())
    for fi,midi in enumerate(unique,1):
        test=np.where(midis==midi)[0];train=np.where(midis!=midi)[0]
        if len(np.unique(truth[train]))<2:continue
        sc=StandardScaler().fit(X[train]);Xt=sc.transform(X[train]);Xq=sc.transform(X[test])
        clf=model().fit(Xt,truth[train]-1); base=clf.predict_proba(Xq)
        for ri,idx in enumerate(test):
            pb=mask(base[ri],midi);pred["base"][idx]=np.argmax(pb)+1;conf["base"][idx]=pb.max()
        for b,frets in budgets.items():
            ci=cal_indices(df,train,frets)
            if len(ci)<2:continue
            Zcal=sc.transform(X[ci]);ycal=truth[ci]
            # calibration reliability prior: Laplace-smoothed per-string global-model correctness
            cp=clf.predict_proba(Zcal); correct=np.zeros(8);count=np.zeros(8)
            for k,idx in enumerate(ci):
                pp=mask(cp[k],midis[idx]);s=truth[idx];count[s-1]+=1;correct[s-1]+=int(np.argmax(pp)+1==s)
            rel=(correct+1)/(count+2); rel=rel/np.mean(rel)
            for ri,idx in enumerate(test):
                pb=mask(base[ri],midi)
                pp=proto_probs(Zcal,ycal,Xq[ri]); pp=mask(pp,midi)
                blend=mask(.8*pb+.2*pp,midi)
                key=f"{b}_prototype";pred[key][idx]=np.argmax(blend)+1;conf[key][idx]=blend.max()
                pr=mask(pb*rel,midi)
                key=f"{b}_prior";pred[key][idx]=np.argmax(pr)+1;conf[key][idx]=pr.max()
        if fi==1 or fi%10==0 or fi==len(unique):
            print(f"FOLD [{fi}/{len(unique)}] MIDI={midi}",flush=True)
    valid=pred["base"]>0
    results={}
    for m in methods:
        v=valid&(pred[m]>0);acc=float(accuracy_score(truth[v],pred[m][v]))
        results[m]={"n":int(v.sum()),"correct":int((truth[v]==pred[m][v]).sum()),"accuracy":acc,
          "errors":int((truth[v]!=pred[m][v]).sum())}
    baseok=pred["base"]==truth
    for m in methods[1:]:
        results[m]["rescues_vs_base"]=int((~baseok&(pred[m]==truth)&valid).sum())
        results[m]["regressions_vs_base"]=int((baseok&(pred[m]!=truth)&valid).sum())
    best=max(methods,key=lambda m:results[m]["accuracy"])
    summary={"step":14,"smoke":a.smoke,"recordings":len(df),"features":int(X.shape[1]),
      "protocol":"leave-one-entire-MIDI-out; calibration anchors drawn only from training MIDIs",
      "budgets":budgets,"methods":results,"best_method":best,"best_accuracy":results[best]["accuracy"],
      "base_accuracy":results["base"]["accuracy"],
      "personalization_survives":bool(best!="base" and results[best]["accuracy"]>results["base"]["accuracy"])}
    out_df=df.copy()
    for m in methods:
        out_df[f"pred_{m}"]=pred[m]
        out_df[f"conf_{m}"]=conf[m]
    out_df.to_csv(a.out/"personalization_predictions.csv",index=False)
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2))
    (a.out/"config.json").write_text(json.dumps({"sr":SR,"frames_ms":[[0,40],[40,80],[80,120]],"n_mfcc":13,"stats":["mean","std"],"budgets":budgets,"prototype_blend":[.8,.2],"trees":100},indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__":main()
