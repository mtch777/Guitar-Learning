#!/usr/bin/env python3
"""Keep encrypted analysis outputs in draft Releases, outside Actions storage.

Migration preserves each Actions ZIP byte-for-byte. A source artifact is deleted
only after a durable source manifest and a matching Release asset are verified.
No command publishes a Release, decrypts data, or overwrites a differing asset.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile


class StorageError(RuntimeError):
    pass


class ApiError(StorageError):
    def __init__(self, status: int, method: str, message: str = ""):
        self.status = status
        suffix = f": {message}" if message else ""
        super().__init__(f"GitHub API {method} failed with HTTP {status}{suffix}")


def sanitized_message(message: str, token: str) -> str:
    """Keep GitHub's actionable reason without credentials or signed queries."""
    message = str(message).replace(token, "[REDACTED]") if token else str(message)
    message = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b", "[REDACTED]", message)
    message = re.sub(r"(?i)Bearer\s+[^\s,;]+", "Bearer [REDACTED]", message)
    message = re.sub(r"https?://[^\s<>\"]+", lambda m: m.group(0).split("?", 1)[0].split("#", 1)[0], message)
    return " ".join(message.split())[:400]


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward the GitHub token to signed object-storage redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and urllib.parse.urlsplit(req.full_url).netloc != urllib.parse.urlsplit(newurl).netloc:
            redirected.remove_header("Authorization")
        return redirected


def file_facts(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return size, "sha256:" + digest.hexdigest()


def require_facts(size: int, digest: str, expected_size: int, expected_digest: str, label: str):
    if size != expected_size or digest != expected_digest:
        raise StorageError(f"Checksum/size mismatch for {label}; source retained")


def safe_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise StorageError("Unsafe asset name")
    return name


class GitHub:
    def __init__(self, repository: str, token: str):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise StorageError("GITHUB_REPOSITORY must be owner/repository")
        if not token:
            raise StorageError("GH_TOKEN or GITHUB_TOKEN is required")
        self.repository = repository
        self.token = token
        self.prefix = f"https://api.github.com/repos/{repository}"

    @contextlib.contextmanager
    def request(self, method, path, payload=None, file=None, accept="application/vnd.github+json"):
        url = path if path.startswith("https://") else self.prefix + path
        if urllib.parse.urlsplit(url).hostname not in {"api.github.com", "uploads.github.com"}:
            raise StorageError("Refusing to send token outside GitHub API/upload hosts")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Guitar-Learning-Release-Storage",
        }
        if payload is not None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        else:
            body = None
        if file is not None:
            headers["Content-Type"] = "application/octet-stream"
            headers["Content-Length"] = str(file.stat().st_size)
        # A separate opener per request avoids sharing mutable handlers among workers.
        response = None
        for attempt in range(8):
            stream = file.open("rb") if file is not None else None
            try:
                req = urllib.request.Request(url, data=stream or body, headers=headers, method=method)
                response = urllib.request.build_opener(SafeRedirect()).open(req, timeout=180)
                break
            except urllib.error.HTTPError as error:
                secondary = False
                message = ""
                try:
                    message = sanitized_message(json.loads(error.read(16384)).get("message", ""), self.token)
                    secondary = error.code == 403 and ("secondary rate limit" in message.lower() or "abuse detection" in message.lower())
                except (ValueError, AttributeError):
                    pass
                retry = error.code in (429, 500, 502, 503, 504) or (
                    error.code == 403 and (secondary or error.headers.get("Retry-After") or error.headers.get("X-RateLimit-Remaining") == "0")
                )
                if not retry or attempt == 7:
                    raise ApiError(error.code, method, message) from None
                delay = max(2 ** attempt, int(error.headers.get("Retry-After", "0")))
                if secondary:
                    delay = max(delay, min(900, 60 * 2 ** attempt))
                if error.headers.get("X-RateLimit-Remaining") == "0":
                    delay = max(delay, int(error.headers.get("X-RateLimit-Reset", "0")) - int(time.time()) + 2)
                if delay > 3700:
                    raise StorageError("GitHub requested a rate-limit wait longer than one hour; safe to rerun") from None
                print(f"GitHub rate/availability limit; retrying {method} after {delay} seconds", flush=True)
                while delay > 0:
                    chunk = min(60, delay)
                    time.sleep(chunk)
                    delay -= chunk
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                if attempt == 7:
                    raise StorageError(f"GitHub {method} transfer failed; source retained") from None
                time.sleep(min(30, 2 ** attempt))
            finally:
                if stream is not None:
                    stream.close()
        # There must be only one yield: retrying a consumer exception from a
        # contextmanager would cause 'generator did not stop after throw'.
        try:
            yield response
        finally:
            response.close()

    def api(self, method, path, payload=None):
        with self.request(method, path, payload=payload) as response:
            data = response.read()
        return json.loads(data) if data else None

    def download(self, path: str, destination: Path) -> tuple[int, str]:
        # Actions archive endpoints negotiate a JSON redirect, while Release
        # assets require octet-stream to request bytes instead of metadata.
        accept = "application/vnd.github+json" if path.startswith("/actions/artifacts/") else "application/octet-stream"
        for attempt in range(6):
            try:
                with self.request("GET", path, accept=accept) as response:
                    with destination.open("wb") as output:
                        while chunk := response.read(1024 * 1024):
                            output.write(chunk)
                return file_facts(destination)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.IncompleteRead):
                if attempt == 5:
                    raise StorageError("Binary download failed; source retained") from None
                time.sleep(min(30, 2 ** attempt))

    def artifacts(self, run_id: int) -> list[dict]:
        rows = []
        page = 1
        while True:
            result = self.api("GET", f"/actions/runs/{run_id}/artifacts?per_page=100&page={page}")
            rows.extend(result["artifacts"])
            if len(rows) >= result["total_count"]:
                return rows
            if not result["artifacts"]:
                raise StorageError("Incomplete artifact pagination")
            page += 1

    def assets(self, release_id: int) -> list[dict]:
        rows = []
        page = 1
        while True:
            batch = self.api("GET", f"/releases/{release_id}/assets?per_page=100&page={page}")
            rows.extend(batch)
            if len(batch) < 100:
                return rows
            page += 1

    def ensure_release(self, tag: str, target: str | None = None) -> dict:
        def find():
            page, matches = 1, []
            while True:
                batch = self.api("GET", f"/releases?per_page=100&page={page}")
                matches.extend(r for r in batch if r.get("tag_name") == tag)
                if len(batch) < 100:
                    break
                page += 1
            if len(matches) > 1:
                raise StorageError("Multiple Releases use the destination tag")
            return matches[0] if matches else None

        # The by-tag endpoint is documented for published Releases. Listing with
        # write access is required to reliably discover drafts during resumes.
        release = find()
        if release is None:
            payload = {
                "tag_name": tag,
                "name": f"Encrypted analysis archive — {tag}",
                "draft": True,
                "prerelease": False,
                "make_latest": "false",
                "body": "Encrypted analysis outputs stored outside GitHub Actions artifact storage. Keep this Release as a draft. Original CMS encryption is preserved.",
            }
            if target:
                payload["target_commitish"] = target
            try:
                release = self.api("POST", "/releases", payload)
            except ApiError as creation_error:
                if creation_error.status != 422:
                    raise
                release = find()
                if release is None:
                    raise StorageError("Release creation conflicted but destination was not found") from None
        require_draft(release, tag)
        return release

    def upload(self, release: dict, name: str, path: Path) -> dict:
        url = release["upload_url"].split("{", 1)[0] + "?name=" + urllib.parse.quote(name, safe="")
        with self.request("POST", url, file=path) as response:
            return json.load(response)


def require_draft(release: dict, tag: str):
    if release.get("draft") is not True or release.get("tag_name") != tag:
        raise StorageError("Destination must be the expected draft Release; source retained")


def asset_map(client, release: dict) -> dict[str, dict]:
    assets = client.assets(release["id"])
    result = {a["name"]: a for a in assets}
    if len(result) != len(assets):
        raise StorageError("Duplicate Release asset names")
    return result


def verify_asset(client, asset: dict, expected_size: int, expected_digest: str):
    # List/upload responses are authoritative server metadata. Avoid a redundant
    # GET per file: a 309-file move already needs 927 download/upload/delete calls.
    current = asset
    if current.get("state") != "uploaded" or current.get("size") != expected_size:
        raise StorageError("Release asset is incomplete or has wrong size; source retained")
    digest = current.get("digest")
    if digest:
        require_facts(current["size"], digest, expected_size, expected_digest, current["name"])
    else:
        with tempfile.TemporaryDirectory(prefix="release-check-") as tmp:
            size, actual_digest = client.download(f"/releases/assets/{current['id']}", Path(tmp) / "asset")
        require_facts(size, actual_digest, expected_size, expected_digest, current["name"])
    return current


def ensure_asset(client, release: dict, name: str, path: Path, existing: dict | None = None):
    safe_name(name)
    expected_size, expected_digest = file_facts(path)
    if expected_size >= 2 * 1024 ** 3:
        raise StorageError("Release asset must be smaller than 2 GiB")
    if existing is None:
        try:
            existing = client.upload(release, name, path)
        except StorageError:
            # A timeout/duplicate response may follow a completed upload. Never
            # replace it: only accept the exact bytes we were trying to store.
            existing = asset_map(client, release).get(name)
            if existing is None:
                raise
    if existing.get("name") != name:
        raise StorageError("Release returned the wrong asset name; source retained")
    return verify_asset(client, existing, expected_size, expected_digest)


def artifact_record(artifact: dict, run_id: int) -> dict:
    if artifact.get("workflow_run", {}).get("id") != run_id:
        raise StorageError("Artifact belongs to another run; source retained")
    if artifact.get("expired"):
        raise StorageError("Source artifact has expired; source retained")
    digest = artifact.get("digest", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise StorageError("Source artifact lacks a valid SHA256 digest; source retained")
    name = safe_name(artifact["name"])
    return {"id": artifact["id"], "name": name, "asset_name": name + ".zip", "size_in_bytes": artifact["size_in_bytes"], "digest": digest, "run_id": run_id}


def load_or_create_manifest(client, release, run, current, expected_count, expected_bytes):
    name = "source-artifacts.json"
    assets = asset_map(client, release)
    with tempfile.TemporaryDirectory(prefix="release-manifest-") as tmp:
        path = Path(tmp) / name
        if name in assets:
            size, digest = client.download(f"/releases/assets/{assets[name]['id']}", path)
            verify_asset(client, assets[name], size, digest)
            manifest = json.loads(path.read_text())
        else:
            records = [artifact_record(a, run["id"]) for a in current]
            manifest = {"version": 1, "repository": client.repository, "run_id": run["id"], "head_sha": run["head_sha"], "artifacts": records}
            validate_manifest(manifest, client.repository, run["id"], expected_count, expected_bytes)
            path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            ensure_asset(client, release, name, path)
        validate_manifest(manifest, client.repository, run["id"], expected_count, expected_bytes)
    originals = {r["id"]: r for r in manifest["artifacts"]}
    for a in current:
        if artifact_record(a, run["id"]) != originals.get(a["id"]):
            raise StorageError("Current source does not match saved manifest; source retained")
    return manifest


def validate_manifest(manifest, repository, run_id, expected_count, expected_bytes):
    if manifest.get("version") != 1 or manifest.get("repository") != repository or manifest.get("run_id") != run_id:
        raise StorageError("Source manifest identity mismatch; source retained")
    records = manifest.get("artifacts", [])
    if len(records) != expected_count or sum(r["size_in_bytes"] for r in records) != expected_bytes:
        raise StorageError("Source manifest count/bytes mismatch; source retained")
    if len({r["id"] for r in records}) != len(records) or len({r["asset_name"] for r in records}) != len(records):
        raise StorageError("Duplicate manifest entries; source retained")
    for r in records:
        if r["run_id"] != run_id or r["asset_name"] != safe_name(r["name"]) + ".zip" or not re.fullmatch(r"sha256:[0-9a-f]{64}", r["digest"]):
            raise StorageError("Invalid source manifest entry; source retained")


def migrate_one(client, release, record, source, existing):
    expected_size, expected_digest = record["size_in_bytes"], record["digest"]
    if existing is not None:
        verify_asset(client, existing, expected_size, expected_digest)
    else:
        if source is None:
            raise StorageError(f"Missing source and destination for artifact {record['id']}")
        with tempfile.TemporaryDirectory(prefix="artifact-move-") as tmp:
            archive = Path(tmp) / record["asset_name"]
            size, digest = client.download(f"/actions/artifacts/{record['id']}/zip", archive)
            require_facts(size, digest, expected_size, expected_digest, record["name"])
            ensure_asset(client, release, record["asset_name"], archive)
    if source is not None:
        # Actions artifact IDs are immutable. The exact run, ID, SHA256, and size
        # were checked against the durable manifest before any workers started.
        if artifact_record(source, record["run_id"]) != record:
            raise StorageError("Source differs from manifest; source retained")
        try:
            client.api("DELETE", f"/actions/artifacts/{record['id']}")
        except ApiError as error:
            if error.status != 404:  # A lost DELETE response can already have succeeded.
                raise
        return "moved"
    return "already_moved"


def migrate(client, run_id, expected_count, expected_bytes, workers=3):
    run = client.api("GET", f"/actions/runs/{run_id}")
    if run.get("id") != run_id or run.get("status") != "completed":
        raise StorageError("Source run must be the selected completed run")
    current = client.artifacts(run_id)
    # Validate all remaining sources before any storage mutation.
    for a in current:
        artifact_record(a, run_id)
    # A workflow token is authorized for its current commit. Tag the archive at
    # that commit (or GitHub's default branch outside Actions); the manifest below
    # independently retains the original source run's head_sha for provenance.
    release = client.ensure_release(f"tiered-analysis-run-{run_id}", os.environ.get("GITHUB_SHA"))
    require_draft(release, f"tiered-analysis-run-{run_id}")
    manifest = load_or_create_manifest(client, release, run, current, expected_count, expected_bytes)
    existing = asset_map(client, release)
    by_id = {a["id"]: a for a in current}
    # A failed partial migration must have a verified surviving destination for
    # every already-deleted source before proceeding with new deletions.
    for record in manifest["artifacts"]:
        if record["id"] not in by_id:
            asset = existing.get(record["asset_name"])
            if asset is None:
                raise StorageError("Prior migration has a missing destination; remaining sources retained")
            verify_asset(client, asset, record["size_in_bytes"], record["digest"])
    counts = {"moved": 0, "already_moved": 0}
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(migrate_one, client, release, record, by_id.get(record["id"]), existing.get(record["asset_name"])): record for record in manifest["artifacts"]}
        for future in concurrent.futures.as_completed(futures):
            record = futures[future]
            try:
                result = future.result()
                counts[result] += 1
                print(f"{result}: {record['name']} ({record['size_in_bytes']} bytes)", flush=True)
            except Exception as error:
                errors.append(f"artifact {record['id']}: {type(error).__name__}: {error}")
                print(f"FAILED: artifact {record['id']}; original retained", flush=True)
    remaining = client.artifacts(run_id)
    summary = {"run_id": run_id, "release_url": release["html_url"], "draft": True, "expected_count": expected_count, "expected_bytes": expected_bytes, **counts, "remaining_artifacts": len(remaining), "remaining_bytes": sum(a["size_in_bytes"] for a in remaining), "errors": errors}
    print(json.dumps(summary, indent=2), flush=True)
    if errors or remaining:
        raise StorageError(f"Migration incomplete: {len(errors)} errors, {len(remaining)} remaining source artifacts; safe to rerun")
    return summary


def make_zip(paths: list[Path], destination: Path):
    existing = [p for p in paths if p.exists()]
    if not existing:
        raise StorageError("No output files exist")
    if any(not p.is_file() or p.is_symlink() for p in existing):
        raise StorageError("Only explicit regular files may be archived")
    if len({p.name for p in existing}) != len(existing):
        raise StorageError("Duplicate basenames in output archive")
    # Fixed metadata gives repeatable bytes on retried packaging steps.
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(existing, key=lambda p: p.name):
            entry = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.external_attr = 0o600 << 16
            with path.open("rb") as source, archive.open(entry, "w", force_zip64=True) as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)


def upload_files(client, tag, name, paths):
    safe_name(name)
    release = client.ensure_release(tag, os.environ.get("GITHUB_SHA"))
    require_draft(release, tag)
    with tempfile.TemporaryDirectory(prefix="release-output-") as tmp:
        path = Path(tmp) / name
        make_zip(paths, path)
        asset = ensure_asset(client, release, name, path)
    print(json.dumps({"release_url": release["html_url"], "asset": asset["name"], "size": asset["size"], "digest": asset.get("digest"), "draft": True}), flush=True)
    return asset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    move = sub.add_parser("migrate")
    move.add_argument("--run-id", type=int, required=True)
    move.add_argument("--expected-count", type=int, required=True)
    move.add_argument("--expected-bytes", type=int, required=True)
    move.add_argument("--workers", type=int, choices=range(1, 5), default=3)
    upload = sub.add_parser("upload")
    upload.add_argument("--tag", required=True)
    upload.add_argument("--asset-name", required=True)
    upload.add_argument("--file", type=Path, action="append", required=True)
    args = parser.parse_args()
    client = GitHub(os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", ""))
    if args.command == "migrate":
        migrate(client, args.run_id, args.expected_count, args.expected_bytes, args.workers)
    else:
        upload_files(client, args.tag, args.asset_name, args.file)


if __name__ == "__main__":
    try:
        main()
    except StorageError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
