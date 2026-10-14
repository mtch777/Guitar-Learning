"""V21 evaluation harness: distinguishes observable invariants, proxy labels, and human ground truth.

No proxy or exact-template match is presented as verified musical accuracy.
"""
from __future__ import annotations
import argparse, csv, json, random
from collections import Counter
from fractions import Fraction
from pathlib import Path
from extract import extract_score
from joint_interpretation_v20 import interpret, boundary_evidence
from harmonic_inference import NAMES


def track_candidates(score):
    """Rank track choices by pitched coverage; do not mislabel the first track as guitar."""
    ans=[]
    for t in score['tracks']:
        events=[e for m in t['measures'] for v in m['voices'] for e in v]
        pitched=[e for e in events if any(n['midi'] is not None for n in e['notes'])]
        ans.append({'index':t['index'],'name':t['name'],'pitched_events':len(pitched),
                    'total_events':len(events),'tuning_available':bool(t['tunings'] and t['tunings'][0])})
    return sorted(ans,key=lambda t:-t['pitched_events'])


def _section_starts(score,track):
    return {Fraction(m['onset_q']) for m in score['tracks'][track]['measures'] if m.get('section') and Fraction(m['onset_q'])!=0}


def _fmt(onset):return str(onset)

def evaluate(score,track,*,sample_size=16,seed=2026):
    post=interpret(score,track)
    boundaries=boundary_evidence(score,track)
    if not post:return {},[]
    by_time={x['onset']:x for x in boundaries}
    section=_section_starts(score,track)
    events=[e for m in score['tracks'][track]['measures'] for v in m['voices'] for e in v]
    attack_times={x['onset'] for x in post}
    # These are *weak* boundary proxies: only section starts that coincide with
    # an attack can be scored, and an unmarked point is NOT a negative label.
    located=section & attack_times
    predicted={x['onset'] for x in boundaries if x['boundary_score']>=.75}
    matched=located & predicted
    exact=sum(x['observed_anchor'] is not None for x in post)
    lowconf=sum(x['confidence']<.5 for x in post)
    probabilities=[x['confidence'] for x in post]
    results={
      'track_index':track,'track_name':score['tracks'][track]['name'],
      'attacks':len(post),'exact_template_matches_not_ground_truth':exact,
      'unresolved_exact_template_match':len(post)-exact,
      'top_hypothesis_confidence_mean_not_calibrated':round(sum(probabilities)/len(probabilities),4),
      'top_hypothesis_confidence_below_half':lowconf,
      'candidate_boundaries':len(predicted),
      'explicit_section_markers_after_start':len(section),
      'section_markers_at_note_attacks':len(located),
      'section_attack_recall_proxy':round(len(matched)/len(located),4) if located else None,
      'section_markers_not_at_attacks':len(section-located),
      'unmarked_attacks_are_not_verified_non_boundaries':True,
      'true_chord_accuracy':None,'true_phrase_boundary_precision':None,
      'reason_ground_truth_missing':'No human-verified, time-aligned chord and phrase boundary annotations',
    }
    # Deliberate mix of template-supported / unsupported and predicted boundary /
    # other points, to avoid only reviewing the easy or high-confidence cases.
    groups={
      'boundary_exact':[x for x in post if x['onset'] in predicted and x['observed_anchor'] is not None],
      'boundary_unresolved':[x for x in post if x['onset'] in predicted and x['observed_anchor'] is None],
      'nonboundary_exact':[x for x in post if x['onset'] not in predicted and x['observed_anchor'] is not None],
      'nonboundary_unresolved':[x for x in post if x['onset'] not in predicted and x['observed_anchor'] is None],
    }
    rng=random.Random(seed+track)
    for group in groups.values():rng.shuffle(group)
    picked=[]
    while len(picked)<sample_size and any(groups.values()):
        for category in groups:
            if len(picked)>=sample_size:break
            if groups[category]:picked.append((category,groups[category].pop()))
    review=[]
    for category,x in sorted(picked,key=lambda pair:pair[1]['onset']):
        onset=x['onset'];b=by_time[onset];top=x['candidates'][0]
        # raw note list for playback/navigation: note that this alone does not
        # contain the other tracks' bass or all contextual notes.
        observed=[e for e in events if Fraction(e['onset_q'])<=onset<Fraction(e['onset_q'])+Fraction(e['duration_q'])]
        review.append({
          'source_file':score['source_file'],'track_index':track,'track_name':score['tracks'][track]['name'],
          'onset_q':_fmt(onset),'measure':max((m['number'] for m in score['tracks'][track]['measures'] if Fraction(m['onset_q'])<=onset),default=None),
          'sample_group':category,'sounding_midi': ' '.join(map(str,x['midi'])),
          'candidate_chord':NAMES[top['root']]+' '+top['quality'],
          'candidate_score_uncalibrated':round(top['probability'],4),
          'template_exact_match':x['observed_anchor'] is not None,
          'predicted_phrase_boundary':b['boundary_score']>=.75,
          'boundary_score':round(b['boundary_score'],3),
          'explicit_section_start':onset in section,
          'human_chord_label':'','human_chord_confidence':'',
          'human_phrase_boundary':'','human_notes':'',
        })
    return results,review


def run(paths,out_dir,*,samples=16,max_measures=20):
    out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
    report={'schema':'V21 musical evaluation / no ground truth yet','songs':[],'interpretation_accuracy_claimed':False}
    all_reviews=[]
    for path in paths:
        score=extract_score(path)
        if max_measures is not None:
            score={**score,'tracks':[{**t,'measures':t['measures'][:max_measures]} for t in score['tracks']]}
        tracks=track_candidates(score)
        eligible=[t for t in tracks if t['pitched_events']>=20 and t['tuning_available']]
        if not eligible:eligible=[t for t in tracks if t['pitched_events']>=20]
        # Choose the most information-rich pitched track while preserving name
        # and index in all results; not an implicit lead/melody role label.
        if not eligible:continue
        chosen=eligible[0]
        result,review=evaluate(score,chosen['index'],sample_size=samples)
        report['songs'].append({'file':Path(path).name,'available_tracks':tracks,'selected':chosen,'measures_evaluated':min(score['measure_count'],max_measures or score['measure_count']),'evaluation':result})
        all_reviews.extend(review)
    (out_dir/'V21_evaluation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (out_dir/'V21_human_review.csv').open('w',newline='',encoding='utf-8') as f:
        if all_reviews:
            w=csv.DictWriter(f,fieldnames=list(all_reviews[0]));w.writeheader();w.writerows(all_reviews)
    return report,all_reviews


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('files',nargs='+');ap.add_argument('--out-dir',required=True)
    ap.add_argument('--samples',type=int,default=16)
    ap.add_argument('--max-measures',type=int,default=20)
    args=ap.parse_args()
    result,rows=run(args.files,args.out_dir,samples=args.samples,max_measures=args.max_measures)
    print(json.dumps({'songs':len(result['songs']),'samples':len(rows),'summary':[(x['file'],x['evaluation']['attacks'],x['evaluation']['exact_template_matches_not_ground_truth'],x['evaluation']['section_attack_recall_proxy']) for x in result['songs']]},indent=2))

if __name__=='__main__':main()