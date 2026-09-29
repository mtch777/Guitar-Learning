#!/usr/bin/env python3
"""Export the archived full-data baseline/harmonic models to browser JSON.

These final fitted models are useful for inference parity, not the OOF accuracy
estimate. The early-MFCC model must be fitted/exported separately.
"""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import xgboost as xgb


def export(model_path, scaler_path):
    native_model = json.loads(model_path.read_text())
    base_score = native_model['learner']['learner_model_param']['base_score']
    base_score = json.loads(base_score) if base_score.startswith('[') else [float(base_score)] * 8
    scaler = joblib.load(scaler_path)
    # Use the native JSON tree arrays. The human-readable get_dump() rounds
    # split thresholds and can change decisions near a threshold.
    native = native_model['learner']['gradient_booster']['model']
    trees = []
    for cls, raw in zip(native['tree_info'], native['trees']):
        trees.append({'class': cls, 'left': raw['left_children'], 'right': raw['right_children'],
                      'feature': raw['split_indices'], 'value': raw['split_conditions'],
                      'defaultLeft': raw['default_left']})
    return {'mean': np.asarray(scaler.mean_).tolist(), 'scale': np.asarray(scaler.scale_).tolist(),
            'classes': list(range(1, 9)), 'baseScore': base_score, 'trees': trees}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline-dir', type=Path, required=True)
    p.add_argument('--harmonic-dir', type=Path, required=True)
    p.add_argument('--mfcc-dir', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    sources = [('baseline', a.baseline_dir, 107), ('harmonic', a.harmonic_dir, 214)]
    if a.mfcc_dir: sources.append(('mfcc', a.mfcc_dir, 26))
    for name, directory, expected in sources:
        data = export(directory/'ringing_xgboost.json', directory/'ringing_scaler.joblib')
        if len(data['mean']) != expected or len(data['trees']) != 800:
            raise ValueError(f'{name}: unexpected feature/tree count')
        target = a.out/f'{name}.json'
        target.write_text(json.dumps(data, separators=(',', ':')))
        print(f'{name}: {len(data["mean"])} features, {len(data["trees"])} trees, {target.stat().st_size} bytes')

if __name__ == '__main__':
    main()
