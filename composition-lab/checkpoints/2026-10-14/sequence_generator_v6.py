"""Step 6: direct, arrangement-neutral Guitar Pro writer for learned event sequences.

The sequence model currently learns from quantized 4/4 material. Output bar
count, quarter-note meter, selected GP instrument, and fret limits are explicit
configuration, not learned stylistic assumptions. No section/riff/genre rules.
"""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import zipfile
from xml.etree import ElementTree as ET
from sequence_model import SequenceModel

RHYTHMS={1:'16th',2:'Eighth',4:'Quarter',8:'Half',16:'Whole'}


def playable_positions(anchor,shape,tuning,max_fret=14):
    """Find octave-equivalent fret/string allocation preserving chord intervals."""
    for shift in sorted(range(-7,8),key=lambda k:(abs(k),k)):
        pitches=[anchor+12*shift+offset for offset in shape]
        if len(set(pitches))!=len(pitches):continue
        used=set();placed=[]
        for pitch in pitches:
            choices=sorted((fret,string) for string,open_pitch in enumerate(tuning)
                           if string not in used for fret in (pitch-open_pitch,)
                           if 0<=fret<=max_fret)
            if not choices:break
            fret,string=choices[0];used.add(string);placed.append((pitch,string,fret))
        if len(placed)==len(pitches):return placed
    return None


def generate(model,tuning,bars=16,meter='4/4',seed=17,max_fret=14):
    """Sample events; no musical transformation after sampling (octave fit only)."""
    numerator,denominator=map(int,meter.split('/'))
    if denominator!=4 or numerator<1:raise ValueError('Step 6 supports positive N/4 meters')
    if bars<1 or not tuning:raise ValueError('Require positive bars and pitched tuning')
    if not model.pitch_starts:raise ValueError('No source initial pitches')
    target=numerator*4
    rng=random.Random(seed)
    anchor=rng.choices(list(model.pitch_starts),weights=list(model.pitch_starts.values()),k=1)[0]
    history=[];result=[];orders=Counter();rests=0
    for _ in range(bars):
        remaining=target;measure=[]
        while remaining:
            valid_options=[];used_order=None
            for order in range(min(len(history),model.max_order),-1,-1):
                context=tuple(history[-order:]) if order else ()
                counts=model.next_counts[order].get(context,{})
                options=[]
                for token,count in counts.items():
                    units,delta,shape=token
                    if units>remaining:continue
                    if shape:
                        # An initial-position marker is not a musical pitch interval.
                        if delta is None and history:continue
                        placed=playable_positions(anchor+(delta or 0),shape,tuning,max_fret)
                        if placed is None:continue
                    else:placed=[]
                    options.append((token,count,placed))
                if options:
                    valid_options=options;used_order=order;break
            if not valid_options:
                # Silence fills only unrepresentable timing gaps; never synthesizes pitches.
                unit=max(v for v in RHYTHMS if v<=remaining)
                measure.append({'units':unit,'positions':[]})
                remaining-=unit;rests+=1;history=[]
                continue
            token,count,placed=rng.choices(valid_options,weights=[n for _,n,_ in valid_options],k=1)[0]
            unit,delta,shape=token
            measure.append({'units':unit,'positions':placed})
            if placed:anchor=placed[0][0]
            else:rests+=1
            history.append(token)
            if model.max_order:history=history[-model.max_order:]
            else:history=[]
            remaining-=unit;orders[used_order]+=1
        result.append(measure)
    return result,{'context_uses':dict(orders),'rest_events':rests,'meter':meter,'bars':bars}


def _pitch_node(number):
    steps=('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
    spelling=steps[number%12]
    pitch=ET.Element('Pitch')
    ET.SubElement(pitch,'Step').text=spelling[0]
    if len(spelling)>1:ET.SubElement(pitch,'Accidental').text='1'
    else:ET.SubElement(pitch,'Accidental')
    ET.SubElement(pitch,'Octave').text=str(number//12-1)
    return pitch


def _note_properties(pitch,string,fret):
    props=ET.Element('Properties')
    for name in ('ConcertPitch','TransposedPitch'):
        node=ET.SubElement(props,'Property',{'name':name});node.append(_pitch_node(pitch))
    ET.SubElement(ET.SubElement(props,'Property',{'name':'String'}),'String').text=str(string)
    ET.SubElement(ET.SubElement(props,'Property',{'name':'Fret'}),'Fret').text=str(fret)
    ET.SubElement(ET.SubElement(props,'Property',{'name':'Midi'}),'Number').text=str(pitch)
    return props


def export_score(template,output,measures,meter='4/4',track_index=0,title='Sequence Composition'):
    """Serialize arbitrary measures directly, not via V2's prescribed arrangement."""
    template=Path(template);output=Path(output)
    if template.resolve()==output.resolve():raise ValueError('Output must differ from template')
    with zipfile.ZipFile(template) as source:
        members=[(info.filename,source.read(info.filename)) for info in source.infolist() if not info.is_dir()]
        root=ET.fromstring(source.read('Content/score.gpif'))
    tracks=root.findall('./Tracks/Track')
    if not (0<=track_index<len(tracks)):raise ValueError('Invalid template track index')
    chosen=tracks[track_index]
    pitches_text=chosen.findtext("./Staves/Staff/Properties/Property[@name='Tuning']/Pitches")
    if not pitches_text:raise ValueError('Selected track has no pitched tuning')
    tuning=[int(x) for x in pitches_text.split()]
    numerator,denominator=map(int,meter.split('/'))
    target=Fraction(16*numerator,denominator)
    if any(sum(e['units'] for e in bar)!=target for bar in measures):raise ValueError('Incorrect measure duration')
    for bar in measures:
        for ev in bar:
            if Fraction(ev['units'])<=0:raise ValueError('Non-positive event duration')
            for pitch,string,fret in ev['positions']:
                if not 0<=string<len(tuning) or tuning[string]+fret!=pitch:raise ValueError('Invalid guitar position')
    root.find('Tracks').clear()
    chosen.set('id','0')
    root.find('Tracks').append(chosen)
    master_tracks=root.find('./MasterTrack/Tracks')
    if master_tracks is not None:master_tracks.text='0'
    score_title=root.find('./Score/Title')
    if score_title is not None:score_title.text=title
    for table in ('MasterBars','Bars','Voices','Beats','Notes','Rhythms'):
        root.find(table).clear()
    rhythms=root.find('Rhythms');refs={}
    from music_events import VALUES, duration as parse_duration
    # Prefer conventional notations and source-compatible tuplet ratios.
    def rhythm_for(units):
        units=Fraction(units)
        if units in refs:return refs[units]
        wanted=units/Fraction(4)
        choices=[]
        for value,base in VALUES.items():
            for dots in range(4):
                dotted=Fraction(base)*sum((Fraction(1,2**i) for i in range(dots+1)),Fraction())
                ratio=wanted/dotted
                if ratio==1:
                    choices.append((0,dots,0,value,dots,None))
                elif ratio>0 and ratio.numerator<=64 and ratio.denominator<=64:
                    # Tuplet num/den = denominator/numerator of duration multiplier.
                    choices.append((2,dots,ratio.denominator+ratio.numerator,value,dots,ratio))
        if not choices:raise ValueError(f'Cannot encode exact rhythmic duration {wanted}')
        _,_,_,value,dots,ratio=min(choices)
        rid=str(len(refs));node=ET.SubElement(rhythms,'Rhythm',{'id':rid})
        ET.SubElement(node,'NoteValue').text=value
        if dots:ET.SubElement(node,'AugmentationDot',{'count':str(dots)})
        if ratio is not None:ET.SubElement(node,'PrimaryTuplet',{'num':str(ratio.denominator),'den':str(ratio.numerator)})
        if parse_duration(node)!=wanted:raise AssertionError('Rhythm encoding failed exact roundtrip')
        refs[units]=rid
        return rid
    total_notes=0;events=0
    for bi,bar_events in enumerate(measures):
        master=ET.SubElement(root.find('MasterBars'),'MasterBar')
        ET.SubElement(master,'Time').text=meter
        ET.SubElement(master,'Bars').text=str(1000+bi)
        bar=ET.SubElement(root.find('Bars'),'Bar',{'id':str(1000+bi)})
        ET.SubElement(bar,'Voices').text=str(2000+bi)
        ET.SubElement(bar,'Clef').text='G2'
        voice=ET.SubElement(root.find('Voices'),'Voice',{'id':str(2000+bi)})
        beat_ids=[]
        for ei,event in enumerate(bar_events):
            beat_id=str(3000+events);events+=1;beat_ids.append(beat_id)
            beat=ET.SubElement(root.find('Beats'),'Beat',{'id':beat_id})
            ET.SubElement(beat,'Dynamic').text='F'
            ET.SubElement(beat,'Rhythm',{'ref':rhythm_for(event['units'])})
            ET.SubElement(beat,'ConcertPitchStemOrientation').text='Undefined'
            note_ids=[]
            for pitch,string,fret in event['positions']:
                nid=str(4000+total_notes);total_notes+=1;note_ids.append(nid)
                note=ET.SubElement(root.find('Notes'),'Note',{'id':nid})
                note.append(_note_properties(pitch,string,fret))
                ET.SubElement(note,'InstrumentArticulation').text='0'
            if note_ids:ET.SubElement(beat,'Notes').text=' '.join(note_ids)
            ET.SubElement(beat,'Properties');ET.SubElement(beat,'XProperties')
        ET.SubElement(voice,'Beats').text=' '.join(beat_ids)
    output.parent.mkdir(parents=True,exist_ok=True)
    xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as target_archive:
        for filename,data in members:
            target_archive.writestr(filename,xml if filename=='Content/score.gpif' else data)
    with zipfile.ZipFile(output) as check_file:
        check=ET.fromstring(check_file.read('Content/score.gpif'))
    if len(check.findall('./MasterBars/MasterBar'))!=len(measures):raise AssertionError('Bar count mismatch')
    if len(check.findall('./Notes/Note'))!=total_notes:raise AssertionError('Note count mismatch')
    check_rhythms={r.get('id'):r for r in check.findall('./Rhythms/Rhythm')}
    for voice in check.findall('./Voices/Voice'):
        beat_table={b.get('id'):b for b in check.findall('./Beats/Beat')}
        total=sum((parse_duration(check_rhythms[beat_table[bid].find('Rhythm').get('ref')]) for bid in (voice.findtext('Beats') or '').split()),Fraction())
        if total!=target/Fraction(4):raise AssertionError('GPIF roundtrip beat durations do not fill bar')
    return {'file':str(output),'measures':len(measures),'meter':meter,'track_name':chosen.findtext('Name'),
            'strings':len(tuning),'notes':total_notes,'events':events,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}


def compose(template,output,sources,bars=16,meter='4/4',track_index=0,seed=17,order=4,max_fret=14):
    with zipfile.ZipFile(template) as z:root=ET.fromstring(z.read('Content/score.gpif'))
    tracks=root.findall('./Tracks/Track')
    if not 0<=track_index<len(tracks):raise ValueError('Invalid track index')
    pitches=tracks[track_index].findtext("./Staves/Staff/Properties/Property[@name='Tuning']/Pitches")
    if not pitches:raise ValueError('Selected output track has no tuning')
    tuning=[int(x) for x in pitches.split()]
    model=SequenceModel.from_paths(sources,max_order=order)
    generated,diagnostics=generate(model,tuning,bars,meter,seed,max_fret)
    result=export_score(template,output,generated,meter,track_index,'Composition V6 — Learned Events')
    result.update(diagnostics)
    result.update({'training_events':model.event_count,'training_sequences':model.sequence_count,'seed':seed,'order':order,
                   'limitations':['training only quantized 4/4 pitched sources',
                                  'output meter configurable N/4 but event model not conditioned on meter',
                                  'single track and voice; no source articulation modeling yet',
                                  'phrase structure not yet learned']})
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--sources',type=Path,nargs='+',required=True)
    p.add_argument('--template',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bars',type=int,default=16)
    p.add_argument('--meter',default='4/4')
    p.add_argument('--track-index',type=int,default=0)
    p.add_argument('--seed',type=int,default=17)
    p.add_argument('--order',type=int,default=4)
    p.add_argument('--max-fret',type=int,default=14)
    args=p.parse_args()
    report=compose(args.template,args.output,args.sources,args.bars,args.meter,args.track_index,args.seed,args.order,args.max_fret)
    Path(str(args.output)+'.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()