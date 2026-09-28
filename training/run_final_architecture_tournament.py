#!/usr/bin/env python3
"""Step 17: final architecture tournament.

Compares only evidence-supported complete pipelines.
New question: when Stage-A pitch is imperfect, which surviving Stage-B/fusion
architecture gives the best end-to-end (MIDI,string) tuple accuracy, latency,
calibration, and implementation cost?

No trainer context is used in acoustic/end-to-end metrics.
"""
from __future__ import annotations
import argparse,json,re,time
from pathlib import Path
import librosa,numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.isotonic import IsotonicRegression
from xgboost import XGBClassifier
from train_full_ringing import extract as extract_engineered
from run_time_phase_experiment import extract_window,columns_for

OPEN={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63}
RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$",re.I)
MIN_HZ=35.; MAX_HZ=1600.
FRAMES=((0,.04),(.04,.08),(.08,.12))

def clf(n,k):
    return XGBClassifier(n_estimators=n,max_depth=3,learning_rate=.04,subsample=.85,
      colsample_bytree=.85,reg_lambda=2,objective="multi:softprob",num_class=k,
      random_state=42,n_jobs=8)

def mask(p,midi):
    q=p.copy()
    for i,s in enumerate(range(1,9)):
        if not OPEN[s] <= midi <= OPEN[s]+24:q[i]=0.
    z=q.sum()
    return q/z if z else q

def mfcc26(y,sr,a,b):
    seg=y[int(a*sr):min(len(y),max(int(a*sr)+1,int(b*sr)))]
    if len(seg)<128:seg=np.pad(seg,(0,128-len(seg)))
    nfft=max(64,2**int(np.floor(np.log2(len(seg)))));nfft=min(2048,nfft,len(seg))
    hop=max(16,nfft//4);nm=min(40,max(16,nfft//8))
    m=librosa.feature.mfcc(y=seg,sr=sr,n_mfcc=13,n_fft=nfft,hop_length=hop,n_mels=nm)
    return np.array([v for z in m for v in (z.mean(),z.std())],np.float32)

def lyin(y,sr):
    try:
        fl=min(4096,max(256,2**int(np.floor(np.log2(len(y))))))
        f=librosa.yin(y,fmin=MIN_HZ,fmax=MAX_HZ,sr=sr,frame_length=fl)
        v=f[np.isfinite(f)]
        return float(np.median(v)) if len(v) else np.nan
    except Exception:return np.nan

def hz_midi(f):
    return int(round(69+12*np.log2(f/440.))) if np.isfinite(f) and f>0 else -999

def oof_probs(X,df,trees,label):
    truth=df.string.to_numpy(int);mids=df.midi.to_numpy(int);P=np.zeros((len(df),8))
    runt=[];unique=sorted(df.midi.unique());st=time.time()
    for n,midi in enumerate(unique,1):
        te=np.where(mids==midi)[0];tr=np.where(mids!=midi)[0]
        classes=np.sort(np.unique(truth[tr]));enc={s:i for i,s in enumerate(classes)}
        sc=StandardScaler().fit(X[tr]);m=clf(trees,len(classes))
        m.fit(sc.transform(X[tr]),np.array([enc[s] for s in truth[tr]],int))
        q=time.perf_counter();raw=m.predict_proba(sc.transform(X[te]));runt.append((time.perf_counter()-q)*1000/max(1,len(te)))
        for ci,s in enumerate(classes):P[te,s-1]=raw[:,ci]
        e=time.time()-st;eta=e/n*(len(unique)-n)
        print(f"{label} FOLD [{n}/{len(unique)}] MIDI {midi} | elapsed {e/60:.1f}m ETA {eta/60:.1f}m",flush=True)
    return P,float(np.mean(runt))

def apply_mask_rows(P,pmidi):
    Q=np.zeros_like(P)
    for i,m in enumerate(pmidi):Q[i]=mask(P[i],int(m))
    return Q

def isotonic_fusion(df,pred_by,conf_by):
    mids=df.midi.to_numpy(int);truth=df.string.to_numpy(int);N=len(df)
    outpred=np.zeros(N,int);outconf=np.zeros(N,float)
    names=list(pred_by)
    for midi in sorted(df.midi.unique()):
        te=np.where(mids==midi)[0];tr=np.where(mids!=midi)[0]
        scores=np.zeros((len(te),len(names)))
        for j,name in enumerate(names):
            x=conf_by[name][tr];y=(pred_by[name][tr]==truth[tr]).astype(int)
            if len(np.unique(y))<2:
                scores[:,j]=float(np.mean(y))
            else:
                cal=IsotonicRegression(out_of_bounds="clip",y_min=0,y_max=1).fit(x,y)
                scores[:,j]=cal.predict(conf_by[name][te])
        win=scores.argmax(1)
        for k,idx in enumerate(te):
            name=names[int(win[k])];outpred[idx]=pred_by[name][idx];outconf[idx]=scores[k,int(win[k])]
    return outpred,outconf

def metrics(df,name,pmidi,spred,sconf,window_ms,feat_ms,infer_ms,feature_count,model_count):
    tm=df.midi.to_numpy(int);ts=df.string.to_numpy(int)
    pitch=pmidi==tm;string=spred==ts;tupleok=pitch&string
    cond=float(np.mean(string[pitch])) if np.any(pitch) else 0.
    brier=float(np.mean((sconf-string.astype(float))**2))
    by={x:float(np.mean(tupleok[df.strength.to_numpy()==x])) for x in sorted(df.strength.unique())}
    return dict(method=name,correct=int(tupleok.sum()),accuracy=float(tupleok.mean()),
      pitch_correct=int(pitch.sum()),string_correct_all=int(string.sum()),
      string_accuracy_given_correct_pitch=cond,brier_string_confidence=brier,
      by_strength=by,decision_window_ms=window_ms,feature_runtime_ms=feat_ms,
      inference_runtime_ms=infer_ms,estimated_availability_ms=window_ms+feat_ms+infer_ms,
      feature_count=feature_count,model_count=model_count)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("wav_dir",type=Path);ap.add_argument("--out",type=Path,required=True);ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);trees=20 if a.smoke else 100
    rec=[]
    for p in sorted(a.wav_dir.glob("*.wav")):
        m=RX.fullmatch(p.name)
        if not m:continue
        s,f=int(m[1]),int(m[2]);midi=OPEN[s]+f
        if a.smoke and not (54<=midi<=60 and m[3].lower()=="normal"):continue
        y,sr=librosa.load(p,sr=22050,mono=True);y,_=librosa.effects.trim(y,top_db=50)
        rec.append((p,s,f,m[3].lower(),midi,y,sr))
    df=pd.DataFrame([dict(file=r[0].name,string=r[1],fret=r[2],strength=r[3],midi=r[4]) for r in rec])
    print(f"STEP17 loaded {len(df)} recordings smoke={a.smoke}",flush=True)

    # Stage A: only the two surviving latency points needed for final system comparison.
    pitch={};pitch_rt={}
    for ms in (200,240):
        vals=[];rts=[]
        for i,r in enumerate(rec,1):
            seg=r[5][:min(len(r[5]),max(128,int(r[6]*ms/1000)))]
            q=time.perf_counter();hz=lyin(seg,r[6]);rts.append((time.perf_counter()-q)*1000);vals.append(hz_midi(hz))
            if i==1 or i%50==0 or i==len(rec):print(f"PITCH {ms}ms [{i}/{len(rec)}]",flush=True)
        pitch[ms]=np.array(vals,int);pitch_rt[ms]=float(np.mean(rts))

    # Feature extraction.
    t=time.time();temporal=[];temporal_feat_rt=[]
    for fi,(x0,x1) in enumerate(FRAMES,1):
        z=[];rr=[]
        for r in rec:
            q=time.perf_counter();z.append(mfcc26(r[5],r[6],x0,x1));rr.append((time.perf_counter()-q)*1000)
        temporal.append(np.vstack(z));temporal_feat_rt.append(float(np.mean(rr)))
        print(f"EXTRACT temporal [{fi}/3] elapsed={time.time()-t:.1f}s",flush=True)

    broad=[];brt=[]
    for i,r in enumerate(rec,1):
        q=time.perf_counter();d=extract_window(r[5],r[6],r[4],0,.12);names=list(d);cols=columns_for(names,"mfcc");broad.append([d[names[j]] for j in cols]);brt.append((time.perf_counter()-q)*1000)
        if i==1 or i%50==0 or i==len(rec):print(f"EXTRACT broadMFCC [{i}/{len(rec)}]",flush=True)
    Xbroad=np.asarray(broad,np.float32)

    Xbase=[];Xharm=[];base_rt=[];harm_rt=[]
    for i,r in enumerate(rec,1):
        q=time.perf_counter();xb,_=extract_engineered(r[0],r[1],r[2],"baseline");base_rt.append((time.perf_counter()-q)*1000)
        q=time.perf_counter();xh,_=extract_engineered(r[0],r[1],r[2],"full");harm_rt.append((time.perf_counter()-q)*1000)
        Xbase.append(xb);Xharm.append(xh)
        if i==1 or i%25==0 or i==len(rec):print(f"EXTRACT engineered [{i}/{len(rec)}]",flush=True)
    Xbase=np.vstack(Xbase);Xharm=np.vstack(Xharm)

    # OOF acoustic probabilities. These are unmasked until architecture application.
    Pt=[];irt=[]
    for fi,X in enumerate(temporal,1):
        p,r=oof_probs(X,df,trees,f"TEMP{fi}");Pt.append(p);irt.append(r)
    Pb,ibr=oof_probs(Xbase,df,trees,"BASE")
    Ph,ihr=oof_probs(Xharm,df,trees,"HARM")
    Pm,imr=oof_probs(Xbroad,df,trees,"BROAD_MFCC")

    rows=[];predrows=[]
    for ms in (200,240):
        pm=pitch[ms]
        Qt=[apply_mask_rows(x,pm) for x in Pt]
        T=np.mean(np.stack(Qt,axis=1),axis=1);tp=T.argmax(1)+1;tc=T.max(1)
        rows.append(metrics(df,f"yin{ms}_temporal120",pm,tp,tc,ms,
          sum(temporal_feat_rt),sum(irt),78,3))

        # Existing evidence-supported 3-model fusion, now evaluated as a complete pipeline
        # with Stage-A-predicted MIDI driving each physical candidate mask.
        masked={"baseline":apply_mask_rows(Pb,pm),"harmonic":apply_mask_rows(Ph,pm),"mfcc":apply_mask_rows(Pm,pm)}
        preds={k:v.argmax(1)+1 for k,v in masked.items()};confs={k:v.max(1) for k,v in masked.items()}
        fp,fc=isotonic_fusion(df,preds,confs)
        rows.append(metrics(df,f"yin{ms}_fusion3",pm,fp,fc,ms,
          float(np.mean(base_rt)+np.mean(harm_rt)+np.mean(brt)),
          ibr+ihr+imr,107+Xharm.shape[1]+Xbroad.shape[1],3))
        for method,sp,sc in ((f"yin{ms}_temporal120",tp,tc),(f"yin{ms}_fusion3",fp,fc)):
            for i,r in df.iterrows():
                predrows.append(dict(method=method,file=r.file,true_midi=int(r.midi),pred_midi=int(pm[i]),
                  true_string=int(r.string),pred_string=int(sp[i]),confidence=float(sc[i]),
                  pitch_correct=bool(pm[i]==r.midi),string_correct=bool(sp[i]==r.string),
                  tuple_correct=bool(pm[i]==r.midi and sp[i]==r.string)))

    # Oracle-pitch references from these newly generated OOF probabilities.
    true=df.midi.to_numpy(int)
    T=np.mean(np.stack([apply_mask_rows(x,true) for x in Pt],axis=1),axis=1)
    tp=T.argmax(1)+1;tc=T.max(1)
    rows.append(metrics(df,"oracle_pitch_temporal120",true,tp,tc,120,sum(temporal_feat_rt),sum(irt),78,3))
    masked={"baseline":apply_mask_rows(Pb,true),"harmonic":apply_mask_rows(Ph,true),"mfcc":apply_mask_rows(Pm,true)}
    preds={k:v.argmax(1)+1 for k,v in masked.items()};confs={k:v.max(1) for k,v in masked.items()}
    fp,fc=isotonic_fusion(df,preds,confs)
    rows.append(metrics(df,"oracle_pitch_fusion3",true,fp,fc,120,float(np.mean(base_rt)+np.mean(harm_rt)+np.mean(brt)),ibr+ihr+imr,107+Xharm.shape[1]+Xbroad.shape[1],3))

    # Pareto among deployable (non-oracle) architectures.
    deploy=[r for r in rows if not r["method"].startswith("oracle_")]
    pareto=[]
    for r in deploy:
        dom=any((q["accuracy"]>=r["accuracy"] and q["estimated_availability_ms"]<=r["estimated_availability_ms"] and
                 (q["accuracy"]>r["accuracy"] or q["estimated_availability_ms"]<r["estimated_availability_ms"])) for q in deploy)
        if not dom:pareto.append(r["method"])

    pd.DataFrame(predrows).to_csv(a.out/"architecture_predictions.csv",index=False)
    pd.DataFrame([{k:v for k,v in r.items() if k!="by_strength"} for r in rows]).to_csv(a.out/"architecture_metrics.csv",index=False)
    summary={"step":17,"smoke":a.smoke,"recordings":len(df),"trees":trees,
      "protocol":"leave-one-entire-true-MIDI-out Stage-B; Stage-A predicted MIDI drives physical mask; trainer context excluded",
      "architectures":rows,"pareto":pareto,
      "implementation":{"temporal120":{"features":78,"models":3,"browser_note":"3 small XGBoost models + scalers; MFCC only"},
                        "fusion3":{"features":int(107+Xharm.shape[1]+Xbroad.shape[1]),"models":3,"browser_note":"baseline + harmonic + broad-MFCC extraction, 3 XGBoost models + isotonic selector"}},
      "references":{"prior_best_fusion_correct":379,"prior_temporal120_correct":376,"prior_yin240_midi_correct":375}}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2))
    (a.out/"config.json").write_text(json.dumps({"pitch_windows_ms":[200,240],"temporal_frames_ms":[[0,40],[40,80],[80,120]],"trees":trees},indent=2))
    print(json.dumps(summary,indent=2),flush=True)
if __name__=="__main__":main()
