"""Behavioral checks on original synthetic material, not accuracy estimates."""

from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import unittest

from tonal_analysis.engine import MODES, analyze, chord_candidates
from tonal_analysis.examples import duplicate_track, example_scores, transpose


def _inventory(score):
    return {e["midi"] % 12 for e in score["events"] if e["eligible"] and e["midi"] is not None}


def _scores(result):
    return {(c["tonic"], c["mode"]): c["score"] for c in result["candidates"]}


def _small_score(specifications, bars=2):
    """Build minimal edge-case material from explicit pitch/time observations."""
    score = deepcopy(example_scores()["silence"])
    score["source"]["name"] = "synthetic_edge_case"
    score["bars"] = [
        {"bar": i + 1, "start_q": str(4 * i), "duration_q": "4",
         "signature": [4, 4], "section": "A"}
        for i in range(bars)
    ]
    template = example_scores()["c_major_cadences"]["events"][0]
    for i, specification in enumerate(specifications):
        event = deepcopy(template)
        event.update(id=f"edge:{i}", track_id="melody", midi=60,
                     onset_q="0", duration_q="1", bar=1, beat=0, note=i,
                     accent=False, raw_note={}, raw_beat={}, tie=False)
        event.update(specification)
        event["bar"] = int(Fraction(event["onset_q"]) // 4) + 1
        event["beat"] = int(Fraction(event["onset_q"]) % 4)
        score["events"].append(event)
    score["coverage"] = {
        "source_note_occurrences": len(score["events"]),
        "retained_note_occurrences": len(score["events"]),
        "eligible_note_occurrences": sum(e["eligible"] for e in score["events"]),
    }
    return score


class TonalBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.examples = example_scores()

    def test_examples_are_independent_and_source_occurrences_unique(self):
        for name, score in self.examples.items():
            with self.subTest(name=name):
                self.assertEqual(score["source"]["kind"], "original_synthetic")
                ids = [e["id"] for e in score["events"]]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(all(Fraction(e["duration_q"]) > 0 for e in score["events"]))
        self.examples["c_major_cadences"]["events"][0]["midi"] = 1
        self.assertNotEqual(example_scores()["c_major_cadences"]["events"][0]["midi"], 1)

    def test_clear_cadences_have_the_intended_center(self):
        for name, tonic in [("c_major_cadences", 0), ("a_minor_leading_tone", 9)]:
            with self.subTest(name=name):
                result = analyze(self.examples[name])["global"]
                self.assertEqual(result["centers"][0]["tonic"], tonic)
                self.assertEqual(result["candidates"][0]["tonic"], tonic)

    def test_shared_pitch_collection_does_not_force_same_tonic(self):
        major = self.examples["c_major_cadences"]
        dorian = self.examples["d_dorian"]
        self.assertEqual(_inventory(major), _inventory(dorian))
        major_result, dorian_result = analyze(major)["global"], analyze(dorian)["global"]
        self.assertEqual(major_result["centers"][0]["tonic"], 0)
        self.assertEqual(dorian_result["centers"][0]["tonic"], 2)
        self.assertEqual(dorian_result["candidates"][0]["mode"], "dorian")

    def test_all_twelve_transpositions_preserve_ranked_evidence(self):
        # Compare all candidate scores rather than tonic-name tie-breaking order.
        for name in ("c_major_cadences", "a_minor_leading_tone", "d_dorian"):
            score = self.examples[name]
            original = analyze(score, top=12 * len(MODES))["global"]
            baseline = _scores(original)
            for shift in range(12):
                with self.subTest(name=name, shift=shift):
                    changed = analyze(transpose(score, shift), top=12 * len(MODES))["global"]
                    self.assertEqual(changed["centers"][0]["tonic"],
                                     (original["centers"][0]["tonic"] + shift) % 12)
                    shifted_scores = _scores(changed)
                    self.assertEqual(len(baseline), len(shifted_scores))
                    for (tonic, mode), value in baseline.items():
                        self.assertAlmostEqual(value, shifted_scores[((tonic + shift) % 12, mode)], places=8)

    def test_duplicate_track_preserves_all_candidate_scores(self):
        for name in ("c_major_cadences", "d_dorian"):
            score = self.examples[name]
            baseline = analyze(score, top=12 * len(MODES))["global"]
            for track in ("bass", "harmony", "melody"):
                with self.subTest(name=name, track=track):
                    result = analyze(duplicate_track(score, track), top=12 * len(MODES))["global"]
                    self.assertEqual(result["centers"][0]["tonic"], baseline["centers"][0]["tonic"])
                    self.assertEqual(result["candidates"][0]["mode"], baseline["candidates"][0]["mode"])
                    self.assertEqual(_scores(result), _scores(baseline))

    def test_power_chord_does_not_invent_a_third_or_unique_mode(self):
        result = analyze(self.examples["ambiguous_power_chord"], top=12 * len(MODES))["global"]
        self.assertIsNone(result["mode"])
        self.assertEqual(result["centers"][0]["tonic"], 4)
        self.assertGreater(len({c["mode"] for c in result["candidates"] if c["tonic"] == 4}), 1)
        candidates = chord_candidates([4, 11], bass=4)
        self.assertFalse(any(c["quality"] in ("major", "minor") for c in candidates))

    def test_silence_and_unpitched_events_do_not_invent_key(self):
        for name in ("silence", "percussion_only"):
            with self.subTest(name=name):
                result = analyze(self.examples[name])["global"]
                self.assertIsNone(result["center"])
                self.assertIsNone(result["mode"])
                self.assertEqual(result["candidates"], [])

    def test_minor_raised_leading_tone_is_not_forced_into_major(self):
        result = analyze(self.examples["a_minor_leading_tone"])["global"]
        self.assertEqual(result["candidates"][0]["tonic"], 9)
        self.assertIn(result["candidates"][0]["mode"],
                      {"harmonic_minor", "harmonic minor", "minor", "aeolian"})

    def test_brief_chromatic_passing_note_keeps_structural_center(self):
        plain = self.examples["c_major_cadences"]
        passing = self.examples["c_major_chromatic_passing"]
        self.assertEqual(_inventory(passing) - _inventory(plain), {6})
        result = analyze(passing)["global"]
        self.assertEqual(result["centers"][0]["tonic"], 0)

    def test_frequent_dominant_pedal_is_not_automatically_the_tonic(self):
        score = self.examples["a_minor_dominant_pedal"]
        attacks = Counter(e["midi"] % 12 for e in score["events"] if e["eligible"] and e["attack"])
        self.assertEqual(attacks.most_common(1)[0][0], 4)
        result = analyze(score)["global"]
        # The sustained E pedal must not erase the recurring E7-Am upper harmony.
        self.assertEqual(result["centers"][0]["tonic"], 9)

    def test_section_and_window_analysis_detects_transposed_return(self):
        report = analyze(self.examples["c_to_d_sections"], window_bars=4)
        section_tonics = [r["centers"][0]["tonic"] for r in report["sections"] if r["centers"]]
        self.assertEqual(section_tonics, [0, 2])
        window_tonics = [r["centers"][0]["tonic"] for r in report["windows"] if r["centers"]]
        self.assertEqual(window_tonics[0], 0)
        self.assertEqual(window_tonics[-1], 2)

    def test_source_is_immutable_and_report_is_json_serializable(self):
        score = self.examples["c_major_cadences"]
        saved = deepcopy(score)
        report = analyze(score)
        self.assertEqual(saved, score)
        encoded = json.dumps(report, allow_nan=False)
        self.assertTrue(encoded)
        self.assertIn("limitations", report)

    def test_tied_segmentation_preserves_all_candidate_scores(self):
        score = self.examples["c_major_cadences"]
        divided = deepcopy(score)
        divided["events"] = []
        for event in score["events"]:
            if event["track_id"] == "melody":
                divided["events"].append(deepcopy(event))
                continue
            first, second = deepcopy(event), deepcopy(event)
            half = Fraction(event["duration_q"]) / 2
            first["duration_q"] = str(half)
            second.update(id=event["id"] + ":tie", onset_q=str(Fraction(event["onset_q"]) + half),
                          duration_q=str(half), attack=False, tie=True, accent=False)
            divided["events"].extend([first, second])
        divided["coverage"] = {
            "source_note_occurrences": len(divided["events"]),
            "retained_note_occurrences": len(divided["events"]),
            "eligible_note_occurrences": len(divided["events"]),
        }
        before = analyze(score, top=12 * len(MODES))["global"]
        after = analyze(divided, top=12 * len(MODES))["global"]
        self.assertEqual(before["centers"][0]["tonic"], after["centers"][0]["tonic"])
        self.assertEqual(before["candidates"][0]["mode"], after["candidates"][0]["mode"])
        self.assertEqual(_scores(before), _scores(after))

    def test_window_edges_do_not_create_attacks_or_voice_endings(self):
        score = _small_score([
            dict(midi=pitch, onset_q="2", duration_q="8") for pitch in (60, 64, 67)
        ], bars=3)
        report = analyze(score, window_bars=1)
        first, middle, last = report["windows"]
        self.assertEqual(first["evidence"]["attack_positions"], 1)
        self.assertEqual(first["evidence"]["arrivals"], [])
        self.assertEqual(middle["evidence"]["attack_positions"], 0)
        self.assertEqual(sum(middle["evidence"]["channels"]["attacks"]), 0)
        self.assertEqual(sum(middle["evidence"]["channels"]["metric"]), 0)
        self.assertEqual(middle["evidence"]["arrivals"], [])
        self.assertEqual(last["evidence"]["attack_positions"], 0)
        self.assertTrue(all(a["at_q"] == "10" for a in last["evidence"]["arrivals"]))

    def test_every_window_chord_witness_covers_the_reported_cell(self):
        # Identical pitch sets are reattacked each bar. Their source witnesses
        # cannot be unioned across time and then copied into every window.
        score = _small_score([
            dict(midi=pitch, onset_q=str(4 * bar), duration_q="4")
            for bar in range(3) for pitch in (60, 64, 67)
        ], bars=3)
        by_id = {event["id"]: event for event in score["events"]}
        report = analyze(score, window_bars=1)
        for window in report["windows"]:
            for cell in window["evidence"]["chords"]:
                left, right = Fraction(cell["clipped_start_q"]), Fraction(cell["clipped_end_q"])
                for ref in cell["note_refs"]:
                    event = by_id[ref]
                    onset = Fraction(event["onset_q"])
                    end = onset + Fraction(event["duration_q"])
                    self.assertLessEqual(onset, left)
                    self.assertGreaterEqual(end, right)

    def test_sequential_chord_tones_are_not_a_simultaneous_chord(self):
        score = _small_score([
            dict(midi=60, onset_q="0", duration_q="1"),
            dict(midi=64, onset_q="1", duration_q="1"),
            dict(midi=67, onset_q="2", duration_q="1"),
        ], bars=1)
        result = analyze(score)["global"]
        self.assertEqual(result["evidence"]["pitch_classes"], [0, 4, 7])
        self.assertTrue(all(len(cell["pitch_classes"]) == 1 for cell in result["evidence"]["chords"]))
        self.assertTrue(all(not cell["candidates"] for cell in result["evidence"]["chords"]))
        self.assertEqual(result["evidence"]["matched_chord_duration_q"], "0")

    def test_excluded_bend_is_not_a_rest_or_a_voice_ending(self):
        bend = dict(midi=62, onset_q="1", duration_q="2", eligible=False, attack=False,
                    exclusions=["unresolved_bend"], raw_note={"bend": {"tone": 50}})
        for trailing in (False, True):
            rows = [dict(midi=60, onset_q="0", duration_q="1"), bend]
            if not trailing:
                rows.append(dict(midi=64, onset_q="3", duration_q="1"))
            with self.subTest(trailing=trailing):
                result = analyze(_small_score(rows, bars=1))["global"]
                false_arrivals = [a for a in result["evidence"]["arrivals"] if a["at_q"] == "1"]
                self.assertEqual(false_arrivals, [])
                self.assertEqual(result["evidence"]["melodic_transitions"], [])

    def test_excluded_pitched_overlap_makes_chord_identity_incomplete(self):
        rows = [dict(midi=p, onset_q="0", duration_q="4") for p in (60, 64, 67)]
        rows.append(dict(track_id="harmony", midi=62, onset_q="1", duration_q="2",
                         eligible=False, attack=False, exclusions=["unresolved_bend"],
                         raw_note={"bend": {"tone": 50}}))
        result = analyze(_small_score(rows, bars=1))["global"]
        cells = result["evidence"]["chords"]
        during = [c for c in cells if Fraction(c["clipped_start_q"]) < 3 and Fraction(c["clipped_end_q"]) > 1]
        outside = [c for c in cells if Fraction(c["clipped_end_q"]) <= 1 or Fraction(c["clipped_start_q"]) >= 3]
        self.assertTrue(during)
        self.assertTrue(outside)
        self.assertTrue(all(c["complete"] is False and not c["candidates"] for c in during))
        self.assertTrue(all(c["complete"] is True and c["candidates"] for c in outside))

    def test_normalized_input_rejects_float_and_noncanonical_timing(self):
        for location, field, value in [
            ("event", "onset_q", 0.0), ("event", "duration_q", 1.0),
            ("event", "onset_q", "0/1"), ("event", "duration_q", "2/2"),
            ("bar", "start_q", 0.0), ("bar", "duration_q", 4.0),
            ("bar", "start_q", "0/1"), ("bar", "duration_q", "8/2"),
        ]:
            score = _small_score([dict(midi=60)], bars=1)
            target = score["events"][0] if location == "event" else score["bars"][0]
            target[field] = value
            with self.subTest(location=location, field=field, value=value):
                with self.assertRaises(ValueError):
                    analyze(score)

    def test_pickup_start_is_not_given_a_full_bar_downbeat_accent(self):
        score = _small_score([dict(midi=60, onset_q='0', duration_q='1'),
                              dict(midi=62, onset_q='1', duration_q='1', bar=2)], bars=2)
        score['bars'][0].update(duration_q='1', pickup=True)
        score['bars'][1].update(start_q='1')
        score['events'][1]['bar'] = 2
        metric = analyze(score)['global']['evidence']['channels']['metric']
        self.assertLess(metric[0], metric[2])

    def test_normalized_input_rejects_duplicate_bar_and_wrong_event_bar(self):
        duplicate = _small_score([dict(midi=60)], bars=2)
        duplicate["bars"][1]["bar"] = 1
        with self.assertRaises(ValueError):
            analyze(duplicate)
        wrong_reference = _small_score([dict(midi=60)], bars=2)
        wrong_reference["events"][0]["bar"] = 2
        with self.assertRaises(ValueError):
            analyze(wrong_reference)

    def test_repeated_explicit_section_labels_retain_distinct_instances(self):
        score = deepcopy(self.examples["c_major_cadences"])
        self.assertEqual(len(analyze(score)["sections"]), 1)
        score["declarations"] = [
            dict(track_id="melody", bar=1, onset_q="0", field="marker", value="A"),
            dict(track_id="melody", bar=5, onset_q="16", field="marker", value="A"),
        ]
        sections = analyze(score)["sections"]
        self.assertEqual([(s["first_bar"], s["last_bar"], s["label"]) for s in sections],
                         [(1, 4, "A"), (5, 8, "A")])

    def test_raw_key_declarations_do_not_supply_inference_answers(self):
        score = deepcopy(self.examples["c_major_cadences"])
        before = analyze(score, top=12 * len(MODES))["global"]
        score["declarations"] = [
            dict(track_id="melody", bar=1, onset_q="0", field="keySignature", value=7),
            dict(track_id="harmony", bar=None, onset_q="0", field="key", value="F# minor"),
        ]
        report = analyze(score, top=12 * len(MODES))
        self.assertEqual(_scores(before), _scores(report["global"]))
        self.assertEqual(before["evidence"], report["global"]["evidence"])
        self.assertEqual(report["declarations"], score["declarations"])

    def test_invalid_rest_duration_warning_blocks_only_affected_voice_end(self):
        # The invalid rest contains no note row: its warning is the only record
        # preventing a fabricated phrase ending after the previous known note.
        score = _small_score([dict(midi=60, voice=0), dict(midi=64, voice=1)], bars=1)
        score["warnings"] = [dict(reason="invalid_duration", track_id="melody", bar=1,
                                  voice=0, beat=1)]
        arrivals = analyze(score)["global"]["evidence"]["arrivals"]
        credited = {ref for arrival in arrivals for ref in arrival["note_refs"]}
        self.assertNotIn("edge:0", credited)
        self.assertIn("edge:1", credited)

    def test_unequal_coattack_durations_credit_only_actual_landing_notes(self):
        score = _small_score([
            dict(midi=60, duration_q="1"),
            dict(midi=64, duration_q="3"),
            dict(midi=67, duration_q="2"),
        ], bars=1)
        arrivals = analyze(score)["global"]["evidence"]["arrivals"]
        self.assertEqual(len(arrivals), 1)
        self.assertEqual(arrivals[0]["at_q"], "3")
        self.assertEqual(arrivals[0]["pitch_classes"], [4])
        self.assertEqual(arrivals[0]["note_refs"], ["edge:1"])

    def test_same_voice_overlap_is_not_a_monophonic_transition(self):
        rows = [dict(midi=60, onset_q="0", duration_q="4"),
                dict(midi=62, onset_q="1", duration_q="1"),
                dict(midi=64, onset_q="2", duration_q="1")]
        result = analyze(_small_score(rows, bars=1))["global"]
        self.assertEqual(result["evidence"]["melodic_transitions"], [])
        self.assertEqual(result["evidence"]["ornament_candidates"], [])
        # The same held pitch in another voice should not block a legitimate
        # D-E transition in the separately represented monophonic voice.
        rows[0]["voice"] = 1
        transitions = analyze(_small_score(rows, bars=1))["global"]["evidence"]["melodic_transitions"]
        self.assertEqual([(t["from_midi"], t["to_midi"]) for t in transitions], [(62, 64)])

    def test_bass_inversion_does_not_replace_harmonic_root(self):
        candidates = chord_candidates([0, 4, 7], bass=4)
        self.assertTrue(any(c["root"] == 0 and c["quality"] == "major" for c in candidates))
        self.assertFalse(any(c["root"] == 4 and c["quality"] == "major" for c in candidates))

    def test_note_order_matters_even_when_histogram_is_identical(self):
        score = self.examples["c_major_cadences"]
        reordered = deepcopy(score)
        melody = sorted((e for e in reordered["events"] if e["track_id"] == "melody"),
                        key=lambda e: Fraction(e["onset_q"]))
        melody[-1]["midi"], melody[-2]["midi"] = melody[-2]["midi"], melody[-1]["midi"]
        counts = lambda s: Counter(e["midi"] for e in s["events"])
        self.assertEqual(counts(score), counts(reordered))
        before, after = analyze(score)["global"], analyze(reordered)["global"]
        self.assertNotEqual([c["score"] for c in before["centers"]],
                            [c["score"] for c in after["centers"]])


if __name__ == "__main__":
    unittest.main()
