#!/usr/bin/env python3
"""Step 16: final time x surviving-method tournament.

Small predeclared Pareto comparison only; no broad search.
Stage B is the proven candidate-masked MFCC temporal model at 80/120/160 ms.
Stage A is the surviving YIN family at 80/120/160/200/240 ms.
The script reports accuracy and measured Python inference runtime separately,
then a simple availability time (= required audio window + measured inference)
for Pareto analysis. No trainer context is used.
"""
from __future__ import annotations
import argparse,json,re,time
from pathlib import Path
import librosa,numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

OPEN={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63}
RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$",re.I)
B_TIMES=(80,120,160); A_TIMES=(80,120,160,200,240)
FRAMES=((0,.04),(.04,.08),(.08,.12),(.12,.16))
MIN_HZ=35.;MAX_HZ=1600.

def mfcc26(y,sr,a,b):
    seg=y[int(a*sr):min(len(y),max(int(a*sr)+1,int(b*sr)))]
    if len(seg)<128:seg=np.pad(seg,(0,128-len(seg)))
    nfft=max(64,2**int(np.floor(np.log2(len(seg)))));nfft=min(2048,nfft,len(seg))
    hop=max(16,nfft//4);nm=min(40,max(16,nfft//8))
    m=librosa.feature.mfcc(y=seg,sr=sr,n_mfcc=13,n_fft=nfft,hop_length=hop,n_mels=nm)
    return np.array([v for z in m for v in (z.mean(),z.std())],np.float32)

def mask(p,midi):
    q=p.copy()
    for i,s in enumerate(range(1,9)):
        if not OPEN[s]<=midi<=OPEN[s]+24:q[i]=0
    return q/q.sum() if q.sum() else q

def model(n,k):
    return XGBClassifier(n_estimators=n,max_depth=3,learning_rate=.04,subsample=.85,
      colsample_bytree=.85,reg_lambda=2,objective="multi:softprob",num_class=k,
      random_state=42,n_jobs=8)

def hz_midi(f):
    return int(round(69+12*np.log2(f/440.))) if np.isfinite(f) and f>0 else None

def lyin(y,sr):
    try:
        fl=min(4096,max(256,2**int(np.floor(np.log2(len(y))))))
        f=librosa.yin(y,fmin=MIN_HZ,fmax=MAX_HZ,sr=sr,frame_length=fl)
        v=f[np.isfinite(f)];return float(np.median(v)) if len(v) else np.nan
    except Exception:return np.nan

def cyin(y,sr,thr=.18):
    lo=max(2,int(sr/MAX_HZ));hi=min(int(sr/MIN_HZ),len(y)//2)
    if hi<=lo+2:return np.nan
    d=np.zeros(hi+1);cm=np.ones(hi+1);run=0.
    for tau in range(1,hi+1):
        z=y[:-tau]-y[tau:];d[tau]=np.dot(z,z);run+=d[tau];cm[tau]=d[tau]*tau/run if run else 1
    tau=None
    for x in range(lo,hi):
        if cm[x]<thr and cm[x]<=cm[x+1]:tau=x;break
    if tau is None:tau=min(range(lo,hi+1),key=lambda x:cm[x])
    return sr/tau

def pareto(rows,acc_key,time_key):
    out=[]
    for r in rows:
        dominated=any((q[acc_key]>=r[acc_key] and q[time_key]<=r[time_key]) and
                      (q[acc_key]>r[acc_key] or q[time_key]<r[time_key]) for q in rows)
        if not dominated:out.append(r["method"])
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("wav_dir",type=Path);ap.add_argument("--out",type=Path,required=True);ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    rec=[]
    for p in sorted(a.wav_dir.glob("*.wav")):
        m=RX.fullmatch(p.name)
        if not m:continue
        s,f=int(m[1]),int(m[2]);midi=OPEN[s]+f
        if a.smoke and not (54<=midi<=60 and m[3].lower()=="normal"):continue
        y,sr=librosa.load(p,sr=22050,mono=True);y,_=librosa.effects.trim(y,top_db=50)
        rec.append((p.name,s,f,m[3].lower(),midi,y,sr))
    df=pd.DataFrame([dict(file=r[0],string=r[1],fret=r[2],strength=r[3],midi=r[4]) for r in rec])
    print(f"FINAL TIME loaded={len(df)} smoke={a.smoke}",flush=True)
    truth=df.string.to_numpy(int);mids=df.midi.to_numpy(int);n=len(df)
    # Stage B: exactly the Step-8 frame recipe, but only first four frames needed.
    X=[];feat_ms=[];t=time.time()
    for k,(x0,x1) in enumerate(FRAMES,1):
        z=[];rt=[]
        for r in rec:
            q=time.perf_counter();z.append(mfcc26(r[5],r[6],x0,x1));rt.append((time.perf_counter()-q)*1000)
        X.append(np.vstack(z));feat_ms.append(float(np.mean(rt)))
        print(f"EXTRACT [{k}/4] {int(x0*1000)}-{int(x1*1000)}ms elapsed={time.time()-t:.1f}s",flush=True)
    P=np.zeros((n,4,8));infer=np.zeros((n,4))
    unique=sorted(df.midi.unique());total=len(unique)*4;done=0;t=time.time()
    for midi in unique:
        te=np.where(mids==midi)[0];tr=np.where(mids!=midi)[0]
        for fi in range(4):
            classes=np.sort(np.unique(truth[tr]));enc={s:i for i,s in enumerate(classes)}
            sc=StandardScaler().fit(X[fi][tr]);clf=model(20 if a.smoke else 100,len(classes))
            clf.fit(sc.transform(X[fi][tr]),np.array([enc[s] for s in truth[tr]]))
            q=time.perf_counter();raw=clf.predict_proba(sc.transform(X[fi][te]));dt=(time.perf_counter()-q)*1000/max(1,len(te))
            p=np.zeros((len(te),8))
            for ci,s in enumerate(classes):p[:,s-1]=raw[:,ci]
            for j,idx in enumerate(te):P[idx,fi]=mask(p[j],midi);infer[idx,fi]=dt
            done+=1;e=time.time()-t
            print(f"MODEL [{done}/{total}] MIDI={midi} frame={fi+1}/4 elapsed={e:.1f}s ETA={e/done*(total-done):.1f}s",flush=True)
    b_rows=[]
    for ms,k in ((80,2),(120,3),(160,4)):
        prob=P[:,:k].mean(1);pred=prob.argmax(1)+1
        inf=float(np.mean(infer[:,:k].sum(1)));feat=float(sum(feat_ms[:k]))
        b_rows.append(dict(method=f"temporal_mfcc_{ms}ms",window_ms=ms,correct=int((pred==truth).sum()),accuracy=float(np.mean(pred==truth)),feature_runtime_ms=feat,inference_runtime_ms=inf,availability_ms=ms+feat+inf))
    # Stage A: surviving YIN methods only.
    a_rows=[];pred_rows=[];total=n*len(A_TIMES)*2;done=0;t=time.time()
    stats={(name,ms):[] for name in ("librosa_yin","custom_yin") for ms in A_TIMES}
    for ri,r in enumerate(rec):
        for ms in A_TIMES:
            seg=r[5][:min(len(r[5]),max(128,int(r[6]*ms/1000)))]
            for name,fn in (("librosa_yin",lyin),("custom_yin",cyin)):
                q=time.perf_counter();hz=fn(seg,r[6]);rt=(time.perf_counter()-q)*1000;pm=hz_midi(hz)
                stats[(name,ms)].append((pm,rt));done+=1
        if ri==0 or (ri+1)%25==0 or ri+1==n:
            e=time.time()-t;print(f"PITCH [{done}/{total}] recordings={ri+1}/{n} elapsed={e:.1f}s ETA={e/done*(total-done):.1f}s",flush=True)
    for (name,ms),vals in stats.items():
        pred=np.array([x[0] if x[0] is not None else -999 for x in vals]);rt=float(np.mean([x[1] for x in vals]))
        a_rows.append(dict(method=f"{name}_{ms}ms",window_ms=ms,correct=int(np.sum(pred==mids)),accuracy=float(np.mean(pred==mids)),inference_runtime_ms=rt,availability_ms=ms+rt))
        for i,x in enumerate(vals):pred_rows.append(dict(file=df.iloc[i].file,detector=name,window_ms=ms,true_midi=int(mids[i]),pred_midi=x[0],runtime_ms=x[1]))
    out={"step":16,"smoke":a.smoke,"recordings":n,"scope":"survivor-only timing grid; no trainer context",
      "stage_b":b_rows,"stage_b_pareto":pareto(b_rows,"accuracy","availability_ms"),
      "stage_a":a_rows,"stage_a_pareto":pareto(a_rows,"accuracy","availability_ms"),
      "references":{"step8_120ms_correct":376,"step9_librosa_yin_240ms_correct":375,"step9_custom_yin_160ms_correct":374}}
    pd.DataFrame(pred_rows).to_csv(a.out/"pitch_predictions.csv",index=False)
    pd.DataFrame(b_rows+a_rows).to_csv(a.out/"time_method_metrics.csv",index=False)
    (a.out/"summary.json").write_text(json.dumps(out,indent=2))
    (a.out/"config.json").write_text(json.dumps({"stage_b_ms":B_TIMES,"stage_a_ms":A_TIMES,"mfcc_frames_ms":[[0,40],[40,80],[80,120],[120,160]],"trees":20 if a.smoke else 100},indent=2))
    print(json.dumps(out,indent=2),flush=True)
if __name__=="__main__":main()
