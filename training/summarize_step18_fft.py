#!/usr/bin/env python3
"""Gate paired FFT vs DFT features and report per-recording runtime."""
import argparse
import json
import statistics
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('paired_json')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    with open(args.paired_json, encoding='utf8') as f:
        rows = json.load(f)
    if not rows:
        raise ValueError('No recordings extracted')
    fast = np.asarray([r['features'] for r in rows], dtype=float)
    baseline = np.asarray([r['baseline_features'] for r in rows], dtype=float)
    if fast.shape != baseline.shape or fast.shape[1:] != (3, 26):
        raise ValueError(f'Unexpected features: {fast.shape}, {baseline.shape}')
    errors = fast - baseline
    float32_differences = int(np.count_nonzero(fast.astype(np.float32) != baseline.astype(np.float32)))
    old = [r['baseline_feature_runtime_ms'] for r in rows]
    new = [r['feature_runtime_ms'] for r in rows]
    warmup = 0 if args.smoke else 25
    result = {
        'recordings': len(rows), 'features': int(errors.size),
        'max_abs_feature_error': float(np.max(np.abs(errors))),
        'rmse_feature_error': float(np.sqrt(np.mean(errors ** 2))),
        'float32_feature_differences': float32_differences,
        'max_abs_power_error_first_segment': max(r['max_power_abs_diff'] for r in rows),
        'steady_state_excludes_first': warmup,
        'dft_median_ms': statistics.median(old[warmup:]),
        'fft_median_ms': statistics.median(new[warmup:]),
        'speedup': statistics.median(old[warmup:]) / statistics.median(new[warmup:]),
    }
    if result['max_abs_feature_error'] > 1e-6:
        raise AssertionError(f'Feature parity failed: {result}')
    if float32_differences:
        raise AssertionError(f'Model input changed: {result}')
    if result['fft_median_ms'] >= result['dft_median_ms']:
        raise AssertionError(f'No runtime improvement: {result}')
    with open(args.out, 'w', encoding='utf8') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
