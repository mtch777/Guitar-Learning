"""Standalone Guitar Pro 7 (.gp) archive inspection and lossless round-trip.

Python standard library only. This module does NOT modify the existing web app.
A round-trip copies every archive entry, including score.gpif, exactly as stored
(logical content). It is not yet a score composer or a GPIF serializer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

REQUIRED = ("VERSION", "Content/score.gpif")

class GPFormatError(ValueError):
    pass

def inspect_gp(path: str | Path) -> dict:
    path = Path(path)
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            missing = set(REQUIRED) - names
            if missing:
                raise GPFormatError(f"Missing required entries: {sorted(missing)}")
            version = archive.read("VERSION").decode("utf-8").strip()
            if not version.startswith("7."):
                raise GPFormatError(f"Expected GP7 archive, got VERSION={version!r}")
            score = ET.fromstring(archive.read("Content/score.gpif"))
            if score.tag != "GPIF":
                raise GPFormatError(f"Unexpected score root: {score.tag}")
            def count(tag: str) -> int:
                node = score.find(tag)
                return len(node) if node is not None else 0
            tracks = []
            for track in score.findall("./Tracks/Track"):
                staves = track.findall("./Staves/Staff")
                tracks.append({
                    "name": track.findtext("Name") or "(unnamed)",
                    "staves": len(staves),
                })
            return {
                "file": path.name,
                "version": version,
                "gp_version": score.findtext("GPVersion"),
                "tracks": count("Tracks"),
                "master_bars": count("MasterBars"),
                "bars": count("Bars"),
                "voices": count("Voices"),
                "beats": count("Beats"),
                "notes": count("Notes"),
                "rhythms": count("Rhythms"),
                "track_names": [t["name"] for t in tracks],
                "archive_members": len(names),
            }
    except (zipfile.BadZipFile, ET.ParseError, UnicodeDecodeError) as exc:
        raise GPFormatError(f"Invalid Guitar Pro archive: {path}: {exc}") from exc

def roundtrip_gp(source: str | Path, destination: str | Path) -> dict:
    """Write a NEW .gp archive preserving all member content and ZIP metadata.

    No edits are made to musical data. Verify re-read and exact per-member bytes.
    """
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError("Source and destination must differ")
    original = inspect_gp(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(destination, "w") as dst:
        for member in src.infolist():
            dst.writestr(member, src.read(member.filename))
    restored = inspect_gp(destination)
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(destination) as dst:
        if src.namelist() != dst.namelist():
            raise AssertionError("Archive member order changed")
        for name in src.namelist():
            if hashlib.sha256(src.read(name)).digest() != hashlib.sha256(dst.read(name)).digest():
                raise AssertionError(f"Content changed: {name}")
    if {k: v for k, v in original.items() if k != "file"} != {k: v for k, v in restored.items() if k != "file"}:
        raise AssertionError("Score summary changed")
    return {"source": original, "output": str(destination), "all_members_identical": True}

def main() -> None:
    parser = argparse.ArgumentParser(description="Independent GP7 archive validation")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Show GP7 score summary")
    inspect.add_argument("files", nargs="+", type=Path)
    copy = commands.add_parser("roundtrip", help="Copy and verify complete GP7 archive")
    copy.add_argument("source", type=Path)
    copy.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.command == "inspect":
        results = [inspect_gp(p) for p in args.files]
        print(json.dumps(results, indent=2))
    else:
        print(json.dumps(roundtrip_gp(args.source, args.destination), indent=2))

if __name__ == "__main__":
    main()
