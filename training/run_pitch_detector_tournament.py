#!/usr/bin/env python3
"""Step 9: Stage-A pitch detector tournament.

Compares detector families on the ringing_384 WAVs using onset-relative frames.
This stage measures pitch only; it does not retrain the physical-string model.
Outputs preserve multiple hypotheses where available for Step 10.

Protocol:
- Ground truth MIDI comes only from filename string/fret + fixed tuning.
- Smoke traverses the complete detector/timing/evaluation/output pipeline.
- Real evaluates all 384 recordings.
- No trainer context is used.
"""
from __future__ import annotations
import argparse, json, math, re, time
from pathlib import Path
import librosa
import numpy as np
import pandas as pd

OPEN={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63}
RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$",re.I)
FRAME_MS=(40,80,120,160,200,240)
MIN_HZ=35.0; MAX_HZ=1600.0

def hz_to_midi_float(f):
    return 69+12*np.log2(f/440.0) if np.isfinite(f) and f>0 else np.nan

def hz_to_midi(f):
    x=hz_to_midi_float(f)
    return int(round(x)) if np.isfinite(x) else None

def rms(y):
    return float(np.sqrt(np.mean(np.square(y,dtype=np.float64)))) if len(y) else 0.0

def parabolic(y,i):
    if i<=0 or i>=len(y)-1: return float(i)
    a,b,c=float(y[i-1]),float(y[i]),float(y[i+1])
    d=a-2*b+c
    return float(i if abs(d)<1e-12 else i+.5*(a-c)/d)

def current_corr(y,sr):
    """Faithful Python port of src/audio/pitch.js selection + top local peaks."""
    r=rms(y)
    if r<1e-4: return np.nan,0.0,[]
    lo=max(1,int(sr//MAX_HZ)); hi=min(int(sr//MIN_HZ),len(y)-2)
    if hi<=lo: return np.nan,0.0,[]
    corr=np.zeros(hi+1,dtype=np.float64); best=-1.; bestoff=-1
    for off in range(lo,hi+1):
        a=y[:-off]; b=y[off:]; den=np.sqrt(np.dot(a,a)*np.dot(b,b))
        if den<=0: continue
        v=float(np.dot(a,b)/den); corr[off]=v
        if v>best: best=v; bestoff=off
    peaks=[]
    for off in range(lo+1,hi):
        v=corr[off]
        if v<.3 or v<corr[off-1] or v<corr[off+1]: continue
        m=hz_to_midi(sr/off)
        if m is None or any(abs(m-x["midi"])<1 for x in peaks): continue
        peaks.append({"midi":m,"frequency":sr/off,"confidence":float(v)})
    peaks.sort(key=lambda x:x["confidence"],reverse=True); peaks=peaks[:5]
    if bestoff<=0 or best<.3: return np.nan,max(0.,best),peaks
    return sr/bestoff,float(best),peaks

def yin_custom(y,sr,threshold=.18):
    """Small YIN implementation; threshold mirrors TheStringTheory research."""
    r=rms(y)
    if r<1e-4: return np.nan,0.0,[]
    min_tau=max(2,int(sr/MAX_HZ)); max_tau=min(int(sr/MIN_HZ),len(y)//2)
    if max_tau<=min_tau+2: return np.nan,0.0,[]
    d=np.zeros(max_tau+1,dtype=np.float64)
    for tau in range(1,max_tau+1):
        z=y[:-tau]-y[tau:]; d[tau]=np.dot(z,z)
    cmnd=np.ones_like(d); running=0.
    for tau in range(1,max_tau+1):
        running+=d[tau]; cmnd[tau]=d[tau]*tau/running if running>0 else 1.
    tau=None
    for t in range(min_tau,max_tau):
        if cmnd[t]<threshold and cmnd[t]<=cmnd[t+1]:
            tau=t; break
    if tau is None: tau=min(range(min_tau,max_tau+1),key=lambda t:cmnd[t])
    pt=parabolic(cmnd,tau); f=sr/pt if pt>0 else np.nan
    conf=float(np.clip(1-cmnd[tau],0,1))
    # Preserve several minima for Step 10.
    mins=[]
    for t in range(min_tau+1,max_tau):
        if cmnd[t]<=cmnd[t-1] and cmnd[t]<=cmnd[t+1]:
            m=hz_to_midi(sr/t)
            if m is None or any(abs(m-x["midi"])<1 for x in mins): continue
            mins.append({"midi":m,"frequency":sr/t,"confidence":float(np.clip(1-cmnd[t],0,1))})
    mins.sort(key=lambda x:x["confidence"],reverse=True)
    return f,conf,mins[:5]

def librosa_yin(y,sr):
    try:
        f=librosa.yin(y,fmin=MIN_HZ,fmax=MAX_HZ,sr=sr,frame_length=min(4096,max(256,2**int(np.floor(np.log2(len(y)))))))
        vals=f[np.isfinite(f)]
        hz=float(np.median(vals)) if len(vals) else np.nan
        return hz,1.0 if np.isfinite(hz) else 0.0,[]
    except Exception:
        return np.nan,0.0,[]

def librosa_pyin(y,sr):
    try:
        fl=min(4096,max(256,2**int(np.floor(np.log2(len(y))))))
        f,voiced,prob=librosa.pyin(y,fmin=MIN_HZ,fmax=MAX_HZ,sr=sr,frame_length=fl)
        ok=np.isfinite(f)
        if not np.any(ok): return np.nan,0.0,[]
        hz=float(np.nanmedian(f)); conf=float(np.nanmean(prob[ok])) if prob is not None else float(np.mean(voiced[ok]))
        return hz,conf,[]
    except Exception:
        return np.nan,0.0,[]

DETECTORS={"current_corr":current_corr,"yin_custom":yin_custom,"librosa_yin":librosa_yin,"librosa_pyin":librosa_pyin}

def load(path,smoke):
    rows=[]
    for p in sorted(path.glob("*.wav")):
        m=RX.fullmatch(p.name)
        if not m: continue
        s,f=int(m[1]),int(m[2]); midi=OPEN[s]+f
        if smoke and not (54<=midi<=60 and m[3].lower()=="normal"): continue
        y,sr=librosa.load(p,sr=22050,mono=True)
        y,_=librosa.effects.trim(y,top_db=50)
        rows.append((p,s,f,m[3].lower(),midi,y,sr))
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("wav_dir",type=Path); ap.add_argument("--out",type=Path,required=True); ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    rec=load(a.wav_dir,a.smoke); print(f"Loaded {len(rec)} recordings",flush=True)
    out=[]; total=len(rec)*len(FRAME_MS)*len(DETECTORS); done=0; st=time.time()
    for ri,(p,s,f,strength,true_midi,y,sr) in enumerate(rec,1):
        for ms in FRAME_MS:
            n=min(len(y),max(128,int(sr*ms/1000))); seg=y[:n]
            for name,fn in DETECTORS.items():
                t0=time.perf_counter(); hz,conf,cands=fn(seg,sr); latency=(time.perf_counter()-t0)*1000
                mf=hz_to_midi_float(hz); pred=int(round(mf)) if np.isfinite(mf) else None
                cents=float((mf-true_midi)*100) if np.isfinite(mf) else None
                out.append({"file":p.name,"string":s,"fret":f,"strength":strength,"true_midi":true_midi,"frame_ms":ms,"detector":name,"frequency":None if not np.isfinite(hz) else float(hz),"pred_midi":pred,"cents_error":cents,"confidence":float(conf),"runtime_ms":latency,"candidates_json":json.dumps(cands,separators=(",",":"))})
                done+=1
        if ri==1 or ri%10==0 or ri==len(rec):
            elapsed=time.time()-st; eta=elapsed/done*(total-done) if done else 0
            print(f"DETECT [{done}/{total}] recordings {ri}/{len(rec)} | elapsed {elapsed/60:.1f}m ETA {eta/60:.1f}m",flush=True)
    df=pd.DataFrame(out); df.to_csv(a.out/"pitch_predictions.csv",index=False)
    metrics=[]; summary={}
    for (det,ms),g in df.groupby(["detector","frame_ms"]):
        valid=g.pred_midi.notna(); exact=(g.loc[valid,"pred_midi"].astype(int)==g.loc[valid,"true_midi"]).sum()
        n=len(g); detected=int(valid.sum()); acc=float(exact/n)
        octave=int(((g.loc[valid,"pred_midi"].astype(int)-g.loc[valid,"true_midi"]).abs()==12).sum())
        medc=float(g.loc[valid,"cents_error"].abs().median()) if detected else None
        row={"detector":det,"frame_ms":int(ms),"recordings":n,"detected":detected,"exact_midi_correct":int(exact),"accuracy":acc,"octave_errors":octave,"median_abs_cents":medc,"mean_runtime_ms":float(g.runtime_ms.mean())}
        metrics.append(row)
    md=pd.DataFrame(metrics).sort_values(["accuracy","mean_runtime_ms"],ascending=[False,True]); md.to_csv(a.out/"pitch_metrics.csv",index=False)
    best=md.iloc[0].to_dict() if len(md) else {}
    # Best per detector, useful for fair detector-family comparison.
    per={}
    for det,g in md.groupby("detector"):
        x=g.sort_values(["accuracy","mean_runtime_ms"],ascending=[False,True]).iloc[0]
        per[det]={k:(int(v) if k in ("frame_ms","recordings","detected","exact_midi_correct","octave_errors") else float(v)) for k,v in x.to_dict().items() if k!="detector"}
    summary={"step":9,"smoke":a.smoke,"recordings":len(rec),"frames_ms":list(FRAME_MS),"detectors":list(DETECTORS),"best":best,"best_per_detector":per,"notes":["current_corr is a Python port of src/audio/pitch.js.","yin_custom uses YIN CMND with threshold 0.18 and preserves top minima candidates.","librosa_yin and librosa_pyin provide independent reference implementations.","No trainer context or string-classifier evidence is used."]}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2,default=lambda x:x.item() if hasattr(x,"item") else x))
    print(json.dumps(summary,indent=2,default=lambda x:x.item() if hasattr(x,"item") else x),flush=True)
if __name__=="__main__": main()
