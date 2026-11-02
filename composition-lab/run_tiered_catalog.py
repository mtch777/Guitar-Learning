"""Capture and verify one Songsterr ID with the existing whole-song tiered pipeline.

Runs are intentionally isolated: a failed ID remains an auditable failure, and
the private captured notation is never committed to source control.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback


ROOT = Path(__file__).resolve().parent
API = ROOT / "songsterr_automation" / "songsterr_api"
EXPECTED_ARTISTS = {53238: "Invent Animate", 57932: "Currents", 17808: "ERRA"}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def catalog(client):
    """Freeze exact artist-ID results; reject changed counts rather than omit songs."""
    expected_counts = {53238: 72, 57932: 103, 17808: 133}
    records = []
    for artist_id, artist in EXPECTED_ARTISTS.items():
        matches = client._json("https://www.songsterr.com/api/songs", pattern=artist, size=250)
        selected = [r for r in matches if r.get("artistId") == artist_id]
        if len(selected) != expected_counts[artist_id]:
            raise RuntimeError(f"Catalog changed for {artist}: {len(selected)} instead of {expected_counts[artist_id]}; inspect before proceeding")
        records.extend({"artist": artist, "artist_id": artist_id, "song_id": r["songId"], "title": r["title"]} for r in selected)
    ids = [r["song_id"] for r in records]
    if len(ids) != 308 or len(ids) != len(set(ids)):
        raise RuntimeError("Expected 308 distinct Songsterr tab IDs")
    return records


def run_song(song_id, output, client):
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite previous result: {output}")
    capture = output / "capture"
    capture.mkdir(parents=True)
    result = {"song_id": song_id, "status": "capture_pending", "started_utc": datetime.now(timezone.utc).isoformat()}
    write_json(output / "status.json", result)
    try:
        metadata = client.meta(song_id)
        if metadata.get("artistId") not in EXPECTED_ARTISTS:
            raise ValueError(f"Unexpected artist identity for {song_id}: {metadata.get('artistId')}")
        write_json(capture / "metadata.json", metadata)
        for part in range(len(metadata["tracks"])):
            data = client.track(song_id, metadata["revisionId"], metadata["image"], part)
            write_json(capture / f"track-{part}.json", data)
        result.update(status="captured", artist=metadata["artist"], title=metadata["title"], revision_id=metadata["revisionId"], tracks=len(metadata["tracks"]))
        write_json(output / "status.json", result)
        bundle = output / "tiered"
        subprocess.run([sys.executable, str(ROOT / "build_tiered_song.py"), str(capture), str(bundle)], check=True)
        result["status"] = "built"
        write_json(output / "status.json", result)
        subprocess.run([sys.executable, str(ROOT / "verify_tiered_song.py"), str(bundle), str(capture)], check=True)
        qa = json.loads((bundle / "qa.json").read_text(encoding="utf-8"))
        if qa.get("status") != "pass":
            raise RuntimeError("Verifier did not report PASS")
        result.update(status="verified", checks=qa.get("checks"), completed_utc=datetime.now(timezone.utc).isoformat())
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc(), completed_utc=datetime.now(timezone.utc).isoformat())
    write_json(output / "status.json", result)
    print(json.dumps({k:v for k,v in result.items() if k not in ("traceback", "checks")}), flush=True)
    return result["status"] == "verified"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog", action="store_true")
    p.add_argument("--song-id", type=int)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if not args.catalog and (args.song_id is None or args.output is None):
        p.error("Provide --catalog, or --song-id and --output")
    if args.output and "local-artifacts" not in args.output.resolve().parts:
        p.error("The private output must be under local-artifacts")
    sys.path.insert(0, os.environ.get("SONGSTERR_CLIENT_ROOT", "/tmp/songsterr-dl"))
    from songsterr_dl.client import SongsterrClient
    with SongsterrClient(timeout=30) as client:
        if args.catalog:
            print(json.dumps(catalog(client), ensure_ascii=False))
            return 0
        return 0 if run_song(args.song_id, args.output, client) else 1


if __name__ == "__main__":
    raise SystemExit(main())
