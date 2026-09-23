#!/usr/bin/env python3
"""Train/evaluate the ringing-only physical-position classifier.

Dataset may contain one or more takes per string/fret. Muted recordings are
deliberately excluded. Expected filenames:
  s{string}_f{fret}_{soft|normal|hard}_ringing.wav

This preparation version keeps the production 107-feature baseline intact and
adds evaluation scaffolding for the next feature/model iteration.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import joblib, librosa, numpy as np, pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

OPEN_MIDI={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63}
STATS=("mean","std","p25","median","p75")
RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$",re.I)

def summary(x):
    x=np.asarray(x).ravel()
    return [float(np.mean(x)),float(np.std(x)),float(np.percentile(x,25)),
            float(np.median(x)),float(np.percentile(x,75))]

def db(v): return float(20*np.log10(max(float(v),1e-12)))

def harmonic_features(y,sr,midi):
    """Pitch-relative harmonic features: H2-H8/H1 in three time regions,
    temporal deltas, peak detuning/shape, and local harmonic-to-noise contrast."""
    f0=440.0*2**((midi-69)/12)
    regions=(("harm_attack",0.00,0.12),("harm_early",0.15,0.40),("harm_late",0.40,0.80))
    vals=[]; names=[]; ratios=[]
    for region,t0,t1 in regions:
        seg=y[int(t0*sr):min(len(y),int(t1*sr))]
        if len(seg)<256: seg=y
        n_fft=max(8192,1<<(max(256,len(seg))-1).bit_length())
        win=np.hanning(len(seg))
        spec=np.abs(np.fft.rfft(seg*win,n=n_fft))
        freqs=np.fft.rfftfreq(n_fft,1/sr)
        amps=[]; region_ratios=[]
        for h in range(1,9):
            target=f0*h
            if target>=sr/2:
                amps.append(1e-12); continue
            bw=max(4.0,target*.006)
            mask=np.abs(freqs-target)<=bw
            amps.append(float(np.sqrt(np.sum(spec[mask]**2))) if np.any(mask) else 1e-12)
        h1=max(amps[0],1e-12)
        for h in range(2,9):
            ratio=20*np.log10(max(amps[h-1],1e-12)/h1)
            vals.append(float(ratio)); names.append(f"{region}_h{h}_db_vs_h1"); region_ratios.append(ratio)
        ratios.append(region_ratios)

        # Peak-level shape around H1-H8: cents detuning, width, and local contrast.
        for h in range(1,9):
            target=f0*h
            if target>=sr/2:
                vals += [0.0,0.0,0.0]
            else:
                search=max(8.0,target*.02)
                idx=np.where(np.abs(freqs-target)<=search)[0]
                if not len(idx):
                    vals += [0.0,0.0,0.0]
                else:
                    peak_idx=idx[np.argmax(spec[idx])]
                    peak_f=max(freqs[peak_idx],1e-9); peak=max(spec[peak_idx],1e-12)
                    cents=1200*np.log2(peak_f/target)
                    half=peak/np.sqrt(2)
                    left=peak_idx
                    while left>0 and spec[left]>=half: left-=1
                    right=peak_idx
                    while right+1<len(spec) and spec[right]>=half: right+=1
                    width=freqs[right]-freqs[left]
                    noise_idx=idx[np.abs(freqs[idx]-peak_f)>max(4.0,target*.006)]
                    noise=float(np.median(spec[noise_idx])) if len(noise_idx) else 1e-12
                    contrast=20*np.log10(peak/max(noise,1e-12))
                    vals += [float(cents),float(width),float(contrast)]
            names += [f"{region}_h{h}_detune_cents",f"{region}_h{h}_width_hz",f"{region}_h{h}_contrast_db"]

    # Harmonic evolution: early-attack and late-early deltas for H2-H8.
    for a,b,label in ((0,1,"early_minus_attack"),(1,2,"late_minus_early")):
        for h in range(2,9):
            vals.append(float(ratios[b][h-2]-ratios[a][h-2]))
            names.append(f"harm_{label}_h{h}_delta_db")
    return vals,names

def extract(path,string,fret,feature_set="full"):
    y,sr=librosa.load(path,sr=22050,mono=True)
    y,_=librosa.effects.trim(y,top_db=50)
    attack=y[:int(.12*sr)]
    sustain=y[int(.15*sr):min(len(y),int(.8*sr))]
    if len(sustain)<512: sustain=y[min(len(y)//2,int(.12*sr)):]
    values=[]; names=[]
    for part,seg in (("attack",attack),("sustain",sustain)):
        mfcc=librosa.feature.mfcc(y=seg,sr=sr,n_mfcc=13)
        for i in range(13):
            values += [float(np.mean(mfcc[i])),float(np.std(mfcc[i]))]
            names += [f"{part}_mfcc{i+1}_mean",f"{part}_mfcc{i+1}_std"]
        descriptors={
          "centroid":librosa.feature.spectral_centroid(y=seg,sr=sr),
          "bandwidth":librosa.feature.spectral_bandwidth(y=seg,sr=sr),
          "rolloff":librosa.feature.spectral_rolloff(y=seg,sr=sr),
          "flatness":librosa.feature.spectral_flatness(y=seg),
          "zcr":librosa.feature.zero_crossing_rate(seg),
        }
        for name,data in descriptors.items():
            values += summary(data)
            names += [f"{part}_{name}_{stat}" for stat in STATS]
    n50=min(len(y),int(.05*sr)); n100=min(len(y),int(.10*sr))
    peak=np.max(np.abs(attack)) if len(attack) else 0
    rms50=np.sqrt(np.mean(y[:n50]**2)) if n50 else 0
    rms100=np.sqrt(np.mean(y[:n100]**2)) if n100 else 0
    energy100=np.sum(y[:n100]**2) if n100 else 0
    total=np.sqrt(np.mean(y**2)) if len(y) else 0
    values += [db(peak),db(rms50),db(rms100),float(energy100),db(total)]
    names += ["attack_peak_dbfs","attack_rms_50_dbfs","attack_rms_100_dbfs",
              "attack_energy_100","total_rms_dbfs"]
    assert len(values)==107
    if feature_set!="baseline":
        hv,hn=harmonic_features(y,sr,OPEN_MIDI[string]+fret)
        values += hv; names += hn
    return np.asarray(values,dtype=np.float32),names

def model(n=100):
    return XGBClassifier(n_estimators=n,max_depth=3,learning_rate=.04,subsample=.85,
      colsample_bytree=.85,reg_lambda=2,objective="multi:softprob",num_class=8,
      random_state=42,n_jobs=8)

def mask(probs,midi):
    p=probs.copy()
    for i,s in enumerate(range(1,9)):
        if not (OPEN_MIDI[s] <= midi <= OPEN_MIDI[s]+24): p[i]=0
    total=p.sum()
    return p/total if total else p

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("wav_dir",type=Path)
    ap.add_argument("--out",type=Path,default=Path("training/results/full_ringing"))
    ap.add_argument("--feature-set",choices=("baseline","full"),default="full")
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    rows=[]; xs=[]
    for path in sorted(a.wav_dir.glob("*.wav")):
        # This is intentional: muted never enters the dataset.
        if "muted" in path.name.lower(): continue
        m=RX.fullmatch(path.name)
        if not m: continue
        string=int(m[1]); fret=int(m[2])
        x,names=extract(path,string,fret,a.feature_set); xs.append(x)
        rows.append({"string":string,"fret":fret,"strength":m[3].lower(),"file":path.name})
    if not rows:
        raise RuntimeError("No ringing recordings found")
    X=np.vstack(xs); df=pd.DataFrame(rows); truth=df.string.to_numpy()
    df["midi"]=[OPEN_MIDI[s]+f for s,f in zip(df.string,df.fret)]
    pred=np.zeros(len(df),dtype=int); confidence=np.zeros(len(df))

    # Primary validation: hold out an entire pitch. This directly tests the
    # generalization problem we care about while candidate masking constrains
    # each prediction to physically possible strings.
    for midi in sorted(df.midi.unique()):
        test=np.where(df.midi.to_numpy()==midi)[0]
        train=np.where(df.midi.to_numpy()!=midi)[0]
        if not len(train): continue
        scaler=StandardScaler().fit(X[train])
        clf=model().fit(scaler.transform(X[train]),truth[train]-1)
        probs=clf.predict_proba(scaler.transform(X[test]))
        for row_i,idx in enumerate(test):
            p=mask(probs[row_i],int(midi))
            pred[idx]=int(np.argmax(p))+1; confidence[idx]=float(np.max(p))

    strengths=sorted(df.strength.unique())
    metrics={"recordings":len(df),"positions":int(df[["string","fret"]].drop_duplicates().shape[0]),
      "muted_included":0,"feature_set":a.feature_set,"features":X.shape[1],
      "leave_one_pitch_out_accuracy":float(accuracy_score(truth,pred)),
      "by_strength":{s:float(accuracy_score(truth[df.strength==s],pred[df.strength.to_numpy()==s]))
                     for s in strengths}}
    final_scaler=StandardScaler().fit(X)
    final_model=model().fit(final_scaler.transform(X),truth-1)
    final_model.save_model(a.out/"ringing_xgboost.json")
    joblib.dump(final_scaler,a.out/"ringing_scaler.joblib")
    (a.out/"feature_names.json").write_text(json.dumps(names,indent=2))
    (a.out/"metrics.json").write_text(json.dumps(metrics,indent=2))
    df.assign(predicted_string=pred,confidence=confidence).to_csv(a.out/"leave_one_pitch_out_predictions.csv",index=False)
    print(json.dumps(metrics,indent=2))

if __name__=="__main__": main()
