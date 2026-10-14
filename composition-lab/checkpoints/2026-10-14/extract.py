"""Extract complete supported GP7 events, without genre labels or pitch-role inference.

Maintains legacy track->measure->voice->beat->notes output and adds absolute
quarter-beat onset/duration, source IDs, ties, beat/technique properties.
"""
from __future__ import annotations
import argparse
import json
import zipfile
from collections import Counter
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET
from music_events import duration, frac, meter_length, validate_events


def _ids(element, tag):
    return (element.findtext(tag) or '').split()


def _property(note,key,child):
    return note.findtext(f"./Properties/Property[@name='{key}']/{child}")


def _numeric(text):
    try:return int(text) if text is not None else None
    except (ValueError,TypeError):return None


def _pitch_number(note):
    midi=_numeric(_property(note,'Midi','Number'))
    if midi is not None:return midi
    node=note.find("./Properties/Property[@name='ConcertPitch']/Pitch")
    if node is None:return None
    step=node.findtext('Step'); octave=_numeric(node.findtext('Octave'))
    if step is None or step not in 'CDEFGAB':return None
    if octave is None:return None
    accident=_numeric(node.findtext('Accidental')) or 0
    return 12*(octave+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]+accident


def extract_score(path: str | Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        root=ET.fromstring(archive.read('Content/score.gpif'))
    def idx(a,b):return {n.get('id'):n for n in root.findall(f'./{a}/{b}')}
    bars,voices,beats,notes,rhythms=[idx(a,b) for a,b in
        [('Bars','Bar'),('Voices','Voice'),('Beats','Beat'),('Notes','Note'),('Rhythms','Rhythm')]]
    tracks=root.findall('./Tracks/Track')
    masters=root.findall('./MasterBars/MasterBar')
    output={'source_file':Path(path).name,'measure_count':len(masters),'tracks':[],
            'format':'gp7-quarter-beat-rational-v1'}
    song_start=Fraction(0)
    for mi,master in enumerate(masters):
        meter=master.findtext('Time')
        start=song_start
        song_start+=meter_length(meter)
        for ti,track in enumerate(tracks):
            if mi==0:
                tunings=[]
                for staff in track.findall('./Staves/Staff'):
                    pitches=staff.findtext("./Properties/Property[@name='Tuning']/Pitches")
                    tunings.append([int(x) for x in pitches.split()] if pitches else [])
                output['tracks'].append({'index':ti,'name':track.findtext('Name'),
                                         'tunings':tunings,'measures':[]})
            barids=_ids(master,'Bars')
            if ti>=len(barids):raise ValueError(f'Missing bar for track {ti} measure {mi+1}')
            bar=bars[barids[ti]]
            m={'number':mi+1,'time_signature':meter,'section':master.findtext('./Section/Text'),
               'onset_q':frac(start),'bar_id':barids[ti],'voices':[]}
            for vi,voice_id in enumerate(_ids(bar,'Voices')):
                if voice_id=='-1':continue
                voice=voices[voice_id];events=[];offset=Fraction(0)
                for beat_id in _ids(voice,'Beats'):
                    beat=beats[beat_id]
                    ref=beat.find('Rhythm')
                    rhythm=rhythms.get(ref.get('ref')) if ref is not None else None
                    dur=duration(rhythm)
                    note_ids=_ids(beat,'Notes')
                    ev={'beat_id':beat_id,'voice_index':vi,'onset_q':frac(start+offset),
                        'local_onset_q':frac(offset),'duration_q':frac(dur),
                        'rhythm':rhythm.findtext('NoteValue'),
                        'dots':rhythm.find('AugmentationDot').get('count','1') if rhythm.find('AugmentationDot') is not None else None,
                        'tuplet':ET.tostring(rhythm.find('PrimaryTuplet'),encoding='unicode') if rhythm.find('PrimaryTuplet') is not None else None,
                        'rest':not bool(note_ids),'beat_tags':[x.tag for x in beat if x.tag not in ('Notes','Rhythm')],
                        'beat_property_names':[x.get('name') for x in beat.findall('./Properties/Property')],
                        'notes':[]}
                    for nid in note_ids:
                        note=notes[nid];props=note.find('Properties')
                        ev['notes'].append({'note_id':nid,'string':_numeric(_property(note,'String','String')),
                            'fret':_numeric(_property(note,'Fret','Fret')),'midi':_pitch_number(note),
                            'onset_q':ev['onset_q'],'duration_q':ev['duration_q'],
                            'tie':dict(note.find('Tie').attrib) if note.find('Tie') is not None else None,
                            'technique_tags':[x.tag for x in note if x.tag!='Properties'],
                            'property_names':[x.get('name') for x in props] if props is not None else [],
                            'articulation':note.findtext('InstrumentArticulation')})
                    events.append(ev);offset+=dur
                m['voices'].append(events)
            output['tracks'][ti]['measures'].append(m)
    output['duration_q']=frac(song_start)
    return output


def summarize(score):
    result=[]
    for t in score['tracks']:
        events=[e for m in t['measures'] for v in m['voices'] for e in v]
        notes=[n for e in events for n in e['notes']]
        result.append({'name':t['name'],'tunings':t['tunings'],'beats':len(events),
            'notes':len(notes),'rests':sum(e['rest'] for e in events),
            'fretted_notes':sum(n['fret'] is not None for n in notes),
            'rhythms':dict(Counter(e['rhythm'] for e in events))})
    return {'source_file':score['source_file'],'measures':score['measure_count'],
        'duration_q':score['duration_q'],'tracks':result,
        'voice_meter_discrepancies':len(validate_events(score))}


def main():
    p=argparse.ArgumentParser();p.add_argument('files',nargs='+',type=Path)
    p.add_argument('--export-json',type=Path)
    args=p.parse_args()
    if args.export_json and len(args.files)!=1:p.error('--export-json requires one file')
    scores=[extract_score(x) for x in args.files]
    if args.export_json:
        args.export_json.parent.mkdir(parents=True,exist_ok=True)
        args.export_json.write_text(json.dumps(scores[0],indent=2),encoding='utf-8')
    print(json.dumps([summarize(s) for s in scores],indent=2))

if __name__=='__main__':main()