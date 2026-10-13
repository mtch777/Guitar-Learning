"""Create an original, editable GP7 16-bar guitar sketch from a symbolic corpus.

Only a compatibility shell (track properties, layout, archive metadata) is reused;
all musical bars, beats, voices, and notes are authored afresh.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, random, zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from phrase_development import parse

RHYTHM_BEATS = {1:'16th', 2:'Eighth', 4:'Quarter', 8:'Half', 16:'Whole'}
NOTES = 'C C# D D# E F F# G G# A A# B'.split()

def pitch_node(number):
    name=NOTES[number%12]
    node=ET.Element('Pitch')
    ET.SubElement(node,'Step').text=name[0]
    accidental=ET.SubElement(node,'Accidental')
    if len(name)>1:accidental.text='1'
    ET.SubElement(node,'Octave').text=str(number//12-1)
    return node

def properties_for_note(string,fret,midi):
    properties=ET.Element('Properties')
    for tag in ('ConcertPitch','TransposedPitch'):
        p=ET.SubElement(properties,'Property',{'name':tag})
        p.append(pitch_node(midi))
    ET.SubElement(ET.SubElement(properties,'Property',{'name':'String'}),'String').text=str(string)
    ET.SubElement(ET.SubElement(properties,'Property',{'name':'Fret'}),'Fret').text=str(fret)
    ET.SubElement(ET.SubElement(properties,'Property',{'name':'Midi'}),'Number').text=str(midi)
    return properties

def training_stats(paths):
    rhythm=Counter();pitches=Counter();interval=Counter()
    seen=set()
    for path in paths:
        song=parse(path)
        for track in song['tracks']:
            if not any(t in track['name'].lower() for t in ('rhythm','distortion','guitar')):continue
            fingerprint=tuple(tuple(m) for m in track['measures'])
            if fingerprint in seen:continue
            seen.add(fingerprint)
            last=None
            for measure in track['measures']:
                voice=[e for e in measure if e[0]==0 and e[3]]
                for _,onset,duration,notes in voice:
                    units=round(duration*4)
                    if units in RHYTHM_BEATS:rhythm[units]+=1
                    pitch=notes[0];pitches[pitch%12]+=1
                    if last is not None and abs(pitch-last)<=12:interval[pitch-last]+=1
                    last=pitch
    if not pitches or not rhythm:raise ValueError('Could not extract rhythm/pitch data')
    return {'rhythm_units':rhythm,'pitch_classes':pitches,'intervals':interval}

def weighted(rng,counter):
    return rng.choices(list(counter),weights=list(counter.values()),k=1)[0]

def nearest_fret(pitch,tuning,max_fret=17):
    candidates=[(abs(fret),string,fret) for string,open_pitch in enumerate(tuning)
                for fret in [pitch-open_pitch] if 0<=fret<=max_fret]
    if not candidates:return None
    _,string,fret=min(candidates)
    return string,fret

def choose_pitch(rng,prev,stats,tuning):
    valid=[]
    for shift,n in stats['intervals'].items():
        target=prev+shift
        if 28<=target<=72 and nearest_fret(target,tuning) is not None:
            valid.append((target,n))
    if valid and rng.random()<.75:
        return rng.choices([v[0] for v in valid],weights=[v[1] for v in valid],k=1)[0]
    pcs=stats['pitch_classes']
    candidates=[p for p in range(30,69) if p%12 in pcs and nearest_fret(p,tuning) is not None]
    weights=[pcs[p%12]/(1+abs(p-prev)*.25) for p in candidates]
    return rng.choices(candidates,weights=weights,k=1)[0]

def compose_four_bars(rng,stats,tuning,style='a'):
    phrase=[]
    pitch=round(tuning[0]+12 if style=='a' else tuning[0]+19)
    # Select a distinct base pitch class favored by the training songs.
    for _ in range(12):
        p=choose_pitch(rng,pitch,stats,tuning)
        if p!=pitch: pitch=p;break
    for bar in range(4):
        remaining=16;notes=[]
        while remaining>0:
            rhythm={unit:count for unit,count in stats['rhythm_units'].items() if unit<=remaining and unit<=4}
            if not rhythm:rhythm={1:1}
            dur=weighted(rng,rhythm)
            # Mark chosen time spans as rests for rhythmic articulation.
            play=rng.random() < (.83 if style=='a' else .7)
            if play:
                pitch=choose_pitch(rng,pitch,stats,tuning)
                position=nearest_fret(pitch,tuning)
                if position is None:raise AssertionError('Unplayable chosen pitch')
                string,fret=position
                notes.append({'units':dur,'pitch':pitch,'string':string,'fret':fret})
            else: notes.append({'units':dur,'pitch':None})
            remaining-=dur
        phrase.append(notes)
    return phrase

def transform_a(phrase,rng,tuning):
    result=copy.deepcopy(phrase)
    populated=[(b,n) for b,bar in enumerate(result) for n,beat in enumerate(bar) if beat['pitch'] is not None]
    for b,n in rng.sample(populated,min(5,len(populated))):
        beat=result[b][n]
        for delta in rng.sample([-2,-1,1,2,3,-3],6):
            pitch=beat['pitch']+delta
            pos=nearest_fret(pitch,tuning)
            if pos is not None:
                beat.update({'pitch':pitch,'string':pos[0],'fret':pos[1]});break
    return result

def render_gp(template,output,source_paths,seed=17):
    stats=training_stats(source_paths)
    rng=random.Random(seed)
    with zipfile.ZipFile(template) as archive:
        members=[(i.filename,archive.read(i.filename)) for i in archive.infolist() if not i.is_dir()]
        root=ET.fromstring(archive.read('Content/score.gpif'))
    track=next(t for t in root.findall('./Tracks/Track')
               if 'rhythm' in (t.findtext('Name') or '').lower())
    tuning_text=track.findtext("./Staves/Staff/Properties/Property[@name='Tuning']/Pitches")
    tuning=[int(n) for n in tuning_text.split()]
    if len(tuning)!=8:raise ValueError('Template selected track must be 8-string')
    a=compose_four_bars(rng,stats,tuning,'a')
    avar=transform_a(a,rng,tuning)
    b=compose_four_bars(rng,stats,tuning,'b')
    reprise=copy.deepcopy(a)
    phrases=[a,avar,b,reprise]
    # Make all relative musical objects from scratch.
    tr=root.find('Tracks');tr.clear()
    track.set('id','0')
    track.find('Name').text='Original 8-String Guitar'
    tr.append(track)
    root.find('./MasterTrack/Tracks').text='0'
    root.find('./Score/Title').text='Original 16-Bar Guitar Study'
    root.find('./Score/Artist').text='Composition Lab'
    root.find('./Score/Tabber').text='Generated using phrase and interval statistics'
    masters=root.find('MasterBars');masters.clear()
    bars=root.find('Bars');bars.clear()
    voices=root.find('Voices');voices.clear()
    beats=root.find('Beats');beats.clear()
    notes=root.find('Notes');notes.clear()
    rhythms=root.find('Rhythms');rhythms.clear()
    lookup={}
    for i,(units,name) in enumerate(RHYTHM_BEATS.items()):
        rhythm=ET.SubElement(rhythms,'Rhythm',{'id':str(i)})
        ET.SubElement(rhythm,'NoteValue').text=name
        lookup[units]=str(i)
    new_notes=[]
    for bar_index,measure in enumerate([measure for phrase in phrases for measure in phrase]):
        master=ET.SubElement(masters,'MasterBar')
        ET.SubElement(master,'Time').text='4/4'
        ET.SubElement(master,'Bars').text=str(1000+bar_index)
        if bar_index in (0,4,8,12):
            section=ET.SubElement(master,'Section')
            label=['A — introduce','A — variation','B — contrast','A — return'][bar_index//4]
            ET.SubElement(section,'Letter').text=label[0]
            ET.SubElement(section,'Text').text=label
        bar=ET.SubElement(bars,'Bar',{'id':str(1000+bar_index)})
        ET.SubElement(bar,'Voices').text=str(2000+bar_index)
        ET.SubElement(bar,'Clef').text='G2'
        voice=ET.SubElement(voices,'Voice',{'id':str(2000+bar_index)})
        beat_refs=[]
        for event in measure:
            beat_id=3000+len(beat_refs)+bar_index*100
            beat_refs.append(str(beat_id))
            beat=ET.SubElement(beats,'Beat',{'id':str(beat_id)})
            ET.SubElement(beat,'Dynamic').text='F'
            ET.SubElement(beat,'Rhythm',{'ref':lookup[event['units']]})
            ET.SubElement(beat,'ConcertPitchStemOrientation').text='Undefined'
            if event['pitch'] is not None:
                nid=4000+len(new_notes)
                ET.SubElement(beat,'Notes').text=str(nid)
                note=ET.SubElement(notes,'Note',{'id':str(nid)})
                note.append(properties_for_note(event['string'],event['fret'],event['pitch']))
                ET.SubElement(note,'InstrumentArticulation').text='0'
                new_notes.append((bar_index+1,event['pitch'],event['string'],event['fret']))
            ET.SubElement(beat,'Properties')
            ET.SubElement(beat,'XProperties')
        ET.SubElement(voice,'Beats').text=' '.join(beat_refs)
    xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as target:
        for name,data in members:
            target.writestr(name,xml if name=='Content/score.gpif' else data)
    with zipfile.ZipFile(output) as verify:
        check=ET.fromstring(verify.read('Content/score.gpif'))
    assert len(check.findall('./MasterBars/MasterBar'))==16
    assert len(check.findall('./Tracks/Track'))==1
    assert len(check.findall('./Notes/Note'))==len(new_notes)
    assert len(set(n.get('id') for n in check.findall('./Notes/Note')))==len(new_notes)
    return {'output':str(output),'seed':seed,'measures':16,'guitar_tracks':1,
            'notes':len(new_notes),'tuning_low_to_high_midi':tuning,
            'sections':['A','A varied','B','A return'],
            'note_event_digest_sha256':hashlib.sha256(json.dumps(new_notes).encode()).hexdigest(),
            'archive_verified':True,
            'limitations':['Synthesis uses corpus rhythmic/pitch/interval distributions, not learned long-range melodic grammar',
                           'A/B/reprise structure is partly designed; guitar playability checks only pitch fret range',
                           'No human audio playback test yet','No simultaneous chords or drum accompaniment']}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--template',type=Path,required=True)
    ap.add_argument('--sources',type=Path,nargs='+',required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--seed',type=int,default=17)
    args=ap.parse_args()
    report=render_gp(args.template,args.output,args.sources,args.seed)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()