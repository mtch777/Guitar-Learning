#!/usr/bin/env python3
"""Readable MusicXML from MIDI performance, with the original MIDI retained.

Do not treat the performance's intentional ~95% key-release gate as a written
rest. Collapse near-simultaneous chord strums; represent changing harmonies as
one voice per source track, tying only notes that really continue.
"""
from collections import defaultdict, deque
from dataclasses import dataclass, replace
from fractions import Fraction as Q
from io import BytesIO
from xml.etree import ElementTree as ET
import mido

GRID=Q(1,4)
DIVISIONS=960
STRUM=Q(2,5)
RELEASE_MATCH=Q(3,5)
LENGTHS=[Q(n,4) for n in range(1,33)]
# Musical subdivisions (whole through sixteenth; avoid 32nd/64th/128th clutter)
FORMS=[
    (Q(4),'whole',0), (Q(7,2),'half',2), (Q(3),'half',1), (Q(2),'half',0),
    (Q(7,4),'quarter',2), (Q(3,2),'quarter',1),
    (Q(1),'quarter',0), (Q(3,4),'eighth',1),
    (Q(1,2),'eighth',0), (Q(1,4),'16th',0),
]
STEP_NAMES=('C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B')
KEY_FIFTHS={'C':0,'G':1,'D':2,'A':3,'E':4,'B':5,'F#':6,'C#':7,
            'F':-1,'Bb':-2,'Eb':-3,'Ab':-4,'Db':-5,'Gb':-6,'Cb':-7}
ENGINE='piano-readable-midi-v2'

@dataclass(frozen=True)
class Note:
    start:Q
    end:Q
    pitch:int
    ident:int

def text(value):
    return ''.join(c for c in str(value) if ord(c) in (9,10,13)
                   or 32<=ord(c)<=0xD7FF or 0xE000<=ord(c)<=0xFFFD
                   or 0x10000<=ord(c)<=0x10FFFF)

def snap(value):
    return round(value/GRID)*GRID

def decode(data):
    mf=mido.MidiFile(file=BytesIO(data))
    ppq=mf.ticks_per_beat
    if ppq<=0:raise ValueError('SMPTE MIDI unsupported')
    tracks=[];meters=[];keys=[];tempos=[]
    for ti,track in enumerate(mf.tracks):
        active=defaultdict(deque);tick=0;notes=[];name=''
        for message in track:
            tick+=message.time
            if message.is_meta:
                if message.type=='track_name' and not name:name=text(message.name).strip()[:100]
                if message.type=='set_tempo':tempos.append((Q(tick,ppq),ti,message.tempo))
                if message.type=='time_signature':meters.append((Q(tick,ppq),ti,(message.numerator,message.denominator)))
                if message.type=='key_signature':keys.append((Q(tick,ppq),ti,message.key))
                continue
            if message.type=='note_on' and message.velocity:
                active[(message.channel,message.note)].append(tick)
            elif message.type=='note_off' or (message.type=='note_on' and not message.velocity):
                waiting=active[(message.channel,message.note)]
                if waiting:
                    begin=waiting.popleft()
                    if tick>begin and message.channel!=9:
                        notes.append(Note(Q(begin,ppq),Q(tick,ppq),message.note,len(notes)))
        if any(active.values()):raise ValueError(f'Unterminated notes in MIDI track {ti+1}')
        if notes:tracks.append((name or f'Piano {ti+1}',sorted(notes,key=lambda n:(n.start,n.pitch))))
    if not tracks:raise ValueError('No completed pitched MIDI notes')
    def metadata(values):
        dedup={}
        for t,ti,*fields in sorted(values,key=lambda v:(v[0],v[1])):
            dedup.setdefault(t,fields[0])
        return sorted(dedup.items())
    return tracks,metadata(meters),metadata(keys),metadata(tempos)

def normalize(events):
    """Quarter/sixteenth-note placement plus note-off gate compensation."""
    clusters=[];group=[]
    for n in events:
        if (group and n.start-group[0].start<=STRUM
            and n.pitch not in {p.pitch for p in group}
            and n.end-n.start>=2 and min(p.end-p.start for p in group)>=2
            and abs(n.end-group[0].end)<=RELEASE_MATCH):
            group.append(n)
        else:
            if group:clusters.append(group)
            group=[n]
    if group:clusters.append(group)
    output=[]
    for group in clusters:
        onset=group[0].start
        if len(group)>1 and abs(onset-round(onset))<=Q(1,4):onset=Q(round(onset))
        onset=snap(onset)
        chord_duration=None
        if len(group)>1:
            # Rolled chord notes can have slightly different starts and ends.
            # The whole chord shares its notation gate; per-string rounding
            # otherwise produces spurious polyphonic voices and extra noteheads.
            shared_end=max(n.end for n in group)
            shared_length=shared_end-onset
            shared_predicted=(shared_length if
                abs(shared_length-snap(shared_length))<=Q(1,40)
                else shared_length/Q(95,100))
            chord_duration=min(LENGTHS,key=lambda d:(abs(d-shared_predicted),d))
        for n in group:
            # Isolated notes retain their own on/off timing and written gate.
            exact=n.end-n.start
            predicted=(n.end-onset) if abs(exact-snap(exact)) <= Q(1,40) else (n.end-onset)/Q(95,100)
            duration=chord_duration if chord_duration is not None else min(
                LENGTHS,key=lambda d:(abs(d-predicted),d))
            output.append(replace(n,start=onset,end=onset+duration))
    bypitch=defaultdict(list)
    for n in output:bypitch[n.pitch].append(n)
    output=[]
    for pitch,notes in bypitch.items():
        notes.sort(key=lambda n:(n.start,n.ident))
        for i,n in enumerate(notes):
            end=min(n.end,notes[i+1].start) if i+1<len(notes) else n.end
            if end<=n.start:raise ValueError(f'Note collisions after notation quantization: MIDI pitch {pitch}')
            output.append(replace(n,end=end))
    return sorted(output,key=lambda n:(n.start,n.pitch))

def add(parent,name,value=None,attributes=None):
    el=ET.SubElement(parent,name,attributes or {})
    if value is not None:el.text=str(value)
    return el

def pieces(start,end):
    while start<end:
        unit,typ,dots=next((f for f in FORMS if f[0]<=end-start),(None,None,None))
        if unit is None:raise ValueError(f'Unrepresentable written duration {end-start}')
        yield start,start+unit,typ,dots
        start+=unit

def write_note(bar,n,lo,hi,typ,dots,member=False,full_rest=False,voice=1):
    el=add(bar,'note')
    if member:add(el,'chord')
    if n is None:
        add(el,'rest',attributes={'measure':'yes'} if full_rest else {})
    else:
        step=STEP_NAMES[n.pitch%12];p=add(el,'pitch')
        add(p,'step',step[0])
        if len(step)>1:add(p,'alter',1 if step[1]=='#' else -1)
        add(p,'octave',n.pitch//12-1)
    add(el,'duration',int((hi-lo)*DIVISIONS))
    before=n is not None and n.start<lo
    after=n is not None and n.end>hi
    if before:add(el,'tie',attributes={'type':'stop'})
    if after:add(el,'tie',attributes={'type':'start'})
    add(el,'voice',voice);add(el,'type',typ)
    for _ in range(dots):add(el,'dot')
    if before or after:
        annotation=add(el,'notations')
        if before:add(annotation,'tied',attributes={'type':'stop'})
        if after:add(annotation,'tied',attributes={'type':'start'})

def allocate_voices(notes):
    """Partition overlapping note spans before engraving.

    Notes that start and finish together are one chord. Different durations
    use independent voices: another pitch changing must NEVER split a held note.
    """
    groups=defaultdict(list)
    for n in notes:
        groups[(n.start,n.end)].append(n)
    voices=[]
    voice_ends=[]
    ordered=sorted(groups.items(),key=lambda entry:
                   (entry[0][0],-entry[0][1],min(n.pitch for n in entry[1])))
    for (onset,off),members in ordered:
        available=[i for i,previous_end in enumerate(voice_ends)
                   if previous_end<=onset]
        voice=max(available,key=lambda i:voice_ends[i]) if available else len(voices)
        if voice==len(voices):
            voices.append([])
            voice_ends.append(Q(0))
        voices[voice].append((onset,off,sorted(members,key=lambda n:n.pitch)))
        voice_ends[voice]=off
    return voices


def encode(data,title=''):
    tracks,meters,keys,tempos=decode(data)
    tracks=[(name,normalize(notes)) for name,notes in tracks]
    max_end=max(n.end for _,notes in tracks for n in notes)
    if not meters or meters[0][0]>0:meters.insert(0,(Q(0),(4,4)))
    bars=[];at=Q(0)
    while at<max_end:
        meter=next((value for t,value in reversed(meters) if t<=at),(4,4))
        end=at+Q(4*meter[0],meter[1])
        if any(at<t<end for t,_ in meters):
            raise ValueError('MIDI contains an unsupported mid-measure meter change')
        bars.append((at,end,meter));at=end
    score=ET.Element('score-partwise',{'version':'4.0'})
    work=add(score,'work');add(work,'work-title',text(title or 'Untitled score'))
    add(score,'movement-title',text(title or 'Untitled score'))
    identification=add(score,'identification')
    misc=add(identification,'miscellaneous')
    add(misc,'miscellaneous-field',ENGINE,{'name':'piano-notation-engine'})
    plist=add(score,'part-list')
    for i,(name,_) in enumerate(tracks):
        part=add(plist,'score-part',attributes={'id':f'P{i+1}'})
        add(part,'part-name',text(name))
    for pi,(name,notes) in enumerate(tracks):
        part=add(score,'part',attributes={'id':f'P{pi+1}'})
        voices=allocate_voices(notes)
        prior_meter=prior_key=None
        for baridx,(start,end,meter) in enumerate(bars):
            meas=add(part,'measure',attributes={'number':str(baridx+1),'implicit':'no'})
            current_key=next((value for t,value in reversed(keys) if t<=start),'C')
            if baridx==0 or meter!=prior_meter or current_key!=prior_key:
                attrs=add(meas,'attributes')
                if baridx==0:add(attrs,'divisions',DIVISIONS)
                if baridx==0 or current_key!=prior_key:
                    key=add(attrs,'key');add(key,'fifths',KEY_FIFTHS.get(current_key,0))
                if baridx==0 or meter!=prior_meter:
                    ts=add(attrs,'time');add(ts,'beats',meter[0]);add(ts,'beat-type',meter[1])
                if baridx==0:
                    clef=add(attrs,'clef');add(clef,'sign','F');add(clef,'line',4)
                prior_meter=meter;prior_key=current_key
            if pi==0:
                for t,micros in tempos:
                    if start<=t<end:
                        direction=add(meas,'direction')
                        if t>start:add(direction,'offset',int((t-start)*DIVISIONS))
                        add(direction,'sound',attributes={'tempo':f'{60000000/micros:.5f}'})
            wrote_voice=False
            for index,events in enumerate(voices,1):
                spans=[(max(onset,start),min(off,end),members)
                       for onset,off,members in events
                       if onset<end and off>start]
                if not spans:
                    continue
                if wrote_voice:
                    backup=add(meas,'backup')
                    add(backup,'duration',int((end-start)*DIVISIONS))
                cursor=start
                for lo,hi,members in spans:
                    if lo>cursor:
                        forward=add(meas,'forward')
                        add(forward,'duration',int((lo-cursor)*DIVISIONS))
                        add(forward,'voice',index)
                    for a,b,typ,dots in pieces(lo,hi):
                        for member,n in enumerate(members):
                            write_note(meas,n,a,b,typ,dots,member=member>0,voice=index)
                    cursor=hi
                if cursor<end:
                    forward=add(meas,'forward')
                    add(forward,'duration',int((end-cursor)*DIVISIONS))
                    add(forward,'voice',index)
                wrote_voice=True
            if not wrote_voice:
                write_note(meas,None,start,end,'whole',0,full_rest=True)
    ET.indent(score,space='  ')
    return ET.tostring(score,encoding='utf-8',xml_declaration=True)
