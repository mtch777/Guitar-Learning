#!/usr/bin/env python3
"""Step 8: multi-frame temporal aggregation for physical-string classification.

Extracts one compact MFCC representation per short onset-relative frame, trains
one classifier per frame under leave-one-entire-MIDI-out validation, then
combines candidate-masked probabilities across time. This directly tests
whether temporal evidence beats the current single-window 0-120 ms MFCC model.

Every reported prediction for a held-out MIDI is produced only by models that
never trained on that MIDI.
"""
from __future__ import annotations
import argparse,json,re,time
from pathlib import Path
import librosa,numpy as np,pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

OPEN={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63}
RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$",re.I)
FRAMES=[("f0_40",0,.04),("f40_80",.04,.08),("f80_120",.08,.12),
        ("f120_160",.12,.16),("f160_200",.16,.20),("f200_240",.20,.24)]
EPS=1e-12

def model(n):
    return XGBClassifier(n_estimators=n,max_depth=3,learning_rate=.04,subsample=.85,
      colsample_bytree=.85,reg_lambda=2,objective="multi:softprob",num_class=8,
      random_state=42,n_jobs=8)

def mask(p,midi):
    q=p.copy()
    for i,s in enumerate(range(1,9)):
        if not (OPEN[s]<=midi<=OPEN[s]+24): q[i]=0
    z=q.sum()
    return q/z if z else q

def mfcc26(y,sr,t0,t1):
    a=int(t0*sr); b=min(len(y),max(a+1,int(t1*sr))); seg=y[a:b]
    if len(seg)<128: seg=np.pad(seg,(0,128-len(seg)))
    nfft=max(64,2**int(np.floor(np.log2(len(seg)))))
    nfft=min(2048,nfft,len(seg)); hop=max(16,nfft//4); n_mels=min(40,max(16,nfft//8))
    m=librosa.feature.mfcc(y=seg,sr=sr,n_mfcc=13,n_fft=nfft,hop_length=hop,n_mels=n_mels)
    return np.asarray([v for i in range(13) for v in (np.mean(m[i]),np.std(m[i]))],np.float32)

def load(wav_dir,smoke):
    rec=[]
    for p in sorted(wav_dir.glob("*.wav")):
        m=RX.fullmatch(p.name)
        if not m: continue
        s,f=int(m[1]),int(m[2]); midi=OPEN[s]+f
        if smoke and not (54<=midi<=60 and m[3].lower()=="normal"): continue
        y,sr=librosa.load(p,sr=22050,mono=True); y,_=librosa.effects.trim(y,top_db=50)
        rec.append((p.name,s,f,m[3].lower(),midi,y,sr))
    df=pd.DataFrame([{"file":r[0],"string":r[1],"fret":r[2],"strength":r[3],"midi":r[4]} for r in rec])
    return rec,df

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("wav_dir",type=Path)
    ap.add_argument("--out",type=Path,required=True); ap.add_argument("--trees",type=int,default=100)
    ap.add_argument("--smoke",action="store_true"); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    rec,df=load(a.wav_dir,a.smoke)
    print(f"Loaded {len(df)} recordings; extracting {len(FRAMES)} temporal frames",flush=True)
    X=[]
    st=time.time()
    for k,(name,t0,t1) in enumerate(FRAMES,1):
        X.append(np.vstack([mfcc26(r[5],r[6],t0,t1) for r in rec]))
        print(f"EXTRACT [{k}/{len(FRAMES)}] {name} | elapsed {time.time()-st:.1f}s",flush=True)
    truth=df.string.to_numpy(int); midis=sorted(df.midi.unique()); n=len(df)
    # Store masked per-frame probabilities from held-out-MIDI models.
    P=np.zeros((n,len(FRAMES),8),float)
    total=len(midis)*len(FRAMES); done=0; st=time.time()
    for midi in midis:
        te=np.where(df.midi.to_numpy()==midi)[0]; tr=np.where(df.midi.to_numpy()!=midi)[0]
        for fi,(name,_,_) in enumerate(FRAMES):
            sc=StandardScaler().fit(X[fi][tr]); clf=model(20 if a.smoke else a.trees)
            clf.fit(sc.transform(X[fi][tr]),truth[tr]-1)
            probs=clf.predict_proba(sc.transform(X[fi][te]))
            for j,idx in enumerate(te): P[idx,fi]=mask(probs[j],int(midi))
            done+=1; elapsed=time.time()-st; eta=elapsed/done*(total-done)
            print(f"MODEL [{done}/{total}] MIDI {midi} {name} | elapsed {elapsed/60:.1f}m ETA {eta/60:.1f}m",flush=True)
    methods={}
    # Individual 40-ms frames.
    for fi,(name,_,_) in enumerate(FRAMES): methods[name]=P[:,fi,:]
    # Uniform cumulative temporal evidence.
    for k in range(2,len(FRAMES)+1): methods[f"mean_first_{k}_frames"]=P[:,:k,:].mean(axis=1)
    # Recency-weighted cumulative evidence: later stable frames receive more weight.
    for k in range(2,len(FRAMES)+1):
        w=np.arange(1,k+1,dtype=float); w/=w.sum()
        methods[f"recency_first_{k}_frames"]=np.sum(P[:,:k,:]*w[None,:,None],axis=1)
    rows=[]; summary={}
    for name,prob in methods.items():
        pred=prob.argmax(axis=1)+1; conf=prob.max(axis=1); acc=float(accuracy_score(truth,pred))
        summary[name]={"correct":int((pred==truth).sum()),"errors":int((pred!=truth).sum()),"accuracy":acc}
        for i,r in df.iterrows(): rows.append({"method":name,"file":r.file,"string":int(r.string),"fret":int(r.fret),"midi":int(r.midi),"strength":r.strength,"predicted_string":int(pred[i]),"confidence":float(conf[i]),"correct":bool(pred[i]==truth[i])})
    best=max(summary,key=lambda x:summary[x]["accuracy"])
    out={"step":8,"smoke":a.smoke,"recordings":n,"frames":[{"name":x[0],"t0_ms":round(x[1]*1000),"t1_ms":round(x[2]*1000)} for x in FRAMES],"trees":20 if a.smoke else a.trees,"best_method":best,"best":summary[best],"methods":summary,"reference":{"single_window_mfcc_0_120_correct":370,"single_window_mfcc_0_120_accuracy":370/384,"current_fusion_correct":379,"current_fusion_accuracy":379/384}}
    pd.DataFrame(rows).to_csv(a.out/"temporal_predictions.csv",index=False)
    (a.out/"summary.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2),flush=True)

if __name__=="__main__": main()
