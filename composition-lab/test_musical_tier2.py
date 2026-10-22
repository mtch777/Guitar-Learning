"""Actual musical relations, ambiguity and blind same-equation reconstruction."""
from copy import deepcopy
from fractions import Fraction as F
import unittest

from musical_tier2 import analyze, note_context, reconstruct, relation, strip_lower, transpose


def facts(notes):
    events = [dict(id=f"note-{i}", part_id=part, bar=1, voice=0, beat=i, note=0,
                   pitch=None if pitch is None else str(pitch), onset_q=str(onset), duration_q=str(duration))
              for i, (part, pitch, onset, duration) in enumerate(notes)]
    return dict(tier=1, schema="normalized-written-fields/1", events=events,
                source_coverage=dict(expected=len(events), actual=len(events), tracks=max((e["part_id"] for e in events), default=-1)+1,
                                     layout_warnings=[], timing_warnings=[]), scope="base_pitch_and_metric_onset_duration_only")


class MusicalTier2Tests(unittest.TestCase):
    def test_same_relation_both_directions_conflict_and_underdetermined(self):
        self.assertEqual(relation(anchor="48", pitch="64")["interval"], "16")
        self.assertEqual(relation(anchor="48", interval="16")["pitch"], "64")
        self.assertEqual(relation(interval="16", pitch="64")["anchor"], "48")
        with self.assertRaises(ValueError): relation(anchor="48", interval="15", pitch="64")
        with self.assertRaises(ValueError): relation(anchor="48")

    def test_c_major_exact_stripped_roundtrip_and_member_context(self):
        lower = facts([(0, 60, 0, 1), (0, 64, 0, 1), (0, 67, 0, 1)])
        upper = analyze(lower)
        self.assertEqual(upper["input"], lower)
        blind = strip_lower(upper)
        self.assertNotIn("input", blind)
        self.assertEqual(reconstruct(blind, {"variation": 0}), lower)
        choices = upper["coattacks"][0]["interpretation"]["chord_candidates"]
        self.assertIn((0, "major"), {(c["root_pc"], c["kind"]) for c in choices})
        coords = note_context(upper, "note-1")["coordinates"]
        e_against_c = next(c for c in coords if c["root_pc"] == 0 and c["kind"] == "major")
        self.assertEqual(e_against_c["unwrapped_semitones"], "4")
        self.assertEqual(e_against_c["relative_octaves"], 0)
        self.assertTrue(e_against_c["chord_member"])

    def test_inversion_bass_not_root(self):
        upper = analyze(facts([(0, 52, 0, 1), (0, 55, 0, 1), (0, 60, 0, 1)]))
        c = next(c for c in upper["coattacks"][0]["interpretation"]["chord_candidates"] if c["root_pc"] == 0 and c["kind"] == "major")
        self.assertEqual(c["bass_interval_pc"], 4)
        self.assertEqual(note_context(upper, "note-2")["coordinates"][0]["unwrapped_semitones"], "12")

    def test_dyad_does_not_invent_a_major_or_minor_third(self):
        upper = analyze(facts([(0, 50, 0, 1), (0, 57, 0, 1)]))
        candidates = upper["coattacks"][0]["interpretation"]["chord_candidates"]
        self.assertFalse(any(c["kind"] in {"major", "minor"} for c in candidates))

    def test_symmetric_sonority_retains_alternative_roots(self):
        upper = analyze(facts([(0, p, 0, 1) for p in (60, 63, 66, 69)]))
        roots = {c["root_pc"] for c in upper["coattacks"][0]["interpretation"]["chord_candidates"] if c["kind"] == "diminished-seventh"}
        self.assertEqual(roots, {0, 3, 6, 9})

    def test_ensemble_is_not_the_same_as_part_context(self):
        upper = analyze(facts([(0, 60, 0, 1), (0, 64, 0, 1), (0, 67, 0, 1), (1, 66, 0, 1)]))
        part = upper["coattacks"][0]["interpretation"]
        ensemble = upper["ensemble_coattacks"][0]["interpretation"]
        self.assertIn((0, "major"), {(c["root_pc"], c["kind"]) for c in part["chord_candidates"]})
        self.assertNotEqual(part["distinct_pitch_classes"], ensemble["distinct_pitch_classes"])

    def test_unknown_grace_and_fractional_pitches_are_not_guessed(self):
        lower = facts([(0, None, 0, 1), (1, "121/2", "1/2", "1/3"), (2, 60, 1, 0), (2, 64, 1, 1), (2, 67, 1, 1)])
        upper = analyze(lower)
        self.assertEqual(reconstruct(strip_lower(upper), {"variation": 0}), lower)
        self.assertEqual(upper["coattacks"][2]["interpretation"]["harmonic_status"], "unresolved_ornament_timing")
        self.assertIsNone(note_context(upper, "note-1")["interval_of_note_base_key"])

    def test_real_intervention_changes_pitch_and_keeps_locked_dimensions(self):
        lower = facts([(0, 60, 0, 1), (0, 64, 0, 1), (0, 67, 0, 1), (1, None, 0, 1)])
        upper = analyze(lower)
        restored = reconstruct(transpose(upper, "2"), {"variation": 0})
        for original, changed in zip(lower["events"], restored["events"]):
            self.assertEqual({k: v for k, v in original.items() if k != "pitch"}, {k: v for k, v in changed.items() if k != "pitch"})
            self.assertEqual(changed["pitch"], str(F(original["pitch"]) + 2) if original["pitch"] else None)
        contexts = transpose(upper, "2")["coattacks"][0]["interpretation"]["chord_candidates"]
        self.assertIn((2, "major"), {(c["root_pc"], c["kind"]) for c in contexts})

    def test_stale_contexts_hidden_pitches_and_lower_copies_refused(self):
        upper = analyze(facts([(0, 60, 0, 1), (0, 64, 0, 1), (0, 67, 0, 1)]))
        with self.assertRaises(ValueError): reconstruct(upper, {"variation": 0})
        bad = strip_lower(upper); bad["coattacks"][0]["bass_register_anchor"] = "62"
        with self.assertRaisesRegex(ValueError, "context"): reconstruct(bad, {"variation": 0})
        bad = strip_lower(upper); bad["coattacks"][0]["members"][0]["pitch"] = "60"
        with self.assertRaises(ValueError): reconstruct(bad, {"variation": 0})
        bad = strip_lower(upper); bad["raw_notes"] = []
        with self.assertRaises(ValueError): reconstruct(bad, {"variation": 0})

    def test_metadata_cannot_hide_lower_stream(self):
        lower = facts([(0, 60, 0, 1)])
        lower["source_coverage"]["hidden_lower_stream"] = lower["events"]
        with self.assertRaises(ValueError): analyze(lower)
        lower = facts([(0, 60, 0, 1)])
        upper = strip_lower(analyze(lower))
        upper["source_quality"]["hidden_lower_stream"] = lower["events"]
        with self.assertRaises(ValueError): reconstruct(upper, {"variation": 0})

    def test_unknown_members_qualify_harmonic_evidence(self):
        upper = analyze(facts([(0, p, 0, 1) for p in (60, 64, 67, None)]))
        context = upper["coattacks"][0]["interpretation"]
        self.assertEqual(context["known_members"], 3)
        self.assertEqual(context["unknown_members"], 1)
        self.assertEqual(context["harmonic_status"], "compatible_known_subset_only")

    def test_bar_clock_collisions_do_not_merge(self):
        lower = facts([(0, 60, 4, 1), (0, 64, 4, 1), (0, 67, 4, 1)])
        lower["events"][2]["bar"] = 2
        upper = analyze(lower)
        self.assertEqual(len(upper["coattacks"]), 2)
        self.assertEqual(len(upper["ensemble_coattacks"]), 2)
        self.assertFalse(any(g["interpretation"]["chord_candidates"] for g in upper["coattacks"]))
        self.assertEqual(reconstruct(strip_lower(upper), {"variation": 0}), lower)

    def test_timing_warnings_quarantine_harmony_but_keep_notes(self):
        lower = facts([(0, p, 0, 1) for p in (60, 64, 67)])
        lower["source_coverage"]["timing_warnings"] = [dict(part_id=0, bar=1, voice=0, reason="voice_overflows_bar", duration_q="5", span_q="4")]
        upper = analyze(lower)
        self.assertEqual(upper["coattacks"][0]["interpretation"]["harmonic_status"], "unresolved_source_timing")
        self.assertEqual(reconstruct(strip_lower(upper), {"variation": 0}), lower)

    def test_stripped_identity_and_types_are_enforced(self):
        upper = strip_lower(analyze(facts([(0, 60, 0, 1), (0, 64, 1, 1)])))
        for mutate in (
            lambda u: u.update(tier=True),
            lambda u: u["coattacks"][0].update(part_id=True),
            lambda u: u["coattacks"][0]["members"][0].update(voice=True),
            lambda u: u["coattacks"][1].update(id=u["coattacks"][0]["id"]),
            lambda u: u["coattacks"][0]["interpretation"].update(known_members=True),
        ):
            bad = deepcopy(upper); mutate(bad)
            with self.assertRaises(ValueError): reconstruct(bad, {"variation": 0})

    def test_counts_and_canonical_context_partition(self):
        from musical_tier2 import ensemble, interpreted
        upper = strip_lower(analyze(facts([(0, 60, 0, 1), (0, 64, 0, 1), (0, 67, 0, 1)])))
        bad = deepcopy(upper); bad["source_quality"]["actual"] = 999
        with self.assertRaises(ValueError): reconstruct(bad, {"variation": 0})
        bad = deepcopy(upper); second = deepcopy(bad["coattacks"][0]); second["id"] = "different"
        second["members"] = [bad["coattacks"][0]["members"].pop()]
        bad["coattacks"].append(second)
        for g in bad["coattacks"]: g["interpretation"] = interpreted(g)
        bad["ensemble_coattacks"] = ensemble(bad["coattacks"])
        with self.assertRaises(ValueError): reconstruct(bad, {"variation": 0})

    def test_declared_theory_hash(self):
        import hashlib, json
        from musical_tier2 import THEORY_FORMS, THEORY_PROVENANCE
        encoded = json.dumps(THEORY_FORMS, separators=(",", ":"))
        self.assertEqual(hashlib.sha256(encoded.encode()).hexdigest(), THEORY_PROVENANCE["forms_sha256"])

    def test_actual_isolated_inverse_and_source_denial(self):
        import tempfile
        from pathlib import Path
        from qa_isolation_harness import execute
        lower = facts([(0, 60, 0, 1), (0, 64, 0, 1), (0, 67, 0, 1)])
        upper = strip_lower(analyze(lower))
        code = Path(__file__).with_name("musical_tier2.py").read_text()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = execute(code, upper, {"variation": 0}, lower, root/"exact")
            self.assertEqual(result["status"], "PASS", result)
            denied = execute(code, upper, {"variation": 0}, lower, root/"denied", challenge="open", forbidden=Path(__file__).resolve())
            self.assertEqual(denied["status"], "PASS", denied)

    def test_runner_retains_failures_and_reports_failclosed(self):
        import tempfile
        from pathlib import Path
        from run_musical_tier2_qa import run
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); capture = root/"capture"; capture.mkdir()
            result = run(capture, root/"failed")
            self.assertEqual(result["technical_status"], "FAIL")
            self.assertTrue((root/"failed/result.json").exists())
            with self.assertRaises(ValueError): run(capture, root/"failed")

    def test_nominal_overlap_differs_from_new_starts(self):
        from musical_tier2 import note_context_at
        # C/G are written to continue; E starts later. No new attack claimed.
        lower = facts([(0, 60, 0, 2), (0, 67, 0, 2), (0, 64, 1, 1)])
        upper = analyze(lower)
        self.assertEqual(upper["coattacks"][1]["interpretation"]["distinct_pitch_classes"], ["4"])
        span = upper["nominal_written_spans"][1]
        self.assertEqual(span["ensemble_context"]["interpretation"]["distinct_pitch_classes"], ["0", "4", "7"])
        self.assertEqual(span["ensemble_context"]["continuing_refs"], ["note-0", "note-1"])
        self.assertEqual(span["ensemble_context"]["starting_refs"], ["note-2"])
        self.assertEqual(note_context_at(upper,"note-2","1")["coordinates"][0]["unwrapped_semitones"], "4")
        self.assertEqual(reconstruct(strip_lower(upper), {"variation":0}), lower)
        with self.assertRaises(ValueError): note_context_at(upper,"note-2","2")

    def test_same_held_note_changes_context_and_stale_span_refused(self):
        from musical_tier2 import note_context_at
        lower = facts([(0, 60, 0, 2), (0, 64, 0, 1), (0, 67, 0, 1), (0, 65, 1, 1), (0, 69, 1, 1)])
        upper = analyze(lower)
        before = note_context_at(upper,"note-0","0")["coordinates"]
        after = note_context_at(upper,"note-0","1")["coordinates"]
        self.assertTrue(any(c["root_pc"] == 0 and c["unwrapped_semitones"] == "0" for c in before))
        self.assertTrue(any(c["root_pc"] == 5 and c["unwrapped_semitones"] == "7" for c in after))
        bad = strip_lower(upper); bad["nominal_written_spans"][0]["ensemble_context"]["continuing_refs"] = ["note-0"]
        with self.assertRaises(ValueError): reconstruct(bad,{"variation":0})

    def test_nested_lower_payload_cannot_disagree_with_shared_relations(self):
        upper = analyze(facts([(0, 60, 0, 1), (0, 64, 0, 1), (0, 67, 0, 1)]))
        upper["input"]["events"][1]["pitch"] = "65"
        with self.assertRaises(ValueError): note_context(upper,"note-1")


if __name__ == "__main__": unittest.main()
