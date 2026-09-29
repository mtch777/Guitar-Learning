#!/usr/bin/env python3
"""Score opt-in browser reference-YIN against current YIN, paired on one JS extraction."""
import argparse
import json
import time
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from run_pitch_detector_tournament import hz_to_midi, librosa_yin
from run_step18_browser_validation import clf, mask

TARGETS = ("s1_f05_hard_ringing.wav", "s3_f12_hard_ringing.wav")
CONTROLS = ("s1_f05_normal_ringing.wav", "s3_f12_normal_ringing.wav",
            "s1_f00_hard_ringing.wav", "s8_f00_soft_ringing.wav")


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
    assert len(names) == len(set(names)) == 384
    assert set(TARGETS + CONTROLS) <= set(names)
    assert all("baseline_pred_midi" in r for r in rows), "Use --compare-yin extraction"
    truth = np.array([r["string"] for r in rows], int)
    midi = np.array([r["true_midi"] for r in rows], int)
    old_midi = np.array([r["baseline_pred_midi"] if r["baseline_pred_midi"] is not None else -999
                         for r in rows], int)
    new_midi = np.array([r["pred_midi"] if r["pred_midi"] is not None else -999
                         for r in rows], int)
    X = [np.asarray([r["features"][j] for r in rows], np.float32)
         for j in range(3)]
    selected = set(TARGETS + CONTROLS) if args.smoke else set(names)
    eval_idx = np.array([i for i, name in enumerate(names) if name in selected])
    py_midi = np.full(len(rows), -999, int)
    py_hz = np.full(len(rows), np.nan)
    start = time.time()
    for count, i in enumerate(eval_idx, 1):
        y, sr = librosa.load(args.wav_dir / names[i], sr=22050, mono=True)
        y, _ = librosa.effects.trim(y, top_db=50)
        seg = y[:min(len(y), max(128, int(sr * .240)))]
        hz, _, _ = librosa_yin(seg, sr)
        py_hz[i] = hz
        m = hz_to_midi(hz)
        py_midi[i] = m if m is not None else -999
        if count == 1 or count % 25 == 0:
            print(f"REFERENCE PITCH [{count}/{len(eval_idx)}] "
                  f"elapsed={time.time()-start:.1f}s", flush=True)

    P = [np.zeros((len(rows), 8)) for _ in range(3)]
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
            scaler = StandardScaler().fit(X[frame][tr])
            model = clf(trees, len(classes))
            model.fit(scaler.transform(X[frame][tr]), labels)
            probs = model.predict_proba(scaler.transform(X[frame][te]))
            for col, string in enumerate(classes):
                P[frame][te, string - 1] = probs[:, col]
        print(f"STAGEB FOLD [{fold}/{len(folds)}] MIDI {m} "
              f"elapsed={time.time()-start:.1f}s", flush=True)

    predictions = []
    for i in eval_idx:
        row = {"file": names[i], "true_midi": int(midi[i]),
               "true_string": int(truth[i]), "old_midi": int(old_midi[i]),
               "new_midi": int(new_midi[i]), "python_yin_midi": int(py_midi[i]),
               "old_hz": rows[i]["baseline_pitch_hz"],
               "new_hz": rows[i]["pitch_hz"], "python_yin_hz": float(py_hz[i]),
               "old_pitch_confidence": rows[i]["baseline_pitch_confidence"],
               "new_pitch_confidence": rows[i]["pitch_confidence"],
               "old_runtime_ms": rows[i]["baseline_pitch_runtime_ms"],
               "new_runtime_ms": rows[i]["pitch_runtime_ms"]}
        for key, pred_midi in (("old", old_midi[i]), ("new", new_midi[i]),
                               ("python_yin", py_midi[i])):
            q = np.mean([mask(P[j][i], pred_midi) for j in range(3)], axis=0)
            row[key + "_string"] = int(np.argmax(q) + 1)
            row[key + "_tuple_correct"] = bool(pred_midi == midi[i] and
                                               row[key + "_string"] == truth[i])
        predictions.append(row)
    df = pd.DataFrame(predictions)
    df.to_csv(args.out / "predictions.csv", index=False)
    # Skip the first 25 recordings for paired steady-state timings; order
    # alternates which detector runs first on each recording.
    timing_idx = [i for i in eval_idx if i >= 25] or list(eval_idx)
    timing = {}
    for name, field in (("old", "baseline_pitch_runtime_ms"),
                        ("new", "pitch_runtime_ms")):
        v = np.array([rows[i][field] for i in timing_idx], float)
        timing[name] = {"n": len(v), "median_ms": float(np.median(v)),
                        "p95_ms": float(np.percentile(v, 95)),
                        "mean_ms": float(v.mean())}
    summary = {"smoke": args.smoke, "trees": trees,
               "recordings_scored": len(df), "folds_scored": len(folds),
               "old_pitch_correct": int((df.old_midi == df.true_midi).sum()),
               "new_pitch_correct": int((df.new_midi == df.true_midi).sum()),
               "python_yin_pitch_correct": int((df.python_yin_midi == df.true_midi).sum()),
               "old_tuple_correct": int(df.old_tuple_correct.sum()),
               "new_tuple_correct": int(df.new_tuple_correct.sum()),
               "python_yin_tuple_correct": int(df.python_yin_tuple_correct.sum()),
               "new_vs_python_midi_disagreements": [r["file"] for r in predictions
                      if r["new_midi"] != r["python_yin_midi"]],
               "old_vs_new_midi_disagreements": [r["file"] for r in predictions
                      if r["old_midi"] != r["new_midi"]],
               "paired_steady_state_pitch_runtime": timing}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    if args.smoke:
        assert set(df.file) == set(TARGETS + CONTROLS), "Smoke omitted cases"
    else:
        assert summary["old_pitch_correct"] == 373, "Old pitch baseline changed"
        assert summary["old_tuple_correct"] == 364, "Old tuple baseline changed"
        assert summary["python_yin_pitch_correct"] == 375, "Python YIN baseline changed"
        assert set(summary["old_vs_new_midi_disagreements"]) == set(TARGETS), "Unexpected port decisions"


if __name__ == "__main__":
    main()
