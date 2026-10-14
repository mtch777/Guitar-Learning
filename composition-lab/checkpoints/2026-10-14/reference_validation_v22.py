"""V22: evaluate *reviewed* chord and phrase labels, never pseudo-ground-truth.

A blank review file yields null accuracy, not zero accuracy. Chord spelling is
normalized for enharmonic root aliases but qualities must agree exactly.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOTS = {'C': 0,'C#':1,'DB':1,'D':2,'D#':3,'EB':3,'E':4,'FB':4,
         'E#':5,'F':5,'F#':6,'GB':6,'G':7,'G#':8,'AB':8,
         'A':9,'A#':10,'BB':10,'B':11,'CB':11,'B#':0}
TRUE={'yes','y','true','1','boundary'}
FALSE={'no','n','false','0','not_boundary'}
UNKNOWN={'','unknown','uncertain','unscorable','skip','n/a'}


def parse_chord(label):
    value=(label or '').strip()
    if value.lower() in UNKNOWN:return None
    match=re.fullmatch(r'([A-Ga-g])([#b♯♭]?)[ ]+([A-Za-z0-9_+#/()♭♯-]+)',value)
    if not match:raise ValueError(f'Invalid chord label {label!r}; expected C# minor7, F major, etc.')
    tonic=(match.group(1).upper()+match.group(2).replace('♯','#').replace('♭','b')).upper()
    if tonic not in ROOTS:raise ValueError(f'Unrecognized root {tonic}')
    # Quality names come from the chord vocabulary and are not inferred.
    quality=match.group(3).lower().replace('♭','b').replace('♯','#')
    return ROOTS[tonic],quality


def parse_boundary(value):
    v=(value or '').strip().lower()
    if v in UNKNOWN:return None
    if v in TRUE:return True
    if v in FALSE:return False
    raise ValueError(f'Invalid boundary label {value!r}; use yes/no/unknown')


def _safe_div(a,b):return round(a/b,4) if b else None


def evaluate_rows(rows):
    seen=set(); chord_total=chord_correct=0; tp=fp=fn=tn=0
    confidence_buckets=defaultdict(lambda:[0,0]); per_song=defaultdict(lambda:Counter())
    invalid=[]; counted=0
    for i,row in enumerate(rows,start=2):
        source=(row.get('source_file') or '').strip()
        track=(row.get('track_index') or '').strip()
        onset=(row.get('onset_q') or '').strip()
        key=(source,track,onset)
        if any(not x for x in key):invalid.append({'row':i,'error':'Missing source_file, track_index, or onset_q'});continue
        if key in seen:invalid.append({'row':i,'error':'Duplicate source/track/onset'});continue
        seen.add(key);counted+=1
        try:
            reviewed=parse_chord(row.get('human_chord_label',''))
            predicted=parse_chord(row.get('candidate_chord',''))
            boundary=parse_boundary(row.get('human_phrase_boundary',''))
            boundary_pred=parse_boundary(row.get('predicted_phrase_boundary',''))
            if boundary is not None and boundary_pred is None:
                raise ValueError('Missing/invalid predicted_phrase_boundary')
        except ValueError as exc:
            invalid.append({'row':i,'error':str(exc)});continue
        song=per_song[source]
        if reviewed is not None:
            chord_total+=1;song['chord_reviewed']+=1
            same=predicted == reviewed
            chord_correct+=int(same);song['chord_correct']+=int(same)
            raw=row.get('candidate_score_uncalibrated','')
            try:
                confidence=float(raw)
                if 0<=confidence<=1:
                    bucket=min(4,int(confidence*5))
                    confidence_buckets[bucket][0]+=int(same)
                    confidence_buckets[bucket][1]+=1
            except (ValueError,TypeError):pass
        if boundary is not None:
            song['boundary_reviewed']+=1
            if boundary and boundary_pred:tp+=1;song['boundary_tp']+=1
            elif not boundary and boundary_pred:fp+=1;song['boundary_fp']+=1
            elif boundary and not boundary_pred:fn+=1;song['boundary_fn']+=1
            else:tn+=1;song['boundary_tn']+=1
    precision=_safe_div(tp,tp+fp);recall=_safe_div(tp,tp+fn)
    f1=_safe_div(2*tp,2*tp+fp+fn)
    return {'schema':'V22 reviewed ground-truth evaluation',
            'reviewed_rows_unique':counted,'invalid_rows':invalid,
            'chord':{'reviewed':chord_total,'top1_correct':chord_correct,
                     'top1_accuracy':_safe_div(chord_correct,chord_total),
                     'unlabeled_not_counted':True},
            'phrase_boundary':{'reviewed':tp+fp+fn+tn,'tp':tp,'fp':fp,'fn':fn,'tn':tn,
                               'precision':precision,'recall':recall,'f1':f1},
            'chord_score_bins_descriptive_only':[
                {'score_bin':f'{k/5:.1f}–{(k+1)/5:.1f}',
                 'count':v[1],'observed_accuracy':_safe_div(v[0],v[1])}
                 for k,v in sorted(confidence_buckets.items())],
            'by_song':dict(per_song),
            'caveat':'Metrics apply ONLY to human-reviewed examples, not all notes. Sampling is stratified; do not treat reviewed accuracy as population accuracy.'}


def evaluate_file(csv_path,report_path=None):
    with open(csv_path,newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        required={'source_file','track_index','onset_q','candidate_chord',
                  'human_chord_label','predicted_phrase_boundary','human_phrase_boundary'}
        missing=required-set(reader.fieldnames or ())
        if missing:raise ValueError(f'Missing columns: {sorted(missing)}')
        report=evaluate_rows(list(reader))
    if report_path:Path(report_path).write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('review_csv');parser.add_argument('--out',default=None)
    args=parser.parse_args()
    print(json.dumps(evaluate_file(args.review_csv,args.out),indent=2))

if __name__=='__main__':main()