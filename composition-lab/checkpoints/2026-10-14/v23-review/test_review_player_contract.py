"""Dependency-free regression checks for the V23 review-player template.

Run: python -m unittest composition-lab/checkpoints/2026-10-14/v23-review/test_review_player_contract.py
Or: python composition-lab/checkpoints/2026-10-14/v23-review/test_review_player_contract.py
These are static contract checks, NOT browser/audio verification.
"""
from html.parser import HTMLParser
from pathlib import Path
import unittest

TEMPLATE = Path(__file__).with_name("player_template.html")

class _Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])

class ReviewPlayerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = TEMPLATE.read_text(encoding="utf-8")
        parser = _Elements()
        parser.feed(cls.html)
        cls.ids = parser.ids

    def test_payload_injection_marker(self):
        self.assertEqual(self.html.count("/*__PAYLOAD__*/"), 1)

    def test_review_controls_present(self):
        expected = {
            "prev", "next", "progress", "play", "stop", "replay",
            "bpm", "context", "piano", "chord", "confidence",
            "boundary", "notes", "save", "saveNext", "saveStatus",
            "reveal", "prediction", "export", "reset", "metrics"
        }
        self.assertFalse(expected - self.ids, f"Missing IDs: {expected - self.ids}")

    def test_event_handlers_present(self):
        for control in ("prev", "next", "play", "stop", "replay",
                        "save", "saveNext", "reveal", "export", "reset"):
            with self.subTest(control=control):
                self.assertIn(f"$('{control}').onclick=", self.html)

    def test_listener_reference_chord_controls(self):
        for control in ("refRoot", "refQuality", "refPlay", "refStop", "refUse"):
            with self.subTest(control=control):
                self.assertIn(control, self.ids)
        self.assertIn("function playReference()", self.html)
        self.assertIn("function stopReference()", self.html)
        self.assertIn("function referenceName()", self.html)

    def test_chromatic_piano_and_note_audition(self):
        self.assertIn("const PIANO_KEYS=48,NOTE_ROW=17", self.html)
        self.assertIn("function auditionPitch(p)", self.html)
        self.assertIn("pianoKeyboard.push(", self.html)
        self.assertIn("pianoHits.push(", self.html)
        self.assertIn("addEventListener('click'", self.html)
        self.assertIn("for(const hit of pianoHits)", self.html)

    def test_export_columns_come_from_review_schema(self):
        self.assertIn("DATA.fields.map(cells)", self.html)
        self.assertIn("human_chord_label", self.html)
        self.assertIn("human_phrase_boundary", self.html)

    def test_local_persistence_and_blind_reveal(self):
        self.assertIn("localStorage.setItem(", self.html)
        self.assertIn("localStorage.getItem(", self.html)
        self.assertIn("$('prediction').hidden=true", self.html)

if __name__ == "__main__":
    unittest.main()
