#!/usr/bin/env python3
"""Fit final early-MFCC model for browser inference, not OOF evaluation."""
import argparse
from pathlib import Path
import joblib
import librosa
import numpy as np
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from train_full_ringing import OPEN_MIDI, RX
from run_time_phase_experiment import extract_window, columns_for


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('wav_dir', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    rows, labels = [], []
    for path in sorted(a.wav_dir.glob('*.wav')):
        match = RX.fullmatch(path.name)
        if not match: continue
        string, fret = int(match[1]), int(match[2])
        y, sr = librosa.load(path, sr=22050, mono=True)
        y, _ = librosa.effects.trim(y, top_db=50)
        d = extract_window(y, sr, OPEN_MIDI[string] + fret, 0, .12)
        names = list(d); cols = columns_for(names, 'mfcc')
        rows.append([d[names[i]] for i in cols]); labels.append(string-1)
        if len(rows) == 1 or len(rows) % 25 == 0:
            print(f'EARLY MFCC EXTRACT [{len(rows)}]', flush=True)
    if len(rows) != 384 or len(rows[0]) != 26:
        raise ValueError('Expected 384 recordings with 26 early MFCC features')
    X = np.asarray(rows, np.float32); sc = StandardScaler().fit(X)
    model = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=.04,
                          subsample=.85, colsample_bytree=.85, reg_lambda=2,
                          objective='multi:softprob', num_class=8, random_state=42, n_jobs=8)
    model.fit(sc.transform(X), np.asarray(labels, int))
    model.save_model(a.out/'ringing_xgboost.json'); joblib.dump(sc, a.out/'ringing_scaler.joblib')
    print('Fitted final 26-feature MFCC model; no in-sample accuracy claim', flush=True)

if __name__ == '__main__': main()
