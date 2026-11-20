#!/usr/bin/env python3
"""Live, reproducible MuseScore score-page -> MIDI -> MusicXML -> lesson QA.

Uses only publicly accessible score pages and their ordinary MIDI player
responses. No authentication, rate-limit evasion, or challenge bypass.
"""
import argparse
import asyncio
import importlib.util
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = [
    ("Fur Elise (classic)", "https://musescore.com/user/80622691/scores/22174756"),
    ("Chopin Waltz E minor", "https://musescore.com/user/83901187/scores/21198217"),
    ("Fur Elise (easy)", "https://musescore.com/user/40809218/scores/23115931"),
    ("Fur Elise (short)", "https://musescore.com/user/37958464/scores/10462393"),
    ("Satie Gymnopedie", "https://musescore.com/user/69359/scores/5701234"),
    ("Satie Gymnopedie in C", "https://musescore.com/user/76124581/scores/21552796"),
    ("Mozart Turkish March", "https://musescore.com/user/35940294/scores/39456287"),
    ("Mozart Rondo alla Turca", "https://musescore.com/user/938326/scores/1050521"),
    ("Mozart Rondo alternative", "https://musescore.com/user/123036626/scores/39976808"),
    ("Bach Prelude BWV 846", "https://musescore.com/user/561641/scores/4137556"),
    ("Joplin Maple Leaf Rag", "https://musescore.com/user/38861570/scores/7885172"),
    ("Joplin Maple Leaf alternative", "https://musescore.com/user/58480/scores/529121"),
    ("Satie Gymnopedie recent", "https://musescore.com/user/62439082/scores/39846665"),
    ("Joplin Maple Leaf recent", "https://musescore.com/user/108525727/scores/40054243"),
]
SEED = 20261119


def load_script(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(limit=14, target=4):
    imports = ROOT / "public/piano/learning-songs"
    parser = load_script(ROOT / "scripts/piano/import-musescore-score.py", "musescore_qa")
    converter = parser.load_converter()
    rng = random.Random(SEED)
    scores = list(CANDIDATES)
    rng.shuffle(scores)
    report = []
    consecutive = 0
    # Full catalog validation verifies that imported MusicXML is readable by
    # the actual JS lesson parser, including valid ties and chord timing.
    for index, (name, page) in enumerate(scores[:limit], 1):
        print(f"QA ATTEMPT {index} | {name} | {page}", flush=True)
        result = {"attempt": index, "title": name, "url": page}
        try:
            midi_url = asyncio.run(parser.retrieve_url(page))
            if not midi_url:
                raise ValueError("No MIDI URL obtained from public score-page player")
            xml_path = converter.import_midi(midi_url, imports, name)
            build = subprocess.run(["npm", "run", "prebuild"], cwd=ROOT,
                                   capture_output=True, text=True, timeout=90)
            if build.returncode:
                raise RuntimeError(f"Catalog build failed: {build.stderr[-500:]}")
            catalog = json.loads((imports / "song-library.json").read_text())
            song = next((song for song in catalog["songs"]
                         if song.get("sourceFilename") == xml_path.name), None)
            if not song or not song.get("attackCount"):
                failures = [e for e in catalog.get("importErrors", [])
                            if e.get("sourceFilename") == xml_path.name]
                raise ValueError(f"Lesson parser rejected imported score: {failures or 'not in catalog'}")
            result.update(outcome="PASS", attacks=song["attackCount"],
                          notes=song["noteCount"])
            consecutive += 1
        except Exception as exc:
            msg = str(exc).replace("\n", " ")[:350]
            result.update(outcome="FAIL", reason=msg)
            consecutive = 0
        report.append(result)
        print(f"QA RESULT {index} {result['outcome']}: {result.get('reason', str(result.get('attacks', 0)) + ' attacks')} | consecutive={consecutive}", flush=True)
        if consecutive >= target:
            break
    out = ROOT / "musescore-live-qa-results.json"
    out.write_text(json.dumps({"target": target, "seed": SEED,
                                "consecutive": consecutive, "results": report}, indent=2))
    print(f"QA FINAL {consecutive}/{target} consecutive successful score-page imports out of {len(report)} sampled URLs.", flush=True)
    return 0 if consecutive >= target else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=14)
    ap.add_argument("--target", type=int, default=4)
    args = ap.parse_args()
    sys.exit(run(args.limit, args.target))
