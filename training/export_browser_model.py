#!/usr/bin/env python3
"""Export trained 107-feature XGBoost model to the website's compact binary format."""
from __future__ import annotations
import argparse, base64, json, struct
from pathlib import Path
import joblib
import numpy as np
import xgboost as xgb

def pack_model(model_path: Path) -> bytes:
    booster=xgb.Booster()
    booster.load_model(model_path)
    dump=booster.get_dump(dump_format="json")
    if len(dump)!=800:
        raise RuntimeError(f"Expected 800 multiclass trees (100 rounds x 8 classes), got {len(dump)}")
    out=bytearray(struct.pack("<H",len(dump)))
    for ti,raw in enumerate(dump):
        root=json.loads(raw)
        nodes=[]
        def visit(node):
            idx=len(nodes); nodes.append(None)
            if "leaf" in node:
                nodes[idx]=("leaf",float(node["leaf"]))
                return idx
            children={int(c["nodeid"]):c for c in node["children"]}
            yes=visit(children[int(node["yes"])])
            no=visit(children[int(node["no"])])
            split=node["split"]
            feature=int(split[1:]) if isinstance(split,str) and split.startswith("f") else int(split)
            nodes[idx]=("split",feature,float(node["split_condition"]),yes,no)
            return idx
        visit(root)
        if len(nodes)>255: raise RuntimeError(f"Tree {ti} has {len(nodes)} nodes; compact format supports <=255")
        out += struct.pack("<BB",ti%8,len(nodes))
        for n in nodes:
            if n[0]=="leaf":
                out += struct.pack("<Bf",255,n[1])
            else:
                _,feature,threshold,left,right=n
                if not 0<=feature<255 or left>255 or right>255:
                    raise RuntimeError(f"Tree {ti} exceeds compact byte-index limits")
                out += struct.pack("<BfBB",feature,threshold,left,right)
    return bytes(out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("model_dir",type=Path)
    ap.add_argument("--public-dir",type=Path,default=Path("public/model"))
    ap.add_argument("--chunk-chars",type=int,default=60000)
    a=ap.parse_args(); a.public_dir.mkdir(parents=True,exist_ok=True)
    model=a.model_dir/"ringing_xgboost.json"
    scaler_path=a.model_dir/"ringing_scaler.joblib"
    scaler=joblib.load(scaler_path)
    mean=np.asarray(scaler.mean_,dtype=float); scale=np.asarray(scaler.scale_,dtype=float)
    if len(mean)!=107 or len(scale)!=107: raise RuntimeError("Expected 107-feature scaler")
    (a.public_dir/"ringing_scaler_384.json").write_text(json.dumps({"mean":mean.tolist(),"scale":scale.tolist()},separators=(",",":")))
    packed=pack_model(model)
    encoded=base64.b64encode(packed).decode("ascii")
    chunks=[encoded[i:i+a.chunk_chars] for i in range(0,len(encoded),a.chunk_chars)]
    for old in a.public_dir.glob("ringing_xgboost_384.b64.*"): old.unlink()
    for i,chunk in enumerate(chunks):
        (a.public_dir/f"ringing_xgboost_384.b64.{i:02d}").write_text(chunk)
    print(json.dumps({"compact_trees":800,"features":107,"packed_bytes":len(packed),"base64_chars":len(encoded),"chunks":len(chunks),"chunk_files":[f"ringing_xgboost_384.b64.{i:02d}" for i in range(len(chunks))]},indent=2))
if __name__=="__main__": main()
