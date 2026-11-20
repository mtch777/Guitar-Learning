"""Regression for MuseScore MIDI files containing unequal simultaneous notes."""
import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from music21 import meter, note, stream


SCRIPT = Path(__file__).parents[1] / "scripts/piano/import-midi-url.py"
SPEC = importlib.util.spec_from_file_location("piano_import_midi", SCRIPT)
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


class MIDIPolyphonyTest(unittest.TestCase):
    def test_unequal_simultaneous_durations_get_separate_voices(self):
        score = stream.Score()
        part = stream.Part()
        measure = stream.Measure(number=98)
        measure.timeSignature = meter.TimeSignature("4/4")
        measure.insert(0, note.Note("A1", quarterLength=1.75))
        measure.insert(0, note.Note("A2", quarterLength=1.5))
        measure.insert(2, note.Note("C3", quarterLength=2))
        part.insert(0, measure)
        score.insert(0, part)

        expected = sorted((n.pitch.midi, n.offset, n.quarterLength) for n in measure.notes)
        self.assertEqual(len(measure.voices), 0)
        IMPORTER.preserve_midi_polyphony(score)
        self.assertEqual(len(measure.voices), 2)
        actual = sorted((n.pitch.midi, n.getOffsetInHierarchy(measure), n.quarterLength)
                        for n in measure.recurse().notes)
        self.assertEqual(actual, expected)

        with tempfile.TemporaryDirectory() as directory:
            target = str(Path(directory) / "score.musicxml")
            score.write("musicxml", fp=target)
            xml = ET.parse(target)
            voices = [n.findtext("voice") for n in xml.findall(".//note")
                      if n.find("pitch") is not None]
            self.assertEqual(len(voices), 3)
            self.assertGreaterEqual(len(set(voices)), 2)

    def test_conflicting_midi_meters_rebar_all_parts_without_changing_timing(self):
        score = stream.Score()
        piano = stream.Part()
        piano.insert(0, meter.TimeSignature('6/8'))
        for onset, pitch in [(0, 'C4'), (3, 'D4'), (6, 'E4'), (9, 'F4')]:
            piano.insert(onset, note.Note(pitch, quarterLength=3))
        piano.makeMeasures(inPlace=True)
        score.insert(0, piano)

        accompaniment = stream.Part()
        accompaniment.insert(0, meter.TimeSignature('4/4'))
        accompaniment.insert(0, note.Note('G3', quarterLength=10))
        accompaniment.insert(0, note.Note('B3', quarterLength=9))
        accompaniment.insert(10, note.Note('C4', quarterLength=2))
        accompaniment.makeMeasures(inPlace=True)
        accompaniment.makeTies(inPlace=True)
        score.insert(0, accompaniment)

        original_duration = score.duration.quarterLength
        self.assertEqual([len(p.getElementsByClass(stream.Measure)) for p in score.parts], [4, 3])
        IMPORTER.align_midi_measure_grids(score)
        IMPORTER.preserve_midi_polyphony(score)
        self.assertEqual([len(p.getElementsByClass(stream.Measure)) for p in score.parts], [4, 4])
        self.assertEqual(score.duration.quarterLength, original_duration)
        for part in score.parts:
            self.assertEqual([m.offset for m in part.getElementsByClass(stream.Measure)], [0, 3, 6, 9])

        with tempfile.TemporaryDirectory() as directory:
            target = str(Path(directory) / 'score.musicxml')
            score.write('musicxml', fp=target)
            xml = ET.parse(target)
            part_measures = [part.findall('measure') for part in xml.findall('part')]
            self.assertEqual([len(measures) for measures in part_measures], [4, 4])
            # A held G3 and B3 still span their original bars, with voices
            # attached to each continuation instead of silently restarting.
            accompaniment_notes = part_measures[1]
            for step in ('G', 'B'):
                notes = [n for measure in accompaniment_notes for n in measure.findall('note')
                         if n.findtext('pitch/step') == step]
                self.assertGreaterEqual(len(notes), 3)
                self.assertEqual(notes[0].find('tie').get('type'), 'start')
                self.assertEqual(notes[-1].find('tie').get('type'), 'stop')
                self.assertEqual(len({n.findtext('voice') for n in notes}), 1)



class ExactMidiTimingTest(unittest.TestCase):
    def make_midi(self, *tracks, ppq=480):
        import io
        import mido
        midi = mido.MidiFile(type=1, ticks_per_beat=ppq)
        for messages in tracks:
            track = mido.MidiTrack()
            track.extend(messages)
            midi.tracks.append(track)
        result = io.BytesIO()
        midi.save(file=result)
        return result.getvalue()

    def test_music21_upstream_offset_drift_regression(self):
        import mido
        t = 480
        M = mido.Message
        data = self.make_midi([
            M('note_on', note=58, velocity=90, time=0),
            M('note_on', note=62, velocity=90, time=0),
            M('note_on', note=55, velocity=90, time=0),
            M('note_off', note=58, velocity=0, time=t * 8),
            M('note_off', note=62, velocity=0, time=0),
            M('note_off', note=55, velocity=0, time=t * 4),
            M('note_on', note=60, velocity=90, time=0),
            M('note_off', note=60, velocity=0, time=t),
        ])
        score = IMPORTER.score_from_midi_bytes(data, 'Offset regression').stripTies()
        actual = sorted((p.midi, float(n.getOffsetInHierarchy(score)), float(n.duration.quarterLength))
                        for n in score.recurse().notes for p in n.pitches)
        self.assertEqual(actual, [(55, 0.0, 12.0), (58, 0.0, 8.0),
                                  (60, 12.0, 1.0), (62, 0.0, 8.0)])

    def test_multi_part_polyrhythm_and_ties_share_one_grid(self):
        import mido
        M, Meta, t = mido.Message, mido.MetaMessage, 480
        data = self.make_midi([
            Meta('time_signature', numerator=3, denominator=4, time=0),
            M('note_on', note=60, velocity=90, time=0),
            M('note_off', note=60, time=t * 7),
        ], [
            M('note_on', note=48, velocity=80, time=0),
            M('note_on', note=55, velocity=80, time=0),
            M('note_off', note=48, time=t * 6),
            M('note_off', note=55, time=t),
        ])
        score = IMPORTER.score_from_midi_bytes(data, 'Cross-bar chords')
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory) / 'output.musicxml'
            score.write('musicxml', fp=str(location))
            root = ET.parse(location).getroot()
            for part in root.findall('part'):
                measures = part.findall('measure')
                self.assertGreaterEqual(len(measures), 3)
                self.assertEqual([m.get('number') for m in measures[:3]], ['1','2','3'])
            self.assertTrue(root.findall('.//tie'))

    def test_midi_note_on_zero_velocity_and_drum_channel(self):
        import mido
        M = mido.Message
        data = self.make_midi([
            M('note_on', note=60, channel=0, velocity=100, time=0),
            M('note_on', note=60, channel=0, velocity=0, time=480),
            M('note_on', note=35, channel=9, velocity=100, time=0),
            M('note_off', note=35, channel=9, time=480),
        ])
        score = IMPORTER.score_from_midi_bytes(data)
        pitched = [p.midi for n in score.recurse().notes for p in n.pitches]
        self.assertEqual(pitched, [60])


if __name__ == "__main__":
    unittest.main()
