#!/usr/bin/env python3
"""Summarize paired live trial exports without counting correlated frames as trials."""
import argparse
import collections
import json
import math
import statistics


def decision(frames, key, confidence_key, threshold=0):
    # The attack may be delayed after Record; use the loudest half of frames.
    if not frames:
        return None
    loudest = max(f.get('rms', 0) for f in frames)
    usable = [f for f in frames if f.get('rms', 0) >= max(0.001, loudest * 0.5)
              and f.get(key) is not None and f.get(confidence_key, 0) >= threshold]
    return statistics.median_low([f[key] for f in usable]) if usable else None


def summary(rows):
    total = len(rows)
    old = sum(r['oldCorrect'] for r in rows)
    new = sum(r['referenceCorrect'] for r in rows)
    gain = sum(r['referenceCorrect'] and not r['oldCorrect'] for r in rows)
    loss = sum(r['oldCorrect'] and not r['referenceCorrect'] for r in rows)
    discordant = gain + loss
    # Exact two-sided sign/McNemar test on paired, independent plucks.
    p = min(1, 2 * sum(math.comb(discordant, k) for k in range(min(gain, loss) + 1)) / (2 ** discordant)) if discordant else 1
    return {'trials': total, 'oldCorrect': old, 'referenceCorrect': new,
            'referenceWins': gain, 'oldWins': loss, 'pairedExactP': p}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exports', nargs='+')
    args = parser.parse_args()
    rows = []
    runtimes = collections.defaultdict(list)
    for filename in args.exports:
        with open(filename, encoding='utf8') as file:
            data = json.load(file)
        if data.get('schema') != 'paired-live-yin-v1':
            raise ValueError(f'{filename}: unsupported export schema')
        for trial in data['trials']:
            frames = trial['frames']
            old = decision(frames, 'oldMidi', 'oldConfidence', 0.55)
            reference = decision(frames, 'referenceMidi', 'referenceConfidence')
            row = {'string': trial['string'], 'fret': trial['fret'], 'attack': trial['attack'],
                   'repeat': trial['repeat'], 'expectedMidi': trial['expectedMidi'],
                   'oldMidi': old, 'referenceMidi': reference,
                   'oldCorrect': old == trial['expectedMidi'],
                   'referenceCorrect': reference == trial['expectedMidi']}
            rows.append(row)
            for frame in frames:
                runtimes['oldMs'].append(frame['oldMs'])
                runtimes['referenceMs'].append(frame['referenceMs'])
    if not rows:
        raise ValueError('No completed trials')
    result = {'overall': summary(rows), 'byAttack': {}, 'byString': {}, 'changedOrIncorrect': [],
              'runtimeMedianMs': {k: statistics.median(v) for k, v in runtimes.items()},
              'warning': 'Reference confidence is uncalibrated; this compares note decisions, not trainer string accuracy.'}
    for field, key in [('byAttack', 'attack'), ('byString', 'string')]:
        for value in sorted({r[key] for r in rows}):
            result[field][value] = summary([r for r in rows if r[key] == value])
    result['changedOrIncorrect'] = [r for r in rows if not (r['oldCorrect'] and r['referenceCorrect'])]
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
