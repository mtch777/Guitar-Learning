#!/usr/bin/env python3
"""Save exact librosa-resampled/trimmed mono Float32 samples for JS parity."""
import argparse
import json
from pathlib import Path
import librosa
import numpy as np


def main():
    ap=argparse.ArgumentParser();ap.add_argument('wav_dir',type=Path)
    ap.add_argument('vectors_json',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    rows=json.loads(a.vectors_json.read_text())
    for i,row in enumerate(rows,1):
        y,_=librosa.load(a.wav_dir/row['file'],sr=22050,mono=True)
        y,_=librosa.effects.trim(y,top_db=50)
        np.asarray(y,np.float32).tofile(a.out/(row['file']+'.f32'))
        if i==1 or i%50==0:print(f'TRIMMED [{i}/{len(rows)}]',flush=True)

if __name__=='__main__':main()
