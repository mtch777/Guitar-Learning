"""Unit tests for standalone GP7 archive reader and lossless repackaging."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from gp_io import GPFormatError, inspect_gp, roundtrip_gp

class GP7Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "input.gp"
        gpif = ET.Element("GPIF")
        ET.SubElement(gpif, "GPVersion").text = "7.0.0"
        for key, count in [("Tracks", 2), ("MasterBars", 3), ("Bars", 6),
                           ("Voices", 6), ("Beats", 9), ("Notes", 12), ("Rhythms", 2)]:
            parent = ET.SubElement(gpif, key)
            for _ in range(count):
                child = ET.SubElement(parent, key[:-1])
                if key == "Tracks":
                    ET.SubElement(child, "Name").text = "Guitar"
        with zipfile.ZipFile(self.source, "w") as archive:
            archive.writestr("VERSION", "7.0")
            archive.writestr("Content/score.gpif", ET.tostring(gpif))
            archive.writestr("Content/BinaryStylesheet", b"\x00\x01\x02")
    def tearDown(self):
        self.temp.cleanup()
    def test_inspection(self):
        info = inspect_gp(self.source)
        self.assertEqual(info["notes"], 12)
        self.assertEqual(info["tracks"], 2)
        self.assertEqual(info["master_bars"], 3)
    def test_roundtrip(self):
        result = roundtrip_gp(self.source, self.root / "output.gp")
        self.assertTrue(result["all_members_identical"])
        self.assertEqual(result["source"]["notes"], 12)
    def test_reject_same_path(self):
        with self.assertRaises(ValueError):
            roundtrip_gp(self.source, self.source)
    def test_reject_wrong_version(self):
        bad = self.root / "bad.gp"
        with zipfile.ZipFile(bad, "w") as archive:
            archive.writestr("VERSION", "5.0")
            archive.writestr("Content/score.gpif", b"<GPIF />")
        with self.assertRaises(GPFormatError):
            inspect_gp(bad)

if __name__ == "__main__":
    unittest.main()
