#!/usr/bin/env python3
"""Abeßer 48-feature string-detection reproduction on ringing_384.

Paper-grounded pieces: 10.1 kHz, 256-sample frames, 64 hop, modified-covariance
AR spectrum, attack transition at max AR process variance, first 15 partials,
48 features, StandardScaler -> LDA(5) -> RBF SVM, 3-fold inner C/gamma search,
candidate plausibility mask, and five-frame probability aggregation.

Important adaptation: the paper does not state the AR model order in the
available method text. We therefore report fixed-order sensitivity (32,48,64)
instead of silently choosing/tuning it on test results. Harmonics above Nyquist
are marked unavailable and imputed inside each training fold.
"""
from __future__ import annotations
import argparse,json,re,time,warnings
from pathlib import Path
import librosa,numpy as np,pandas as pd
from scipy.signal import freqz
from scipy.stats import skew,kurtosis
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score,f1_score,confusion_matrix
from sklearn.model_selection import GroupKFold,GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

SR=10100; N=256; H=64; OPEN={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63}
RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav",re.I)
STAT_NAMES=["max","min","mean","median","mode","var","skew","kurt"]

def midi_hz(m): return 440.0*2**((m-69)/12)
def mode_sample(x):
    x=np.asarray(x); x=x[np.isfinite(x)]
    if not len(x): return np.nan
    # Continuous estimates rarely repeat exactly; paper says mode but not binning.
    # Quantization makes the statistic deterministic without using labels.
    q=np.round(x,6); vals,c=np.unique(q,return_counts=True); return float(vals[c.argmax()])
def stats8(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if not len(x): return [np.nan]*8
    return [np.max(x),np.min(x),np.mean(x),np.median(x),mode_sample(x),
            np.var(x),float(skew(x,bias=False)) if len(x)>2 else 0.0,
            float(kurtosis(x,bias=False)) if len(x)>3 else 0.0]

def modified_covariance_ar(x,p):
    x=np.asarray(x,float); x=x-np.mean(x)
    if len(x)<=p+2: return np.r_[1.,np.zeros(p)],float(np.var(x)+1e-12)
    # Simultaneously minimize forward and backward prediction errors.
    F=[]; yf=[]; B=[]; yb=[]
    for n in range(p,len(x)):
        F.append(x[n-1:n-p-1:-1] if n-p-1>=0 else x[n-1::-1][:p]); yf.append(-x[n])
    xr=x[::-1]
    for n in range(p,len(xr)):
        B.append(xr[n-1:n-p-1:-1] if n-p-1>=0 else xr[n-1::-1][:p]); yb.append(-xr[n])
    A=np.vstack([np.asarray(F),np.asarray(B)]); y=np.r_[yf,yb]
    coef=np.linalg.lstsq(A,y,rcond=None)[0]; ar=np.r_[1.,coef]
    ef=np.array(yf)-np.asarray(F)@coef; eb=np.array(yb)-np.asarray(B)@coef
    return ar,float(np.mean(np.r_[ef**2,eb**2])+1e-12)

def frame_ar(frame,p):
    ar,var=modified_covariance_ar(frame,p)
    roots=np.roots(ar)
    roots=roots[(np.imag(roots)>0)&(np.abs(roots)>1e-8)]
    freqs=np.angle(roots)*SR/(2*np.pi)
    freqs=freqs[(freqs>0)&(freqs<SR/2)]
    # AR PSD sampled densely for amplitudes.
    w,h=freqz([np.sqrt(var)],ar,worN=8192,fs=SR)
    amp=np.abs(h)
    return ar,var,np.asarray(freqs),w,amp

def assign_partials(pole_freqs,w,amp,f0):
    est=np.full(15,np.nan); amps=np.full(15,np.nan)
    for k in range(1,16):
        target=k*f0
        if target>=SR/2: continue
        if len(pole_freqs):
            j=np.argmin(np.abs(pole_freqs-target)); f=float(pole_freqs[j])
            # Avoid assigning a wildly unrelated pole.
            if abs(f-target)<=max(0.45*f0,25.0): est[k-1]=f
        if np.isfinite(est[k-1]):
            amps[k-1]=float(np.interp(est[k-1],w,amp))
    return est,amps

def features48(est,amps,f0):
    valid=np.isfinite(est); ks=np.arange(1,16,dtype=float)
    beta=np.nan
    if valid.sum()>=5:
        try: beta=float(np.polyfit(ks[valid],(est[valid]/f0)**2,4)[0])
        except Exception: pass
    rel=amps/(amps[0] if np.isfinite(amps[0]) and amps[0]>1e-12 else np.nan)
    theo=ks*f0*np.sqrt(np.maximum(0,1+(0 if not np.isfinite(beta) else beta)*ks**2))
    dev=(theo-est)/est
    slope=np.nan
    v=np.isfinite(rel)
    if v.sum()>=2: slope=float(np.polyfit(ks[v],rel[v],1)[0])
    return np.r_[beta,rel,stats8(rel),dev,stats8(dev),slope].astype(float)

def extract_record(path,midi,p):
    y,_=librosa.load(path,sr=SR,mono=True); y,_=librosa.effects.trim(y,top_db=50)
    if len(y)<N: return None
    frames=[]; vars=[]
    for st in range(0,len(y)-N+1,H):
        fr=y[st:st+N]; ar,var,poles,w,amp=frame_ar(fr,p); frames.append((poles,w,amp)); vars.append(var)
    if not frames:return None
    # Restrict transition search to first 150 ms so late variance spikes cannot become "attack".
    lim=max(1,min(len(vars),int(.150*SR/H)+1)); tstar=int(np.argmax(vars[:lim]))
    use=list(range(tstar+1,min(tstar+6,len(frames))))
    if not use: use=[tstar]
    f0=midi_hz(midi); feats=[]
    for i in use:
        poles,w,amp=frames[i]; est,amps=assign_partials(poles,w,amp,f0); feats.append(features48(est,amps,f0))
    while len(feats)<5: feats.append(np.full(48,np.nan))
    return np.asarray(feats),tstar,int(np.floor((SR/2)/f0))

def possible(midi): return [s for s,o in OPEN.items() if 0<=midi-o<=24]

def fit_predict(Xframes,df,order,out):
    truth=df.string.to_numpy(int); pred=np.zeros(len(df),int); conf=np.zeros(len(df)); rows=[]
    smoke=bool(getattr(df,"attrs",{}).get("smoke",False))
    Cs=[1] if smoke else [.1,1,10,100]
    gammas=["scale"] if smoke else ["scale",.01,.1,1]
    midis=sorted(df.midi.unique()); start=time.time()
    for fi,midi in enumerate(midis,1):
        test=np.where(df.midi.to_numpy()==midi)[0]; train=np.where(df.midi.to_numpy()!=midi)[0]
        # Train on frame rows. Inner CV is grouped by MIDI so hyperparameter selection
        # matches the outer unseen-pitch generalization problem.
        Xt=[];yt=[];groups=[]
        for ridx in train:
            for frame in Xframes[ridx]:
                if np.isfinite(frame).any(): Xt.append(frame);yt.append(truth[ridx]);groups.append(int(df.iloc[ridx].midi))
        Xt=np.asarray(Xt);yt=np.asarray(yt);groups=np.asarray(groups)
        # Abeßer defines Nd = Nstrings - 1. For this 8-string instrument that is 7.
        ncomp=min(len(OPEN)-1,len(np.unique(yt))-1)
        pipe=Pipeline([("imp",SimpleImputer(strategy="median",add_indicator=False,keep_empty_features=True)),
          ("scale",StandardScaler()),("lda",LinearDiscriminantAnalysis(n_components=ncomp)),
          ("svm",SVC(kernel="rbf",probability=True))])
        cv=list(GroupKFold(3).split(Xt,yt,groups))
        # Materialize splits so joblib workers receive a picklable object.
        gs=GridSearchCV(pipe,{"svm__C":Cs,"svm__gamma":gammas},cv=cv,scoring="f1_macro",n_jobs=-1)
        gs.fit(Xt,yt); model=gs.best_estimator_; classes=model.named_steps["svm"].classes_
        for ridx in test:
            valid=[f for f in Xframes[ridx] if np.isfinite(f).any()]
            probs=model.predict_proba(np.asarray(valid))
            agg=probs.sum(axis=0)
            allowed=set(possible(int(df.iloc[ridx].midi)))
            agg=np.array([v if int(c) in allowed else 0.0 for c,v in zip(classes,agg)])
            j=int(np.argmax(agg)); pred[ridx]=int(classes[j]); conf[ridx]=float(agg[j]/max(agg.sum(),1e-12))
            rows.append({"order":order,"file":df.iloc[ridx].file,"midi":int(midi),"string":int(truth[ridx]),
              "predicted_string":int(pred[ridx]),"confidence":conf[ridx],"correct":bool(pred[ridx]==truth[ridx]),
              "C":gs.best_params_["svm__C"],"gamma":str(gs.best_params_["svm__gamma"])})
        elapsed=time.time()-start; eta=elapsed/fi*(len(midis)-fi)
        print(f"ORDER {order} FOLD [{fi}/{len(midis)}] MIDI {midi} | elapsed {elapsed/60:.1f}m ETA {eta/60:.1f}m",flush=True)
        pd.DataFrame(rows).to_csv(out/f"predictions_ar{order}.csv",index=False)
    return pred,conf,rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("wav_dir",type=Path); ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--orders",default="32,48,64"); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    meta=[]
    for p in sorted(a.wav_dir.glob("*.wav")):
        m=RX.fullmatch(p.name)
        if m:
            s,f=int(m[1]),int(m[2]); meta.append({"file":p.name,"path":p,"string":s,"fret":f,"strength":m[3].lower(),"midi":OPEN[s]+f})
    df=pd.DataFrame(meta); print(f"Loaded {len(df)} recordings",flush=True); assert len(df)==384
    summaries=[]
    for oi,order in enumerate(map(int,a.orders.split(",")),1):
        print(f"START ORDER [{oi}] AR={order}: extracting paper features",flush=True)
        X=[];diag=[]
        for i,r in df.iterrows():
            z=extract_record(r.path,int(r.midi),order)
            if z is None: X.append(np.full((5,48),np.nan)); diag.append({"file":r.file,"tstar":-1,"observable_partials":0})
            else:
                feats,tstar,npart=z;X.append(feats);diag.append({"file":r.file,"tstar":tstar,"observable_partials":npart})
            if (i+1)%24==0: print(f"AR={order} EXTRACT [{i+1}/{len(df)}]",flush=True)
        pd.DataFrame(diag).to_csv(a.out/f"diagnostics_ar{order}.csv",index=False)
        pred,conf,rows=fit_predict(X,df,order,a.out)
        acc=float(accuracy_score(df.string,pred)); macro=float(f1_score(df.string,pred,average="macro"))
        summaries.append({"ar_order":order,"accuracy":acc,"macro_f1":macro,"correct":int((pred==df.string).sum()),"errors":int((pred!=df.string).sum())})
        pd.DataFrame(confusion_matrix(df.string,pred,labels=range(1,9)),index=range(1,9),columns=range(1,9)).to_csv(a.out/f"confusion_ar{order}.csv")
        (a.out/"summary.json").write_text(json.dumps({"method":"Abesser 48 -> scaler -> LDA(Nstrings-1=7) -> RBF-SVM; five-frame aggregation","results":summaries},indent=2))
        print(f"DONE AR={order}: {acc:.4%} macro-F1={macro:.4f}",flush=True)
    print(json.dumps(summaries,indent=2),flush=True)

if __name__=="__main__": main()
