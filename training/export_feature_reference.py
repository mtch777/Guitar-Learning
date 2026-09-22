#!/usr/bin/env python3
"""Export librosa's exact 107-feature vector for one training WAV."""
import argparse, json
from pathlib import Path
import importlib.util
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("train_full_ringing", HERE/"train_full_ringing.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

ap=argparse.ArgumentParser()
ap.add_argument("wav",type=Path)
ap.add_argument("--out",type=Path)
args=ap.parse_args()
values,names=mod.extract(args.wav)
payload={"file":args.wav.name,"count":len(values),"features":dict(zip(names,map(float,values)))}
text=json.dumps(payload,indent=2)
if args.out:
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(text)
else:
    print(text)
