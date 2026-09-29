#!/usr/bin/env python3
"""Step 18 Stage-A diagnosis and complete tuple impact, Smoke -> Real."""
import argparse
import json
import time
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from run_pitch_detector_tournament import hz_to_midi, librosa_yin, yin_custom
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
    truth = np.array([r["string"] for r in rows], int)
    midi = np.array([r["true_midi"] for r in rows], int)
    js_midi = np.array([r["pred_midi"] if r["pred_midi"] is not None else -999
                        for r in rows], int)
    X = [np.asarray([r["features"][j] for r in rows], np.float32)
         for j in range(3)]
    selected = set(TARGETS + CONTROLS) if args.smoke else set(names)
    eval_idx = np.array([i for i, name in enumerate(names) if name in selected])
    py_midi = np.full(len(rows), -999, int)
    custom_midi = np.full(len(rows), -999, int)
    pitch_details = {}
    start = time.time()
    for count, i in enumerate(eval_idx, 1):
        y, sr = librosa.load(args.wav_dir / names[i], sr=22050, mono=True)
        y, trim_idx = librosa.effects.trim(y, top_db=50)
        seg = y[:min(len(y), max(128, int(sr * .240)))]
        py_hz, _, _ = librosa_yin(seg, sr)
        custom_hz, custom_conf, minima = yin_custom(seg, sr)
        py_midi[i] = hz_to_midi(py_hz) if hz_to_midi(py_hz) is not None else -999
        custom_midi[i] = hz_to_midi(custom_hz) if hz_to_midi(custom_hz) is not None else -999
        pitch_details[names[i]] = {
            "python_yin_hz": float(py_hz) if np.isfinite(py_hz) else None,
            "python_custom_yin_hz": float(custom_hz) if np.isfinite(custom_hz) else None,
            "python_custom_yin_confidence": float(custom_conf),
            "custom_yin_minima": minima,
            "python_trim_indices": [int(v) for v in trim_idx],
            "js_hz": rows[i]["pitch_hz"],
            "js_confidence": rows[i]["pitch_confidence"],
        }
        if count == 1 or count % 25 == 0:
            print(f"PITCH [{count}/{len(eval_idx)}] elapsed={time.time()-start:.1f}s", flush=True)

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
               "true_string": int(truth[i]), "js_midi": int(js_midi[i]),
               "python_yin_midi": int(py_midi[i]),
               "python_custom_yin_midi": int(custom_midi[i]),
               "js_hz": rows[i]["pitch_hz"],
               "python_yin_hz": pitch_details[names[i]]["python_yin_hz"],
               "js_confidence": rows[i]["pitch_confidence"]}
        for key, pred_midi in (("js", js_midi[i]), ("python_yin", py_midi[i]),
                               ("oracle", midi[i])):
            prob = np.mean([mask(P[frame][i], pred_midi)
                            for frame in range(3)], axis=0)
            row[key + "_string"] = int(np.argmax(prob) + 1)
            row[key + "_confidence"] = float(prob.max())
            row[key + "_tuple_correct"] = bool(pred_midi == midi[i] and
                                               row[key + "_string"] == truth[i])
        predictions.append(row)
    df = pd.DataFrame(predictions)
    df.to_csv(args.out / "predictions.csv", index=False)
    details = {name: pitch_details[name] for name in TARGETS + CONTROLS}
    (args.out / "pitch_details.json").write_text(json.dumps(details, indent=2))
    summary = {"smoke": args.smoke, "trees": trees,
               "recordings_scored": len(df), "folds_scored": len(folds),
               "js_pitch_correct": int((df.js_midi == df.true_midi).sum()),
               "python_yin_pitch_correct": int((df.python_yin_midi == df.true_midi).sum()),
               "python_custom_yin_pitch_correct": int((df.python_custom_yin_midi == df.true_midi).sum()),
               "js_tuple_correct": int(df.js_tuple_correct.sum()),
               "python_yin_tuple_correct": int(df.python_yin_tuple_correct.sum()),
               "oracle_string_correct": int(df.oracle_tuple_correct.sum()),
               "pitch_disagreements": [r["file"] for r in predictions
                                       if r["js_midi"] != r["python_yin_midi"]]}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    if args.smoke:
        assert set(df.file) == set(TARGETS + CONTROLS), "Smoke omitted cases"
    else:
        assert summary["js_pitch_correct"] == 373, "JS pitch baseline changed"
        assert summary["python_yin_pitch_correct"] == 375, "Python YIN baseline changed"
        assert summary["js_tuple_correct"] == 364, "JS tuple baseline changed"
        assert set(summary["pitch_disagreements"]) == set(TARGETS), "Error overlap changed"


if __name__ == "__main__":
    main()
