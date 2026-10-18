"""Run revised source-only detector; feedback remains private development evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pedal_regions import detect_regions


def feedback_audit(feedback,cases):
    fingerprint=hashlib.sha256(json.dumps([(c['source_sha256'],c['target_ids']) for c in cases]).encode()).hexdigest()[:16]
    if feedback.get('qa') or feedback.get('study') not in tuple(prefix+fingerprint for prefix in ('pedal-identification-','pedal-revision-','pedal-fresh-')):raise ValueError('Feedback belongs to another source study or QA')
    records=[]
    for case in cases:
        judgment=feedback.get('judgments',{}).get(case['id'],{})
        by_id={n['occurrence']:n for n in case['notes']}; selected=set()
        for mark in judgment.get('selected_notes',[]):
            note=by_id.get(mark['occurrence'])
            if note is None or note['midi']!=mark['pitch'] or note['bar']!=mark['bar']:raise ValueError('Invalid feedback note identity')
            selected.add(mark['occurrence'])
        predicted=detect_regions(case['notes']);new={i for r in predicted for i in r['anchor_occurrences']}
        old=set(case['target_ids']) if 'revised_regions' in case else {n['occurrence'] for n in case['notes'] if n['occurrence'] in case['target_ids'] and n['midi']==case['anchor']}
        records.append(dict(case=case['id'],answer=judgment.get('answer',''),notes=judgment.get('notes',''),
                            selected_notes=len(selected),old_selected_covered=len(old&selected),new_selected_covered=len(new&selected),
                            old_marked=len(old),new_marked=len(new),missing_selected=sorted(selected-new),
                            cohort=case.get('cohort'),marking_coverage=judgment.get('marking_coverage'),
                            extra_predictions=sorted(new-selected) if judgment.get('marking_coverage') in ('all','none') else None,
                            pre_reveal_judgment=judgment.get('pre_reveal_judgment'),
                            unselected_prediction_status='negative only when explicitly marked exhaustive or no anchors',regions=predicted))
    return dict(records=records,selected=sum(r['selected_notes'] for r in records),
                old_selected_covered=sum(r['old_selected_covered'] for r in records),new_selected_covered=sum(r['new_selected_covered'] for r in records),
                limitations=['Development feedback used to revise rules, not held-out accuracy.',
                             'Blank or Unclear answers are not converted into Yes/No.',
                             'Unselected notes are negative only for explicit all/none coverage; otherwise unknown.'])


def run(report):
    counts=Counter();private=[]
    for song in report['songs']:
        for track in song['tracks']:
            if not track['guitar_or_bass'] or not track['temporal_relationships_eligible']:continue
            found=detect_regions(track['rows']);counts['eligible_tracks']+=1
            counts['region_hypotheses']+=len(found)
            counts.update(p['anchor_kind'] for p in found)
            counts['anchor_occurrences']+=sum(len(p['anchor_occurrences']) for p in found)
            private.append(dict(song_id=song['song_id'],part_id=track['part_id'],regions=found))
    return dict(schema='pedal-region-observations-v2',counts=dict(counts),
                limitations=['Rules revised using nine reviewed passages: this is development evidence, not held-out accuracy.',
                             'Standalone single/dyad anchors and temporal separation are operational hypotheses.',
                             'Section-wide extension can span unrelated material; phrase segmentation remains unresolved.',
                             'Exact dyads support standalone reduced voicings; octave-equivalent or unmarked ties remain limited.',
                             'Lowest concurrent anchor preference and uniform-triad abstention are explicit heuristics, not universal musical rules.']),private


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True)
    p.add_argument('--feedback',type=Path);p.add_argument('--cases',type=Path);a=p.parse_args()
    if 'local-artifacts' not in a.private.resolve().parts:p.error('Occurrence evidence stays private')
    public,private=run(json.loads(a.report.read_text(encoding='utf-8')))
    public['input_sha256']=hashlib.sha256(a.report.read_bytes()).hexdigest()
    a.public.write_text(json.dumps(public,indent=2),encoding='utf-8');a.private.write_text(json.dumps(private,separators=(',',':')),encoding='utf-8');print(json.dumps(public))
    if a.feedback:
        if not a.cases:p.error('--cases is required with feedback')
        audit=feedback_audit(json.loads(a.feedback.read_text(encoding='utf-8')),json.loads(a.cases.read_text(encoding='utf-8')))
        audit['feedback_sha256']=hashlib.sha256(a.feedback.read_bytes()).hexdigest()
        a.private.with_name('feedback-comparison.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
