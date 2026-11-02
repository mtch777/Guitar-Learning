"""Failure-safety tests for migration of irreplaceable encrypted output bytes."""

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.request
import urllib.error
import zipfile

import release_storage as storage


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


class FakeGitHub:
    repository = "owner/repo"

    def __init__(self, contents=(b"encrypted notation bytes",)):
        self.sources = {}
        self.source_data = {}
        self.release_assets = {}
        self.asset_data = {}
        self.events = []
        self.release = {"id": 8, "tag_name": "tiered-analysis-run-42", "draft": True, "html_url": "https://github.com/owner/repo/releases/tag/archive", "upload_url": "https://uploads.github.com/repos/owner/repo/releases/8/assets{?name,label}"}
        self.corrupt_download = set()
        self.corrupt_upload = set()
        self.fail_upload = set()
        self.no_digest = False
        self.next_asset_id = 200
        for index, data in enumerate(contents, 10):
            self.source_data[index] = data
            self.sources[index] = {"id": index, "name": f"tiered-song-{index}", "size_in_bytes": len(data), "digest": digest(data), "expired": False, "workflow_run": {"id": 42}}

    def api(self, method, path, payload=None):
        if method == "GET" and path == "/actions/runs/42":
            return {"id": 42, "status": "completed", "head_sha": "a" * 40}
        if method == "DELETE" and path.startswith("/actions/artifacts/"):
            artifact_id = int(path.rsplit("/", 1)[-1])
            self.events.append(("delete", artifact_id))
            if artifact_id not in self.sources:
                raise storage.ApiError(404, method)
            del self.sources[artifact_id]
            return None
        raise AssertionError((method, path, payload))

    def artifacts(self, run_id):
        self.assert_run(run_id)
        return copy.deepcopy(list(self.sources.values()))

    def assert_run(self, run_id):
        if run_id != 42:
            raise AssertionError("wrong run")

    def assets(self, release_id):
        assert release_id == self.release["id"]
        return copy.deepcopy(list(self.release_assets.values()))

    def ensure_release(self, tag, target=None):
        assert tag == self.release["tag_name"]
        self.release_target = target
        return copy.deepcopy(self.release)

    def upload(self, release, name, path):
        self.events.append(("upload", name))
        if name in self.fail_upload:
            raise storage.StorageError("Simulated failed upload")
        if name in self.release_assets:
            raise storage.ApiError(422, "POST")
        data = path.read_bytes()
        if name in self.corrupt_upload:
            data = b"X" + data[1:]
        return self.add_asset(name, data)

    def add_asset(self, name, data):
        self.next_asset_id += 1
        asset = {"id": self.next_asset_id, "name": name, "size": len(data), "digest": None if self.no_digest else digest(data), "state": "uploaded"}
        self.release_assets[name] = asset
        self.asset_data[asset["id"]] = data
        return copy.deepcopy(asset)

    def download(self, path, destination):
        self.events.append(("download", path))
        if path.startswith("/actions/artifacts/"):
            artifact_id = int(path.split("/")[3])
            data = self.source_data[artifact_id]
            if artifact_id in self.corrupt_download:
                data = b"corrupted source download"
        elif path.startswith("/releases/assets/"):
            data = self.asset_data[int(path.rsplit("/", 1)[-1])]
        else:
            raise AssertionError(path)
        destination.write_bytes(data)
        return len(data), digest(data)


class MigrationTests(unittest.TestCase):
    def run_migration(self, client):
        with mock.patch("builtins.print"):
            return storage.migrate(client, 42, len(client.source_data), sum(map(len, client.source_data.values())), workers=1)

    def test_success_preserves_exact_zip_and_deletes_after_manifest_and_copy(self):
        client = FakeGitHub()
        result = self.run_migration(client)
        self.assertEqual(result["moved"], 1)
        self.assertFalse(client.sources)
        source = client.source_data[10]
        asset = client.release_assets["tiered-song-10.zip"]
        self.assertEqual(client.asset_data[asset["id"]], source)
        self.assertLess(client.events.index(("upload", "source-artifacts.json")), client.events.index(("upload", "tiered-song-10.zip")))
        self.assertLess(client.events.index(("upload", "tiered-song-10.zip")), client.events.index(("delete", 10)))
        self.assertEqual(client.events.count(("delete", 10)), 1)

    def test_source_hash_failure_retains_source(self):
        client = FakeGitHub()
        client.corrupt_download.add(10)
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        self.assertIn(10, client.sources)
        self.assertNotIn(("delete", 10), client.events)
        self.assertNotIn("tiered-song-10.zip", client.release_assets)

    def test_release_targets_current_commit_but_manifest_keeps_source_commit(self):
        client = FakeGitHub()
        with mock.patch.dict(os.environ, {"GITHUB_SHA": "b" * 40}):
            self.run_migration(client)
        self.assertEqual(client.release_target, "b" * 40)
        manifest_asset = client.release_assets["source-artifacts.json"]
        manifest = json.loads(client.asset_data[manifest_asset["id"]])
        self.assertEqual(manifest["head_sha"], "a" * 40)

    def test_source_size_failure_retains_source(self):
        client = FakeGitHub()
        client.sources[10]["size_in_bytes"] += 1
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        self.assertIn(10, client.sources)
        self.assertNotIn(("delete", 10), client.events)

    def test_destination_hash_failure_retains_source(self):
        client = FakeGitHub()
        client.corrupt_upload.add("tiered-song-10.zip")
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        self.assertIn(10, client.sources)
        self.assertNotIn(("delete", 10), client.events)

    def test_failed_upload_retains_source(self):
        client = FakeGitHub()
        client.fail_upload.add("tiered-song-10.zip")
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        self.assertIn(10, client.sources)
        self.assertNotIn(("delete", 10), client.events)

    def test_manifest_upload_failure_prevents_all_deletion(self):
        client = FakeGitHub()
        client.fail_upload.add("source-artifacts.json")
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        self.assertIn(10, client.sources)
        self.assertNotIn(("delete", 10), client.events)

    def test_wrong_run_rejected_before_upload_or_deletion(self):
        client = FakeGitHub()
        client.sources[10]["workflow_run"]["id"] = 43
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        self.assertEqual(client.events, [])
        self.assertIn(10, client.sources)

    def test_published_destination_rejected_before_deletion(self):
        client = FakeGitHub()
        client.release["draft"] = False
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        self.assertEqual(client.events, [])
        self.assertIn(10, client.sources)

    def test_conflicting_existing_asset_is_not_overwritten_or_deleted(self):
        client = FakeGitHub()
        original = client.add_asset("tiered-song-10.zip", b"someone else's data")
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        self.assertEqual(client.release_assets["tiered-song-10.zip"], original)
        self.assertNotIn(("upload", "tiered-song-10.zip"), client.events)
        self.assertIn(10, client.sources)

    def test_partial_migration_resumes_from_durable_manifest(self):
        client = FakeGitHub((b"first ciphertext", b"second ciphertext"))
        client.fail_upload.add("tiered-song-11.zip")
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        self.assertNotIn(10, client.sources)
        self.assertIn(11, client.sources)
        client.fail_upload.clear()
        result = self.run_migration(client)
        self.assertEqual(result["already_moved"], 1)
        self.assertEqual(result["moved"], 1)
        self.assertFalse(client.sources)
        self.assertEqual(client.events.count(("upload", "source-artifacts.json")), 1)
        self.assertEqual(client.events.count(("upload", "tiered-song-10.zip")), 1)

    def test_missing_prior_destination_stops_remaining_deletion(self):
        client = FakeGitHub((b"first ciphertext", b"second ciphertext"))
        client.fail_upload.add("tiered-song-11.zip")
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        del client.release_assets["tiered-song-10.zip"]
        client.fail_upload.clear()
        with self.assertRaises(storage.StorageError):
            self.run_migration(client)
        self.assertIn(11, client.sources)
        self.assertNotIn(("delete", 11), client.events)

    def test_missing_server_digest_uses_readback_before_deletion(self):
        client = FakeGitHub()
        client.no_digest = True
        self.run_migration(client)
        asset = client.release_assets["tiered-song-10.zip"]
        event = ("download", f"/releases/assets/{asset['id']}")
        self.assertLess(client.events.index(event), client.events.index(("delete", 10)))


class PackagingTests(unittest.TestCase):
    def test_explicit_files_only_with_deterministic_bytes_and_optional_missing_cms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "status.json"
            status.write_text('{"status":"failed"}')
            (root / "secret-plaintext.json").write_text("must never be included")
            first, second = root / "first.zip", root / "second.zip"
            storage.make_zip([root / "missing.cms", status], first)
            storage.make_zip([root / "missing.cms", status], second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(archive.namelist(), ["status.json"])

    def test_empty_output_and_directories_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(storage.StorageError):
                storage.make_zip([root / "absent"], root / "out.zip")
            with self.assertRaises(storage.StorageError):
                storage.make_zip([root], root / "out.zip")


class TransportTests(unittest.TestCase):
    def test_cross_host_redirect_strips_authorization(self):
        req = urllib.request.Request("https://api.github.com/repos/o/r/actions/artifacts/1/zip", headers={"Authorization": "Bearer SECRET"})
        redirected = storage.SafeRedirect().redirect_request(req, None, 302, "", {}, "https://blob.example/download?sig=signed")
        self.assertIsNone(redirected.get_header("Authorization"))

    def test_draft_discovery_uses_paginated_release_list(self):
        client = storage.GitHub("owner/repo", "dummy")
        target = {"id": 99, "draft": True, "tag_name": "desired"}
        calls = []
        def fake_api(method, path, payload=None):
            calls.append((method, path))
            if path.endswith("page=1"):
                return [{"id": i, "tag_name": f"other-{i}", "draft": True} for i in range(100)]
            if path.endswith("page=2"):
                return [target]
            raise AssertionError(path)
        client.api = fake_api
        self.assertEqual(client.ensure_release("desired"), target)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("/releases?" in path for _, path in calls))

    def test_interrupted_download_restarts_complete_transfer(self):
        client = storage.GitHub("owner/repo", "dummy")
        class Broken(io.BytesIO):
            def read(self, _n=-1):
                raise ConnectionError("interrupted")
        opener = mock.Mock()
        opener.open.side_effect = [Broken(b"partial"), io.BytesIO(b"complete")]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(storage.urllib.request, "build_opener", return_value=opener), mock.patch.object(storage.time, "sleep"):
            facts = client.download("/actions/artifacts/1/zip", Path(tmp) / "copy.zip")
            self.assertEqual(facts, (8, digest(b"complete")))
        self.assertEqual(opener.open.call_count, 2)

    def test_secondary_rate_limit_without_retry_after_is_retried(self):
        client = storage.GitHub("owner/repo", "dummy")
        opener = mock.Mock()
        error = urllib.error.HTTPError("https://api.github.com/repos/owner/repo/releases", 403, "Forbidden", {"X-RateLimit-Remaining": "200"}, io.BytesIO(b'{"message":"You have exceeded a secondary rate limit."}'))
        opener.open.side_effect = [error, io.BytesIO(b'{"ok":true}')]
        with mock.patch.object(storage.urllib.request, "build_opener", return_value=opener), mock.patch.object(storage.time, "sleep") as sleep, mock.patch("builtins.print"):
            self.assertEqual(client.api("GET", "/releases"), {"ok": True})
        sleep.assert_called_once_with(60)
        self.assertEqual(opener.open.call_count, 2)

    def test_forbidden_error_preserves_reason_and_redacts_credentials(self):
        client = storage.GitHub("owner/repo", "dummy-secret-token")
        opener = mock.Mock()
        payload = json.dumps({"message": "Resource not accessible by integration; token dummy-secret-token; https://host.example/path?signature=private"}).encode()
        opener.open.side_effect = urllib.error.HTTPError("https://api.github.com/repos/owner/repo/releases", 403, "Forbidden", {}, io.BytesIO(payload))
        with mock.patch.object(storage.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(storage.ApiError) as raised:
                client.api("POST", "/releases", {"draft": True})
        self.assertIn("Resource not accessible by integration", str(raised.exception))
        self.assertNotIn("dummy-secret-token", str(raised.exception))
        self.assertNotIn("signature=private", str(raised.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
