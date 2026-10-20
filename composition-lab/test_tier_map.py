"""Validate the authored data catalog, not GP extraction or musical quality."""
import importlib.util
import json
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).parent / "examples"
spec = importlib.util.spec_from_file_location("tier_map_fixture", ROOT / "build_tier_map.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class TierMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = M.build()

    def test_catalog_is_reproducible_and_varied(self):
        self.assertEqual(self.data, json.loads((ROOT / "tier-map.examples.json").read_text(encoding="utf-8")))
        cases = self.data["cases"]
        self.assertEqual(len({c["id"] for c in cases}), 39)
        self.assertEqual({c["group"] for c in cases}, {"A/B", "Techniques", "Chords", "Modes", "Progressions", "Melodies"})
        for group in {c["group"] for c in cases}:
            signatures = {json.dumps(c["records"], sort_keys=True) for c in cases if c["group"] == group}
            self.assertGreater(len(signatures), 1)

    def test_inputs_are_adjacent_and_time_is_exact(self):
        for c in self.data["cases"]:
            records = c["records"]
            for id, r in records.items():
                with self.subTest(case=c["id"], record=id):
                    for input_id in r["inputs"]:
                        self.assertIn(input_id, records)
                        self.assertEqual(records[input_id]["tier"], r["tier"] - 1)
                    if r["time"]:
                        start, duration = map(Fraction, (r["time"]["start_q"], r["time"]["duration_q"]))
                        self.assertGreaterEqual(start, 0)
                        self.assertGreater(duration, 0)
                        self.assertLessEqual(start + duration, Fraction(c["duration_q"]))
            for channel in ("melody", "harmony"):
                slots = sorted({(Fraction(r["time"]["start_q"]), Fraction(r["time"]["duration_q"])) for r in records.values() if r["tier"] == 1 and r["channel"] == channel and r["time"]})
                self.assertEqual(sum(d for _, d in slots), 8)
                self.assertEqual([s + d for s, d in slots[:-1]], [s for s, _ in slots[1:]])

    def test_pitch_coordinates_and_source_fingering(self):
        for c in self.data["cases"]:
            records = c["records"]
            for r in records.values():
                if r["kind"] == "note":
                    raw = records[r["inputs"][0]]
                    self.assertEqual(M.TUNING[raw["string"] - 1] + raw["fret"], r["pitch_midi"])
                    self.assertEqual(r["letter_octave"], M.name(r["pitch_midi"]))
                    self.assertEqual(raw["techniques"], r["techniques"])
                if r["kind"] == "note_relations":
                    pitch = records[r["note_ref"]]["pitch_midi"]
                    for field in ("interval_of_note_base_key", "interval_of_note_current_chord_mode"):
                        v = r[field]
                        self.assertEqual(v["reference_midi"] + v["signed_semitones"], pitch)
                        self.assertEqual(v["relative_octave"] * 12 + v["semitones_mod12"], v["signed_semitones"])
                        if v["mode_degree"]:
                            self.assertEqual(M.MODES[v["mode"]][v["mode_degree"] - 1], v["semitones_mod12"])

    def test_chord_members_match_declared_shapes(self):
        for c in self.data["cases"]:
            for r in c["records"].values():
                if r["kind"] != "chord":
                    continue
                pitches = [c["records"][id]["pitch_midi"] for id in r["members"]]
                self.assertEqual(pitches, r["pitch_members"])
                self.assertEqual([p - r["root_midi"] for p in pitches], M.CHORDS[r["quality"]])
                self.assertEqual(len({c["records"][id]["string"] for id in r["members"]}), len(pitches))
                if r["mode_status"] == "unknown":
                    self.assertIsNone(r["mode"])

    def test_technique_endpoints_and_rest_slots(self):
        cases = {c["id"]: c["records"] for c in self.data["cases"]}
        for kind, direction in (("hammer", 1), ("pull", -1), ("slide", 1)):
            r = cases["tech_" + kind]
            a, b = r["n0_1"], r["n1_1"]
            self.assertEqual(a["string"], b["string"])
            self.assertGreater((b["fret"] - a["fret"]) * direction, 0)
            self.assertEqual(a["techniques"][kind]["destination_index"], 1)
        tie = cases["tech_tie"]
        self.assertEqual(tie["n0_1"]["pitch_midi"], tie["n1_1"]["pitch_midi"])
        self.assertFalse(tie["n1_1"]["attack"])
        self.assertIsNone(cases["tech_vibrato"]["n2_1"]["techniques"]["vibrato"]["depth_semitones"])
        self.assertIsNone(cases["rest"]["def0"]["relative_pitches"][3])
        self.assertEqual(cases["rest"]["n3_1"]["kind"], "rest")


if __name__ == "__main__":
    unittest.main()
