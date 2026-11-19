#!/usr/bin/env python3
"""Import a user-provided, directly downloadable MIDI file into the piano library.

This does not access MuseScore's internal API or generate authentication tokens.
"""
import argparse
import hashlib
import os
import re
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES = 12 * 1024 * 1024
ALLOWED_HOSTS = {"s3w.musescore.com", "raw.githubusercontent.com"}


def validate_url(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Use a direct HTTPS MIDI download URL from an allowed host.")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("The download URL is invalid.")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("Redirected downloads are not supported.")


def download_midi(value):
    request = urllib.request.Request(validate_url(value), headers={"User-Agent": "Guitar-Learning-MIDI-Importer/1.0"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        if int(response.headers.get("Content-Length", "0")) > MAX_BYTES:
            raise ValueError("MIDI file exceeds 12 MB.")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or not data.startswith(b"MThd"):
        raise ValueError("The URL did not return a supported MIDI file (12 MB maximum).")
    return data


def preserve_midi_polyphony(score):
    """Make simultaneous, differently held MIDI notes explicit MusicXML voices."""
    from music21 import stream

    for part in score.parts:
        for measure in part.getElementsByClass(stream.Measure):
            if not measure.voices:
                measure.makeVoices(inPlace=True)


def align_midi_measure_grids(score):
    """Re-bar MIDI parts onto one time grid without moving their note events.

    MIDI carries a single timeline, but music21 may infer different meters for
    different tracks (e.g. 6/8 piano and 4/4 accompaniment). MusicXML and OSMD
    expect every part's measure N to refer to the same interval; otherwise the
    engraved notation can omit notes and the lesson's beat positions drift.
    """
    from music21 import meter, stream

    parts = list(score.parts)
    if len(parts) < 2:
        return
    reference = list(parts[0].getElementsByClass(stream.Measure))
    if not reference:
        return
    reference_grid = [(float(measure.offset), float(measure.barDuration.quarterLength))
                      for measure in reference]
    shared_meter = stream.Stream()
    for measure in reference:
        if measure.timeSignature:
            shared_meter.insert(measure.offset, measure.timeSignature)
    if not shared_meter:
        shared_meter.insert(0, meter.TimeSignature('4/4'))

    for part in parts[1:]:
        measures = list(part.getElementsByClass(stream.Measure))
        grid = [(float(measure.offset), float(measure.barDuration.quarterLength))
                for measure in measures]
        if grid == reference_grid:
            continue
        flattened = part.flatten()
        for signature in list(flattened.getElementsByClass(meter.TimeSignature)):
            flattened.remove(signature)
        # Establish voices on the complete timeline before splitting at bar
        # lines, or a held pitch can switch voice mid-tie between measures.
        flattened.makeVoices(inPlace=True)
        rebuilt = flattened.makeMeasures(
            meterStream=shared_meter, refStreamOrTimeRange=[0, score.duration.quarterLength],
        )
        rebuilt.makeTies(inPlace=True)
        rebuilt.partName = part.partName
        score.replace(part, rebuilt)


def import_bytes(data, directory, title="", *, replace_existing=False):
    from music21 import converter, metadata
    if not data.startswith(b"MThd") or len(data) > MAX_BYTES:
        raise ValueError("Invalid MIDI file.")
    digest = hashlib.sha256(data).hexdigest()
    stem = f"midi-{digest}"
    uploads = directory / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    midi_path = uploads / f"{stem}.mid"
    if not midi_path.exists():
        midi_path.write_bytes(data)
    xml_path = uploads / f"{stem}.musicxml"
    if replace_existing or not xml_path.exists():
        score = converter.parse(str(midi_path))
        align_midi_measure_grids(score)
        # music21's MIDI import can leave unequal-length simultaneous notes
        # in a measure without Voices. Its MusicXML writer then serializes
        # those notes sequentially, corrupting timing and cross-bar ties.
        # Explicit Voices preserve the original overlapping MIDI timing.
        preserve_midi_polyphony(score)
        if title.strip():
            if score.metadata is None:
                score.insert(0, metadata.Metadata())
            score.metadata.title = title.strip()[:100]
        # Never leave a partial or failed conversion in place of a saved song.
        with tempfile.TemporaryDirectory(prefix="piano-midi-", dir=uploads) as temporary:
            temporary_xml = Path(temporary) / "score.musicxml"
            score.write("musicxml", fp=str(temporary_xml))
            temporary_xml.replace(xml_path)
    print(f"Imported {stem}.musicxml ({len(data)} MIDI bytes)")
    return xml_path


def import_midi(url, directory, title=""):
    return import_bytes(download_midi(url), directory, title)


def repair_saved_imports(directory):
    """Repair old MIDI-backed XML only if the parts' time grids disagree."""
    from music21 import converter, stream

    uploads = directory / "uploads"
    for midi_path in sorted(uploads.glob("midi-*.mid")):
        if not re.fullmatch(r"midi-[a-f0-9]{64}\.mid", midi_path.name):
            continue
        xml_path = midi_path.with_suffix(".musicxml")
        if not xml_path.is_file():
            continue
        saved = converter.parse(str(xml_path))
        part_grids = [[(measure.offset, measure.barDuration.quarterLength)
                       for measure in part.getElementsByClass(stream.Measure)]
                      for part in saved.parts]
        if not part_grids or all(grid == part_grids[0] for grid in part_grids[1:]):
            continue
        title = saved.metadata.title if saved.metadata else ""
        import_bytes(midi_path.read_bytes(), directory, title or "", replace_existing=True)
        print(f"Repaired inconsistent measures in {xml_path.name}")


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--file", type=Path)
    source.add_argument("--repair-saved", action="store_true")
    parser.add_argument("--title", default="")
    parser.add_argument("--library", type=Path, default=Path("public/piano/learning-songs"))
    args = parser.parse_args()
    if args.repair_saved:
        repair_saved_imports(args.library)
        return
    if args.file:
        xml_path = import_bytes(args.file.read_bytes(), args.library, args.title)
    else:
        xml_path = import_midi(args.url, args.library, args.title)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"source_filename={xml_path.name}\n")


if __name__ == "__main__":
    main()
