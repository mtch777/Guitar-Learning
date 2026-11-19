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


if __name__ == "__main__":
    unittest.main()
