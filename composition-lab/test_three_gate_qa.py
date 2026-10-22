"""Negative controls for QA machinery; no musical accuracy claim."""
import copy
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from three_gate_qa import (check_intervention, digest, exact_diff, freeze_valid,
                           musical_abstraction, portability, reversal, run)


def contract():
    c = dict(tier=2, input_tier=1, musical_question="How does this note relate to a candidate chord?",
             new_relationship="note_to_candidate_harmony", ownership="T2 owns relation; T1 owns occurrence",
             removed_or_transformed_fields=["pitch coordinate"],
             realization_parameter_meanings={"octave": "register choice"},
             inverse_obligations=["recover exact coordinate"],
             source_to_tier_to_source_trace=["occurrence→relation→occurrence"],
             predecessor_schema="score-facts/test", predecessor_sha256="test-only-not-source-evidence",
             relationship_intervention_evidence="test-only-not-product-evidence",
             duplicates_lower_payload=False, operation_kind="musical_relationship",
             preceding_evidence={"e1": dict(start_q="1/3", end_q="2/3", occurrence_refs=["note1"])},
             examples=[dict(kind=k, claim="test claim " + k, interpretation_status="ambiguous" if k == "ambiguous" else "inferred",
                            evidence_refs=["e1"]) for k in ("support", "contrast", "ambiguous")])
    return sign(c)


def sign(c):
    unsigned = {k: v for k, v in c.items() if k != "planner_review"}
    c["planner_review"] = dict(verdict="approved", contract_sha256=hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
    return c


class ThreeGateQATests(unittest.TestCase):
    def source_case(self, root):
        capture = root / "capture"; capture.mkdir()
        (capture / "metadata.json").write_text(json.dumps(dict(songId=1, revisionId=2, tracks=[{}])))
        (capture / "track-0.json").write_text(json.dumps(dict(partId=0, tuning=[40], measures=[
            dict(signature=[4, 4], voices=[dict(beats=[dict(duration=[1, 1], notes=[dict(string=0, fret=3)])])])])))
        rng = random.Random(42)
        selection = dict(seed=42, query=rng.choice("abcdefghijklmnopqrstuvwxyz"), candidate_ids=[1],
                         excluded_ids=[], selected_song_id=rng.choice([1]), revision_id=2)
        path = root / "selection.json"; path.write_text(json.dumps(selection))
        return capture, path

    def test_actual_source_check_and_corrupted_extraction(self):
        from run_reversible_tier_qa import extract
        with tempfile.TemporaryDirectory() as temp:
            capture, selection = self.source_case(Path(temp))
            self.assertEqual(portability(capture, selection)["status"], "PASS")
            changed = extract(capture); changed["events"][0]["pitch"] = "99"
            with patch("run_reversible_tier_qa.extract", return_value=changed):
                self.assertEqual(portability(capture, selection)["status"], "FAIL")

    def test_executed_pipeline_freeze_and_completion_block(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); capture, selection = self.source_case(root)
            report = run(capture, selection, root / "qa")
            self.assertEqual(report["gates"]["1_portability"]["status"], "PASS")
            self.assertFalse(report["completion_allowed"])
            frozen = json.loads((root / "qa/before-analysis-freeze.json").read_text())
            self.assertEqual(frozen["files"][str(selection.resolve())], digest(selection))

    def test_null_missing_false_zero_and_float_distinct(self):
        for a, b in (({}, {"x": None}), (False, 0), (1, 1.0), ([1], [1, 2])):
            self.assertTrue(exact_diff(a, b))
        self.assertEqual(exact_diff({"x": [False, None, "1/3"]}, {"x": [False, None, "1/3"]}), [])

    def test_selection_replay_and_no_replacement(self):
        rng = random.Random(42)
        record = dict(seed=42, query=rng.choice("abcdefghijklmnopqrstuvwxyz"), candidate_ids=[1, 2, 3],
                      excluded_ids=[4], selected_song_id=rng.choice([1, 2, 3]), revision_id=7)
        self.assertEqual(freeze_valid(record), [])
        record["selected_song_id"] = 99
        self.assertTrue(freeze_valid(record))
        record["excluded_ids"] = [1]
        self.assertTrue(freeze_valid(record))

    def test_no_active_inverse_does_not_pass(self):
        self.assertEqual(reversal(None)["status"], "NOT RUN")
        report = reversal(dict(architecture="historical", controls={"pitch": 0}))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("Historical" in s for s in report["issues"]))

    def test_explicit_zero_and_source_answer_config_required(self):
        for controls in ({}, {"pitch": False}, {"pitch": 0.5}, None):
            report = reversal(dict(architecture="active", controls=controls))
            self.assertTrue(any("numeric zero" in s for s in report["issues"]))
        report = reversal(dict(architecture="active", controls={"pitch": 0}, configuration_contains_source_answers=True))
        self.assertTrue(any("ownership" in s for s in report["issues"]))

    def test_flags_without_files_cannot_pass(self):
        self.assertEqual(reversal(dict(architecture="active", controls={"pitch": 0},
                                      source_denied=True, cache_denied=True, network_denied=True))["status"], "FAIL")

    def test_contract_completeness_is_never_musical_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "predecessor.json"
            path.write_text(json.dumps(dict(tier=1, schema="score-facts/test", events=[
                dict(id="note1", onset_q="1/3", duration_q="1/3")])) )
            c = contract(); c.update(predecessor_path=str(path), predecessor_sha256=digest(path))
            self.assertEqual(musical_abstraction([sign(c)], "PASS")["status"], "INCONCLUSIVE")

    def test_fake_predecessor_and_copied_extra_payload_rejected(self):
        c = contract(); c["copied_original_notes"] = [{"pitch": 60}]
        issues = musical_abstraction([sign(c)], "PASS")["issues"]
        self.assertTrue(any("predecessor file" in s for s in issues))
        self.assertTrue(any("undeclared payload" in s for s in issues))

    def test_real_predecessor_binding_and_occurrence_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lower.json"
            path.write_text(json.dumps(dict(tier=1, schema="score-facts/test", events=[
                dict(id="different-note", onset_q="1/3", duration_q="1/3")])) )
            c = contract(); c.update(predecessor_path=str(path), predecessor_sha256=digest(path))
            self.assertTrue(any("timed evidence" in s for s in musical_abstraction([sign(c)], "PASS")["issues"]))
            path.write_text("{}")
            self.assertTrue(any("stale actual predecessor" in s for s in musical_abstraction([sign(c)], "PASS")["issues"]))

    def test_repeated_example_without_distinct_claim_rejected(self):
        c = contract()
        for e in c["examples"]:
            e["claim"] = "same"
        self.assertTrue(any("distinct explicit" in s for s in musical_abstraction([sign(c)], "PASS")["issues"]))

    def test_no_contract_or_inverse_blocks_completion(self):
        self.assertEqual(musical_abstraction([], "PASS")["status"], "FAIL")
        self.assertEqual(musical_abstraction([contract()], "NOT RUN")["status"], "FAIL")

    def test_stale_review_after_edit(self):
        c = contract(); c["musical_question"] = "Changed claim"
        self.assertTrue(any("stale" in s for s in musical_abstraction([c], "PASS")["issues"]))

    def test_predecessor_only_and_payload_ownership(self):
        c = contract(); c.update(input_tier=0, duplicates_lower_payload=True)
        issues = musical_abstraction([sign(c)], "PASS")["issues"]
        self.assertTrue(any("preceding" in s for s in issues))
        self.assertTrue(any("duplication" in s for s in issues))

    def test_structural_operations_not_musical_tiers(self):
        for kind in ("rename", "nest", "compress", "coordinate_change"):
            c = contract(); c["operation_kind"] = kind
            self.assertEqual(musical_abstraction([sign(c)], "PASS")["status"], "FAIL")

    def test_contrasts_and_ambiguity_required(self):
        c = contract(); c["examples"] = c["examples"][:1]
        self.assertTrue(any("ambiguity" in s for s in musical_abstraction([sign(c)], "PASS")["issues"]))

    def test_dangling_ref_and_bad_time(self):
        c = contract(); c["examples"][0]["evidence_refs"] = ["missing"]
        c["preceding_evidence"]["e1"]["end_q"] = "1/0"
        issues = musical_abstraction([sign(c)], "PASS")["issues"]
        self.assertTrue(any("dangling" in s for s in issues))
        self.assertTrue(any("timed" in s for s in issues))

    def test_emotion_not_inferred_as_fact(self):
        c = contract(); c["claims_emotion_or_artist_fidelity"] = True
        self.assertEqual(musical_abstraction([sign(c)], "PASS")["status"], "FAIL")

    def test_decorative_relation_ignored(self):
        self.assertEqual(check_intervention({"pitch": 60}, {"pitch": 60}, ["$.pitch"])["status"], "FAIL")
        self.assertEqual(check_intervention({"pitch": 60}, {"pitch": 62}, ["$.pitch"])["status"], "PASS")
        self.assertNotEqual(check_intervention({}, {}, [], refused=True)["status"], "PASS")
        self.assertEqual(check_intervention({"pitch": 60, "duration": "1/2"},
                                           {"pitch": 62, "duration": "1"}, ["$.pitch"],
                                           protected=["$.duration"])["status"], "FAIL")

    def test_run_retains_failure_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = run(root / "missing", root / "missing-selection", root / "output")
            self.assertFalse(report["completion_allowed"])
            self.assertEqual(report["gates"]["1_portability"]["status"], "FAIL")
            self.assertTrue((root / "output/result.json").is_file())
            with self.assertRaises(ValueError):
                run(root / "missing", root / "missing-selection", root / "output")

    def test_malformed_later_gates_preserve_result(self):
        for evidence in ({"reversal": True, "musical_contracts": [None]}, [], {"musical_contracts": ["invalid"]}):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                report = run(root / "missing", root / "missing-selection", root / "output", evidence)
                self.assertFalse(report["completion_allowed"])
                self.assertEqual(report["gates"]["3_musical_abstraction"]["status"], "FAIL")
                self.assertTrue((root / "output/result.json").is_file())


if __name__ == "__main__":
    unittest.main()
