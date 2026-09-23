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

def extract(path):
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
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    rows=[]; xs=[]
    for path in sorted(a.wav_dir.glob("*.wav")):
        # This is intentional: muted never enters the dataset.
        if "muted" in path.name.lower(): continue
        m=RX.fullmatch(path.name)
        if not m: continue
        x,names=extract(path); xs.append(x)
        rows.append({"string":int(m[1]),"fret":int(m[2]),"strength":m[3].lower(),"file":path.name})
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
      "muted_included":0,"features":X.shape[1],
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
