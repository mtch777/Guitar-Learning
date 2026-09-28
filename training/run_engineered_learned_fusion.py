#!/usr/bin/env python3
"""Step 12: preserved-prediction learned-model complementarity screen.

No base model is retrained. Joins preserved OOF predictions from the original
baseline/harmonic benchmark, the confirmed 0-120 ms MFCC model, and Step 11's
compact CNN. The smoke test runs the exact join/scoring path on a tiny subset;
the real run evaluates all 384 recordings.

The learned branch survives only if it supplies meaningful unique rescues or
oracle headroom. This script intentionally does not fit a new fusion model:
that is gated on the complementarity result.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd,numpy as np

KEY=["file","string","fret","midi","strength"]

def csvs(root): return list(Path(root).rglob("*.csv"))

def find_cols(root, required, preferred=()):
    hits=[]
    for p in csvs(root):
        try:d=pd.read_csv(p,nrows=3)
        except Exception:continue
        if set(required)<=set(d.columns):
            score=sum(x.lower() in p.name.lower() for x in preferred)
            hits.append((score,p))
    if not hits: raise RuntimeError(f"No CSV under {root} with columns {required}")
    return sorted(hits,key=lambda x:(-x[0],str(x[1])))[0][1]

def load_original(root):
    p=find_cols(root,KEY+["predicted_string","confidence"],("prediction",))
    d=pd.read_csv(p)
    # The benchmark prediction file normally carries a model/config discriminator.
    disc=next((x for x in ("model","config","feature_set","method") if x in d.columns),None)
    if disc is None:
        raise RuntimeError(f"{p} has no model discriminator; columns={list(d.columns)}")
    vals=d[disc].astype(str).str.lower()
    def pick(tokens):
        q=np.zeros(len(d),dtype=bool)
        for t in tokens:q|=vals.str.contains(t,regex=False).to_numpy()
        z=d[q].copy()
        if len(z)!=384: raise RuntimeError(f"{disc} {tokens} selected {len(z)} rows, expected 384; values={sorted(d[disc].astype(str).unique())}")
        return z
    # Prefer explicit baseline and harmonic/full labels.
    base=pick(["baseline"])
    harm_mask=vals.str.contains("harmonic",regex=False)|vals.str.fullmatch("full")
    harm=d[harm_mask].copy()
    if len(harm)!=384: raise RuntimeError(f"harmonic/full selected {len(harm)} rows; values={sorted(d[disc].astype(str).unique())}")
    return p,base,harm

def load_mfcc(root):
    p=find_cols(root,KEY+["predicted_string","confidence"],("prediction",))
    d=pd.read_csv(p)
    if "config" in d.columns:
        z=d[d.config.astype(str)=="mfcc_cum_0_120"].copy()
        if len(z)==384:return p,z
    # tolerate an artifact containing only the confirmed config
    if len(d)==384:return p,d
    raise RuntimeError(f"Could not identify 384-row mfcc_cum_0_120 in {p}")

def load_cnn(root):
    p=find_cols(root,KEY+["masked_pred","masked_conf"],("spectral_cnn_predictions",))
    d=pd.read_csv(p)
    if len(d)!=384:raise RuntimeError(f"CNN rows={len(d)}, expected 384")
    return p,d

def prep(d,name,pred,conf):
    z=d[KEY+[pred,conf]].copy().rename(columns={pred:f"{name}_pred",conf:f"{name}_conf"})
    z[f"{name}_correct"]=z[f"{name}_pred"].astype(int)==z.string.astype(int)
    return z

def main():
    ap=argparse.ArgumentParser()
    for x in ("original","confirmation","cnn"):ap.add_argument(f"--{x}",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True); ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    op,b,h=load_original(a.original); mp,m=load_mfcc(a.confirmation); cp,c=load_cnn(a.cnn)
    print(f"INPUT original={op} confirmation={mp} cnn={cp}",flush=True)
    parts=[prep(b,"baseline","predicted_string","confidence"),prep(h,"harmonic","predicted_string","confidence"),
           prep(m,"mfcc","predicted_string","confidence"),prep(c,"cnn","masked_pred","masked_conf")]
    d=parts[0]
    for i,x in enumerate(parts[1:],2):
        d=d.merge(x,on=KEY,validate="one_to_one");print(f"JOIN [{i}/4] rows={len(d)}",flush=True)
    if len(d)!=384:raise RuntimeError(f"joined rows={len(d)}, expected 384")
    if a.smoke:
        # Exercise the identical metrics/output path on a deterministic tiny slice.
        d=d.sort_values("file").iloc[:24].copy();print("SMOKE subset=24",flush=True)
    strong=["baseline","harmonic","mfcc"]; allm=strong+["cnn"]
    for x in allm:d[f"{x}_correct"]=d[f"{x}_correct"].astype(bool)
    strong_any=d[[f"{x}_correct" for x in strong]].any(axis=1)
    all_any=d[[f"{x}_correct" for x in allm]].any(axis=1)
    cnn_unique=d.cnn_correct & ~strong_any
    cnn_regression=(~d.cnn_correct)&strong_any
    d["strong_oracle_correct"]=strong_any;d["all4_oracle_correct"]=all_any;d["cnn_unique_rescue"]=cnn_unique
    d.to_csv(a.out/"learned_complementarity.csv",index=False)
    summary={"step":12,"phase":"complementarity_gate","smoke":a.smoke,"recordings":len(d),
      "correct":{x:int(d[f"{x}_correct"].sum()) for x in allm},
      "errors":{x:int((~d[f"{x}_correct"]).sum()) for x in allm},
      "strong3_oracle":{"correct":int(strong_any.sum()),"errors":int((~strong_any).sum()),"accuracy":float(strong_any.mean())},
      "with_cnn_oracle":{"correct":int(all_any.sum()),"errors":int((~all_any).sum()),"accuracy":float(all_any.mean())},
      "cnn_unique_rescues":int(cnn_unique.sum()),"cnn_wrong_when_strong3_any_correct":int(cnn_regression.sum()),
      "all_four_wrong_files":d.loc[~all_any,"file"].tolist(),"cnn_unique_rescue_files":d.loc[cnn_unique,"file"].tolist()}
    # Gate: require at least one unique rescue in the full real run. Even then,
    # later calibrated fusion must justify complexity; this is only an oracle gate.
    summary["proceed_to_learned_fusion"]=bool((not a.smoke) and summary["cnn_unique_rescues"]>0)
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__":main()
