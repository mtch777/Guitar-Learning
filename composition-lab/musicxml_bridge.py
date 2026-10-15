"""Auditable exact-time MusicXML bridge; source GP is never modified.

Each written note retains an occurrence ID. GP XML/techniques remain in the
canonical JSON sidecar: MusicXML is an inference view, not a lossless GP format.
Overfull voices are reported and rejected rather than truncated or rescaled.
"""
import argparse
import json
import math
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET
from exact_score import extract_score, validate_events


def occurrence_rows(score):
    return {f't{t["index"]}m{mi}v{vi}b{ei}n{ni}':
            (t['index'], mi, vi, Fraction(e['onset_q']), Fraction(e['duration_q']), n['midi'])
            for t in score['tracks'] for mi,m in enumerate(t['measures'])
            for vi,v in enumerate(m['voices']) for ei,e in enumerate(v)
            for ni,n in enumerate(e['notes'])}


def export_musicxml(score, path):
    findings = validate_events(score)
    overfull = [f for f in findings if Fraction(f['duration_q']) > Fraction(f['meter_q'])]
    if overfull:
        raise ValueError('Overfull source voices require source-level reconciliation: ' + json.dumps(overfull))
    root = ET.Element('score-partwise', version='4.0')
    # Partitura requires one divisions value per part for note-array inference.
    divisions=math.lcm(*[Fraction(e['duration_q']).denominator for t in score['tracks']
                         for m in t['measures'] for v in m['voices'] for e in v],1)
    parts = ET.SubElement(root, 'part-list')
    for track in score['tracks']:
        ti = track['index']; pid = f'P{ti}'
        entry = ET.SubElement(parts, 'score-part', id=pid)
        ET.SubElement(entry, 'part-name').text = track['name'] or pid
        part = ET.SubElement(root, 'part', id=pid)
        for mi, measure in enumerate(track['measures']):
            bar = ET.SubElement(part, 'measure', number=str(mi+1))
            attrs = ET.SubElement(bar, 'attributes')
            ET.SubElement(attrs, 'divisions').text = str(divisions)
            if measure.get('key_signature'):
                key=ET.SubElement(attrs,'key')
                ET.SubElement(key,'fifths').text=str(measure['key_signature']['fifths'])
                ET.SubElement(key,'mode').text=(measure['key_signature']['mode'] or 'major').lower()
            time = ET.SubElement(attrs, 'time')
            num, den = measure['time_signature'].split('/')
            ET.SubElement(time, 'beats').text = num
            ET.SubElement(time, 'beat-type').text = den
            if not any(measure['voices']):
                # GP empty bar is implicit silence; MusicXML readers need its
                # metrical extent. No source note occurrence is synthesized.
                rest=ET.SubElement(bar,'note',id=f'implicit-rest-t{ti}m{mi}')
                ET.SubElement(rest,'rest',measure='yes')
                ET.SubElement(rest,'duration').text=str(int(Fraction(4*int(num),int(den))*divisions))
                ET.SubElement(rest,'voice').text='1'
            previous_total = 0
            for vi, voice in enumerate(measure['voices']):
                if not voice:
                    continue
                if previous_total:
                    ET.SubElement(ET.SubElement(bar, 'backup'), 'duration').text = str(previous_total)
                total = 0
                for ei, event in enumerate(voice):
                    raw = ET.fromstring(event.get('beat_xml', '<Beat/>'))
                    grace_type=event.get('grace_type')
                    ticks = Fraction(event['duration_q']) * divisions
                    assert ticks.denominator == 1
                    total += int(ticks)
                    for ni, note in enumerate(event['notes'] or [None]):
                        nid = f't{ti}m{mi}v{vi}b{ei}n{ni}'
                        node = ET.SubElement(bar, 'note', id=nid)
                        if grace_type: ET.SubElement(node,'grace')
                        if ni:
                            ET.SubElement(node, 'chord')
                        if note is None:
                            ET.SubElement(node, 'rest')
                        else:
                            midi = note['midi']
                            if midi is None:
                                raise ValueError('Unresolved pitch: ' + nid)
                            pitch = ET.SubElement(node, 'pitch')
                            names = ('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
                            spelling = names[midi % 12]
                            ET.SubElement(pitch, 'step').text = spelling[0]
                            if '#' in spelling:
                                ET.SubElement(pitch, 'alter').text = '1'
                            ET.SubElement(pitch, 'octave').text = str(midi//12-1)
                        if not grace_type: ET.SubElement(node, 'duration').text = str(int(ticks))
                        ET.SubElement(node, 'voice').text = str(vi+1)
                        if grace_type:
                            types={'Whole':'whole','Half':'half','Quarter':'quarter','Eighth':'eighth',
                                   '16th':'16th','32nd':'32nd','64th':'64th','128th':'128th','256th':'256th'}
                            ET.SubElement(node,'type').text=types[event['rhythm']]
                        if note:
                            for attr, kind in [('destination','stop'), ('origin','start')]:
                                if (note.get('tie') or {}).get(attr) == 'true':
                                    ET.SubElement(node, 'tie', type=kind)
                previous_total = total
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
    return dict(source_voice_findings=findings, **audit_musicxml(score, path))


def audit_musicxml(score, path):
    """Independent cursor parser: backup/forward/chords must preserve occurrences."""
    expected = occurrence_rows(score); actual = {}; duplicates = []
    for part in ET.parse(path).getroot().findall('part'):
        ti = int(part.get('id')[1:]); start = Fraction(0); divisions = 1
        for mi, measure in enumerate(part.findall('measure')):
            div = measure.findtext('./attributes/divisions')
            if div: divisions = int(div)
            cursor = Fraction(0); last = Fraction(0)
            source_measure = next(t for t in score['tracks'] if t['index']==ti)['measures'][mi]
            for node in measure:
                if node.tag in ('backup', 'forward'):
                    cursor += Fraction(int(node.findtext('duration')), divisions) * (-1 if node.tag == 'backup' else 1)
                if node.tag != 'note': continue
                dur = Fraction(int(node.findtext('duration') or '0'), divisions)
                onset = last if node.find('chord') is not None else cursor
                if node.find('chord') is None:
                    last = cursor; cursor += dur
                if node.find('rest') is not None: continue
                p = node.find('pitch')
                midi = 12*(int(p.findtext('octave'))+1) + dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)[p.findtext('step')] + int(p.findtext('alter') or 0)
                nid = node.get('id')
                if nid in actual: duplicates.append(nid)
                actual[nid] = (ti, mi, int(node.findtext('voice'))-1, start+onset, dur, midi)
            num, den = map(int, source_measure['time_signature'].split('/'))
            start += Fraction(4*num, den)
    mismatches = [nid for nid in expected.keys() | actual.keys() if expected.get(nid) != actual.get(nid)]
    return dict(notes_expected=len(expected), notes_observed=len(actual), mismatched_occurrences=sorted(mismatches),
                duplicate_ids=duplicates, exact_note_timing_pitch_voice=not mismatches and not duplicates,
                technique_preservation='canonical JSON sidecar only; not an inference feature')


def main():
    p = argparse.ArgumentParser(); p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    args = p.parse_args(); score = extract_score(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix('.canonical.json').write_text(json.dumps(score), encoding='utf-8')
    findings = validate_events(score)
    args.output.with_suffix('.timing.json').write_text(json.dumps(findings, indent=2), encoding='utf-8')
    report = export_musicxml(score, args.output)
    args.output.with_suffix('.audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not report['exact_note_timing_pitch_voice']: raise SystemExit(1)


if __name__ == '__main__': main()
