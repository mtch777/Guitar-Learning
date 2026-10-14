"""Recover author-supplied GP7 chord symbols and sections as *provisional* references.

Neither diagrams nor section headings are independently verified ground truth.
Never infer a chord label from a GP diagram's placeholder KeyNote field: use Item.name.
"""
import csv
import json
import zipfile
from collections import defaultdict, Counter
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET
from extract import extract_score


def score_annotations(path):
    path=Path(path)
    with zipfile.ZipFile(path) as archive:
        root=ET.fromstring(archive.read('Content/score.gpif'))
    # Diagram item IDs are reused within distinct track catalogs; scope to track.
    gp_tracks=root.findall('./Tracks/Track')
    tracks=[]
    for tr in gp_tracks:
        catalog={}
        for item in tr.findall('.//Property[@name="DiagramCollection"]/Items/Item'):
            catalog[item.get('id')]=item.get('name','').strip()
        # Some GP scores use ChordCollection, a separate item catalog.
        for item in tr.findall('.//Property[@name="ChordCollection"]/Items/Item'):
            catalog.setdefault(item.get('id'), item.get('name','').strip())
        tracks.append(catalog)
    beats={b.get('id'):b.findtext('Chord') for b in root.findall('./Beats/Beat')}
    score=extract_score(path)
    annotated=[];unmapped=[]
    for ti,track in enumerate(score['tracks']):
        catalog=tracks[ti] if ti<len(tracks) else {}
        for measure_idx,measure in enumerate(track['measures']):
            for voice_idx,voice in enumerate(measure['voices']):
                for event in voice:
                    beat_id=str(event['beat_id'])
                    ref=beats.get(beat_id)
                    if ref is None:continue
                    chord=catalog.get(str(ref))
                    if not chord:
                        unmapped.append({'track':ti,'beat_id':beat_id,'reference':ref})
                        continue
                    annotated.append({'file':path.name,'track':ti,'measure':measure_idx+1,
                        'voice':voice_idx,'onset_q':str(Fraction(event['onset_q'])),
                        'beat_id':beat_id,'chord_symbol':chord,
                        'evidence':'source_authored_diagram_label','verified':False})
    sections=[]
    for i,m in enumerate(root.findall('./MasterBars/MasterBar')):
        section=m.find('./Section/Text')
        if section is not None and (section.text or '').strip():
            sections.append({'file':path.name,'measure':i+1,'section':section.text.strip(),
                             'evidence':'source_authored_section','verified':False})
    return {'file':path.name,'chords':annotated,'sections':sections,
            'unmapped_chord_references':unmapped}


def review_cross_reference(review_csv,annotations):
    with open(review_csv,newline='',encoding='utf-8-sig') as f:cases=list(csv.DictReader(f))
    indexed=defaultdict(set)
    for data in annotations:
        for a in data['chords']:
            indexed[(a['file'],a['track'],Fraction(a['onset_q']))].add(a['chord_symbol'])
    output=[]
    for row in cases:
        names=indexed.get((row['source_file'],int(row['track_index']),Fraction(row['onset_q'])),set())
        item=dict(row)
        item['source_gp_chord_symbol']=' | '.join(sorted(names))
        item['source_gp_chord_status']='present' if len(names)==1 else 'conflicting' if names else 'not_annotated_at_attack'
        item['reference_verified']='false'
        output.append(item)
    return output


def save_csv(path,rows):
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def build(paths,review_csv,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    ann=[score_annotations(p) for p in paths]
    rows=review_cross_reference(review_csv,ann)
    save_csv(outdir/'V24_review_with_source_annotations.csv',rows)
    (outdir/'V24_source_annotations.json').write_text(json.dumps(ann,indent=2),encoding='utf-8')
    stats={'source_chord_occurrences':sum(len(a['chords']) for a in ann),
           'source_sections':sum(len(a['sections']) for a in ann),
           'review_cases':len(rows),
           'review_cases_with_source_chord':sum(x['source_gp_chord_status']=='present' for x in rows),
           'conflicting_source_labels':sum(x['source_gp_chord_status']=='conflicting' for x in rows),
           'human_verified_cases':sum(bool(x.get('human_chord_label','').strip()) for x in rows),
           'source_annotations_are_ground_truth':False,
           'by_song':[{'file':a['file'],'chords':len(a['chords']),'sections':len(a['sections']),
                       'unmapped':len(a['unmapped_chord_references'])} for a in ann]}
    (outdir/'V24_annotation_report.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    return stats

if __name__=='__main__':
    base=Path('/mnt/data')
    paths=[base/x for x in ['Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp',
             "Sweet Child O' Mine.gp",'Cloud Cascade (Tuned Down).gp',
             'Nocturne_ Lost Faith (Tuned Down).gp','Immolation of Night (Tuned Down).gp']]
    print(json.dumps(build(paths,base/'V21_Music_Validation/V21_human_review.csv',base/'V24_Source_Reference'),indent=2))