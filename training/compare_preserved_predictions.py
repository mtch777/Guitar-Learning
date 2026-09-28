#!/usr/bin/env python3
"""Compare preserved prediction artifacts without retraining any model."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

KEY=["file","string","fret","midi","strength"]

def load(path):
    d=pd.read_csv(path)
    d["correct"]=d.predicted_string==d.string
    return d

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline",type=Path,required=True)
    ap.add_argument("--harmonic",type=Path,required=True)
    ap.add_argument("--confirmation",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)

    base=load(a.baseline).rename(columns={"predicted_string":"baseline_pred","confidence":"baseline_conf","correct":"baseline_correct"})
    harm=load(a.harmonic).rename(columns={"predicted_string":"harmonic_pred","confidence":"harmonic_conf","correct":"harmonic_correct"})
    conf=pd.read_csv(a.confirmation)
    mf=conf[conf.config=="mfcc_cum_0_120"].copy()
    mf["mfcc_correct"]=mf.predicted_string==mf.string
    mf=mf.rename(columns={"predicted_string":"mfcc_pred","confidence":"mfcc_conf"})

    keepb=KEY+["baseline_pred","baseline_conf","baseline_correct"]
    keeph=KEY+["harmonic_pred","harmonic_conf","harmonic_correct"]
    keepm=KEY+["mfcc_pred","mfcc_conf","mfcc_correct"]
    m=base[keepb].merge(harm[keeph],on=KEY,validate="one_to_one").merge(mf[keepm],on=KEY,validate="one_to_one")
    assert len(m)==384

    flags=["baseline_correct","harmonic_correct","mfcc_correct"]
    m["correct_count"]=m[flags].sum(axis=1)
    m["all_correct"]=m.correct_count==3
    m["all_wrong"]=m.correct_count==0
    m["mfcc_unique_save"]=(m.mfcc_correct & ~m.baseline_correct & ~m.harmonic_correct)
    m["harmonic_unique_save"]=(m.harmonic_correct & ~m.baseline_correct & ~m.mfcc_correct)
    m["baseline_unique_save"]=(m.baseline_correct & ~m.harmonic_correct & ~m.mfcc_correct)
    m.to_csv(a.out/"prediction_overlap.csv",index=False)
    m[m.correct_count<3].to_csv(a.out/"disagreements_and_errors.csv",index=False)

    wrong={k:set(m.loc[~m[f"{k}_correct"],"file"]) for k in ("baseline","harmonic","mfcc")}
    summary={
      "recordings":len(m),
      "accuracy":{
        "baseline":float(m.baseline_correct.mean()),
        "harmonic_214":float(m.harmonic_correct.mean()),
        "mfcc_0_120":float(m.mfcc_correct.mean())},
      "errors":{k:len(v) for k,v in wrong.items()},
      "error_overlap":{
        "all_three":len(wrong["baseline"]&wrong["harmonic"]&wrong["mfcc"]),
        "baseline_harmonic":len(wrong["baseline"]&wrong["harmonic"]),
        "baseline_mfcc":len(wrong["baseline"]&wrong["mfcc"]),
        "harmonic_mfcc":len(wrong["harmonic"]&wrong["mfcc"])},
      "unique_saves":{
        "baseline":int(m.baseline_unique_save.sum()),
        "harmonic_214":int(m.harmonic_unique_save.sum()),
        "mfcc_0_120":int(m.mfcc_unique_save.sum())},
      "oracle_any_model_correct":float((m.correct_count>0).mean()),
      "oracle_errors":int((m.correct_count==0).sum()),
      "all_correct":int(m.all_correct.sum()),
      "disagreement_recordings":int((m.correct_count<3).sum())
    }
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__": main()
