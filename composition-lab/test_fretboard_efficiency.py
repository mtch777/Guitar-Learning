"""Adversarial, source-backed tests of the Drop E fingering contract."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import importlib
import json
from pathlib import Path
import unittest

from check_fretboard_efficiency import (
    EXPECTED_SOURCES, ROOT, ValidationError, maximum_open_attacks,
    read_midi_source, validate_dataset, validate_string_export, validate_version,
)


def note(note_id, pitch, start=0, end=960, velocity=90):
    return {"id": note_id, "pitch": pitch, "start_tick": start,
            "end_tick": end, "velocity": velocity, "channel": 0}


def artificial_version(notes, contacts, anchors):
    """Build only a declared assignment; the independent oracle judges it."""
    return {
        "assignments": [dict(note_id=n["id"], string_number=c[0], fret=c[1])
                        for n, c in zip(notes, contacts)],
        "positions": [
            {"time_seconds": t / 1920, "position": p,
             "attack_note_ids": [n["id"] for n in notes if n["start_tick"] == t],
             "active_note_ids": [n["id"] for n in notes if n["start_tick"] <= t < n["end_tick"]],
             "shape_labels": []}
            for t, p in zip(sorted({n["start_tick"] for n in notes}), anchors)
        ],
        "metrics": {},
    }


class IndependentOracleTests(unittest.TestCase):
    def test_duplicate_pitch_is_two_occurrences_and_one_open(self):
        notes = [note("a", 59), note("b", 59)]
        good = artificial_version(notes, [(2, 0), (3, 4)], [1])
        self.assertEqual(validate_version(notes, good, check_metrics=False)["open_note_count"], 1)
        self.assertEqual(maximum_open_attacks(notes), 1)
        bad = artificial_version(notes, [(2, 0), (2, 0)], [1])
        with self.assertRaisesRegex(ValidationError, "Overlapping"):
            validate_version(notes, bad, check_metrics=False)
        missing = deepcopy(good)
        missing["assignments"].pop()
        with self.assertRaisesRegex(ValidationError, "Missing or added"):
            validate_version(notes, missing, check_metrics=False)

    def test_octave_substitution_cannot_pass_as_open(self):
        notes = [note(1, 76)]
        bad = artificial_version(notes, [(1, 0)], [1])
        with self.assertRaisesRegex(ValidationError, "Pitch/octave"):
            validate_version(notes, bad, check_metrics=False)

    def test_overlap_is_checked_between_attacks(self):
        notes = [note("held", 64, 0, 1920), note("new", 66, 960, 1920)]
        bad = artificial_version(notes, [(1, 0), (1, 2)], [1, 1])
        with self.assertRaisesRegex(ValidationError, "Overlapping"):
            validate_version(notes, bad, check_metrics=False)
        good = artificial_version(notes, [(1, 0), (2, 7)], [1, 3])
        checked = validate_version(notes, good, check_metrics=False)
        self.assertEqual(checked["max_simultaneous_notes"], 2)

    def test_open_oracle_keeps_held_contacts_across_later_attacks(self):
        # E6 has only the highest string. Its overlap forces the preceding E4
        # off its open string; counting each onset independently would return1.
        held = [note("held-e4", 64, 0, 1920), note("later-e6", 88, 960, 1920)]
        self.assertEqual(maximum_open_attacks(held), 0)
        released = deepcopy(held)
        released[0]["end_tick"] = 960
        self.assertEqual(maximum_open_attacks(released), 1)
        with self.assertRaisesRegex(ValidationError, "Unplayable overlap"):
            maximum_open_attacks([note("held-e1", 28, 0, 1920),
                                  note("later-f1", 29, 960, 1920)])

    def test_same_tick_release_and_retrigger_do_not_overlap(self):
        notes = [note(1, 28, 0, 960), note(2, 28, 960, 1920)]
        good = artificial_version(notes, [(8, 0), (8, 0)], [1, 1])
        self.assertEqual(validate_version(notes, good, check_metrics=False)["open_note_count"], 2)

    def test_held_notes_constrain_hand_span(self):
        notes = [note(1, 29, 0, 1920), note(2, 71, 960, 1920)]
        bad = artificial_version(notes, [(8, 1), (1, 7)], [1, 3])
        with self.assertRaisesRegex(ValidationError, "Fretted span"):
            validate_version(notes, bad, check_metrics=False)

    def test_forged_window_and_metrics_are_rejected(self):
        notes = [note(1, 71)]
        bad = artificial_version(notes, [(1, 7)], [1])
        with self.assertRaisesRegex(ValidationError, "window"):
            validate_version(notes, bad, check_metrics=False)
        good = artificial_version(notes, [(1, 7)], [3])
        good["metrics"] = {"hand_travel_frets": 999, "rapid_shift_count": 0, "rapid_shift_cost": 0}
        with self.assertRaisesRegex(ValidationError, "hand_travel_frets"):
            validate_version(notes, good)

    def test_open_frame_cannot_hide_a_shift(self):
        notes = [note(1, 29, 0, 240), note(2, 28, 240, 480), note(3, 76, 480, 720)]
        bad = artificial_version(notes, [(8, 1), (8, 0), (1, 12)], [1, 8, 8])
        with self.assertRaisesRegex(ValidationError, "Open-only"):
            validate_version(notes, bad, check_metrics=False)
        hidden = artificial_version(notes, [(8, 1), (8, 0), (1, 12)], [1, None, 8])
        with self.assertRaisesRegex(ValidationError, "unestablished"):
            validate_version(notes, hidden, check_metrics=False)
        good = artificial_version(notes, [(8, 1), (8, 0), (1, 12)], [1, 1, 8])
        checked = validate_version(notes, good, check_metrics=False)
        self.assertEqual(checked["hand_travel_frets"], 7)
        self.assertEqual(checked["rapid_shift_count"], 1)
        # Released gap 0.125s + transition allowance 0.125s: excess=7-8*0.25=5.
        self.assertEqual(checked["rapid_shift_cost"], 100000)

    def test_sustained_grip_is_not_free_travel_time(self):
        held = [note(1, 31, 0, 3840), note(2, 38, 0, 3840),
                note(3, 43, 0, 3840), note(4, 83, 3840, 4080)]
        contacts = [(8, 3), (7, 3), (6, 3), (1, 19)]
        long = artificial_version(held, contacts, [3, 15])
        long_metrics = validate_version(held, long, check_metrics=False)
        self.assertEqual(long_metrics["rapid_shift_count"], 1)
        # No released gap; 12-fret jump with only0.125s allowance: excess11.
        self.assertEqual(long_metrics["rapid_shift_cost"], 968000)
        released = deepcopy(held)
        for n in released[:3]:
            n["end_tick"] = 480
        short = artificial_version(released, contacts, [3, 15])
        short_metrics = validate_version(released, short, check_metrics=False)
        self.assertEqual(short_metrics["rapid_shift_count"], 0)
        self.assertEqual(short_metrics["rapid_shift_cost"], 0)


class MapperContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.mapper = importlib.import_module("fretboard_efficiency")
        except ModuleNotFoundError as exc:
            if exc.name == "fretboard_efficiency":
                raise unittest.SkipTest("Mapper implementation has not arrived")
            raise

    def checked(self, notes, **kwargs):
        before = deepcopy(notes)
        version = self.mapper.optimize_fingering(notes, **kwargs)
        self.assertEqual(notes, before, "Mapper mutated the original MIDI notes")
        metrics = validate_version(notes, version, **kwargs)
        return version, metrics

    def test_duplicate_b3_preserved_on_two_strings(self):
        notes = [note("copy-one", 59), note("copy-two", 59)]
        result, metrics = self.checked(notes)
        self.assertEqual(len(result["assignments"]), 2)
        self.assertEqual(metrics["open_note_count"], 1)

    def test_exact_open_octaves_and_high_e_fretted(self):
        notes = [note(1, 28, 0, 240), note(2, 64, 240, 480), note(3, 76, 480, 720)]
        version, metrics = self.checked(notes)
        contacts = {a["note_id"]: (a["string_number"], a["fret"]) for a in version["assignments"]}
        self.assertEqual(contacts[1], (8, 0))
        self.assertEqual(contacts[2], (1, 0))
        self.assertGreater(contacts[3][1], 0)
        self.assertEqual(metrics["open_note_count"], 2)

    def test_held_open_string_remains_reserved(self):
        notes = [note("held", 64, 0, 1920), note("later", 66, 960, 1920)]
        version, _ = self.checked(notes)
        contacts = {a["note_id"]: (a["string_number"], a["fret"]) for a in version["assignments"]}
        self.assertEqual(contacts["held"], (1, 0))
        self.assertNotEqual(contacts["later"][0], 1)

    def test_impossible_overlap_is_explicit_and_atomic(self):
        notes = [note("held", 28, 0, 1920), note("later", 29, 960, 1920)]
        before = deepcopy(notes)
        with self.assertRaises(ValueError):
            self.mapper.optimize_fingering(notes)
        self.assertEqual(notes, before)

    def test_future_overlap_can_require_an_open_string_exception(self):
        # E6 needs the highest string. An earlier held E4 can therefore NOT use
        # its otherwise available open string. Within span four, both can be
        # preserved at fret24 on strings6 and1. Greedy open pruning would falsely
        # reject this physically feasible sequence.
        notes = [note("held-e4", 64, 0, 1920), note("later-e6", 88, 960, 1920)]
        version, metrics = self.checked(notes)
        contacts = {a["note_id"]: (a["string_number"], a["fret"]) for a in version["assignments"]}
        self.assertEqual(contacts["held-e4"], (6, 24))
        self.assertEqual(contacts["later-e6"], (1, 24))
        self.assertEqual(metrics["open_note_count"], 0)

    def test_release_and_reattack_same_tick(self):
        _, metrics = self.checked([note(1, 28, 0, 240), note(2, 28, 240, 480)])
        self.assertEqual(metrics["open_note_count"], 2)

    def test_out_of_range_is_explicit(self):
        for pitch in (27, 89):
            with self.subTest(pitch=pitch), self.assertRaises(ValueError):
                self.mapper.optimize_fingering([note(1, pitch)])

    def test_phrase_lookahead_finds_available_zero_shift_route(self):
        notes = [note("a", 71, 0, 480), note("b", 72, 0, 480),
                 note("c", 76, 480, 960), note("d", 83, 480, 960),
                 note("e", 71, 960, 1440), note("f", 72, 960, 1440)]
        _, metrics = self.checked(notes)
        self.assertEqual(metrics["hand_travel_frets"], 0)
        self.assertEqual(metrics["rapid_shift_count"], 0)
        baseline = self.mapper.greedy_fingering(notes)
        baseline_metrics = validate_version(notes, baseline)
        self.assertGreater(baseline_metrics["hand_travel_frets"], 0)

    def test_sustained_low_chord_does_not_hide_a_rapid_high_shift(self):
        held = [note(1, 31, 0, 3840), note(2, 38, 0, 3840),
                note(3, 43, 0, 3840), note(4, 83, 3840, 4080)]
        _, held_metrics = self.checked(held)
        self.assertGreater(held_metrics["rapid_shift_cost"], 0)
        self.assertEqual(held_metrics["rapid_shift_count"], 1)
        released = deepcopy(held)
        for n in released[:3]:
            n["end_tick"] = 480
        _, released_metrics = self.checked(released)
        self.assertLess(released_metrics["rapid_shift_cost"], held_metrics["rapid_shift_cost"])
        self.assertEqual(released_metrics["rapid_shift_count"], 0)

    def test_tier_one_open_choice_survives_a_motion_incentive(self):
        notes = [note(1, 71, 0, 240), note(2, 64, 240, 480), note(3, 72, 480, 720)]
        version, _ = self.checked(notes)
        middle = next(a for a in version["assignments"] if a["note_id"] == 2)
        self.assertEqual((middle["string_number"], middle["fret"]), (1, 0))


class SourceFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_dir = ROOT / "tests/fixtures/fretboard-efficiency"
        cls.dataset_path = ROOT / "public/data/fretboard-efficiency-fixtures.json"
        if not cls.dataset_path.exists() or not all((cls.source_dir / f).exists() for f in EXPECTED_SOURCES):
            raise unittest.SkipTest("Frozen source fixtures and generated comparison have not arrived")

    def test_all_outputs_against_raw_midi_and_independent_metrics(self):
        result = validate_dataset(json.loads(self.dataset_path.read_text()), self.source_dir)
        self.assertTrue(result["passed"])
        self.assertEqual(sum(f["raw_notes_preserved"] for f in result["fixtures"]), 596)
        self.assertEqual({f["fixture"]: f["raw_notes_preserved"] for f in result["fixtures"]},
                         {"cfa029a2": 164, "da80eca9": 191, "c5a35486": 241})

    def test_duplicate_high_chords_remain_four_occurrences(self):
        for filename, expected in EXPECTED_SOURCES.items():
            if "duplicate_chord_ticks" not in expected:
                continue
            with self.subTest(source=filename):
                raw = read_midi_source(self.source_dir / filename)
                for tick in expected["duplicate_chord_ticks"]:
                    pitches = sorted(n["pitch"] for n in raw["notes"] if n["start_tick"] == tick)
                    self.assertEqual(pitches, [59, 59, 62, 69])

    def test_uploaded_rewrite_frozen_clock_dynamics_and_holds(self):
        # The lesson keeps its stable C ID while adopting the user's replacement.
        # The original source remains byte-identical as historical evidence.
        historical = read_midi_source(self.source_dir / "2026-11-15_midi_rewrite.mid")
        self.assertEqual(historical["sha256"],
                         "c5a35486923e3b819d9f7cb7176cb1c39546c26471093862e5e67c27fbe46461")
        raw = read_midi_source(self.source_dir / "2026-11-15_midi_rewrite_2.mid")
        self.assertEqual(raw["sha256"], EXPECTED_SOURCES["2026-11-15_midi_rewrite_2.mid"]["sha256"])
        self.assertEqual((raw["format"], raw["track_count"], raw["ticks_per_beat"]), (0, 1, 96))
        self.assertEqual(raw["tempo_events"], [])
        self.assertEqual((raw["tempo_bpm"], raw["duration_ticks"], raw["duration_seconds"]),
                         (120, 4608, 24))
        notes = raw["notes"]
        self.assertEqual(len(notes), 241)
        self.assertEqual(Counter(n["velocity"] for n in notes), Counter({90: 217, 74: 24}))
        self.assertEqual({n["channel"] for n in notes}, {0})
        self.assertEqual((min(n["pitch"] for n in notes), max(n["pitch"] for n in notes)), (28, 83))
        self.assertEqual(max(n["end_tick"] for n in notes), 4608)
        onsets = sorted({n["start_tick"] for n in notes})
        self.assertEqual(len(onsets), 172)
        self.assertEqual(sum(any(n["start_tick"] < t < n["end_tick"] for n in notes)
                             for t in onsets), 14)
        self.assertEqual(maximum_open_attacks(notes), 132)
        self.assertEqual([(n["pitch"], n["start_tick"], n["end_tick"])
                          for n in notes[2:6]],
                         [(28, 48, 120), (35, 48, 120), (28, 120, 144), (35, 120, 144)])
        self.assertEqual([(n["pitch"], n["start_tick"], n["end_tick"])
                          for n in notes if n["id"] in (29, 30, 31)],
                         [(60, 672, 696), (76, 684, 720), (83, 696, 720)])
        self.assertEqual([(n["pitch"], n["start_tick"], n["end_tick"])
                          for n in notes[-6:]],
                         [(60, 4512, 4524), (69, 4524, 4536), (83, 4536, 4560),
                          (60, 4560, 4572), (69, 4572, 4584), (83, 4584, 4608)])

    def test_uploaded_rewrite_tick_resolution_and_end_of_track_are_locked(self):
        original = json.loads(self.dataset_path.read_text())
        for field, value, message in (("ticks_per_beat", 960, "tick resolution"),
                                      ("duration_ticks", 4607, "end-of-track")):
            data = deepcopy(original)
            fixture = next(f for f in data["fixtures"] if f["id"] == "c5a35486")
            fixture[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValidationError, message):
                validate_dataset(data, self.source_dir)

    def test_uploaded_rewrite_soft_note_velocity_cannot_be_flattened(self):
        data = json.loads(self.dataset_path.read_text())
        fixture = next(f for f in data["fixtures"] if f["id"] == "c5a35486")
        next(n for n in fixture["notes"] if n["velocity"] == 74)["velocity"] = 90
        with self.assertRaisesRegex(ValidationError, "raw MIDI occurrence"):
            validate_dataset(data, self.source_dir)

    def test_uploaded_rewrite_held_overlap_cannot_share_a_string(self):
        data = json.loads(self.dataset_path.read_text())
        fixture = next(f for f in data["fixtures"] if f["id"] == "c5a35486")
        version = next(v for v in fixture["versions"] if v["id"] == "optimized")
        # Both contacts individually preserve pitch and fret range, but their
        # actual12-tick overlap makes the common physical string impossible.
        for assignment in version["assignments"]:
            if assignment["note_id"] in (29, 30):
                assignment["string_number"] = 2
                assignment["fret"] = 1 if assignment["note_id"] == 29 else 17
        with self.assertRaisesRegex(ValidationError, "Overlapping"):
            validate_version(fixture["notes"], version, ticks_per_beat=96)

    def test_source_clock_tampering_is_detected(self):
        data = json.loads(self.dataset_path.read_text())
        data["fixtures"][0]["notes"][0]["end_tick"] -= 1
        with self.assertRaisesRegex(ValidationError, "raw MIDI occurrence"):
            validate_dataset(data, self.source_dir)

    def test_source_duplicate_deletion_is_detected(self):
        data = json.loads(self.dataset_path.read_text())
        notes = data["fixtures"][0]["notes"]
        index = next(i for i, n in enumerate(notes) if n["pitch"] == 59 and n["start_tick"] == 3840)
        notes.pop(index)
        with self.assertRaisesRegex(ValidationError, "raw MIDI occurrence"):
            validate_dataset(data, self.source_dir)

    def test_false_source_hash_is_detected(self):
        data = json.loads(self.dataset_path.read_text())
        data["fixtures"][0]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "SHA-256"):
            validate_dataset(data, self.source_dir)

    def test_string_export_channels_must_match_the_actual_contacts(self):
        data = json.loads(self.dataset_path.read_text())
        fixture = data["fixtures"][0]
        version = next(v for v in fixture["versions"] if v["id"] == "optimized")
        contact = version["assignments"][0]
        contact["string_number"] = contact["string_number"] % 8 + 1
        with self.assertRaisesRegex(ValidationError, "assigned string channels"):
            validate_string_export(fixture, version, ROOT / "public" / version["midi_path"])


if __name__ == "__main__":
    unittest.main()
