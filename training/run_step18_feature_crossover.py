#!/usr/bin/env python3
"""Step 18: isolate training-feature versus test-feature parity drift.

All four paths use ground-truth MIDI for the physical candidate mask. The
training pool, held-out MIDI folds, model settings and recording order are
identical. Smoke fits fewer trees and scores the four disagreements plus two
controls; Real scores all 384 and verifies both published baselines.
"""
import argparse
import json
import time
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

OPEN = {1: 27, 2: 34, 3: 39, 4: 44, 5: 49, 6: 54, 7: 58, 8: 63}
FRAMES = [(0, .04), (.04, .08), (.08, .12)]
TARGETS = (
    "s3_f00_soft_ringing.wav",
    "s5_f06_normal_ringing.wav",
    "s7_f00_soft_ringing.wav",
    "s8_f00_soft_ringing.wav",
)
CONTROLS = ("s5_f04_normal_ringing.wav", "s3_f12_hard_ringing.wav")
PATHS = ("python_python", "python_js", "js_python", "js_js")


def mfcc26(y, sr, t0, t1):
    # Keep this equivalent to run_context_ablation.py (the 376/384 reference).
    a = int(t0 * sr)
    b = min(len(y), max(a + 1, int(t1 * sr)))
    seg = y[a:b]
    if len(seg) < 128:
        seg = np.pad(seg, (0, 128 - len(seg)))
    nfft = max(64, 2 ** int(np.floor(np.log2(len(seg)))))
    nfft = min(2048, nfft, len(seg))
    hop = max(16, nfft // 4)
    n_mels = min(40, max(16, nfft // 8))
    m = librosa.feature.mfcc(y=seg, sr=sr, n_mfcc=13,
                             n_fft=nfft, hop_length=hop, n_mels=n_mels)
    return np.asarray([v for row in m for v in (row.mean(), row.std())], np.float32)


def model(n, k):
    return XGBClassifier(n_estimators=n, max_depth=3, learning_rate=.04,
                         subsample=.85, colsample_bytree=.85, reg_lambda=2,
                         objective="multi:softprob", num_class=k,
                         random_state=42, n_jobs=8)


def physical_mask(p, midi):
    q = p.copy()
    for i, s in enumerate(range(1, 9)):
        if not OPEN[s] <= midi <= OPEN[s] + 24:
            q[i] = 0
    return q / q.sum() if q.sum() else q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav_dir", type=Path)
    ap.add_argument("browser_json", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    rows = json.loads(args.browser_json.read_text())
    names = [r["file"] for r in rows]
    assert len(names) == len(set(names)) == 384, "Expected 384 unique recordings"
    assert set(TARGETS + CONTROLS) <= set(names)
    truth = np.array([r["string"] for r in rows], int)
    midis = np.array([r["true_midi"] for r in rows], int)
    X = {"js": [np.asarray([r["features"][j] for r in rows], np.float32)
                for j in range(3)]}
    py = [[], [], []]
    start = time.time()
    for i, name in enumerate(names, 1):
        y, sr = librosa.load(args.wav_dir / name, sr=22050, mono=True)
        y, _ = librosa.effects.trim(y, top_db=50)
        for j, (t0, t1) in enumerate(FRAMES):
            py[j].append(mfcc26(y, sr, t0, t1))
        if i == 1 or i % 25 == 0:
            print(f"PYTHON FEATURES [{i}/384] elapsed={time.time()-start:.1f}s", flush=True)
    X["python"] = [np.vstack(frame) for frame in py]
    assert all(X["js"][j].shape == X["python"][j].shape == (384, 26)
               for j in range(3))

    selected = set(TARGETS + CONTROLS) if args.smoke else set(names)
    eval_idx = np.array([i for i, name in enumerate(names) if name in selected])
    raw = {key: np.zeros((len(names), 3, 8)) for key in PATHS}
    trees = 20 if args.smoke else 100
    folds = [m for m in sorted(set(midis)) if np.any((midis == m) &
              np.isin(names, list(selected)))]
    start = time.time()
    for fold, midi in enumerate(folds, 1):
        te = np.array([i for i in eval_idx if midis[i] == midi])
        tr = np.where(midis != midi)[0]
        classes = np.sort(np.unique(truth[tr]))
        enc = {s: i for i, s in enumerate(classes)}
        labels = np.array([enc[s] for s in truth[tr]])
        for frame in range(3):
            for train_source in ("python", "js"):
                scaler = StandardScaler().fit(X[train_source][frame][tr])
                clf = model(trees, len(classes))
                clf.fit(scaler.transform(X[train_source][frame][tr]), labels)
                for test_source in ("python", "js"):
                    key = train_source + "_" + test_source
                    probs = clf.predict_proba(scaler.transform(X[test_source][frame][te]))
                    for col, string in enumerate(classes):
                        raw[key][te, frame, string - 1] = probs[:, col]
        print(f"CROSSOVER FOLD [{fold}/{len(folds)}] MIDI {midi} "
              f"elapsed={time.time()-start:.1f}s", flush=True)

    predictions = []
    details = []
    for i in eval_idx:
        row = {"file": names[i], "true_string": int(truth[i]),
               "true_midi": int(midis[i])}
        detail = {"file": names[i], "true_string": int(truth[i]),
                  "true_midi": int(midis[i]), "paths": {}, "features": {}}
        for key in PATHS:
            masked = np.array([physical_mask(p, midis[i]) for p in raw[key][i]])
            mean = masked.mean(axis=0)
            row[key + "_pred"] = int(np.argmax(mean) + 1)
            row[key + "_confidence"] = float(mean.max())
            detail["paths"][key] = {
                "raw_per_frame": raw[key][i].tolist(),
                "masked_per_frame": masked.tolist(),
                "mean": mean.tolist(),
                "prediction": row[key + "_pred"],
            }
        if names[i] in TARGETS + CONTROLS:
            for frame in range(3):
                a, b = X["python"][frame][i], X["js"][frame][i]
                detail["features"][str(frame)] = {
                    "python": a.tolist(), "js": b.tolist(),
                    "rmse": float(np.sqrt(np.mean((a - b) ** 2))),
                }
            details.append(detail)
        predictions.append(row)
    df = pd.DataFrame(predictions)
    df.to_csv(args.out / "predictions.csv", index=False)
    (args.out / "decision_traces.json").write_text(json.dumps(details, indent=2))
    accuracy = {key: {"correct": int((df[key + "_pred"] == df.true_string).sum()),
                      "total": len(df)} for key in PATHS}
    disagreements = [r["file"] for r in predictions
                     if r["python_python_pred"] != r["js_js_pred"]]
    summary = {"smoke": args.smoke, "trees": trees,
               "recordings_scored": len(df), "folds_scored": len(folds),
               "accuracy": accuracy, "baseline_disagreements": disagreements,
               "targets": list(TARGETS), "controls": list(CONTROLS)}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    if not args.smoke:
        assert accuracy["python_python"]["correct"] == 376, "Python baseline changed"
        assert accuracy["js_js"]["correct"] == 375, "JS baseline changed"
        assert len(disagreements) == 4, "Baseline disagreement set changed"
    else:
        assert set(TARGETS + CONTROLS) == set(df.file), "Smoke skipped a target"


if __name__ == "__main__":
    main()
