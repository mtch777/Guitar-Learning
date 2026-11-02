"""Guard the six reviewed catalog/metadata discrepancies without changing analysis."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import run_tiered_catalog as runner


# These reviewed identity pairs are independent assertions about the six rules.
# Track descriptors come from the committed public evidence snapshots.
REVIEWED = {
    4081672: ((57932, "Currents", "Unf (Drop C#)"), (122760, "Lexi", "Unf")),
    6656103: ((53238, "Invent Animate", "Halcyon (drop E)"), (86430, "Misc Covers", "Halcyon (drop E) by Invent Animate")),
    3851017: ((17808, "ERRA", "Cure (Light Bass)"), (500784, "misc covers", "Cure by Erra (Light Bass)")),
    2457200: ((17808, "ERRA", "Echo Sonata intro Tapping"), (485079, "ERR", "Echo Sonata intro Tapping")),
    3956211: ((17808, "ERRA", "further eden (Bass in Drop Eb)"), (500784, "misc covers", "further eden by Erra")),
    4472844: ((17808, "ERRA", "Black Cloud (Guitar · 7-string)"), (182939, "yuyayu24", "Black Cloud - ERRA")),
}


def identity(values):
    return dict(zip(("artistId", "artist", "title"), values))


def fixture(song_id=4081672):
    rule = runner.RECONCILIATIONS[str(song_id)]
    catalog_identity, metadata_identity = REVIEWED[song_id]
    metadata = dict(
        songId=song_id,
        revisionId=rule["reviewed_revision_id"],
        image="fixture-image",
        tracks=deepcopy(rule["tracks"]),
        isJunk=True,
        aiGenerated=False,
        extraSourceField={"opaque": [False, None, 0, "unchanged"]},
        **identity(metadata_identity),
    )
    catalog_record = dict(songId=song_id, tracks=deepcopy(rule["tracks"]), **identity(catalog_identity))
    return metadata, catalog_record


class Client:
    def __init__(self, metadata, records):
        self.metadata = metadata
        self.records = records
        self.catalog_calls = []
        self.track_calls = []

    def meta(self, song_id):
        return self.metadata

    def _json(self, url, **query):
        self.catalog_calls.append((url, query))
        return self.records

    def track(self, song_id, revision_id, image, part):
        self.track_calls.append((song_id, revision_id, image, part))
        return {"partId": part, "measures": [], "testPayload": "unchanged"}


class IdentityTests(unittest.TestCase):
    def resolve(self, song_id=4081672, metadata=None, catalog_record=None):
        default_metadata, default_catalog = fixture(song_id)
        metadata = default_metadata if metadata is None else metadata
        catalog_record = default_catalog if catalog_record is None else catalog_record
        client = Client(metadata, [catalog_record])
        return runner.resolve_catalog_identity(song_id, metadata, client)

    def test_rule_set_contains_only_the_six_reviewed_ids(self):
        self.assertEqual(set(runner.RECONCILIATIONS), {str(i) for i in REVIEWED})
        self.assertEqual(runner.EXPECTED_ARTISTS, {53238: "Invent Animate", 57932: "Currents", 17808: "ERRA"})
        for song_id, (catalog_identity, metadata_identity) in REVIEWED.items():
            with self.subTest(song_id=song_id):
                rule = runner.RECONCILIATIONS[str(song_id)]
                self.assertEqual(rule["catalog_identity"], identity(catalog_identity))
                self.assertEqual(rule["metadata_identity"], identity(metadata_identity))

    def test_all_six_reviewed_discrepancies_are_accepted_without_mutation(self):
        for song_id in REVIEWED:
            with self.subTest(song_id=song_id):
                metadata, row = fixture(song_id)
                before = deepcopy((metadata, row, runner.RECONCILIATIONS))
                client = Client(metadata, [row])
                audit = runner.resolve_catalog_identity(song_id, metadata, client)
                self.assertEqual(audit["song_id"], song_id)
                self.assertEqual(audit["catalog_identity"], runner.RECONCILIATIONS[str(song_id)]["catalog_identity"])
                self.assertEqual(audit["metadata_identity"], runner.RECONCILIATIONS[str(song_id)]["metadata_identity"])
                self.assertEqual(audit["decision"], "verified_catalog_metadata_reconciliation")
                self.assertEqual(audit["track_count"], len(metadata["tracks"]))
                self.assertRegex(audit["track_identity_sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue(audit["raw_metadata_preserved"])
                self.assertEqual(audit["metadata_revision_id"], metadata["revisionId"])
                self.assertEqual((metadata, row, runner.RECONCILIATIONS), before)
                self.assertEqual(client.catalog_calls, [("https://www.songsterr.com/api/songs", {"pattern": row["artist"], "size": 250})])

    def test_exact_upstream_correction_is_accepted_with_same_track_checks(self):
        for song_id in REVIEWED:
            with self.subTest(song_id=song_id):
                metadata, row = fixture(song_id)
                metadata.update(identity(REVIEWED[song_id][0]))
                audit = self.resolve(song_id, metadata, row)
                self.assertEqual(audit["metadata_identity"], audit["catalog_identity"])
                metadata["tracks"][0]["hash"] += "-changed"
                with self.assertRaises(ValueError):
                    self.resolve(song_id, metadata, row)

    def test_unlisted_song_with_any_exception_artist_remains_rejected(self):
        for song_id in REVIEWED:
            with self.subTest(song_id=song_id):
                metadata, row = fixture(song_id)
                metadata["songId"] = 99999999
                client = Client(metadata, [row])
                with self.assertRaisesRegex(ValueError, "Unexpected artist identity"):
                    runner.resolve_catalog_identity(99999999, metadata, client)
                self.assertEqual(client.catalog_calls, [])

    def test_mapped_song_cannot_bypass_rule_using_another_allowed_artist(self):
        metadata, row = fixture()
        metadata.update(artistId=17808, artist="ERRA", title=row["title"])
        with self.assertRaisesRegex(ValueError, "Reviewed metadata identity changed"):
            self.resolve(metadata=metadata, catalog_record=row)

    def test_metadata_identity_drift_is_rejected(self):
        mutations = {"artistId": 57932, "artist": "Different alias", "title": "Different composition"}
        for field, value in mutations.items():
            with self.subTest(field=field):
                metadata, row = fixture()
                metadata[field] = value
                with self.assertRaisesRegex(ValueError, "Reviewed metadata identity changed"):
                    self.resolve(metadata=metadata, catalog_record=row)

    def test_requested_song_id_must_match_exact_integer(self):
        for value in (4081673, "4081672", None, True):
            with self.subTest(value=value):
                metadata, row = fixture()
                metadata["songId"] = value
                client = Client(metadata, [row])
                with self.assertRaisesRegex(ValueError, "Unexpected metadata song ID"):
                    runner.resolve_catalog_identity(4081672, metadata, client)
                self.assertEqual(client.catalog_calls, [])

    def test_normal_canonical_artist_still_requires_correct_song_id(self):
        metadata = dict(songId=460099, artistId=53238, artist="Invent Animate", title="Cloud Cascade")
        client = Client(metadata, [])
        self.assertIsNone(runner.resolve_catalog_identity(460099, metadata, client))
        self.assertEqual(client.catalog_calls, [])
        metadata["songId"] = 460100
        with self.assertRaisesRegex(ValueError, "Unexpected metadata song ID"):
            runner.resolve_catalog_identity(460099, metadata, client)

    def test_missing_duplicate_and_wrong_catalog_song_ids_are_rejected(self):
        metadata, row = fixture()
        wrong = deepcopy(row)
        wrong["songId"] += 1
        wrong_type = deepcopy(row)
        wrong_type["songId"] = str(wrong_type["songId"])
        cases = {"missing": [], "duplicate": [row, deepcopy(row)], "wrong_id": [wrong], "wrong_type": [wrong_type]}
        for case, records in cases.items():
            with self.subTest(case=case):
                with self.assertRaisesRegex(ValueError, "Expected one catalog identity"):
                    runner.resolve_catalog_identity(4081672, metadata, Client(metadata, records))

    def test_exact_catalog_match_is_selected_among_unrelated_results(self):
        metadata, row = fixture()
        unrelated = deepcopy(row)
        unrelated.update(songId=777, artistId=122760, artist="Lexi", title="Unrelated")
        audit = runner.resolve_catalog_identity(4081672, metadata, Client(metadata, [unrelated, row]))
        self.assertEqual(audit["catalog_record"], row)

    def test_catalog_identity_drift_is_rejected(self):
        for field, value in {"artistId": 17808, "artist": "Other artist", "title": "Other song"}.items():
            with self.subTest(field=field):
                metadata, row = fixture()
                row[field] = value
                with self.assertRaisesRegex(ValueError, "Reviewed catalog identity changed"):
                    self.resolve(metadata=metadata, catalog_record=row)

    def test_track_drift_on_either_surface_is_rejected(self):
        def change_tuning(tracks):
            tracks[0]["tuning"][0] += 1
        mutations = {
            "hash": lambda tracks: tracks[0].update(hash="changed-track-content"),
            "name": lambda tracks: tracks[0].update(name="Changed track identity"),
            "instrument": lambda tracks: tracks[0].update(instrumentId=25),
            "tuning": change_tuning,
            "order": lambda tracks: tracks.reverse(),
            "count_drop": lambda tracks: tracks.pop(),
            "count_add": lambda tracks: tracks.append(deepcopy(tracks[0])),
        }
        for surface in ("metadata", "catalog", "both"):
            for mutation, mutate in mutations.items():
                with self.subTest(surface=surface, mutation=mutation):
                    metadata, row = fixture()
                    if surface in ("metadata", "both"):
                        mutate(metadata["tracks"])
                    if surface in ("catalog", "both"):
                        mutate(row["tracks"])
                    with self.assertRaisesRegex(ValueError, "Reviewed track identity changed"):
                        self.resolve(metadata=metadata, catalog_record=row)

    def test_missing_or_invalid_track_evidence_is_rejected(self):
        for case in ("missing_tracks", "empty_tracks", "missing_hash", "empty_hash", "missing_name", "missing_instrument", "boolean_instrument", "missing_guitar_tuning"):
            with self.subTest(case=case):
                metadata, row = fixture()
                if case == "missing_tracks":
                    metadata.pop("tracks")
                elif case == "empty_tracks":
                    metadata["tracks"] = []
                elif case == "empty_hash":
                    metadata["tracks"][0]["hash"] = ""
                elif case == "boolean_instrument":
                    metadata["tracks"][0]["instrumentId"] = True
                else:
                    key = {"missing_hash": "hash", "missing_name": "name", "missing_instrument": "instrumentId", "missing_guitar_tuning": "tuning"}[case]
                    metadata["tracks"][0].pop(key)
                with self.assertRaises(ValueError):
                    self.resolve(metadata=metadata, catalog_record=row)

    def test_source_flags_are_preserved_without_becoming_attribution_overrides(self):
        for junk, generated in ((False, False), (True, False), (False, True), (True, True)):
            with self.subTest(isJunk=junk, aiGenerated=generated):
                metadata, row = fixture()
                metadata.update(isJunk=junk, aiGenerated=generated)
                before = deepcopy(metadata)
                self.resolve(metadata=metadata, catalog_record=row)
                self.assertEqual(metadata, before)


class RunSongBoundaryTests(unittest.TestCase):
    def test_identity_failures_stop_before_track_capture_or_analysis(self):
        for reason in ("wrong_artist", "wrong_song", "wrong_tracks", "missing_catalog"):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                metadata, row = fixture()
                records = [row]
                if reason == "wrong_artist":
                    metadata["artistId"] = 777777
                elif reason == "wrong_song":
                    metadata["songId"] += 1
                elif reason == "wrong_tracks":
                    metadata["tracks"][0]["hash"] = "unexpected"
                else:
                    records = []
                snapshot = deepcopy(metadata)
                client = Client(metadata, records)
                output = Path(tmp) / "local-artifacts" / "failed"
                with mock.patch.object(runner.subprocess, "run") as run, mock.patch("builtins.print"):
                    self.assertFalse(runner.run_song(4081672, output, client))
                run.assert_not_called()
                self.assertEqual(client.track_calls, [])
                self.assertEqual(metadata, snapshot)
                self.assertEqual(json.loads((output / "capture" / "metadata.json").read_text()), snapshot)
                status = json.loads((output / "status.json").read_text())
                self.assertEqual(status["status"], "failed")
                self.assertEqual(status["artist_id"], snapshot["artistId"])
                self.assertIn("ValueError", status["error"])
                self.assertFalse((output / "identity-reconciliation.json").exists())

    def test_success_keeps_raw_source_and_audit_outside_capture(self):
        for song_id in REVIEWED:
            with self.subTest(song_id=song_id), tempfile.TemporaryDirectory() as tmp:
                metadata, row = fixture(song_id)
                snapshot = deepcopy(metadata)
                client = Client(metadata, [row])
                output = Path(tmp) / "local-artifacts" / str(song_id)
                calls = []

                def execute(args, check):
                    self.assertIs(check, True)
                    calls.append(args)
                    if Path(args[1]).name == "build_tiered_song.py":
                        self.assertEqual(Path(args[2]), output / "capture")
                        self.assertEqual(Path(args[3]), output / "tiered")
                        Path(args[3]).mkdir()
                    elif Path(args[1]).name == "verify_tiered_song.py":
                        self.assertEqual(Path(args[2]), output / "tiered")
                        self.assertEqual(Path(args[3]), output / "capture")
                        (Path(args[2]) / "qa.json").write_text(json.dumps({"status": "pass", "checks": {"mocked_analysis": 1}}))
                    else:
                        self.fail("Unexpected analysis entrypoint")
                    return subprocess.CompletedProcess(args, 0)

                with mock.patch.object(runner.subprocess, "run", side_effect=execute), mock.patch("builtins.print"):
                    self.assertTrue(runner.run_song(song_id, output, client))
                self.assertEqual(len(calls), 2)
                self.assertEqual(client.track_calls, [(song_id, metadata["revisionId"], metadata["image"], part) for part in range(len(metadata["tracks"]))])
                self.assertEqual(metadata, snapshot)
                self.assertEqual(json.loads((output / "capture" / "metadata.json").read_text()), snapshot)
                self.assertEqual({p.name for p in (output / "capture").iterdir()}, {"metadata.json", *(f"track-{part}.json" for part in range(len(metadata["tracks"])))})
                self.assertTrue((output / "identity-reconciliation.json").is_file())
                self.assertFalse((output / "capture" / "identity-reconciliation.json").exists())
                status = json.loads((output / "status.json").read_text())
                self.assertEqual(status["status"], "verified")
                self.assertEqual(status["artist"], snapshot["artist"])
                self.assertEqual(status["artist_id"], snapshot["artistId"])
                self.assertEqual(status["title"], snapshot["title"])
                self.assertEqual(status["catalog_identity"], identity(REVIEWED[song_id][0]))

    def test_analysis_failure_remains_a_failure_after_identity_is_resolved(self):
        metadata, row = fixture()
        client = Client(metadata, [row])
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "local-artifacts" / "analysis-failure"
            failure = subprocess.CalledProcessError(1, ["build_tiered_song.py"])
            with mock.patch.object(runner.subprocess, "run", side_effect=failure) as run, mock.patch("builtins.print"):
                self.assertFalse(runner.run_song(4081672, output, client))
            self.assertEqual(run.call_count, 1)
            self.assertTrue((output / "identity-reconciliation.json").exists())
            status = json.loads((output / "status.json").read_text())
            self.assertEqual(status["status"], "failed")
            self.assertEqual(status["identity_resolution"], "verified_catalog_metadata_reconciliation")
            self.assertIn("CalledProcessError", status["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
