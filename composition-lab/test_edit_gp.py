"""GP7 score edit integration test with generated fixture (no copyrighted songs)."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from edit_gp import edit_note, prop

def fixture(path):
    root = ET.Element("GPIF")
    notes = ET.SubElement(root,"Notes")
    note = ET.SubElement(notes,"Note",id="1")
    props = ET.SubElement(note,"Properties")
    for name, child, value in [("String","String","2"),("Fret","Fret","5"),("Midi","Number","45")]:
        ET.SubElement(ET.SubElement(props,"Property",name=name),child).text = value
    for name in ("ConcertPitch","TransposedPitch"):
        pitch = ET.SubElement(ET.SubElement(props,"Property",name=name),"Pitch")
        ET.SubElement(pitch,"Step").text="A"
        ET.SubElement(pitch,"Accidental")
        ET.SubElement(pitch,"Octave").text="2"
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("VERSION","7.0")
        z.writestr("Content/score.gpif",ET.tostring(root))
        z.writestr("Content/BinaryStylesheet",b"\x00\x01")

class GP7EditorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.input=Path(self.tmp.name)/"in.gp"
        self.output=Path(self.tmp.name)/"out.gp"
        fixture(self.input)
    def tearDown(self):
        self.tmp.cleanup()
    def test_one_note_modified_and_reimported(self):
        result=edit_note(self.input,self.output)
        self.assertTrue(result["reimport_verified"])
        self.assertEqual(result["change"]["new_fret"],6)
        with zipfile.ZipFile(self.output) as archive:
            note=ET.fromstring(archive.read("Content/score.gpif")).find("./Notes/Note")
            self.assertEqual(prop(note,"Midi","Number").text,"46")
    def test_semitone_down(self):
        self.assertEqual(edit_note(self.input,self.output,semitones=-1)["change"]["new_fret"],4)
    def test_reject_in_place(self):
        with self.assertRaises(ValueError):
            edit_note(self.input,self.input)
    def test_reject_unsupported_shift(self):
        with self.assertRaises(ValueError):
            edit_note(self.input,self.output,semitones=7)
    def test_reject_unknown_note_id(self):
        with self.assertRaises(ValueError):
            edit_note(self.input,self.output,note_id="missing")

if __name__=="__main__":
    unittest.main()
