#!/usr/bin/env python3
"""100-tree confirmation of winners from the completed time-phase screening run.

This does NOT repeat the 315-configuration screen. It evaluates only the
preselected winning/near-winning configurations under the same leave-one-pitch-
out + candidate-mask protocol, with live per-configuration progress.
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import librosa, numpy as np, pandas as pd
from run_time_phase_experiment import OPEN_MIDI, RX, onset_trim, extract_window, columns_for, evaluate

# Selected from completed screening artifact 10945985689.
CONFIGS=[
    ("all_cum_0_120",0.0,0.120,"all"),
    ("all_cum_0_160",0.0,0.160,"all"),
    ("all_cum_0_900",0.0,0.900,"all"),
    ("mfcc_cum_0_80",0.0,0.080,"mfcc"),
    ("mfcc_cum_0_120",0.0,0.120,"mfcc"),
    ("mfcc_cum_0_160",0.0,0.160,"mfcc"),
    ("all_slide_40_120",0.040,0.120,"all"),
    ("all_slide_320_400",0.320,0.400,"all"),
]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("wav_dir",type=Path)
    ap.add_argument("--out",type=Path,default=Path("training/results/time_phase_confirmation"))
    ap.add_argument("--trees",type=int,default=100)
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)

    recs=[]
    for p in sorted(a.wav_dir.glob("*.wav")):
        m=RX.fullmatch(p.name)
        if not m: continue
        s,f=int(m[1]),int(m[2]); y,sr=librosa.load(p,sr=22050,mono=True)
        recs.append((p.name,s,f,m[3].lower(),OPEN_MIDI[s]+f,onset_trim(y),sr))
    df=pd.DataFrame([{"file":r[0],"string":r[1],"fret":r[2],"strength":r[3],"midi":r[4]} for r in recs])
    print(f"Loaded {len(df)} recordings",flush=True)
    print(f"Confirmation: {len(CONFIGS)} saved-screen winners x {a.trees} trees",flush=True)

    results=[]; predictions=[]; start=time.time()
    for ci,(label,t0,t1,family) in enumerate(CONFIGS,1):
        print(f"START [{ci}/{len(CONFIGS)}] {label}: extracting {round(t0*1000)}-{round(t1*1000)} ms",flush=True)
        feats=[extract_window(r[5],r[6],r[4],t0,t1) for r in recs]
        names=list(feats[0]); X=np.asarray([[d[n] for n in names] for d in feats],dtype=np.float32)
        cols=columns_for(names,family)
        st=time.time(); pred,conf,acc=evaluate(X,df,cols,a.trees)
        elapsed=time.time()-start; eta=(elapsed/ci)*(len(CONFIGS)-ci)
        row={"config":label,"t0_ms":round(t0*1000),"t1_ms":round(t1*1000),
             "family":family,"features":len(cols),"trees":a.trees,
             "correct":int((pred==df.string.to_numpy()).sum()),"total":len(df),
             "accuracy":acc,"seconds":round(time.time()-st,2)}
        results.append(row)
        for i,r in df.iterrows():
            predictions.append({"config":label,"family":family,"file":r.file,
              "string":int(r.string),"fret":int(r.fret),"midi":int(r.midi),
              "strength":r.strength,"predicted_string":int(pred[i]),
              "confidence":float(conf[i]),"correct":bool(pred[i]==r.string)})
        pd.DataFrame(results).to_csv(a.out/"confirmation_results.csv",index=False)
        pd.DataFrame(predictions).to_csv(a.out/"confirmation_predictions.csv",index=False)
        print(f"DONE  [{ci}/{len(CONFIGS)}] {label}: {acc:.4%} ({row['correct']}/{row['total']}) | step {row['seconds']:.1f}s | elapsed {elapsed/60:.1f}m | ETA {eta/60:.1f}m",flush=True)

    rdf=pd.DataFrame(results).sort_values(["accuracy","features"],ascending=[False,True])
    rdf.to_csv(a.out/"confirmation_results.csv",index=False)
    best=rdf.iloc[0].to_dict()
    errors=pd.DataFrame(predictions)
    errors=errors[~errors.correct].copy()
    errors.to_csv(a.out/"confirmation_errors.csv",index=False)
    summary={"source_screening_run":36358305377,"source_artifact_id":10945985689,
             "recordings":len(df),"trees":a.trees,"configs_tested":len(CONFIGS),
             "best":best,"results":rdf.to_dict(orient="records")}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__": main()
