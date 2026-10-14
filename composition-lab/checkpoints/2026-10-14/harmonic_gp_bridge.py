"""Apply explicitly supplied chord timelines to extracted GP7 events.

This module never guesses harmonic context. It adds *derived* chord-relative
notes without changing the original GP observations. A target timeline can
reharmonize the same event timing and voice layout into a separate score view.
"""
from __future__ import annotations
import argparse
import copy
import json
from fractions import Fraction
from pathlib import Path
from extract import extract_score
from harmonic_relative import Chord, analyze_note, map_note


def _chord(item):
    return Chord(int(item['root']), tuple((int(d), int(s)) for d,s in item['degrees']))


def _timeline(entries):
    spans=[]
    for entry in entries:
        start,end=Fraction(entry['start']),Fraction(entry['end'])
        if start>=end: raise ValueError('Invalid chord span')
        spans.append((start,end,_chord(entry)))
    for a,b in zip(sorted(spans),sorted(spans)[1:]):
        if b[0]<a[1]:raise ValueError('Overlapping chord spans')
    return spans


def _at(spans, onset):
    found=[ch for start,end,ch in spans if start<=onset<end]
    return found[0] if found else None


def _relative_record(note, chord):
    if note['midi'] is None:
        return None
    rel=analyze_note(note['midi'],chord)
    return {'degree':rel.degree,'octave_displacement':rel.octave_displacement,
            'chromatic_interval':rel.interval_from_root if rel.degree is None else None}


def annotate_score(score, source_harmony, *, track_indices=None):
    """Add chord-relative role to notes without replacing original note data.

    source_harmony maps original track index (str or int) to chord spans.
    Missing source harmony leaves every note explicitly unclassified.
    """
    spans={int(k):_timeline(v) for k,v in source_harmony.items()}
    selected=set(spans) if track_indices is None else set(track_indices)
    output=copy.deepcopy(score)
    count={'pitched':0,'classified':0,'chord_tones':0,'unclassified':0}
    for track in output['tracks']:
        if track['index'] not in selected:continue
        timeline=spans.get(track['index'],[])
        for measure in track['measures']:
            for voice in measure['voices']:
                for event in voice:
                    chord=_at(timeline,Fraction(event['onset_q']))
                    for note in event['notes']:
                        if note['midi'] is None:continue
                        count['pitched']+=1
                        note['harmonic_relation']=_relative_record(note,chord) if chord else None
                        if chord:
                            count['classified']+=1
                            if note['harmonic_relation']['degree'] is not None:count['chord_tones']+=1
                        else:count['unclassified']+=1
    output['harmonic_annotation_summary']=count
    return output


def reharmonize_score(annotated, source_harmony, target_harmony, *, missing='preserve_interval'):
    """Return transformed view; never mutate the original note's original_midi.

    Both timelines explicitly supplied; no guessed chord quality or key.
    Notes without source harmony remain unchanged. A source chord with no target
    chord raises rather than silently inventing pitches.
    """
    sources={int(k):_timeline(v) for k,v in source_harmony.items()}
    targets={int(k):_timeline(v) for k,v in target_harmony.items()}
    output=copy.deepcopy(annotated)
    changed=0
    for track in output['tracks']:
        ti=track['index']
        if ti not in sources:continue
        for measure in track['measures']:
            for voice in measure['voices']:
                for event in voice:
                    at=Fraction(event['onset_q'])
                    source=_at(sources[ti],at)
                    if source is None:continue
                    target=_at(targets.get(ti,[]),at)
                    if target is None:raise ValueError(f'Missing target harmony for track {ti} at {at}')
                    for note in event['notes']:
                        if note['midi'] is None:continue
                        before=note['midi']
                        note['original_midi']=before
                        after=map_note(analyze_note(before,source),target,missing=missing)
                        note['midi']=after
                        if after != before:
                            changed+=1
                            # Existing guitar positions are no longer valid; do not lie.
                            note['string']=None
                            note['fret']=None
    output['reharmonization_summary']={'notes_changed':changed, 'output':'symbolic events; requires fingering and GP serialization'}
    return output


def main():
    p=argparse.ArgumentParser(description='GP-to-chord-relative annotation and symbolic reharmonization')
    p.add_argument('source_gp',type=Path)
    p.add_argument('--source-harmony',type=Path,required=True,help='JSON map track index to chord spans')
    p.add_argument('--target-harmony',type=Path,help='Optional JSON for symbolic reharmonization')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    src=json.loads(args.source_harmony.read_text())
    annotated=annotate_score(extract_score(args.source_gp),src)
    result=reharmonize_score(annotated,src,json.loads(args.target_harmony.read_text())) if args.target_harmony else annotated
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result.get('reharmonization_summary',result['harmonic_annotation_summary']),indent=2))

if __name__=='__main__':main()