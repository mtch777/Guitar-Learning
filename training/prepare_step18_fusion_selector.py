#!/usr/bin/env python3
"""Merge preserved OOF artifacts into a JS fusion validation fixture."""
import argparse
import json
from pathlib import Path
import pandas as pd

KEY = ['file', 'string', 'fret', 'midi', 'strength']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--harmonic', type=Path, required=True)
    parser.add_argument('--confirmation', type=Path, required=True)
    parser.add_argument('--fusion-gold', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    def load(path, name):
        d = pd.read_csv(path)
        return d[KEY + ['predicted_string', 'confidence']].rename(columns={
            'predicted_string': name + '_pred', 'confidence': name + '_conf'})
    rows = load(a.baseline, 'baseline').merge(load(a.harmonic, 'harmonic'), on=KEY, validate='one_to_one')
    c = pd.read_csv(a.confirmation)
    c = c[c.config == 'mfcc_cum_0_120']
    c = c[KEY + ['predicted_string', 'confidence']].rename(columns={
        'predicted_string': 'mfcc_pred', 'confidence': 'mfcc_conf'})
    rows = rows.merge(c, on=KEY, validate='one_to_one').sort_values('file')
    gold = pd.read_csv(a.fusion_gold)
    gold = gold[gold.method == 'calibrated_isotonic'][['file', 'predicted_string', 'score']]
    if len(rows) != 384 or len(gold) != 384:
        raise ValueError(f'Expected 384 rows and 384 references: {len(rows)}, {len(gold)}')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({'rows': rows.to_dict('records'), 'expected': gold.to_dict('records')}))
    print(f'Prepared {len(rows)} original out-of-fold rows')

if __name__ == '__main__': main()
