"""Cross-song engineering comparisons; no accuracy or listening verdicts."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from exact_score import extract_score
from generation_validation import validate_split, copying_ngrams, track_metrics


def distribution(score):
    pitches=Counter();durations=Counter()
    for track in score['tracks']:
        for m in track['measures']:
            for voice in m['voices']:
                for e in voice:
                    if e.get('grace_type'):continue
                    durations[str(Fraction(e['duration_q']))]+=1
                    pitches.update(n['midi']%12 for n in e['notes'] if n['midi'] is not None)
    return pitches,durations


def js_divergence(a,b):
    if not a or not b:return None
    keys=set(a)|set(b);ta,tb=sum(a.values()),sum(b.values());value=0
    for key in keys:
        p,q=a[key]/ta,b[key]/tb;mean=(p+q)/2
        if p:value+=p*math.log2(p/mean)/2
        if q:value+=q*math.log2(q/mean)/2
    return value


def main():
    p=argparse.ArgumentParser();p.add_argument('--training',required=True,type=Path)
    p.add_argument('--held-out',required=True,type=Path);p.add_argument('--generated',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);args=p.parse_args()
    split=validate_split([args.training],[args.held_out]); training=extract_score(args.training);heldout=extract_score(args.held_out)
    manifest=json.loads((args.generated/'manifest.json').read_text())
    if manifest['source_sha256']!=training['source_sha256']:raise ValueError('Generated artifact training provenance mismatch')
    report=dict(split=split,seed=manifest['seed'],training=args.training.name,held_out=args.held_out.name,stages={})
    for file in sorted(args.generated.glob('*.gp')):
        score=extract_score(file);metrics=track_metrics(score)
        a,b=distribution(score);ta,tb=distribution(training);ha,hb=distribution(heldout)
        report['stages'][file.stem]=dict(sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
            tracks=len(score['tracks']),bars=score['measure_count'],metrics=metrics,
            training_copying=copying_ngrams(training,score),heldout_copying=copying_ngrams(heldout,score),
            pitch_class_js_training=js_divergence(a,ta),pitch_class_js_heldout=js_divergence(a,ha),
            duration_js_training=js_divergence(b,tb),duration_js_heldout=js_divergence(b,hb))
    report['limitations']=['Two source songs only; no population accuracy estimate',
        'Pooled histograms are descriptive and sensitive to track selection; not role/style quality',
        'Holdout never fitted; no independent harmonic/phrase reference labels',
        'Copying checks cover exact relative windows only; not proof of originality',
        'Human listening review pending']
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(training=report['training'],held_out=report['held_out'],stages={k:dict(tracks=v['tracks'],copy_train=v['training_copying']['exact_relative_match_share'],copy_heldout=v['heldout_copying']['exact_relative_match_share']) for k,v in report['stages'].items()}),indent=2))


if __name__=='__main__':main()
