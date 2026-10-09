"""Synthetic GPIF fixtures for independent feature-analysis regression tests."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from analyze_style import profile

class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"fixture.gp"
        root=ET.Element("GPIF")
        tracks=ET.SubElement(root,"Tracks")
        track=ET.SubElement(tracks,"Track")
        ET.SubElement(track,"Name").text="Test Guitar"
        staves=ET.SubElement(track,"Staves")
        staff=ET.SubElement(staves,"Staff")
        props=ET.SubElement(staff,"Properties")
        ET.SubElement(ET.SubElement(props,"Property",name="Tuning"),"Pitches").text="40 45 50 55 59 64"
        masters=ET.SubElement(root,"MasterBars")
        bars=ET.SubElement(root,"Bars")
        voices=ET.SubElement(root,"Voices")
        beats=ET.SubElement(root,"Beats")
        notes=ET.SubElement(root,"Notes")
        rhythms=ET.SubElement(root,"Rhythms")
        rhythm=ET.SubElement(rhythms,"Rhythm",id="0")
        ET.SubElement(rhythm,"NoteValue").text="16th"
        for i in range(4):
            master=ET.SubElement(masters,"MasterBar")
            ET.SubElement(master,"Time").text="4/4"
            ET.SubElement(master,"Bars").text=str(i)
            if i==0:
                ET.SubElement(ET.SubElement(master,"Section"),"Text").text="Intro"
            ET.SubElement(ET.SubElement(bars,"Bar",id=str(i)),"Voices").text=str(i)
            ET.SubElement(ET.SubElement(voices,"Voice",id=str(i)),"Beats").text=str(i)
            beat=ET.SubElement(beats,"Beat",id=str(i))
            ET.SubElement(beat,"Rhythm",ref="0")
            ET.SubElement(beat,"Notes").text=str(i)
            note=ET.SubElement(notes,"Note",id=str(i))
            p=ET.SubElement(note,"Properties")
            for name,tag,value in (("String","String","0"),("Fret","Fret","3"),("Midi","Number","43")):
                ET.SubElement(ET.SubElement(p,"Property",name=name),tag).text=value
            ET.SubElement(ET.SubElement(p,"Property",name="PalmMuted"),"Enable")
        with zipfile.ZipFile(self.path,"w") as z:
            z.writestr("Content/score.gpif",ET.tostring(root))
    def tearDown(self):
        self.tmp.cleanup()
    def test_measures_repeats_and_techniques(self):
        result=profile(self.path)
        self.assertEqual(result["measures"],4)
        self.assertEqual(result["section_markers"][0]["label"],"Intro")
        guitar=result["tracks"][0]
        self.assertEqual(guitar["notes"],4)
        self.assertEqual(guitar["techniques"]["PalmMuted"],4)
        self.assertEqual(guitar["repeated_measure_groups"][0],[1,2,3,4])
        self.assertEqual(guitar["repeated_two_measure_groups"][0],[1,2,3])
        self.assertEqual(guitar["pitch_classes"][0]["value"],"G")

if __name__=="__main__":
    unittest.main()
