#!/usr/bin/env python3
"""Step 15: physical candidate-mask + trainer-context ablations.

Layers are kept separate:
 A raw_acoustic_40ms: first-frame string probabilities, no physical mask.
 B physical_mask_40ms: same probabilities after MIDI/string/fret feasibility mask.
 C temporal_masked_120ms: equal mean of three independently trained/masked 40 ms frames.
 D trainer_context: apply the current trainer hint semantics to C: when the detected
   MIDI has answerStrings, restrict string probabilities to those strings.
 E final_gameplay: same decision rule as D; reported separately to prevent context
   from being mistaken for acoustic accuracy.

Stored WAVs do not contain quiz state. Therefore D/E are explicit controlled
context scenarios, not a claim about the distribution of live lessons:
  inclusive_pair  = true string + strongest competing physically valid string
  inclusive_singleton = true string only (upper bound)
  wrong_singleton = strongest wrong physically valid string (harmful/stale bound)
  no_match = trainer reports no matching answer; C passes through unchanged.

This reproduces the semantics of getGuitarTrainerAudioHints(midi): context only
acts through answerStrings when hasMatchingAnswer is true.
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
FRAMES=[("f0_40",0,.04),("f40_80",.04,.08),("f80_120",.08,.12)]

def model(n,k):
    return XGBClassifier(n_estimators=n,max_depth=3,learning_rate=.04,subsample=.85,
      colsample_bytree=.85,reg_lambda=2,objective="multi:softprob",num_class=k,
      random_state=42,n_jobs=8)

def physical_mask(p,midi):
    q=p.copy()
    for i,s in enumerate(range(1,9)):
        if not OPEN[s]<=midi<=OPEN[s]+24:q[i]=0
    return q/q.sum() if q.sum() else q

def mfcc26(y,sr,t0,t1):
    a=int(t0*sr);b=min(len(y),max(a+1,int(t1*sr)));seg=y[a:b]
    if len(seg)<128:seg=np.pad(seg,(0,128-len(seg)))
    nfft=max(64,2**int(np.floor(np.log2(len(seg)))));nfft=min(2048,nfft,len(seg))
    hop=max(16,nfft//4);n_mels=min(40,max(16,nfft//8))
    m=librosa.feature.mfcc(y=seg,sr=sr,n_mfcc=13,n_fft=nfft,hop_length=hop,n_mels=n_mels)
    return np.asarray([v for i in range(13) for v in (m[i].mean(),m[i].std())],np.float32)

def apply_hints(prob,answer_strings,has_match):
    if not has_match or not answer_strings:return prob.copy()
    q=np.zeros_like(prob)
    for s in answer_strings:q[s-1]=prob[s-1]
    return q/q.sum() if q.sum() else prob.copy()

def main():
    ap=argparse.ArgumentParser();ap.add_argument("wav_dir",type=Path)
    ap.add_argument("--out",type=Path,required=True);ap.add_argument("--smoke",action="store_true")
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
    print(f"CONTEXT loaded={len(df)} smoke={a.smoke}",flush=True)
    X=[];t=time.time()
    for fi,(name,t0,t1) in enumerate(FRAMES,1):
        X.append(np.vstack([mfcc26(r[5],r[6],t0,t1) for r in rec]))
        print(f"EXTRACT [{fi}/{len(FRAMES)}] {name} elapsed={time.time()-t:.1f}s",flush=True)
    truth=df.string.to_numpy(int);midi_arr=df.midi.to_numpy(int);n=len(df)
    raw=np.zeros((n,3,8));masked=np.zeros((n,3,8))
    midis=sorted(df.midi.unique());total=len(midis)*3;done=0;t=time.time()
    for midi in midis:
        te=np.where(midi_arr==midi)[0];tr=np.where(midi_arr!=midi)[0]
        for fi in range(3):
            classes=np.sort(np.unique(truth[tr]));enc={s:i for i,s in enumerate(classes)}
            sc=StandardScaler().fit(X[fi][tr]);clf=model(20 if a.smoke else 100,len(classes))
            clf.fit(sc.transform(X[fi][tr]),np.array([enc[s] for s in truth[tr]]))
            z=clf.predict_proba(sc.transform(X[fi][te]));p=np.zeros((len(te),8))
            for ci,s in enumerate(classes):p[:,s-1]=z[:,ci]
            raw[te,fi]=p
            for j,idx in enumerate(te):masked[idx,fi]=physical_mask(p[j],midi)
            done+=1;e=time.time()-t
            print(f"MODEL [{done}/{total}] MIDI={midi} frame={fi+1}/3 elapsed={e:.1f}s ETA={e/done*(total-done):.1f}s",flush=True)
    A=raw[:,0];B=masked[:,0];C=masked.mean(axis=1)
    probs={"A_raw_acoustic_40ms":A,"B_physical_mask_40ms":B,"C_temporal_masked_120ms":C}
    context={}
    for scenario in ("no_match","inclusive_pair","inclusive_singleton","wrong_singleton"):
        q=np.zeros_like(C)
        for i in range(n):
            valid=[s for s in range(1,9) if OPEN[s]<=midi_arr[i]<=OPEN[s]+24]
            wrong=[s for s in valid if s!=truth[i]]
            strongest=max(wrong,key=lambda s:C[i,s-1]) if wrong else None
            if scenario=="no_match": strings=[];has=False
            elif scenario=="inclusive_singleton":strings=[truth[i]];has=True
            elif scenario=="inclusive_pair":strings=[truth[i]]+([strongest] if strongest else []);has=True
            else:strings=([strongest] if strongest else []);has=bool(strongest)
            q[i]=apply_hints(C[i],strings,has)
        context[scenario]=q
        probs[f"D_context_{scenario}"]=q
        probs[f"E_final_{scenario}"]=q
    rows=[];metrics={}
    pred_cache={}
    for name,p in probs.items():
        pred=p.argmax(1)+1;pred_cache[name]=pred
        metrics[name]={"correct":int((pred==truth).sum()),"errors":int((pred!=truth).sum()),"accuracy":float(accuracy_score(truth,pred))}
    c_pred=pred_cache["C_temporal_masked_120ms"]
    for scenario in context:
        p=pred_cache[f"D_context_{scenario}"]
        metrics[f"D_context_{scenario}"]["rescues_vs_C"]=int(((c_pred!=truth)&(p==truth)).sum())
        metrics[f"D_context_{scenario}"]["harmful_overrides_vs_C"]=int(((c_pred==truth)&(p!=truth)).sum())
    for i,r in df.iterrows():
        row={**r.to_dict(),"truth":int(truth[i])}
        for name,p in probs.items():
            row[f"{name}_pred"]=int(np.argmax(p[i])+1);row[f"{name}_confidence"]=float(np.max(p[i]))
        rows.append(row)
    out={"step":15,"smoke":a.smoke,"recordings":n,
      "protocol":"leave-one-entire-MIDI-out; context scenarios controlled because stored WAVs contain no quiz state",
      "trainer_hint_semantics":"if hasMatchingAnswer and answerStrings nonempty, restrict C probabilities to answerStrings; otherwise pass through",
      "context_scenarios":{
        "no_match":"no matching trainer answer; no override",
        "inclusive_pair":"true string plus strongest physically-valid competing string",
        "inclusive_singleton":"true string only; optimistic upper bound",
        "wrong_singleton":"strongest wrong physically-valid string; stale/harmful upper bound"},
      "metrics":metrics}
    pd.DataFrame(rows).to_csv(a.out/"context_ablation_predictions.csv",index=False)
    (a.out/"summary.json").write_text(json.dumps(out,indent=2))
    (a.out/"config.json").write_text(json.dumps({"frames_ms":[[0,40],[40,80],[80,120]],"mfcc_per_frame":26,"trees":20 if a.smoke else 100},indent=2))
    print(json.dumps(out,indent=2),flush=True)

if __name__=="__main__":main()
