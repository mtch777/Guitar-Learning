"""Independent GPIF/archive and rendered-sample comparison of owned edits."""
from array import array
from collections import Counter
from fractions import Fraction as F
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import wave
import xml.etree.ElementTree as ET
import zipfile


GUID=re.compile(r'^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$',re.I)


def canonical_ids(root):
    """Normalize ONLY generated chord-definition UUIDs and their references.

    Keep definition contents, order, duplicate-alias topology and every other
    score value. This is not a blanket removal of chord annotations or IDs.
    """
    mapping={}
    for node in root.iter('Item'):
        value=node.get('id')
        if value and GUID.fullmatch(value):
            if value not in mapping:mapping[value]=f'generated-chord:{len(mapping)}'
            node.set('id',mapping[value])
    for node in root.iter('Chord'):
        value=(node.text or '').strip()
        if GUID.fullmatch(value):
            if value not in mapping:raise ValueError('Unresolved generated chord reference')
            node.text=mapping[value]
    return len(mapping)


def differences(a,b,path=''):
    out=[]
    if (a.tag,a.attrib,(a.text or '').strip())!=(b.tag,b.attrib,(b.text or '').strip()):out.append(dict(path=path,old_tag=a.tag,new_tag=b.tag,old_attributes=a.attrib,new_attributes=b.attrib,old_text=(a.text or '').strip(),new_text=(b.text or '').strip()))
    if len(a)!=len(b):out.append(dict(path=path,structural_child_count=[len(a),len(b)]))
    for i,(x,y) in enumerate(zip(a,b)):out+=differences(x,y,path+'/'+x.tag+f'[{i}]')
    return out


def source_note_id(root,part,bar,voice,beat,note):
    tracks=list(root.find('Tracks'));staff_offset=sum(len(t.find('Staves')) for t in tracks[:part])
    if len(tracks[part].find('Staves'))!=1:raise ValueError('Declared single-staff mapping required')
    bar_id=list(root.find('MasterBars'))[bar-1].find('Bars').text.split()[staff_offset]
    bars={r.get('id'):r for r in root.find('Bars')};voices={r.get('id'):r for r in root.find('Voices')};beats={r.get('id'):r for r in root.find('Beats')}
    voice_id=bars[bar_id].find('Voices').text.split()[voice];beat_id=voices[voice_id].find('Beats').text.split()[beat]
    return beats[beat_id].find('Notes').text.split()[note]


def audio(path):
    with wave.open(str(path),'rb') as stream:
        if stream.getnchannels()!=1 or stream.getsampwidth()!=2:raise ValueError('Expected mono16-bit native render')
        samples=array('h',stream.readframes(stream.getnframes()));rate=stream.getframerate()
        if sys.byteorder!='little':samples.byteswap()
    return samples,rate


def written_pitch(pitch):
    step=pitch.findtext('Step');accidental=pitch.findtext('Accidental') or ''
    if type(step)is not str or len(step)!=1 or step not in 'CDEFGAB' or accidental not in ('','b','bb','#','##'):
        raise ValueError('Unknown GP pitch spelling')
    return 12*(int(pitch.findtext('Octave'))+1)+dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)[step]+accidental.count('#')-accidental.count('b')


def check(root,qa,*,allow_inner_degree_changes=False):
    if type(allow_inner_degree_changes)is not bool:raise ValueError('Explicit pitch audit scope required')
    sources={name:zipfile.ZipFile(root/name/'score.gp') for name in ('source','zero','changed')};issues=[]
    names=sources['source'].namelist()
    if any(z.namelist()!=names for z in sources.values()):issues.append('Archive member inventory/order changed')
    gpif=next(n for n in names if n.endswith('.gpif'));trees={n:ET.fromstring(z.read(gpif)) for n,z in sources.items()}
    uuid_counts={n:canonical_ids(t) for n,t in trees.items()}
    zero_diff=differences(trees['source'],trees['zero']);changed_diff=differences(trees['source'],trees['changed'])
    if zero_diff:issues.append('Source/zero GPIF values differ beyond generated chord UUIDs')
    for name in names:
        if name!=gpif and any(z.read(name)!=sources['source'].read(name) for z in sources.values()):issues.append('Locked non-score GP asset changed: '+name)
    expected={}
    before_docs={p.name:json.loads(p.read_text()) for p in (qa/'zero-capture').glob('*.json')}
    after_docs={p.name:json.loads(p.read_text()) for p in (qa/'changed-capture').glob('*.json')}
    for document,before in before_docs.items():
        if not document.startswith('track-'):continue
        part=int(document.split('-')[1].split('.')[0]);after=after_docs[document]
        for mi,m in enumerate(before['measures']):
            for vi,v in enumerate(m.get('voices',[])):
                for bi,beat in enumerate(v.get('beats',[])):
                    for ni,note in enumerate(beat.get('notes',[])):
                        new=after['measures'][mi]['voices'][vi]['beats'][bi]['notes'][ni]
                        if note.get('fret')!=new.get('fret') or note.get('string')!=new.get('string'):
                            ident=source_note_id(trees['source'],part,mi+1,vi,bi,ni)
                            expected[ident]=dict(old_fret=note['fret'],new_fret=new['fret'],old_gp_string=len(before['tuning'])-1-note['string'],new_gp_string=len(after['tuning'])-1-new['string'],
                                shift=after['tuning'][new['string']]+(after.get('capo')or 0)+new['fret']-before['tuning'][note['string']]-(before.get('capo')or 0)-note['fret'])
    actual_notes=set();allowed_properties={'ConcertPitch','TransposedPitch','Fret','Midi','String'}
    old_notes={r.get('id'):r for r in trees['source'].find('Notes')};new_notes={r.get('id'):r for r in trees['changed'].find('Notes')}
    for ident,node in old_notes.items():
        delta=differences(node,new_notes[ident])
        if not delta:continue
        actual_notes.add(ident)
        if ident not in expected:issues.append('Unexpected GP note changed: '+ident);continue
        before={p.get('name'):p for p in node.find('Properties')};after={p.get('name'):p for p in new_notes[ident].find('Properties')};e=expected[ident]
        if int(before['Fret'].find('Fret').text)!=e['old_fret'] or int(after['Fret'].find('Fret').text)!=e['new_fret']:issues.append('GP fret does not match owned source equation')
        if int(before['String'].find('String').text)!=e['old_gp_string'] or int(after['String'].find('String').text)!=e['new_gp_string']:issues.append('GP string does not match owned source assignment')
        if int(after['Midi'].find('Number').text)-int(before['Midi'].find('Number').text)!=e['shift']:issues.append('GP MIDI shift differs from physical pitch equation')
        for pitch_name in ('ConcertPitch','TransposedPitch'):
            old=before[pitch_name].find('Pitch');new=after[pitch_name].find('Pitch')
            if allow_inner_degree_changes:
                if written_pitch(new)-written_pitch(old)!=e['shift']:issues.append('GP spelling does not realize the owned pitch change')
                if written_pitch(old)%12!=int(before['Midi'].find('Number').text)%12:issues.append('GP spelling disagrees with source MIDI pitch class')
            elif int(new.find('Octave').text)-int(old.find('Octave').text)!=e['shift']//12 or e['shift']%12:issues.append('Unexpected GP spelling/register change')
        # Only these dependent scalar leaves may change inside the owned note.
        for change in delta:
            path=change['path']
            allowed=False
            if '/Properties[' in path:
                prop_match=re.search(r'/Property\[(\d+)\]',path)
                if prop_match:
                    prop=list(node.find('Properties'))[int(prop_match.group(1))].get('name')
                    leaves=('/Octave[2]','/Fret[0]','/Number[0]','/String[0]')
                    if allow_inner_degree_changes:leaves+=('/Step[0]','/Accidental[1]')
                    allowed=prop in allowed_properties and path.endswith(leaves)
            if not allowed or change['old_attributes']!=change['new_attributes']:issues.append('Other GP note field changed: '+path)
    if actual_notes!=set(expected):issues.append('Changed GP note identity set differs from source changes')
    # Entire score differences must be restricted to those same note nodes.
    changed_note_indices={i for i,node in enumerate(trees['source'].find('Notes')) if node.get('id') in expected}
    if any(not any(f'/Note[{i}]/' in d['path'] for i in changed_note_indices) for d in changed_diff):issues.append('Non-note GPIF fields changed')
    audio_checks={}
    for mode in ('focused','ensemble'):
        source,rate=audio(root/'source'/(mode+'.wav'));zero,zr=audio(root/'zero'/(mode+'.wav'));changed,cr=audio(root/'changed'/(mode+'.wav'))
        if rate!=zr or rate!=cr or len(source)!=len(zero) or len(source)!=len(changed):raise ValueError('Audio clocks differ')
        delta=[b-a for a,b in zip(source,changed)];nonzero=[i for i,v in enumerate(delta) if v]
        if source!=zero:issues.append('Source/zero rendered samples differ')
        if not nonzero and any(e['shift'] for e in expected.values()):issues.append('No actual rendered pitch change')
        audio_checks[mode]=dict(source_zero_sample_exact=source==zero,changed_sample_frames=len(nonzero),frames=len(source),rate=rate,seconds=len(source)/rate,
            delta_rms=math.sqrt(sum(v*v for v in delta)/len(delta))/32768,
            delta_start_seconds=nonzero[0]/rate if nonzero else None,delta_end_seconds=nonzero[-1]/rate if nonzero else None)
    report=dict(status=('PASS_NATIVE_GP_AND_AUDIO_CHANGE' if any(e['shift'] for e in expected.values()) else 'PASS_NATIVE_GP_AND_RENDER_CHECKS') if not issues else 'FAIL',issues=issues,
        normalized_generated_chord_definitions=uuid_counts,source_zero_normalized_gpif_exact=not zero_diff,
        changed_gp_note_ids=sorted(actual_notes),dependent_gp_scalar_changes=len(changed_diff),expected_fret_changes=expected,audio=audio_checks,
        scope='Native GP data and rendering check (physical-only changes need not alter MIDI audio), not human listening, source-feel or physical playability')
    if allow_inner_degree_changes:report.update(pitch_audit_scope='Source-owned inner degree changes; symbolic inner/outer/source-component checks required separately',human_playability='UNVERIFIED')
    (root/'independent-gp-audio-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('qa',type=Path);a=p.parse_args();r=check(a.root,a.qa);print(json.dumps(r));raise SystemExit(0 if r['status'] in ('PASS_NATIVE_GP_AND_AUDIO_CHANGE','PASS_NATIVE_GP_AND_RENDER_CHECKS') else 1)
