"""Conservative chord-relative reharmonization of a GP7 guitar track.

Uses the existing shared chord analyzer vocabulary (not a second triad detector).
No tonic, genre, or unobserved chord is presumed. Missing/ambiguous harmonic
context remains unchanged. A change_rate is probability of choosing a different
observed chord at each anchored span, not a calibrated similarity percentage.
"""
from __future__ import annotations
import argparse, copy, json, random, zipfile
from collections import Counter
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET
from extract import extract_score
from harmonic_relative import Chord, analyze_note, map_note
from harmonic_inference import CHORDS, chords_for
from harmonic_continuity import expand_agreed_anchors, at_time
from contextual_harmony import supplement_anchors

# Degree labels track functional thirds/sevenths. Every pitch interval is
# preserved independently; unrecognized sonorities are left untouched.
# Chord-tone identities depend on the written interval, not pitch-class alone.
# e.g. 2 and 9 are distinct roles; #9 is not mislabeled a minor third.
DEGREES = {
    0: 1, 1: 2, 2: 2, 3: 3, 4: 3, 5: 4, 6: 5, 7: 5,
    8: 5, 9: 6, 10: 7, 11: 7,
    13: 9, 14: 9, 15: 9,
    17: 11, 18: 11,
    20: 13, 21: 13,
}

def _named_degrees(intervals):
    """Keep unique chord-tone roles; reject qualities requiring duplicate roles."""
    degrees=tuple((DEGREES.get(offset),offset) for offset in intervals)
    return degrees if all(d is not None for d,_ in degrees) and len({d for d,_ in degrees})==len(degrees) else None

def candidate_chords(pitches):
    """Use existing analyzer; accept only uniquely fully evidenced chord sets.

    Weak/partial matches are useful for reporting possibilities but unsafe for
    destructive reharmonization, so they are *not* silently promoted to fact.
    """
    pcs={p%12 for p in pitches}
    if len(pcs)<2:return []
    # Shared analyzer produces candidate scores; retain exact, complete
    # pitch-class matches only. Request ALL candidates, not the top five.
    ranked=chords_for(pcs,limit=12*len(CHORDS))
    exact=[]
    for item in ranked:
        offsets=CHORDS[item['quality']]
        if {(item['root']+i)%12 for i in offsets} != pcs:continue
        degrees=_named_degrees(offsets)
        if degrees is None:continue
        root_pc=item['root']
        root=min((p for p in pitches if p%12==root_pc),default=None)
        if root is None:
            # Inversions and rootless octave voicings may not contain root:
            # use a root near the lowest source pitch, preserving pitch range.
            lowest=min(pitches)
            root=min((root_pc+12*k for k in range(-2,12)),
                     key=lambda p:(abs(p-lowest),p))
        exact.append((item['quality'],Chord(root,degrees)))
    if len(exact)>1:
        # A sounded bass root can disambiguate some sus inversions, but do not
        # assume the lowest note is always the root if multiple candidates fit.
        bass_pc=min(pitches)%12
        rooted=[c for c in exact if c[1].root%12==bass_pc]
        exact=rooted if len(rooted)==1 else []
    return exact if len(exact)==1 else []

def infer_harmony(score,track_index):
    """Extract exact supported chord sonorities, anchored to their actual durations.

    A chord anchor covers only the observed sounding beat, never inferred
    through unexplained gaps or overlapping ambiguous observations.
    """
    track=score['tracks'][track_index]
    spans=[];uncertain=0;anchors=0
    for measure in track['measures']:
        for voice in measure['voices']:
            for event in voice:
                notes=[n['midi'] for n in event['notes'] if n['midi'] is not None]
                options=candidate_chords(notes)
                if len(options)==1:
                    _,ch=options[0]
                    start=Fraction(event['onset_q']);end=start+Fraction(event['duration_q'])
                    spans.append({'start':start,'end':end,'chord':ch,
                                  'beat_id':event['beat_id'],'voice':event['voice_index']})
                    anchors+=1
                elif len(set(n%12 for n in notes))>=3:uncertain+=1
    # Overlapping voices can produce contradictory anchors. Keep only spans
    # that cannot be contradicted by other anchored simultaneities.
    accepted=[]
    for x in spans:
        conflicts=[y for y in spans if y is not x and x['start']<y['end'] and y['start']<x['end'] and x['chord']!=y['chord']]
        if not conflicts:accepted.append(x)
    accepted.sort(key=lambda x:(x['start'],x['end'],x['voice']))
    return accepted,{'observed_chord_events':anchors,'unresolved_chord_events':uncertain,
                      'accepted_chord_events':len(accepted),'conflicts_excluded':anchors-len(accepted)}

def selected_harmony(source_spans,rate,seed=17):
    if not 0<=rate<=1:raise ValueError('Change probability must be between 0 and 1')
    rng=random.Random(seed)
    pool=sorted(set(x['chord'] for x in source_spans),key=lambda c:(c.root%12,c.degrees,c.root))
    output=[]
    for src in source_spans:
        chord=src['chord'];options=[c for c in pool if (c.root%12,c.degrees)!=(chord.root%12,chord.degrees)]
        if options and rng.random()<rate:
            chosen=rng.choice(options)
            # Preserve the source chord root register, only change pitch class
            # according to an actually observed chord from this song.
            source_root=chord.root
            target_root=min((chosen.root%12+12*k for k in range(-2,11)),key=lambda p:(abs(p-source_root),p))
            target=Chord(target_root,chosen.degrees)
        else:target=chord
        output.append({**src,'target':target})
    return output

def _position(pitch,tuning,original_string=None,max_fret=24,used=None):
    used=used or set()
    choices=[(abs(i-(original_string if original_string is not None else i))*8 +f,f,i)
             for i,open_pitch in enumerate(tuning) if i not in used
             for f in [pitch-open_pitch] if 0<=f<=max_fret]
    if not choices:return None
    _,f,i=min(choices)
    return i,f

def build_changes(score,track_index,spans):
    """Conservatively edit GPIF note definitions only when all uses agree.

    GPIF note/beat definitions can be shared by multiple measures. An in-place
    change to a shared note would otherwise alter unrelated source music.
    """
    tr=score['tracks'][track_index]
    tuning=tr['tunings'][0]
    if not tuning:raise ValueError('A pitched track tuning is required for GP tablature export')
    # Windows are based on exact onset; do not key by GPIF beat IDs, which
    # may be reused across different measures and voices.
    windows=sorted(spans,key=lambda s:s['start'])
    total_uses=Counter()
    original_pitch={}
    requested={}
    for track in score['tracks']:
        for measure in track['measures']:
            for voice in measure['voices']:
                for ev in voice:
                    for note in ev['notes']:
                        total_uses[note['note_id']]+=1
                        original_pitch[note['note_id']]=note['midi']
    considered=0;unplayable=0
    for measure in tr['measures']:
        for voice in measure['voices']:
            for ev in voice:
                src=at_time(windows,Fraction(ev['onset_q']))
                if src is None:continue
                used=set();proposal={};valid=True
                for note in ev['notes']:
                    pitch=note['midi']
                    if pitch is None:continue
                    considered+=1
                    new=map_note(analyze_note(pitch,src['chord']),src['target'])
                    position=_position(new,tuning,note.get('string'),used=used)
                    if position is None:
                        valid=False;break
                    used.add(position[0]);proposal[note['note_id']]=(new,*position)
                if valid:
                    for n in ev['notes']:
                        nid=n['note_id']
                        if nid in proposal:requested.setdefault(nid,[]).append(proposal[nid])
                else:unplayable+=1
    # Edit a definition only if every use is covered AND agrees on the same
    # output pitch/fingering. Others remain completely unchanged.
    changes={};shared_skipped=0
    for nid,proposals in requested.items():
        if len(proposals)==total_uses[nid] and len(set(proposals))==1 and proposals[0][0]!=original_pitch[nid]:
            changes[nid]=proposals[0]
        else:shared_skipped+=1
    return changes,{'chord_note_instances_considered':considered,
                    'note_definitions_safely_editable':len(changes),
                    'shared_or_conflicting_note_ids_skipped':shared_skipped,
                    'chord_beats_skipped_unplayable':unplayable}

def _write_note(n,pitch,string,fret):
    properties=n.find('Properties')
    if properties is None:properties=ET.SubElement(n,'Properties')
    for label,value,child in [('String',string,'String'),('Fret',fret,'Fret'),('Midi',pitch,'Number')]:
        prop=next((p for p in properties.findall('Property') if p.get('name')==label),None)
        if prop is None:prop=ET.SubElement(properties,'Property',{'name':label})
        e=prop.find(child)
        if e is None:e=ET.SubElement(prop,child)
        e.text=str(value)
    names='C C# D D# E F F# G G# A A# B'.split()
    for label in ('ConcertPitch','TransposedPitch'):
        prop=next((p for p in properties.findall('Property') if p.get('name')==label),None)
        if prop is None:prop=ET.SubElement(properties,'Property',{'name':label})
        p=prop.find('Pitch')
        if p is None:p=ET.SubElement(prop,'Pitch')
        name=names[pitch%12]
        for x in list(p):p.remove(x)
        ET.SubElement(p,'Step').text=name[0]
        ET.SubElement(p,'Accidental').text='1' if '#' in name else '0'
        ET.SubElement(p,'Octave').text=str(pitch//12-1)

def export_changes(source,destination,changes):
    source=Path(source);destination=Path(destination)
    if source.resolve()==destination.resolve():raise ValueError('Cannot overwrite input')
    with zipfile.ZipFile(source) as zi:
        members=[(i,zi.read(i.filename)) for i in zi.infolist()]
        root=ET.fromstring(zi.read('Content/score.gpif'))
    seen=set()
    for note in root.findall('./Notes/Note'):
        nid=note.get('id')
        if nid in changes:
            _write_note(note,*changes[nid]);seen.add(nid)
    if seen!=set(changes):raise ValueError('GPIF note IDs missing from source: '+str(set(changes)-seen))
    output_xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w') as zo:
        for info,data in members:
            zo.writestr(info,output_xml if info.filename=='Content/score.gpif' else data)
    parsed=extract_score(destination)
    if parsed['measure_count']!=len(root.findall('./MasterBars/MasterBar')):raise AssertionError('Measure count changed')
    for tr in parsed['tracks']:
        for measure in tr['measures']:
            for voice in measure['voices']:
                for event in voice:
                    for n in event['notes']:
                        if n['note_id'] in changes and n['midi']!=changes[n['note_id']][0]:
                            raise AssertionError('Output pitch not preserved')
    return parsed

def run(source,output,track=0,change_probability=1.0,seed=17):
    score=extract_score(source)
    anchors,diagnostics=infer_harmony(score,track)
    anchors,context_report=supplement_anchors(score,track,anchors,max_gap=4)
    windows,continuity=expand_agreed_anchors(anchors,max_gap=4)
    windows=selected_harmony(windows,change_probability,seed)
    changes,details=build_changes(score,track,windows)
    restored=export_changes(source,output,changes)
    return {'source':Path(source).name,'output':str(output),'track_index':track,
            'change_probability':change_probability,'seed':seed,
            **diagnostics,**context_report,**continuity,**details,'changed_source_note_ids':len(changes),
            'measure_count':restored['measure_count'],
            'status':'conservative full-vocabulary chord reharmonization, not calibrated chord similarity'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--track',type=int,default=0)
    p.add_argument('--change-probability',type=float,default=1)
    p.add_argument('--seed',type=int,default=17)
    a=p.parse_args()
    print(json.dumps(run(a.source,a.output,a.track,a.change_probability,a.seed),indent=2))
if __name__=='__main__':main()