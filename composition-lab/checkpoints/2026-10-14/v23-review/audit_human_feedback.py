"""Diagnostic V23 CSV audit. Usage: python audit_human_feedback.py first.csv second.csv"""
import argparse,csv
from collections import Counter
KEY=('source_file','track_index','onset_q')
def analyze(paths):
    reviews={}
    for path in paths:
        with open(path,encoding='utf-8-sig',newline='') as file:
            for row in csv.DictReader(file):
                if not any((row.get(k) or '').strip() for k in ('human_chord_label','human_phrase_boundary','human_notes')):continue
                key=tuple(row[k] for k in KEY)
                if key in reviews and any(reviews[key].get(k)!=row.get(k) for k in ('human_chord_label','human_phrase_boundary','human_notes')):
                    raise ValueError('Conflicting reviews for '+repr(key))
                reviews[key]=row
    matrix=Counter()
    def boundary(x):return {'true':'yes','false':'no','yes':'yes','no':'no'}.get(str(x).strip().lower())
    for row in reviews.values():
        prediction=boundary(row.get('predicted_phrase_boundary'))
        actual=boundary(row.get('human_phrase_boundary'))
        if prediction and actual:matrix[(prediction,actual)]+=1
    tp=matrix['yes','yes'];fp=matrix['yes','no'];tn=matrix['no','no'];fn=matrix['no','yes']
    print(f'Reviewed: {len(reviews)} | TP={tp} FP={fp} TN={tn} FN={fn} | agreement={tp+tn}/{tp+fp+tn+fn}')
    for row in reviews.values():
        print(row['onset_q'], 'model_boundary='+str(boundary(row.get('predicted_phrase_boundary'))),
              'human_boundary='+str(boundary(row.get('human_phrase_boundary'))),
              'model_chord='+str(row.get('candidate_chord')),
              'human_chord='+str(row.get('human_chord_label')),
              'note='+str(row.get('human_notes')))
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('csv',nargs='+')
    analyze(parser.parse_args().csv)
