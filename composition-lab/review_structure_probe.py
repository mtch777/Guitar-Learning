"""Read-only score-aware diagnostic for V23 phrase boundary reviews.

Usage: python review_structure_probe.py SOURCE.gp FIRST.csv SECOND.csv
No threshold tuning: this conservative structural comparator is diagnostic,
NOT a replacement for the original model or a validated classifier.
"""
from __future__ import annotations
import argparse,csv,zipfile
from xml.etree import ElementTree as ET
from collections import Counter
from fractions import Fraction
from pathlib import Path
from phrase_development import parse,analyze_track
KEY=('source_file','track_index','onset_q')
def load_reviews(paths):
    reviews={}
    for path in paths:
        with open(path,newline='',encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                if row.get('human_phrase_boundary','').strip().lower() not in ('yes','no'):continue
                key=tuple(row[k] for k in KEY)
                if key in reviews and reviews[key]['human_phrase_boundary']!=row['human_phrase_boundary']:
                    raise ValueError('Conflicting boundary judgments for '+repr(key))
                reviews[key]=row
    return reviews
def meter_lengths(path):
    """Read authoritative measure durations from GPIF master-bar time signatures."""
    with zipfile.ZipFile(path) as archive:
        root=ET.fromstring(archive.read('Content/score.gpif'))
    lengths=[]
    for bar in root.findall('./MasterBars/MasterBar'):
        signature=(bar.findtext('Time') or '').strip()
        numerator,denominator=map(int,signature.split('/'))
        lengths.append(4*numerator/denominator)
    return lengths

def timeline(track,bar_lengths):
    cursor=0.;events=[];overflow=[]
    for number,(measure,length) in enumerate(zip(track['measures'],bar_lengths),1):
        for voice,onset,dur,pitches in measure:
            if onset+dur>length+.025:
                overflow.append(dict(measure=number,voice=voice,onset=onset,duration=dur,bar_length=length))
            events.append(dict(t=round(cursor+onset,5),end=round(cursor+onset+dur,5),voice=voice,pitches=pitches,measure=number))
        cursor+=length
    return events,overflow
def features(row,events,phrase_starts,section_starts,bar_starts):
    t=float(Fraction(row['onset_q']));near=[e for e in events if abs(e['t']-t)<.025]
    voices=sorted({e['voice'] for e in near})
    previous=[e for e in events if e['t']<t-.025 and e['voice'] in voices]
    previous_end=max((e['end'] for e in previous),default=None)
    gap=round(max(0.,t-previous_end),3) if previous_end is not None else None
    measure=int(row['measure']);downbeat=abs(t-4*(measure-1))<.025
    section_start=downbeat and measure in section_starts
    phrase_start=downbeat and measure in phrase_starts
    return dict(onset=t,voices=voices,gap=gap,downbeat=downbeat,section_start=section_start,
                phrase_start=phrase_start,structural_candidate=section_start or phrase_start,
                exact_source_onset=bool(near))
def confusion(pairs):
    c=Counter(pairs)
    return dict(tp=c[True,True],fp=c[True,False],tn=c[False,False],fn=c[False,True])
def probe(score_path,csv_paths):
    song=parse(score_path);reviews=load_reviews(csv_paths)
    original=[];structural=[];details=[];sections={m for m,_ in song['sections']}
    lengths=meter_lengths(score_path)
    starts=[];cursor=0.
    for length in lengths:
        starts.append(cursor);cursor+=length
    overflow=[];missing_onsets=[];source_pitch_matches=[]
    for key,row in reviews.items():
        if row['source_file']!=score_path.name:continue
        track=song['tracks'][int(row['track_index'])]
        phrases=analyze_track(track,song['sections'],song['measures'])['phrases']
        phrase_starts={p['start_measure'] for p in phrases}
        bar_starts=starts
        events,extra=timeline(track,lengths)
        overflow.extend(extra)
        feat=features(row,events,phrase_starts,sections,bar_starts=bar_starts)
        if not feat['exact_source_onset']:missing_onsets.append(row['onset_q'])
        expected=set(map(int,row.get('sounding_midi','').split()))
        observed={p for e in events if abs(e['t']-float(Fraction(row['onset_q'])))<.025 for p in e['pitches']}
        source_pitch_matches.append({'onset':row['onset_q'],'expected':sorted(expected),'observed':sorted(observed),'overlap':sorted(expected & observed)})
        human=row['human_phrase_boundary'].lower()=='yes';pred=row['predicted_phrase_boundary'].lower()=='true'
        original.append((pred,human));structural.append((feat['structural_candidate'],human))
        details.append(dict(review_onset=row['onset_q'],human=human,original=pred,**feat))
    return dict(reviewed=len(details),original=confusion(original),structural=confusion(structural),cases=details,overlong_voice_events=sorted(set(tuple(x.values()) for x in overflow)),missing_onsets=missing_onsets,source_pitch_matches=source_pitch_matches,
                limitations=['GPIF meter used for bar starts; voice durations exceeding bar are reported, not used to stretch bar','Source parser omits some ties/rests and may not match V23 event extraction',
                             'Nine selected reviews are not a held-out evaluation set',
                             'Barline-only baseline necessarily misses within-measure phrase starts'])
def main():
    p=argparse.ArgumentParser();p.add_argument('score',type=Path);p.add_argument('csv',nargs='+',type=Path);args=p.parse_args()
    r=probe(args.score,args.csv)
    print('Reviewed:',r['reviewed'],'original:',r['original'],'structural baseline:',r['structural'])
    for case in r['cases']:print(case)
    print('Overlong voice events:',r['overlong_voice_events'])
    print('Unmatched source onsets:',r['missing_onsets'])
    print('Source pitch checks:',r['source_pitch_matches'])
    print('Limitations:','; '.join(r['limitations']))
if __name__=='__main__':main()
