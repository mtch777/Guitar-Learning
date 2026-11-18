#!/usr/bin/env python3
"""Reproduce the practice score from the preserved Edgar Roock MIDI.

Requires mido==1.3.3. Run from any directory:
  python scripts/piano/convert_phoebe_midi.py [path/to/source.mid]

All note pitches/occurrences survive. MusicXML is a NOTATION conversion:
starts/releases snap to the nearest 1/32 note, and staff, voice, enharmonic
spelling and ties are derived. Exact source timing/velocity remains in the
untouched MIDI and the accompanying event JSON. No audio/PDF extraction.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import shutil
import statistics
import xml.etree.ElementTree as ET

import mido

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "public/piano/learning-songs/scores"
STEM = "phoebe-bridgers-i-know-the-end"
SOURCE_SHA = "5339cdf536ad2af95d720f82ce3304547f3b97a9f3f4eee2f3cabf4291dc0364"
AUTHOR_URL = "https://www.youtube.com/watch?v=qjnUrgG_hv4"
DOWNLOAD_URL = "https://drive.google.com/file/d/1L4st5kX-nMDU-mLMMrTjmzmmurRcSjLb/view"
PITCH_NAMES = [("C", 0), ("D", -1), ("D", 0), ("E", -1),
               ("E", 0), ("F", 0), ("G", -1), ("G", 0),
               ("A", -1), ("A", 0), ("B", -1), ("B", 0)]


def sub(parent, name, text=None, **attrs):
    node = ET.SubElement(parent, name, {k.replace("_", "-"): str(v) for k, v in attrs.items()})
    if text is not None:
        node.text = str(text)
    return node


def extract(source):
    midi = mido.MidiFile(source)
    if midi.ticks_per_beat != 480 or midi.type != 1:
        raise ValueError("This reproducible source conversion expects the preserved type-1, 480-PPQ MIDI.")
    tracks = []
    tempos = []
    for track_index, messages in enumerate(midi.tracks):
        track = {"index": track_index, "name": "", "notes": [], "controllers": [], "other_events": []}
        tick = 0
        playing = defaultdict(deque)
        on_index = 0
        for msg in messages:
            tick += msg.time
            if msg.type == "track_name":
                track["name"] = msg.name
            if msg.type == "set_tempo":
                tempos.append({"tick": tick, "microseconds_per_quarter": msg.tempo})
            if msg.type == "note_on" and msg.velocity:
                event = {"id": f"t{track_index}-n{on_index}", "track": track_index,
                         "channel": msg.channel, "midi": msg.note, "start_tick": tick,
                         "velocity": msg.velocity}
                on_index += 1
                playing[(msg.channel, msg.note)].append(event)
                track["notes"].append(event)
            elif msg.type == "note_off" or (msg.type == "note_on" and not msg.velocity):
                queue = playing[(msg.channel, msg.note)]
                if not queue:
                    raise ValueError(f"Unmatched release at track {track_index}, tick {tick}")
                event = queue.popleft()
                event.update(end_tick=tick, duration_ticks=tick - event["start_tick"], release_velocity=msg.velocity)
            elif msg.type == "control_change":
                track["controllers"].append({"tick": tick, "channel": msg.channel,
                                              "controller": msg.control, "value": msg.value})
            else:
                track["other_events"].append({"tick": tick, **{k: v for k, v in msg.dict().items() if k != "time"}})
        if any(playing.values()):
            raise ValueError("The source contains unfinished notes.")
        track["last_event_tick"] = tick
        tracks.append(track)
    notes = [note for track in tracks for note in track["notes"]]
    end_tick = max(note["end_tick"] for note in notes)
    unique_tempos = []
    for tempo in sorted(tempos, key=lambda t: t["tick"]):
        if tempo["tick"] > end_tick:
            continue
        if not unique_tempos or tempo["microseconds_per_quarter"] != unique_tempos[-1]["microseconds_per_quarter"]:
            unique_tempos.append(tempo)
    return tracks, notes, unique_tempos, end_tick


def quantize(tick):
    # Integer half-up rounding; deterministic for the two genuine 1/32 releases.
    return ((tick + 30) // 60) * 60


def seconds_at(tick, tempos):
    result = 0.0
    for index, tempo in enumerate(tempos):
        end = min(tick, tempos[index + 1]["tick"] if index + 1 < len(tempos) else tick)
        if end > tempo["tick"]:
            result += (end - tempo["tick"]) * tempo["microseconds_per_quarter"] / 480 / 1_000_000
    return result


def make_voices(track):
    groups = defaultdict(list)
    for original in track["notes"]:
        start = quantize(original["start_tick"])
        end = max(start + 60, quantize(original["end_tick"]))
        groups[(start, end)].append(original)
    voices = []
    voice_ends = []
    for (start, end), notes in sorted(groups.items()):
        free = [index for index, previous_end in enumerate(voice_ends) if previous_end <= start]
        index = free[0] if free else len(voices)
        if index == len(voices):
            voices.append([])
            voice_ends.append(0)
        voice_ends[index] = end
        voices[index].append({"start": start, "end": end, "notes": sorted(notes, key=lambda n: n["midi"])})
        for note in notes:
            note["notation"] = {"start_tick": start, "end_tick": end, "staff": track["index"], "voice": index + 1 + (track["index"] - 1) * 4}
    return voices


def components(start, end):
    """Conventional binary/dotted values, split at bar boundaries."""
    choices = [(1920, "whole", 0), (1440, "half", 1), (960, "half", 0),
               (720, "quarter", 1), (480, "quarter", 0), (360, "eighth", 1),
               (240, "eighth", 0), (180, "16th", 1), (120, "16th", 0), (60, "32nd", 0)]
    while start < end:
        remaining = min(end, (start // 1920 + 1) * 1920) - start
        length, kind, dots = next(value for value in choices if value[0] <= remaining)
        yield start, length, kind, dots
        start += length


def add_beams(measure):
    """Beam adjacent short notes within quarter-note beats; never across rests."""
    cursor = 0
    voices = defaultdict(list)
    levels = {"eighth": 1, "16th": 2, "32nd": 3}
    for element in measure:
        if element.tag == "backup":
            cursor -= int(element.findtext("duration"))
        elif element.tag == "note" and element.find("chord") is None:
            length = int(element.findtext("duration"))
            if element.find("rest") is None:
                voices[element.findtext("voice")].append((cursor, length, levels.get(element.findtext("type"), 0), element))
            cursor += length
    for events in voices.values():
        runs = []
        for event in events:
            if event[2] and runs and runs[-1][-1][2] and event[0] == runs[-1][-1][0] + runs[-1][-1][1] and event[0] // 480 == runs[-1][-1][0] // 480:
                runs[-1].append(event)
            else:
                runs.append([event])
        for run in runs:
            if len(run) < 2 or not run[0][2]:
                continue
            for index, (_, _, level_count, node) in enumerate(run):
                for level in range(1, level_count + 1):
                    before = index > 0 and run[index - 1][2] >= level
                    after = index + 1 < len(run) and run[index + 1][2] >= level
                    value = "continue" if before and after else "end" if before else "begin" if after else "backward hook" if index else "forward hook"
                    beam = ET.Element("beam", number=str(level))
                    beam.text = value
                    notations = node.find("notations")
                    node.insert(list(node).index(notations), beam) if notations is not None else node.append(beam)


def write_score(tracks, tempos, end_tick, output):
    root = ET.Element("score-partwise", version="4.0")
    sub(sub(root, "work"), "work-title", "I Know the End")
    identification = sub(root, "identification")
    sub(identification, "creator", "Phoebe Bridgers", type="composer")
    sub(identification, "creator", "Edgar Roock", type="arranger")
    encoding = sub(identification, "encoding")
    sub(encoding, "software", "Guitar-Learning deterministic MIDI-to-MusicXML converter")
    sub(encoding, "encoding-description", "Existing MIDI notes converted to readable notation; source timing preserved separately.")
    sub(identification, "source", AUTHOR_URL)
    defaults = sub(root, "defaults")
    scaling = sub(defaults, "scaling")
    sub(scaling, "millimeters", 7)
    sub(scaling, "tenths", 40)
    part_list = sub(root, "part-list")
    score_part = sub(part_list, "score-part", id="P1")
    sub(score_part, "part-name", "Piano")
    sub(score_part, "part-abbreviation", "Pno.")
    instrument = sub(score_part, "score-instrument", id="I1")
    sub(instrument, "instrument-name", "Piano")
    midi_instrument = sub(score_part, "midi-instrument", id="I1")
    sub(midi_instrument, "midi-channel", 1)
    sub(midi_instrument, "midi-program", 1)
    part = sub(root, "part", id="P1")
    staff_voices = {track["index"]: make_voices(track) for track in tracks if track["notes"]}
    final_tick = quantize(end_tick)
    segment_count = 0
    for measure_index in range(ceil(final_tick / 1920)):
        measure_start = measure_index * 1920
        measure_end = min(measure_start + 1920, final_tick)
        measure = sub(part, "measure", number=measure_index + 1)
        if measure_index == 0:
            attributes = sub(measure, "attributes")
            sub(attributes, "divisions", 480)
            key = sub(attributes, "key")
            sub(key, "fifths", -5)
            sub(key, "mode", "major")
            time = sub(attributes, "time")
            sub(time, "beats", 4)
            sub(time, "beat-type", 4)
            sub(attributes, "staves", 2)
            for staff, sign, line in [(1, "G", 2), (2, "F", 4)]:
                clef = sub(attributes, "clef", number=staff)
                sub(clef, "sign", sign)
                sub(clef, "line", line)
        for tempo in tempos:
            if measure_start <= tempo["tick"] < measure_end:
                direction = sub(measure, "direction", placement="above")
                metronome = sub(sub(direction, "direction-type"), "metronome")
                bpm = 60_000_000 / tempo["microseconds_per_quarter"]
                sub(metronome, "beat-unit", "quarter")
                sub(metronome, "per-minute", round(bpm))
                sub(direction, "offset", tempo["tick"] - measure_start)
                sub(direction, "staff", 1)
                sub(direction, "sound", tempo=repr(bpm))
        first_voice = True
        for staff, voices in staff_voices.items():
            for voice_index, groups in enumerate(voices):
                active_groups = [g for g in groups if g["start"] < measure_end and g["end"] > measure_start]
                if not active_groups and voice_index:
                    continue
                if not first_voice:
                    sub(sub(measure, "backup"), "duration", measure_end - measure_start)
                first_voice = False
                voice = voice_index + 1 + (staff - 1) * 4
                cursor = measure_start
                for group in active_groups:
                    start, end = max(measure_start, group["start"]), min(measure_end, group["end"])
                    if start > cursor:
                        write_rest(measure, cursor, start, voice, staff)
                    for tick, length, kind, dots in components(start, end):
                        for chord_index, source in enumerate(group["notes"]):
                            node = sub(measure, "note", id=f"{source['id']}-s{tick}")
                            if chord_index:
                                sub(node, "chord")
                            pitch = sub(node, "pitch")
                            step, alter = PITCH_NAMES[source["midi"] % 12]
                            sub(pitch, "step", step)
                            if alter:
                                sub(pitch, "alter", alter)
                            sub(pitch, "octave", source["midi"] // 12 - 1)
                            sub(node, "duration", length)
                            stop_tie = tick > group["start"]
                            start_tie = tick + length < group["end"]
                            if stop_tie:
                                sub(node, "tie", type="stop")
                            if start_tie:
                                sub(node, "tie", type="start")
                            sub(node, "voice", voice)
                            sub(node, "type", kind)
                            for _ in range(dots):
                                sub(node, "dot")
                            sub(node, "staff", staff)
                            if stop_tie or start_tie:
                                notations = sub(node, "notations")
                                if stop_tie:
                                    sub(notations, "tied", type="stop")
                                if start_tie:
                                    sub(notations, "tied", type="start")
                            segment_count += 1
                    cursor = end
                if cursor < measure_end:
                    write_rest(measure, cursor, measure_end, voice, staff)
        if measure_end == final_tick:
            sub(sub(measure, "barline", location="right"), "bar-style", "light-heavy")
        add_beams(measure)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    return {"measures": ceil(final_tick / 1920), "written_note_segments": segment_count,
            "staff_voice_counts": {str(staff): len(voices) for staff, voices in staff_voices.items()},
            "duration_quarters": final_tick / 480}


def write_rest(measure, start, end, voice, staff):
    for _, length, kind, dots in components(start, end):
        node = sub(measure, "note")
        sub(node, "rest")
        sub(node, "duration", length)
        sub(node, "voice", voice)
        sub(node, "type", kind)
        for _ in range(dots):
            sub(node, "dot")
        sub(node, "staff", staff)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=OUTPUT / f"{STEM}.mid")
    args = parser.parse_args()
    source_bytes = args.source.read_bytes()
    if sha256(source_bytes).hexdigest() != SOURCE_SHA:
        raise ValueError("Source hash differs from the published author MIDI; refusing silent source substitution.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_copy = OUTPUT / f"{STEM}.mid"
    if args.source.resolve() != source_copy.resolve():
        shutil.copyfile(args.source, source_copy)
    tracks, notes, tempos, end_tick = extract(args.source)
    score_path = OUTPUT / f"{STEM}.musicxml"
    score_metrics = write_score(tracks, tempos, end_tick, score_path)
    deltas = {}
    for name in ["start_tick", "end_tick"]:
        values = [n["notation"][name] - n[name] for n in notes]
        seconds = [seconds_at(n["notation"][name], tempos) - seconds_at(n[name], tempos) for n in notes]
        deltas[name] = {"changed_notes": sum(bool(v) for v in values), "max_absolute_ticks": max(map(abs, values)),
                        "mean_absolute_ticks": statistics.mean(map(abs, values)),
                        "max_absolute_milliseconds": max(map(abs, seconds)) * 1000,
                        "mean_absolute_milliseconds": statistics.mean(map(abs, seconds)) * 1000}
    event_path = OUTPUT / f"{STEM}-events.json"
    event_data = {"source": source_copy.name, "source_sha256": SOURCE_SHA, "ticks_per_quarter": 480,
                  "tempos_within_music": tempos, "notes": notes,
                  "controllers": [{"track": t["index"], **event} for t in tracks for event in t["controllers"]]}
    event_path.write_text(json.dumps(event_data, ensure_ascii=False, separators=(",", ":")) + "\n")
    report = {"song": "I Know the End", "artist": "Phoebe Bridgers", "arranger": "Edgar Roock",
              "author_publish_url": AUTHOR_URL, "author_midi_url": DOWNLOAD_URL,
              "source_filename": source_copy.name, "source_sha256": SOURCE_SHA,
              "musicxml_filename": score_path.name, "musicxml_sha256": sha256(score_path.read_bytes()).hexdigest(),
              "source_note_count": len(notes), "source_note_count_by_track": {str(t["index"]): len(t["notes"]) for t in tracks if t["notes"]},
              "distinct_pitch_attack_count": len({(n["notation"]["start_tick"], n["midi"]) for n in notes}),
              "source_music_end_tick": end_tick, "source_music_seconds": seconds_at(end_tick, tempos),
              "source_file_last_event_tick": max(t["last_event_tick"] for t in tracks),
              "notation": score_metrics, "quantization_grid_ticks": 60, "timing_changes": deltas,
              "source_scope": "Edgar Roock's author-published piano arrangement, not a transcription of the original studio recording.",
              "conversion_scope": "Existing MIDI pitches only; no scanning, optical recognition, PDF or audio transcription.",
              "preservation": "All source notes retained with exact MIDI pitches, source ticks, channels and velocities in events JSON; original MIDI bytes unchanged.",
              "notation_decisions": ["One piano part: source track 1 on treble staff and track 2 on bass staff; overlapping notes allocated to separate voices.",
                                     "D-flat major spelling (enharmonic to author's original C-sharp major); source's incorrect C-major key metadata not copied.",
                                     "Note starts/releases rounded to nearest 1/32 note (60 MIDI ticks); bar-crossing and compound lengths notated with ties.",
                                     "All music retained through last note release; no empty measures created from trailing nonmusical metadata.",
                                     "Redundant tempo messages collapsed; actual 75 BPM and 112.00005973336519 BPM changes retained.",
                                     "MIDI controller/pedal values preserved in original and events JSON; current lesson synth grades pitch/onset and plays written note lengths."],
              "license_note": "Author supplied a public MIDI download. No explicit redistribution license was located; attribution is not a public-domain or permissive-license claim. User explicitly requested this score be stored in this repository.",
              "validation": {"source_hash_verified": True, "all_midi_note_ons_have_matching_release": True,
                             "model_and_renderer": "See phoebe-score-validation.json, generated by validate_phoebe_score.mjs."}}
    report_path = OUTPUT / f"{STEM}.provenance.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"score": str(score_path), **score_metrics, "notes": len(notes), "timing_changes": deltas}, indent=2))


if __name__ == "__main__":
    main()
