"""Author new GPIF occurrence tables from canonical pitched events.

For generated scores only: unsupported source techniques are rejected. Use the
occurrence writer for source editing. This writer never copies source ZIP assets.
"""
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile
from exact_score import extract_score
from musicxml_bridge import occurrence_rows


def text(parent, tag, value, **attrs):
    node=ET.SubElement(parent,tag,attrs); node.text=str(value); return node


def write_gp(score, destination, title='Composition Lab experiment'):
    root=ET.Element('GPIF')
    text(root,'GPVersion','7.0.0')
    meta=ET.SubElement(root,'Score'); text(meta,'Title',title); text(meta,'Artist','Composition Lab')
    master=ET.SubElement(root,'MasterTrack'); text(master,'Tracks',' '.join(str(i) for i in range(len(score['tracks']))))
    automations=ET.SubElement(master,'Automations'); automation=ET.SubElement(automations,'Automation')
    for tag,value in [('Type','Tempo'),('Linear','false'),('Bar',0),('Position',0),('Visible','true'),('Value','120 2')]: text(automation,tag,value)
    tables={name:ET.SubElement(root,name) for name in ['Tracks','MasterBars','Bars','Voices','Beats','Notes','Rhythms']}
    for ti,track in enumerate(score['tracks']):
        if ti>=15: raise ValueError('At most 15 pitched MIDI channels; percussion is not supported')
        if track['index'] != ti: raise ValueError('Contiguous track indices required')
        tuning=track['tunings']
        if len(tuning)!=1 or not tuning[0]: raise ValueError('Single pitched staff required')
        t=ET.SubElement(tables['Tracks'],'Track',id=str(ti)); text(t,'Name',track['name']); text(t,'ShortName',track['name'][:8])
        text(t,'Color','80 120 180'); text(t,'SystemsDefautLayout',3)
        instrument=ET.SubElement(t,'Instrument',ref='guitar-steel')
        midi=ET.SubElement(t,'GeneralMidi',table='Instrument')
        channel=ti if ti<9 else ti+1
        for tag,value in [('Program',track.get('program',25)),('Port',0),('PrimaryChannel',channel),('SecondaryChannel',channel)]: text(midi,tag,value)
        staff=ET.SubElement(ET.SubElement(t,'Staves'),'Staff')
        props=ET.SubElement(staff,'Properties'); prop=ET.SubElement(props,'Property',name='Tuning')
        text(prop,'Pitches',' '.join(map(str,tuning[0]))); text(prop,'Label','Custom'); text(prop,'LabelVisible','true')
    refs={}; counter=dict(Bars=0,Voices=0,Beats=0,Notes=0)
    def element(table,tag):
        ident=str(counter[table]); counter[table]+=1
        return ident,ET.SubElement(tables[table],tag,id=ident)
    def rhythm(d):
        d=Fraction(d)
        if d<=0: raise ValueError('Positive duration required')
        if d not in refs:
            rid=str(len(refs)); refs[d]=rid
            r=ET.SubElement(tables['Rhythms'],'Rhythm',id=rid)
            text(r,'NoteValue','Quarter')
            if d!=1: ET.SubElement(r,'PrimaryTuplet',num=str(d.denominator),den=str(d.numerator))
        return refs[d]
    count=len(score['tracks'][0]['measures'])
    if any(len(t['measures'])!=count for t in score['tracks']): raise ValueError('Unequal track lengths')
    for mi in range(count):
        mb=ET.SubElement(tables['MasterBars'],'MasterBar'); measure=score['tracks'][0]['measures'][mi]
        text(mb,'Time',measure['time_signature']); barids=[]
        if measure.get('section'): text(ET.SubElement(mb,'Section'),'Text',measure['section'])
        for ti,track in enumerate(score['tracks']):
            m=track['measures'][mi]
            if m['time_signature']!=measure['time_signature']: raise ValueError('Conflicting meters')
            bid,bar=element('Bars','Bar'); barids.append(bid); text(bar,'Clef','G2'); vids=[]
            for vi,voice in enumerate(m['voices']):
                if not voice: vids.append('-1'); continue
                vid,v=element('Voices','Voice'); vids.append(vid); beatids=[]
                offset=Fraction(0)
                for e in voice:
                    if Fraction(e['local_onset_q'])!=offset: raise ValueError('Non-contiguous voice')
                    offset+=Fraction(e['duration_q'])
                    eid,b=element('Beats','Beat'); beatids.append(eid); text(b,'Dynamic','MF')
                    ET.SubElement(b,'Rhythm',ref=rhythm(e['duration_q'])); noteids=[]
                    for note in e['notes']:
                        if note.get('technique_tags') or note.get('tie'):
                            raise ValueError('Use occurrence writer for source techniques/ties')
                        pitch,string,fret=(note[k] for k in ('midi','string','fret'))
                        if not 0<=string<len(track['tunings'][0]) or not 0<=fret<=24 or track['tunings'][0][string]+fret!=pitch:
                            raise ValueError('Unplayable note')
                        nid,n=element('Notes','Note'); noteids.append(nid); props=ET.SubElement(n,'Properties')
                        for name,child,value in [('Midi','Number',pitch),('String','String',string),('Fret','Fret',fret)]:
                            text(ET.SubElement(props,'Property',name=name),child,value)
                        for name in ['ConcertPitch','TransposedPitch']:
                            p=ET.SubElement(ET.SubElement(props,'Property',name=name),'Pitch')
                            spelling=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][pitch%12]
                            text(p,'Step',spelling[0]); text(p,'Accidental',int('#' in spelling)); text(p,'Octave',pitch//12-1)
                        text(n,'InstrumentArticulation',0)
                    if noteids: text(b,'Notes',' '.join(noteids))
                num,den=map(int,m['time_signature'].split('/'))
                if offset!=Fraction(4*num,den): raise ValueError('Voice does not fill meter')
                text(v,'Beats',' '.join(beatids))
            text(bar,'Voices',' '.join(vids))
        text(mb,'Bars',' '.join(barids))
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('VERSION','7.0'); z.writestr('Content/score.gpif',ET.tostring(root,encoding='utf-8',xml_declaration=True))
    restored=extract_score(destination)
    if occurrence_rows(score)!=occurrence_rows(restored): raise AssertionError('GP occurrence roundtrip differs')
    return restored
