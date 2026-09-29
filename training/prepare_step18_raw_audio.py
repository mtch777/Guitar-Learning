#!/usr/bin/env python3
"""Extract native 44.1 kHz mono float samples for browser resampling parity."""
import argparse
import json
from pathlib import Path
import numpy as np
import soundfile as sf


def main():
    ap=argparse.ArgumentParser();ap.add_argument('wav_dir',type=Path)
    ap.add_argument('fixture',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    source=json.loads(a.fixture.read_text());rows=source if isinstance(source,list) else source['rows']
    for i,row in enumerate(rows,1):
        y,sr=sf.read(a.wav_dir/row['file'],dtype='float32')
        if sr!=44100 or y.ndim!=1:raise ValueError(f'Unexpected WAV format: {row["file"]} {sr} {y.shape}')
        np.asarray(y,np.float32).tofile(a.out/(row['file']+'.f32'))
        if i==1 or i%50==0:print(f'RAW AUDIO [{i}/{len(rows)}]',flush=True)

if __name__=='__main__':main()
