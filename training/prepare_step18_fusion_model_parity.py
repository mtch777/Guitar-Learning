#!/usr/bin/env python3
"""Generate feature/model inference parity vectors from the original final models."""
import argparse
import json
from pathlib import Path
import joblib
import librosa  # required by train_full_ringing
import numpy as np
import xgboost as xgb
from train_full_ringing import extract, OPEN_MIDI, RX
from run_time_phase_experiment import extract_window, columns_for


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('wav_dir', type=Path)
    ap.add_argument('--baseline-dir', type=Path, required=True)
    ap.add_argument('--harmonic-dir', type=Path, required=True)
    ap.add_argument('--mfcc-dir', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args()
    models = {}
    sources = [('baseline', a.baseline_dir), ('harmonic', a.harmonic_dir)]
    if a.mfcc_dir: sources.append(('mfcc', a.mfcc_dir))
    for name, directory in sources:
        model = xgb.XGBClassifier()
        model.load_model(directory/'ringing_xgboost.json')
        models[name] = model, joblib.load(directory/'ringing_scaler.joblib')
    rows = []
    for path in sorted(a.wav_dir.glob('*.wav')):
        match = RX.fullmatch(path.name)
        if not match:
            continue
        string, fret = int(match[1]), int(match[2])
        midi = OPEN_MIDI[string] + fret
        if a.smoke and not (54 <= midi <= 60 and match[3].lower() == 'normal'):
            continue
        x, _ = extract(path, string, fret, 'full')
        row = {'file': path.name, 'midi': midi, 'string': string}
        vectors = {'baseline': x[:107], 'harmonic': x[:214]}
        if a.mfcc_dir:
            y, sr = librosa.load(path, sr=22050, mono=True)
            y, _ = librosa.effects.trim(y, top_db=50)
            d = extract_window(y, sr, midi, 0, .12)
            names = list(d); cols = columns_for(names, 'mfcc')
            vectors['mfcc'] = np.asarray([d[names[i]] for i in cols], np.float32)
        for name, vector in vectors.items():
            model, scaler = models[name]
            row[name + '_features'] = vector.astype(float).tolist()
            scaled = scaler.transform(vector[None, :]); row[name + '_scaled'] = scaled[0].astype(float).tolist()
            row[name + '_probabilities'] = model.predict_proba(scaled)[0].astype(float).tolist()
        rows.append(row)
        if len(rows) == 1 or len(rows) % 25 == 0:
            print(f'MODEL PARITY EXTRACT [{len(rows)}]', flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rows))
    print(f'WROTE {len(rows)} parity rows to {a.out}', flush=True)

if __name__ == '__main__':
    main()
