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


# V2: purposeful harmonic roots, repeating motifs, and explicit power chords.
V2_TONIC_PC = 2  # D Aeolian, a deliberate composition choice, not a verified song key.
V2_PCS = {2,4,5,7,9,10,0}

def _positions(pitches, tuning):
    used=set();result=[]
    for pitch in pitches:
        options=[(abs(fret),string,fret) for string,open_pitch in enumerate(tuning)
                 for fret in [pitch-open_pitch] if 0<=fret<=14 and string not in used]
        if not options:raise ValueError('Unplayable voicing: '+str(pitches))
        _,string,fret=min(options)
        used.add(string);result.append((pitch,string,fret))
    return result

def _event(units, pitches, tuning, palm=False):
    positions=_positions(pitches,tuning) if pitches else []
    return {'units':units,'pitch':positions[0][0] if positions else None,
            'pitches':positions,'palm_muted':palm}

def _riff_bar(root, bar, tuning, variant=0):
    fifth=root+7
    # The high notes are intentionally limited to the same D natural minor pool.
    climb=[p for p in (root+12,root+15,root+17,root+19,root+22,root+24)
           if p%12 in V2_PCS and _positions([p],tuning)]
    if len(climb)<2:climb=[root+12,root+19]
    lead=climb[(bar+variant)%len(climb)]
    answer=climb[(bar+variant+1)%len(climb)]
    # 16 x 16th-note pulses, a coherent rhythm repeated through A.
    pitches=[(root,fifth),(root,),(),(root,), (lead,), (root,), (answer,), (root,fifth)]
    lengths=[2,1,1,2,2,2,2,4]
    if variant and bar==3:
        lengths=[2,1,1,2,2,2,2,2,2]
        pitches=[(root,fifth),(root,),(),(root,), (lead,), (root,), (answer,), (root,), (root,fifth)]
    return [_event(n,ps,tuning,palm=(len(ps)==1 and ps[0]==root) if ps else False)
            for n,ps in zip(lengths,pitches)]

def compose_four_bars(rng,stats,tuning,style='a'):
    if len(tuning)!=8:raise ValueError('Requires 8 strings')
    if style=='a':
        return [_riff_bar(root,i,tuning) for i,root in enumerate((26,26,34,36))]
    # B: contrasting half-time phrasing, still D Aeolian, more space and upper notes.
    roots=(31,34,36,33)  # G, Bb, C, A
    melody=((43,45),(46,48),(48,45),(45,41))
    out=[]
    for i,root in enumerate(roots):
        m,n=melody[i]
        out.append([_event(4,[root,root+7],tuning),_event(2,[m],tuning),
                    _event(2,[],tuning),_event(4,[root,root+7],tuning),
                    _event(2,[n],tuning),_event(2,[root],tuning,palm=True)])
    return out

def transform_a(phrase,rng,tuning):
    varied=copy.deepcopy(phrase)
    # Sparse, deliberate development: preserve the initial motif and overall rhythm.
    for index in (1,3):
        bar=varied[index]
        for slot in (4,6):
            old=bar[slot]['pitch']
            candidates=[v for v in (old+2,old-2,old+3,old-3,old+5,old-5)
                        if v%12 in V2_PCS and 35<=v<=54]
            if candidates:bar[slot]=_event(bar[slot]['units'],[candidates[0]],tuning)
    return varied

def transform_reprise(phrase,rng,tuning):
    reprise=copy.deepcopy(phrase)
    # A returns almost intact, but ends on the actual tonic rather than C.
    reprise[3]=_riff_bar(26,3,tuning,variant=1)
    return reprise

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
    reprise=transform_reprise(a,rng,tuning)
    phrases=[a,avar,b,reprise]
    # Make all relative musical objects from scratch.
    tr=root.find('Tracks');tr.clear()
    track.set('id','0')
    track.find('Name').text='Original 8-String Guitar'
    tr.append(track)
    root.find('./MasterTrack/Tracks').text='0'
    root.find('./Score/Title').text='Original 16-Bar Guitar Study V2'
    root.find('./Score/Artist').text='Composition Lab'
    root.find('./Score/Tabber').text='Composition V2 - intentional motifs and harmonic roots'
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
                ids=[]
                for pitch,string,fret in event['pitches']:
                    nid=4000+len(new_notes)
                    ids.append(str(nid))
                    note=ET.SubElement(notes,'Note',{'id':str(nid)})
                    properties=properties_for_note(string,fret,pitch)
                    if event.get('palm_muted'):
                        ET.SubElement(ET.SubElement(properties,'Property',{'name':'PalmMuted'}),'Enable')
                    note.append(properties)
                    ET.SubElement(note,'InstrumentArticulation').text='0'
                    new_notes.append((bar_index+1,pitch,string,fret))
                ET.SubElement(beat,'Notes').text=' '.join(ids)
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
            'sections':['A','A varied','B','A varied return'],
            'tonal_center':'D','mode':'Aeolian',
            'harmonic_roots_by_bar':['D','D','A#','C','D','D','A#','C','G','A#','C','A','D','D','A#','D'],
            'note_event_digest_sha256':hashlib.sha256(json.dumps(new_notes).encode()).hexdigest(),
            'archive_verified':True,
            'limitations':['Deterministic designed riffs, not yet a learned generative style model',
                           'Some harmonic roots are represented by power chords, without a major/minor third',
                           'No human audio playback test yet','No drum accompaniment']}

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