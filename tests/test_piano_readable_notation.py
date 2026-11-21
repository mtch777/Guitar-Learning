"""Readable piano MIDI notation regression tests (isolated from legacy music21 tests)."""
import importlib.util
import io
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

import mido

ROOT=Path(__file__).parents[1]
source=ROOT/'scripts/piano/readable_midi_notation.py'
spec=importlib.util.spec_from_file_location('readable_midi_notation',source)
notation=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=notation
spec.loader.exec_module(notation)


def create_midi(events,ppq=480,meter=(4,4)):
    f=mido.MidiFile(type=0,ticks_per_beat=ppq)
    track=mido.MidiTrack()
    records=[(0,-1,mido.MetaMessage('time_signature',numerator=meter[0],denominator=meter[1]))]
    for start,end,pitch in events:
        records.append((start,1,mido.Message('note_on',note=pitch,velocity=90)))
        records.append((end,0,mido.Message('note_off',note=pitch)))
    last=0
    for tick,_,message in sorted(records,key=lambda row:(row[0],row[1])):
        track.append(message.copy(time=tick-last))
        last=tick
    f.tracks.append(track)
    output=io.BytesIO()
    f.save(file=output)
    return output.getvalue()


def describe(data):
    xml=notation.encode(data,'Test')
    root=ET.fromstring(xml)
    written=root.findall('.//note')
    pitched=[n for n in written if n.find('pitch') is not None]
    rests=[n for n in written if n.find('rest') is not None]
    attacks=[n for n in pitched if all(t.get('type')!='stop' for t in n.findall('tie'))]
    return root,written,pitched,rests,attacks


class ReadableNotation(unittest.TestCase):
    def test_polite_company_real_midi_is_legible(self):
        data=(ROOT/'public/piano/learning-songs/uploads/midi-190ee0d516e3917d53b1951bcf08d0577cf9f500819429dad87463c7ee3aba89.mid').read_bytes()
        root,written,pitched,rests,attacks=describe(data)
        self.assertEqual(len(attacks),219)
        self.assertLessEqual(len(pitched),420)
        self.assertLessEqual(len(rests),140)
        self.assertTrue(root.findall('.//measure'))
        self.assertTrue(all(int(n.findtext('voice') or '1')>=1 for n in written))
        self.assertFalse(any(n.findtext('type') in ('32nd','64th','128th','256th') for n in written))
        self.assertTrue(root.findall('.//backup'), 'Independent held-note voices expected')
        self.assertEqual(len(root.findall('./part')),2)

    def test_humanized_gated_chord_becomes_one_notated_chord(self):
        data=create_midi([(0,3647,60),(23,3646,64),(48,3647,67)])
        root,written,pitched,rests,attacks=describe(data)
        self.assertEqual(len(attacks),3)
        first=root.findall('./part/measure')[0]
        pitched_notes=[n for n in first.findall('note') if n.find('pitch') is not None]
        self.assertEqual(len(pitched_notes),3)
        self.assertEqual(sum(n.find('chord') is not None for n in pitched_notes),2)
        self.assertFalse(any(n.find('rest') is not None for n in first.findall('note')))

    def test_only_common_pitch_is_tied_between_changes(self):
        data=create_midi([(0,3840,60),(0,1920,64),(1920,3840,67)])
        root,written,pitched,rests,attacks=describe(data)
        self.assertEqual(len(attacks),3)
        names=Counter()
        for n in pitched:
            if n.find('tie') is not None:
                names[n.findtext('pitch/step')]+=1
        self.assertGreater(names['C'],0)
        self.assertEqual(names['E'],0)
        self.assertEqual(names['G'],0)
        self.assertEqual(len(rests),0)

    def test_held_pitch_is_not_sliced_when_other_pitches_change(self):
        data=create_midi([
            (0,1920,60),     # C4 holds four beats.
            (0,480,64),      # E4
            (480,960,67),    # G4
            (960,1440,69),   # A4
            (1440,1920,72),  # C5
        ])
        root,_,pitched,_,attacks=describe(data)
        held=[n for n in pitched
              if n.findtext('pitch/step')=='C'
              and n.findtext('pitch/octave')=='4']
        self.assertEqual(len(held),1)
        self.assertEqual(held[0].findtext('duration'),'3840')
        self.assertEqual(len(held[0].findall('tie')),0)
        self.assertTrue(root.findall('.//backup'))
        self.assertEqual(len(attacks),5)

    def test_double_dotted_half_prevents_false_mid_measure_ties(self):
        data=create_midi([
            (0,1920,60),
            (0,240,64),
            (240,1920,64),
        ])
        _,_,pitched,_,attacks=describe(data)
        e_notes=[n for n in pitched if n.findtext('pitch/step')=='E']
        self.assertEqual(len(e_notes),2)
        self.assertEqual(e_notes[1].findtext('duration'),'3360')
        self.assertEqual(e_notes[1].findtext('type'),'half')
        self.assertEqual(len(e_notes[1].findall('dot')),2)
        self.assertEqual(len(attacks),3)

    def test_repeated_note_has_a_new_attack_not_a_tie(self):
        data=create_midi([(0,456,60),(480,936,60)])
        root,written,pitched,rests,attacks=describe(data)
        self.assertEqual(len(attacks),2)
        self.assertEqual(len(pitched),2)

    def test_performance_gate_ends_on_the_written_beat(self):
        data=create_midi([(0,3647,60),(3840,4752,62)])
        root,written,pitched,rests,attacks=describe(data)
        self.assertEqual(len(attacks),2)
        self.assertEqual(len(root.findall('./part/measure')),3)
        self.assertLess(len(rests),2)

    def test_meter_and_tempos(self):
        data=create_midi([(0,480,60),(480,2400,62)],meter=(5,8))
        root,written,pitched,rests,attacks=describe(data)
        self.assertEqual(root.findtext('.//time/beats'),'5')
        self.assertEqual(root.findtext('.//time/beat-type'),'8')
        self.assertEqual(len(attacks),2)

    def test_rejects_shorter_than_grid_repeated_pitches(self):
        data=create_midi([(0,45,60),(48,120,60)])
        with self.assertRaisesRegex(ValueError,'collisions after notation'):
            notation.encode(data,'Too fast')

    def test_invalid_track_name_cannot_break_xml(self):
        m=mido.MidiFile(type=0,ticks_per_beat=480)
        track=mido.MidiTrack([
            mido.MetaMessage('track_name',name='Piano\x00',time=0),
            mido.Message('note_on',note=60,velocity=90,time=0),
            mido.Message('note_off',note=60,time=480),
        ])
        m.tracks.append(track)
        b=io.BytesIO();m.save(file=b)
        xml=notation.encode(b.getvalue())
        self.assertNotIn(b'\x00',xml)
        ET.fromstring(xml)


if __name__=='__main__':
    unittest.main()
