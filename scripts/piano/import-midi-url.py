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
import xml.etree.ElementTree as ET
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



def xml_text(value):
    """Keep only legal XML 1.0 scalar values in imported metadata."""
    return ''.join(char for char in str(value) if ord(char) in (9, 10, 13)
                   or 32 <= ord(char) <= 0xD7FF
                   or 0xE000 <= ord(char) <= 0xFFFD
                   or 0x10000 <= ord(char) <= 0x10FFFF)


def score_from_midi_bytes(data, title=''):
    """Decode original MIDI note-on/off ticks before building stable cross-bar notation."""
    from collections import defaultdict, deque
    from fractions import Fraction
    from io import BytesIO
    import mido
    from music21 import chord, key, metadata, meter, tempo, note, stream

    midi_file = mido.MidiFile(file=BytesIO(data))
    ppq = midi_file.ticks_per_beat
    if ppq <= 0:
        raise ValueError('SMPTE-timed MIDI is not supported; export in PPQ timing.')
    tracks, meters, tempos, keys = [], [], [], []
    for track_index, track in enumerate(midi_file.tracks):
        tick, name = 0, ''
        active = defaultdict(deque)
        notes = []
        for event in track:
            tick += event.time
            if event.is_meta:
                if event.type == 'track_name' and not name:
                    name = xml_text(event.name)[:100]
                elif event.type == 'time_signature':
                    meters.append((tick, track_index, event.numerator, event.denominator))
                elif event.type == 'set_tempo':
                    tempos.append((tick, track_index, event.tempo))
                elif event.type == 'key_signature':
                    keys.append((tick, track_index, event.key))
                continue
            if event.type == 'note_on' and event.velocity:
                active[(event.channel, event.note)].append(tick)
            elif event.type == 'note_off' or (event.type == 'note_on' and not event.velocity):
                starts = active[(event.channel, event.note)]
                if starts:
                    onset = starts.popleft()
                    if tick > onset and event.channel != 9:
                        notes.append((onset, tick, event.note))
        if any(active.values()):
            raise ValueError(f'MIDI track {track_index+1} contains notes without note-offs.')
        if notes:
            tracks.append((name or f'Track {track_index+1}', notes))
    if not tracks:
        raise ValueError('This MIDI contains no completed pitched notes.')

    def ordered_changes(changes):
        by_tick = {}
        for event in sorted(changes, key=lambda row: (row[0], row[1])):
            by_tick.setdefault(event[0], event[2:])
        return sorted(by_tick.items())

    # MusicXML cannot represent arbitrary sub-tick tuplets produced by raw MIDI
    # jitter. Pick the coarsest standard notation grid within 1/128 quarter;
    # preserve triplet grids (3-based subdivisions) whenever they fit.
    note_ticks = [tick for _, notes in tracks for start, end, _ in notes for tick in (start, end)]
    note_ticks.extend(tick for tick, *_ in meters + tempos + keys)
    def max_grid_error(subdivisions):
        return max((abs(Fraction(round(Fraction(tick*subdivisions, ppq)), subdivisions)
                         - Fraction(tick, ppq)) for tick in note_ticks), default=Fraction(0))
    subdivisions = next((grid for grid in (4, 6, 8, 12, 16, 24, 32, 48, 64)
                         if max_grid_error(grid) <= Fraction(1, 128)), 64)
    def position(tick):
        return Fraction(round(Fraction(tick*subdivisions, ppq)), subdivisions)
    adjustment = max_grid_error(subdivisions)
    if adjustment:
        print(f'Normalized raw MIDI timing to 1/{subdivisions}-quarter grid '
              f'(maximum correction {float(adjustment):.5f} quarter notes).')

    def snapped_changes(changes):
        # The score's rhythmic grid can collapse adjacent MIDI metadata ticks.
        # Retain exactly one event per written position (latest event wins),
        # preventing contradictory tempos or meters at the same onset.
        by_position = {}
        for tick, values in ordered_changes(changes):
            by_position[position(tick)] = values
        return sorted(by_position.items())

    score = stream.Score()
    score.insert(0, metadata.Metadata())
    if title.strip():
        score.metadata.title = xml_text(title).strip()[:100]
    meter_changes = snapped_changes(meters)
    if not meter_changes or meter_changes[0][0] > 0:
        meter_changes.insert(0, (0, (4, 4)))
    meter_stream = stream.Stream()
    for onset, (numerator, denominator) in meter_changes:
        meter_stream.insert(onset, meter.TimeSignature(f'{numerator}/{denominator}'))
    end_time = max((position(end) for _, events in tracks for _, end, _ in events))
    for part_index, (name, events) in enumerate(tracks):
        part = stream.Part()
        part.partName = name
        grouped = defaultdict(set)
        for onset, end, pitch in events:
            snapped_start = position(onset)
            snapped_end = max(position(end), snapped_start + Fraction(1, subdivisions))
            grouped[(snapped_start, snapped_end)].add(pitch)
        for (onset, end), pitches in sorted(grouped.items()):
            duration = end - onset
            musical_note = (chord.Chord(sorted(pitches), quarterLength=duration)
                            if len(pitches) > 1 else note.Note(next(iter(pitches)), quarterLength=duration))
            part.insert(onset, musical_note)
        if part_index == 0:
            for onset, (microseconds_per_beat,) in snapped_changes(tempos):
                part.insert(onset, tempo.MetronomeMark(number=mido.tempo2bpm(microseconds_per_beat)))
            for onset, (signature,) in snapped_changes(keys):
                try:
                    part.insert(onset, key.Key(signature))
                except Exception:
                    pass
        # Music21's per-measure voice assignment can break ties. Allocate on
        # the global timeline, split into measures only afterward.
        part.makeVoices(inPlace=True)
        part = part.makeMeasures(meterStream=meter_stream, refStreamOrTimeRange=[0, end_time])
        part.makeTies(inPlace=True)
        part.partName = name
        score.insert(0, part)
    return score


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
        score = score_from_midi_bytes(data, title)
        if title.strip():
            if score.metadata is None:
                score.insert(0, metadata.Metadata())
            score.metadata.title = xml_text(title).strip()[:100]
        # Never leave a partial or failed conversion in place of a saved song.
        with tempfile.TemporaryDirectory(prefix="piano-midi-", dir=uploads) as temporary:
            temporary_xml = Path(temporary) / "score.musicxml"
            score.write("musicxml", fp=str(temporary_xml))
            # xmldom is lenient; browsers and strict MusicXML consumers are not.
            # Reject illegal XML controls before publishing or replacing a good score.
            ET.parse(temporary_xml)
            temporary_xml.replace(xml_path)
    print(f"Imported {stem}.musicxml ({len(data)} MIDI bytes)")
    return xml_path


def import_midi(url, directory, title=""):
    return import_bytes(download_midi(url), directory, title)


def repair_saved_imports(directory):
    """Repair malformed MIDI-backed XML or mismatched measures from original MIDI."""
    from music21 import converter, stream
    import json

    uploads = directory / "uploads"
    for midi_path in sorted(uploads.glob("midi-*.mid")):
        if not re.fullmatch(r"midi-[a-f0-9]{64}\.mid", midi_path.name):
            continue
        xml_path = midi_path.with_suffix(".musicxml")
        if not xml_path.is_file():
            continue
        try:
            # A browser's lenient XML parser must never let a NUL-containing
            # imported track title bypass strict XML verification.
            ET.parse(xml_path)
        except ET.ParseError:
            seed_path = directory / "song-library.seed.json"
            labels = json.loads(seed_path.read_text()).get("uploadedLabels", {}) if seed_path.exists() else {}
            title = labels.get(xml_path.name, {}).get("title", "")
            import_bytes(midi_path.read_bytes(), directory, title, replace_existing=True)
            print(f"Rebuilt malformed XML from original MIDI: {xml_path.name}")
            continue
        saved = converter.parse(str(xml_path))
        part_grids = [[(measure.offset, measure.barDuration.quarterLength)
                       for measure in part.getElementsByClass(stream.Measure)]
                      for part in saved.parts]
        if not part_grids or all(grid == part_grids[0] for grid in part_grids[1:]):
            continue
        # Parsing the saved XML through music21 can substitute the generic
        # "Music21 Fragment" title even when the original XML has a work-title.
        # Read the original metadata directly so a repair never renames a song.
        root = ET.parse(xml_path).getroot()
        title = root.findtext("./work/work-title") or root.findtext("./movement-title") or ""
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
