"""Occurrence-cloned pitch/voicing experiments; rhythm and archive assets stay locked.

These are explicit generic construction rules, not artist-trained models. Refuse
technique-bearing events rather than erase or reinterpret their performance.
"""
from copy import deepcopy
from fractions import Fraction as F
from importlib import import_module
import itertools
from functools import lru_cache
import json
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET
from exact_score import extract_score, validate_events
from technique_strength import released
from technique_edits import transact
from technique_analysis import classify_group

apply_occurrence_edits = import_module('checkpoints.2026-10-14.gp_occurrence_writer').apply_occurrence_edits
FAMILIES = ('pedal_notes', 'close_interval_texture', 'power_chord', 'extended_power_chord', 'double_stop')
PLAIN = {'Midi', 'String', 'Fret', 'ConcertPitch', 'TransposedPitch'}


def voicing(tuning, family, index=0, method='compact'):
    """Search physically bounded shapes, independent of original event pitches."""
    if family not in FAMILIES or method not in ('compact', 'upper'):
        raise ValueError('Unknown construction method/family')
    if family == 'pedal_notes':
        # Repeated anchor with short contrasting answers; register derives from tuning.
        anchor_count = 5 if method == 'compact' else 3
        strings_by_pitch=sorted(range(len(tuning)),key=lambda s:tuning[s])
        string = strings_by_pitch[0] if index % 8 < anchor_count else strings_by_pitch[min(2, len(tuning)-1)]
        fret = 0 if index % 8 < anchor_count else (index % 3) + 2
        return [(tuning[string]+fret, string, fret)]
    size = 3 if family == 'extended_power_chord' else 2
    return _shapes(tuple(tuning), family, method)[index % min(4,len(_shapes(tuple(tuning),family,method)))]


@lru_cache(maxsize=64)
def _shapes(tuning, family, method):
    size = 3 if family == 'extended_power_chord' else 2
    candidates = []
    for strings in itertools.combinations(range(len(tuning)), size):
        if max(strings)-min(strings) > 3:
            continue
        for frets in itertools.product(range(0, 8), repeat=size):
            stopped = [f for f in frets if f]
            if stopped and max(stopped)-min(stopped) > 4:
                continue
            positions = [(tuning[s]+f, s, f) for s, f in zip(strings, frets)]
            labels = classify_group([dict(midi=p, string=s) for p,s,f in positions])
            if family not in labels:
                continue
            # A general double-stop comparison excludes the other named dyad classes.
            if family == 'double_stop' and ('power_chord' in labels or 'close_interval_texture' in labels):
                continue
            cost = (sum(frets), max(frets), sum(p for p,s,f in positions))
            candidates.append((cost, positions))
    if not candidates:
        raise ValueError('No shape satisfies declared string/fret constraints')
    candidates.sort(key=lambda c:c[0], reverse=method=='upper')
    # Progress through a small bounded vocabulary; no fixed key or artist examples.
    return [c[1] for c in candidates]


def plain(event):
    if not event['notes'] or F(event['duration_q']) <= 0:
        return False
    beat = ET.fromstring(event['beat_xml'])
    if any(x.tag not in ('Notes','Rhythm','Dynamic','Properties','ConcertPitchStemOrientation','TransposedPitchStemOrientation','XProperties') for x in beat):
        return False
    if any(len(x) for x in beat.findall('XProperties')):return False
    if len(beat.findall('./Properties/Property')):
        return False
    for n in event['notes']:
        xml = ET.fromstring(n['note_xml'])
        if xml.findtext('InstrumentArticulation') not in (None,'0'):return False
        if n.get('tie') or any(x.tag not in ('Properties','InstrumentArticulation') for x in xml):
            return False
        if set(n['property_names'])-PLAIN:
            return False
    return True


def set_position(note, midi, string, fret):
    props = note.find('Properties')
    for name, child, value in [('Midi','Number',midi),('String','String',string),('Fret','Fret',fret)]:
        p = props.find(f"Property[@name='{name}']")
        if p is None:p=ET.SubElement(props,'Property',name=name)
        for x in list(p):p.remove(x)
        ET.SubElement(p,child).text=str(value)
    for name in ('ConcertPitch','TransposedPitch'):
        p=props.find(f"Property[@name='{name}']")
        if p is None:p=ET.SubElement(props,'Property',name=name)
        for x in list(p):p.remove(x)
        pitch=ET.SubElement(p,'Pitch'); spelling=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][midi%12]
        for tag,value in [('Step',spelling[0]),('Accidental',int('#' in spelling)),('Octave',midi//12-1)]:ET.SubElement(pitch,tag).text=str(value)


def generate(source, destination, track_index, family, strength=100, method='compact', pitch_unlocked=False, voicing_unlocked=False):
    if family not in FAMILIES:raise ValueError('Unknown pattern family')
    released('validate',strength)
    if strength == 0:return dict(**transact(source,destination,{},{}),family=family,strength=0,changed_events=0)
    if not pitch_unlocked or not voicing_unlocked:raise ValueError('Construction requires explicit pitch AND voicing unlocks')
    source,destination=Path(source),Path(destination)
    if destination.exists():raise FileExistsError(destination)
    score=extract_score(source);track=score['tracks'][track_index]
    if len(track['tunings'])!=1:raise ValueError('Single pitched staff required')
    tuning=track['tunings'][0];plans={};skipped=0;index=0
    for mi,m in enumerate(track['measures']):
        if sum(bool(v) for v in m['voices'])!=1:skipped+=sum(len(v) for v in m['voices']);continue
        for vi,v in enumerate(m['voices']):
            # Whole measures released for pedal organization, not scattered anchor notes.
            release=released(f'{track_index}:{mi}:pedal',strength)
            for ei,e in enumerate(v):
                key=(mi,vi,ei)
                active=release if family=='pedal_notes' else released(str(key),strength)
                if active and plain(e):plans[key]=voicing(tuning,family,index,method)
                else:skipped+=1
                index+=1
    if not plans:raise ValueError('No safe unlocked events; source left untouched')
    with zipfile.ZipFile(source) as src:
        original=ET.fromstring(src.read('Content/score.gpif'));root=deepcopy(original)
        # Existing occurrence writer clones the complete bar/voice/beat ancestor path.
        dummy={(*key,0):positions[0] for key,positions in plans.items()}
        audit=apply_occurrence_edits(root,score,track_index,dummy,set_position)
        tables={name:{n.get('id'):n for n in root.find(name)} for name in ('Bars','Voices','Beats','Notes')}
        notes=root.find('Notes');next_id=max(int(n.get('id')) for n in notes)+1
        for (mi,vi,ei),positions in plans.items():
            bar_id=root.findall('./MasterBars/MasterBar')[mi].findtext('Bars').split()[track_index]
            voice=tables['Voices'][tables['Bars'][bar_id].findtext('Voices').split()[vi]]
            beat=tables['Beats'][voice.findtext('Beats').split()[ei]]
            template=tables['Notes'][beat.findtext('Notes').split()[0]];ids=[]
            for position in positions:
                n=deepcopy(template);n.set('id',str(next_id));next_id+=1;set_position(n,*position);notes.append(n);ids.append(n.get('id'))
            beat.find('Notes').text=' '.join(ids)
        # Original definition tables are immutable; only new clones and master refs allowed.
        for table in ('Tracks','Rhythms','Bars','Voices','Beats','Notes'):
            before=original.find(table);after=root.find(table)
            if any(ET.tostring(a)!=ET.tostring(b) for a,b in zip(before,after)):raise AssertionError('Original definition mutated')
        mb0=deepcopy(original.find('MasterBars'));mb1=deepcopy(root.find('MasterBars'))
        for a,b in zip(mb0,mb1):a.remove(a.find('Bars'));b.remove(b.find('Bars'))
        if ET.tostring(mb0)!=ET.tostring(mb1):raise AssertionError('Master timing changed')
        destination.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(destination,'w') as dst:
            dst.comment=src.comment
            for entry in src.infolist():dst.writestr(entry,ET.tostring(root,encoding='utf-8',xml_declaration=True) if entry.filename=='Content/score.gpif' else src.read(entry.filename))
    restored=extract_score(destination)
    with zipfile.ZipFile(source) as src,zipfile.ZipFile(destination) as dst:
        if src.namelist()!=dst.namelist() or src.comment!=dst.comment:raise AssertionError('Archive structure changed')
        if any(src.read(n)!=dst.read(n) for n in src.namelist() if n!='Content/score.gpif'):raise AssertionError('Archive asset changed')
    if validate_events(restored):raise AssertionError('Invalid output timing')
    # Exhaustive occurrence comparison; only declared beat note payloads may change.
    for ti,(a,b) in enumerate(zip(score['tracks'],restored['tracks'])):
        for mi,(ma,mb) in enumerate(zip(a['measures'],b['measures'])):
            for vi,(va,vb) in enumerate(zip(ma['voices'],mb['voices'])):
                if len(va)!=len(vb):raise AssertionError('Event count changed')
                for ei,(ea,eb) in enumerate(zip(va,vb)):
                    for name in ('onset_q','local_onset_q','duration_q'):
                        if ea[name]!=eb[name]:raise AssertionError('Rhythm lock violated')
                    if ti==track_index and (mi,vi,ei) in plans:
                        actual=[(n['midi'],n['string'],n['fret']) for n in eb['notes']]
                        if actual!=plans[mi,vi,ei]:raise AssertionError('Voicing export mismatch')
                    elif [n['note_xml'] for n in ea['notes']] != [n['note_xml'] for n in eb['notes']]:raise AssertionError('Unselected occurrence changed')
    return dict(family=family,strength=strength,method=method,changed_events=len(plans),skipped_events=skipped,
                rhythm_locked=True,unselected_occurrences_locked=True,original_definitions_immutable=True,
                reference_pitch_values_used=False,reference_timing_used=True,cloning=audit,
                limitations=['Generic bounded shape search, not learned artist style','Four-fret stopped span and distinct strings are necessary, not sufficient ergonomic checks','Technique-bearing and polyphonic-voice events skipped','Pedal organization uses event index, not inferred phrase boundaries'])


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--track',type=int,required=True);p.add_argument('--family',choices=FAMILIES,required=True);p.add_argument('--strength',type=int,default=100);p.add_argument('--method',default='compact');p.add_argument('--unlock-pitch',action='store_true');p.add_argument('--unlock-voicing',action='store_true')
    a=p.parse_args();r=generate(a.source,a.out,a.track,a.family,a.strength,a.method,a.unlock_pitch,a.unlock_voicing);a.out.with_suffix('.edit.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
