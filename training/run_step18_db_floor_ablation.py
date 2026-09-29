#!/usr/bin/env python3
"""Measure the classifier effect of segment-global versus frame-local dB floor."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from run_step18_feature_crossover import CONTROLS, TARGETS, model, physical_mask

PATHS = ("local_local", "local_global", "global_local", "global_global")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("local_json", type=Path)
    ap.add_argument("global_json", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    local = json.loads(args.local_json.read_text())
    glob = json.loads(args.global_json.read_text())
    names = [r["file"] for r in local]
    assert len(names) == len(set(names)) == 384
    assert names == [r["file"] for r in glob], "Recording order differs"
    assert set(TARGETS + CONTROLS) <= set(names)
    truth = np.array([r["string"] for r in local], int)
    midi = np.array([r["true_midi"] for r in local], int)
    assert all(r["string"] == s["string"] and r["true_midi"] == s["true_midi"]
               for r, s in zip(local, glob))
    X = {"local": [np.asarray([r["features"][j] for r in local], np.float32)
                   for j in range(3)],
         "global": [np.asarray([r["features"][j] for r in glob], np.float32)
                    for j in range(3)]}
    assert all(X[k][j].shape == (384, 26) for k in X for j in range(3))
    selected = set(TARGETS + CONTROLS) if args.smoke else set(names)
    eval_idx = np.array([i for i, name in enumerate(names) if name in selected])
    raw = {key: np.zeros((384, 3, 8)) for key in PATHS}
    trees = 20 if args.smoke else 100
    folds = [m for m in sorted(set(midi)) if np.any(midi[eval_idx] == m)]
    start = time.time()
    for fold, m in enumerate(folds, 1):
        te = eval_idx[midi[eval_idx] == m]
        tr = np.where(midi != m)[0]
        classes = np.sort(np.unique(truth[tr]))
        enc = {s: i for i, s in enumerate(classes)}
        labels = np.array([enc[s] for s in truth[tr]])
        for frame in range(3):
            for train in ("local", "global"):
                scaler = StandardScaler().fit(X[train][frame][tr])
                clf = model(trees, len(classes))
                clf.fit(scaler.transform(X[train][frame][tr]), labels)
                for test in ("local", "global"):
                    probs = clf.predict_proba(scaler.transform(X[test][frame][te]))
                    for col, string in enumerate(classes):
                        raw[train + "_" + test][te, frame, string - 1] = probs[:, col]
        print(f"DB FLOOR FOLD [{fold}/{len(folds)}] MIDI {m} "
              f"elapsed={time.time()-start:.1f}s", flush=True)

    predictions, traces = [], []
    for i in eval_idx:
        row = {"file": names[i], "true_string": int(truth[i]),
               "true_midi": int(midi[i])}
        trace = {"file": names[i], "paths": {}}
        for key in PATHS:
            masked = np.array([physical_mask(p, midi[i]) for p in raw[key][i]])
            mean = masked.mean(axis=0)
            row[key + "_pred"] = int(np.argmax(mean) + 1)
            row[key + "_confidence"] = float(mean.max())
            if names[i] in TARGETS + CONTROLS:
                trace["paths"][key] = {"raw_per_frame": raw[key][i].tolist(),
                                        "masked_per_frame": masked.tolist(),
                                        "mean": mean.tolist()}
        if names[i] in TARGETS + CONTROLS:
            trace["feature_rmse_per_frame"] = [float(np.sqrt(np.mean(
                (X["local"][j][i] - X["global"][j][i]) ** 2)))
                for j in range(3)]
            traces.append(trace)
        predictions.append(row)
    df = pd.DataFrame(predictions)
    df.to_csv(args.out / "predictions.csv", index=False)
    (args.out / "decision_traces.json").write_text(json.dumps(traces, indent=2))
    summary = {"smoke": args.smoke, "trees": trees,
               "recordings_scored": len(df), "folds_scored": len(folds),
               "accuracy": {key: int((df[key + "_pred"] == df.true_string).sum())
                            for key in PATHS},
               "changed_predictions": [r["file"] for r in predictions
                                       if r["local_local_pred"] != r["global_global_pred"]]}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    if args.smoke:
        assert set(df.file) == set(TARGETS + CONTROLS), "Smoke skipped a target"
    else:
        assert summary["accuracy"]["local_local"] == 375, "JS baseline changed"


if __name__ == "__main__":
    main()
