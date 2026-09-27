#!/usr/bin/env python3
"""Time-resolved physical-string information experiment on ringing_384.

For each onset-relative window, extract independent feature families and evaluate
physical-string prediction with the repository's leave-one-pitch-out protocol
and candidate-string masking. Also evaluates cumulative windows to test how
quickly evidence becomes useful.
"""
from __future__ import annotations
import argparse, json, re, time
from pathlib import Path
import librosa, numpy as np, pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

OPEN_MIDI={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63}
RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$",re.I)
EPS=1e-12

def model(n):
    return XGBClassifier(n_estimators=n,max_depth=3,learning_rate=.04,subsample=.85,
      colsample_bytree=.85,reg_lambda=2,objective="multi:softprob",num_class=8,
      random_state=42,n_jobs=8)

def mask(probs,midi):
    p=probs.copy()
    for i,s in enumerate(range(1,9)):
        if not (OPEN_MIDI[s] <= midi <= OPEN_MIDI[s]+24): p[i]=0
    z=p.sum()
    return p/z if z else p

def db(x): return float(20*np.log10(max(float(x),EPS)))

def onset_trim(y):
    # Match production training preprocessing: silence trim establishes t=0.
    z,_=librosa.effects.trim(y,top_db=50)
    return z

def extract_window(y,sr,midi,t0,t1):
    a=max(0,int(t0*sr)); b=min(len(y),max(a+1,int(t1*sr)))
    seg=y[a:b]
    if len(seg)<128: seg=np.pad(seg,(0,128-len(seg)))
    f0=440.0*2**((midi-69)/12)
    vals={}

    # Envelope/time-domain.
    absx=np.abs(seg)
    vals["env_peak_db"]=db(absx.max() if len(absx) else 0)
    vals["env_rms_db"]=db(np.sqrt(np.mean(seg**2)))
    vals["env_crest_db"]=vals["env_peak_db"]-vals["env_rms_db"]
    vals["env_zcr"]=float(np.mean(librosa.feature.zero_crossing_rate(seg)))
    vals["env_energy"]=float(np.sum(seg**2))

    # MFCC/timbre.
    mf=librosa.feature.mfcc(y=seg,sr=sr,n_mfcc=13,n_fft=min(2048,max(256,2**int(np.floor(np.log2(len(seg)))))))
    for i in range(13):
        vals[f"mfcc_{i+1}_mean"]=float(np.mean(mf[i]))
        vals[f"mfcc_{i+1}_std"]=float(np.std(mf[i]))

    # Generic spectral shape.
    nfft=max(8192,1<<(max(256,len(seg))-1).bit_length())
    spec=np.abs(np.fft.rfft(seg*np.hanning(len(seg)),n=nfft))
    freqs=np.fft.rfftfreq(nfft,1/sr)
    S=np.abs(librosa.stft(seg,n_fft=min(2048,nfft),hop_length=256))
    vals["spec_centroid"]=float(np.mean(librosa.feature.spectral_centroid(S=S,sr=sr)))
    vals["spec_bandwidth"]=float(np.mean(librosa.feature.spectral_bandwidth(S=S,sr=sr)))
    vals["spec_rolloff"]=float(np.mean(librosa.feature.spectral_rolloff(S=S,sr=sr)))
    vals["spec_flatness"]=float(np.mean(librosa.feature.spectral_flatness(S=S)))

    # Pitch-relative harmonic/partial evidence.
    amps=[]
    for h in range(1,16):
        target=f0*h
        if target>=sr/2:
            amps.append(EPS)
            continue
        bw=max(4.0,target*.006)
        ix=np.where(np.abs(freqs-target)<=bw)[0]
        amps.append(float(np.sqrt(np.sum(spec[ix]**2))) if len(ix) else EPS)
    h1=max(amps[0],EPS)
    for h in range(2,16):
        vals[f"harm_ratio_h{h}"]=float(20*np.log10(max(amps[h-1],EPS)/h1))

    detunes=[]; contrasts=[]; widths=[]
    for h in range(1,16):
        target=f0*h
        if target>=sr/2:
            detunes.append(0.0); widths.append(0.0); contrasts.append(0.0); continue
        search=max(8.0,target*.02)
        ix=np.where(np.abs(freqs-target)<=search)[0]
        if not len(ix):
            detunes.append(0.0); widths.append(0.0); contrasts.append(0.0); continue
        pi=ix[np.argmax(spec[ix])]; pf=max(freqs[pi],EPS); pk=max(spec[pi],EPS)
        detunes.append(float(1200*np.log2(pf/target)))
        half=pk/np.sqrt(2); l=pi; r=pi
        while l>0 and spec[l]>=half: l-=1
        while r+1<len(spec) and spec[r]>=half: r+=1
        widths.append(float(freqs[r]-freqs[l]))
        nix=ix[np.abs(freqs[ix]-pf)>max(4.0,target*.006)]
        noise=float(np.median(spec[nix])) if len(nix) else EPS
        contrasts.append(float(20*np.log10(pk/max(noise,EPS))))
        vals[f"detune_h{h}"]=detunes[-1]
        vals[f"width_h{h}"]=widths[-1]
        vals[f"contrast_h{h}"]=contrasts[-1]

    # Abeßer-inspired aggregate partial-frequency statistics + spectral slope.
    d=np.asarray(detunes,dtype=float)
    vals["inharm_detune_mean"]=float(np.mean(d))
    vals["inharm_detune_std"]=float(np.std(d))
    vals["inharm_detune_absmean"]=float(np.mean(np.abs(d)))
    vals["inharm_detune_high_std"]=float(np.std(d[7:]))
    hs=np.arange(1,16,dtype=float)
    la=np.log(np.maximum(np.asarray(amps),EPS))
    vals["harm_slope"]=float(np.polyfit(hs,la,1)[0])
    vals["harm_amp_max_rel_db"]=float(np.max(20*np.log10(np.maximum(np.asarray(amps),EPS)/h1)))
    return vals

FAMILY_PREFIXES={
 "envelope":("env_",),
 "mfcc":("mfcc_",),
 "spectral":("spec_",),
 "harmonic_ratios":("harm_ratio_",),
 "detuning_inharmonicity":("detune_","inharm_"),
 "harmonic_shape":("width_","contrast_","harm_slope","harm_amp_"),
}
def columns_for(names,family):
    if family=="all": return list(range(len(names)))
    prefs=FAMILY_PREFIXES[family]
    return [i for i,n in enumerate(names) if any(n.startswith(p) for p in prefs)]

def evaluate(X,df,cols,trees):
    truth=df.string.to_numpy(); pred=np.zeros(len(df),dtype=int); conf=np.zeros(len(df))
    midis=df.midi.to_numpy()
    for midi in sorted(df.midi.unique()):
        te=np.where(midis==midi)[0]; tr=np.where(midis!=midi)[0]
        sc=StandardScaler().fit(X[tr][:,cols])
        clf=model(trees).fit(sc.transform(X[tr][:,cols]),truth[tr]-1)
        probs=clf.predict_proba(sc.transform(X[te][:,cols]))
        for j,idx in enumerate(te):
            p=mask(probs[j],int(midi)); pred[idx]=int(np.argmax(p))+1; conf[idx]=float(np.max(p))
    return pred,conf,float(accuracy_score(truth,pred))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("wav_dir",type=Path)
    ap.add_argument("--out",type=Path,default=Path("training/results/time_phase"))
    ap.add_argument("--trees",type=int,default=40)
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)

    # Fixed bins plus overlapping sliding windows. All times are seconds after
    # librosa trim onset (same t=0 convention as existing trainer).
    fixed=[("attack_0_40",0,.04),("attack_40_80",.04,.08),
      ("transition_80_120",.08,.12),("early_120_200",.12,.20),
      ("early_200_300",.20,.30),("stable_300_450",.30,.45),
      ("stable_450_650",.45,.65),("late_650_900",.65,.90),
      ("late_900_1200",.90,1.20),("tail_1200_1600",1.20,1.60)]
    sliding=[(f"slide_{c-40}_{c+40}",(c-40)/1000,(c+40)/1000) for c in range(40,1001,40)]
    cumulative=[(f"cum_0_{e}",0,e/1000) for e in (40,80,120,160,200,300,450,650,900,1200)]
    windows=fixed+sliding+cumulative

    recs=[]
    for p in sorted(a.wav_dir.glob("*.wav")):
        m=RX.fullmatch(p.name)
        if not m: continue
        s,f=int(m[1]),int(m[2]); y,sr=librosa.load(p,sr=22050,mono=True)
        recs.append((p.name,s,f,m[3].lower(),OPEN_MIDI[s]+f,onset_trim(y),sr))
    df=pd.DataFrame([{"file":r[0],"string":r[1],"fret":r[2],"strength":r[3],"midi":r[4]} for r in recs])
    print(f"Loaded {len(df)} recordings")

    families=list(FAMILY_PREFIXES)+["all"]
    results=[]; predictions=[]
    for wi,(label,t0,t1) in enumerate(windows,1):
        feats=[extract_window(r[5],r[6],r[4],t0,t1) for r in recs]
        names=list(feats[0]); X=np.asarray([[d[n] for n in names] for d in feats],dtype=np.float32)
        for family in families:
            cols=columns_for(names,family)
            if not cols: continue
            st=time.time(); pred,conf,acc=evaluate(X,df,cols,a.trees)
            results.append({"window":label,"t0_ms":round(t0*1000),"t1_ms":round(t1*1000),
              "window_ms":round((t1-t0)*1000),"family":family,"features":len(cols),
              "trees":a.trees,"correct":int((pred==df.string.to_numpy()).sum()),
              "total":len(df),"accuracy":acc,"seconds":round(time.time()-st,2)})
            for i,row in df.iterrows():
                predictions.append({"window":label,"family":family,"file":row.file,
                  "string":int(row.string),"fret":int(row.fret),"midi":int(row.midi),
                  "strength":row.strength,"predicted_string":int(pred[i]),"confidence":float(conf[i])})
        pd.DataFrame(results).to_csv(a.out/"time_family_results.csv",index=False)
        print(f"[{wi}/{len(windows)}] {label}: best={max(x['accuracy'] for x in results if x['window']==label):.4%}")

    rdf=pd.DataFrame(results)
    rdf.to_csv(a.out/"time_family_results.csv",index=False)
    pd.DataFrame(predictions).to_csv(a.out/"predictions.csv",index=False)
    best_by_family=rdf.loc[rdf.groupby("family").accuracy.idxmax()].sort_values("accuracy",ascending=False)
    best_by_window=rdf.loc[rdf.groupby("window").accuracy.idxmax()].sort_values(["t0_ms","t1_ms"])
    best_by_family.to_csv(a.out/"best_by_family.csv",index=False)
    best_by_window.to_csv(a.out/"best_by_window.csv",index=False)
    overall=rdf.sort_values(["accuracy","features"],ascending=[False,True]).iloc[0].to_dict()
    summary={"recordings":len(df),"windows":len(windows),"families":families,
      "overall_best":overall,
      "best_by_family":best_by_family.to_dict(orient="records")}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
