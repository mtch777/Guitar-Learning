#!/usr/bin/env python3
"""Analyze leave-one-pitch-out classifier errors from train_full_ringing.py."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from train_full_ringing import OPEN_MIDI

def candidates(midi):
    return [s for s in range(1,9) if OPEN_MIDI[s] <= midi <= OPEN_MIDI[s]+24]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("predictions",type=Path)
    ap.add_argument("--out",type=Path,default=None)
    a=ap.parse_args()
    out=a.out or a.predictions.parent/"error_analysis"
    out.mkdir(parents=True,exist_ok=True)

    df=pd.read_csv(a.predictions)
    df["correct"]=df["string"]==df["predicted_string"]
    df["candidate_strings"]=df["midi"].map(lambda m: ",".join(map(str,candidates(int(m)))))
    df["candidate_count"]=df["midi"].map(lambda m: len(candidates(int(m))))
    df["error_pair"]=df.apply(lambda r:f"S{int(r.string)}->S{int(r.predicted_string)}",axis=1)
    errors=df.loc[~df.correct].copy()

    # Position-level context: did other takes at the same physical position pass?
    pos=df.groupby(["string","fret"]).correct.agg(["sum","count"]).reset_index()
    pos["position_accuracy"]=pos["sum"]/pos["count"]
    errors=errors.merge(pos[["string","fret","position_accuracy","count"]],on=["string","fret"],how="left")
    errors=errors.rename(columns={"count":"position_takes"})
    errors=errors.sort_values(["midi","string","fret","strength"])
    errors.to_csv(out/"errors.csv",index=False)

    pair=(errors.groupby(["string","predicted_string"]).size().reset_index(name="errors")
          .sort_values("errors",ascending=False))
    pair.to_csv(out/"confusion_pairs.csv",index=False)
    by_strength=(df.groupby("strength").correct.agg(["sum","count"]).reset_index())
    by_strength["accuracy"]=by_strength["sum"]/by_strength["count"]
    by_strength.to_csv(out/"accuracy_by_strength.csv",index=False)
    by_string=(df.groupby("string").correct.agg(["sum","count"]).reset_index())
    by_string["accuracy"]=by_string["sum"]/by_string["count"]
    by_string.to_csv(out/"accuracy_by_string.csv",index=False)
    by_midi=(df.groupby("midi").correct.agg(["sum","count"]).reset_index())
    by_midi["errors"]=by_midi["count"]-by_midi["sum"]
    by_midi["accuracy"]=by_midi["sum"]/by_midi["count"]
    by_midi=by_midi.sort_values(["errors","midi"],ascending=[False,True])
    by_midi.to_csv(out/"accuracy_by_midi.csv",index=False)

    summary={
      "recordings":int(len(df)),
      "correct":int(df.correct.sum()),
      "errors":int((~df.correct).sum()),
      "accuracy":float(df.correct.mean()),
      "error_pairs":[{"true_string":int(r.string),"predicted_string":int(r.predicted_string),"errors":int(r.errors)}
                     for r in pair.itertuples(index=False)],
      "errors_by_strength":{str(k):int(v) for k,v in errors.groupby("strength").size().items()},
      "errors_by_true_string":{str(int(k)):int(v) for k,v in errors.groupby("string").size().items()},
      "error_midis":{str(int(k)):int(v) for k,v in errors.groupby("midi").size().items()},
      "mean_wrong_confidence":float(errors.confidence.mean()) if len(errors) else None,
      "high_confidence_errors":int((errors.confidence>=0.8).sum()) if len(errors) else 0
    }
    (out/"summary.json").write_text(json.dumps(summary,indent=2))

    cols=["file","string","fret","strength","midi","predicted_string","confidence",
          "candidate_strings","candidate_count","position_accuracy","position_takes"]
    print(json.dumps(summary,indent=2))
    if len(errors):
        print("\nERRORS")
        print(errors[cols].to_string(index=False))
    print(f"\nDetailed CSVs written to {out}")

if __name__=="__main__": main()
