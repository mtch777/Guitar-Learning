#!/usr/bin/env python3
"""Repair previously saved MIDI-backed scores only if source-note fidelity fails.

Never repair a public song by silently suppressing the mismatch; reconstruct it
from its retained original MIDI, rebuild the exact lesson catalog, and validate
the result with the independent MIDI/score comparison.
"""
import importlib.util
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / 'public/piano/learning-songs'
VALIDATOR = ROOT / 'scripts/piano/assert-midi-import.mjs'
CONVERTER = ROOT / 'scripts/piano/import-midi-url.py'


def run(*args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=120)


def score_title(xml_path, labels):
    title = labels.get(xml_path.name, {}).get('title')
    if title:
        return title
    try:
        tree = ET.parse(xml_path)
        return tree.findtext('./work/work-title') or tree.findtext('./movement-title') or ''
    except (ET.ParseError, OSError):
        return ''


def main():
    spec = importlib.util.spec_from_file_location('piano_import', CONVERTER)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    seed = json.loads((LIBRARY / 'song-library.seed.json').read_text())
    labels = seed.get('uploadedLabels', {})
    repaired = []
    for midi in sorted((LIBRARY / 'uploads').glob('midi-*.mid')):
        xml = midi.with_suffix('.musicxml')
        if not xml.exists():
            raise RuntimeError(f'Stored MIDI missing MusicXML: {midi.name}')
        check = run('node',str(VALIDATOR),xml.name)
        if check.returncode == 0:
            print(f'Fidelity OK: {midi.name}', flush=True)
            continue
        print(f'Fidelity mismatch: {xml.name}. Rebuilding from original MIDI.', flush=True)
        print((check.stderr or check.stdout)[-700:], flush=True)
        title = score_title(xml, labels)
        converter.import_bytes(midi.read_bytes(), LIBRARY, title, replace_existing=True)
        build = run('npm','run','prebuild')
        if build.returncode:
            raise RuntimeError(f'Catalog rebuild failed: {build.stderr[-500:]}')
        again = run('node',str(VALIDATOR),xml.name)
        if again.returncode:
            raise RuntimeError(f'Rebuilt MIDI still fails fidelity: {xml.name}: {again.stderr[-600:]}')
        repaired.append(xml.name)
        print(f'Fidelity REPAIRED: {xml.name}', flush=True)
    print(f'Existing MIDI archive verified; repaired {len(repaired)}: {repaired}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
