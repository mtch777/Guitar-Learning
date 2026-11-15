#!/usr/bin/env python3
"""Independent source/geometry oracle for the Drop E fingering comparison.

This module deliberately does not import the fingering engine. Its MIDI reader,
source occurrence comparison, interval sweep, and movement accounting are separate
from the optimizer. It verifies the declared geometric/timing model, not a human
player's comfort or an optimal right-hand technique.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
import math
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]
TUNING_HIGH_TO_LOW = (64, 59, 55, 50, 45, 40, 35, 28)
EXPECTED_SOURCES = {
    "6_review_cfa029a287078971a412e05347b5612f6d9ef8c0ea69a1e9b0b58a82fb71aafd.mid": {
        "sha256": "cfa029a287078971a412e05347b5612f6d9ef8c0ea69a1e9b0b58a82fb71aafd",
        "note_count": 164, "open_eligible": 86, "feasible_opens": 82,
    },
    "6_review_da80eca929e874d93378b26542ed63cb17be1735f2470a387fe0ad284431535a.mid": {
        "sha256": "da80eca929e874d93378b26542ed63cb17be1735f2470a387fe0ad284431535a",
        "note_count": 191, "open_eligible": 77, "feasible_opens": 73,
    },
}


class ValidationError(AssertionError):
    """A claim in a fingering artifact does not match independent evidence."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _vlq(data, offset):
    value = 0
    for _ in range(4):
        require(offset < len(data), "Truncated MIDI variable-length integer")
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 127)
        if byte < 128:
            return value, offset
    raise ValidationError("Invalid MIDI variable-length integer")


def read_midi_source(path):
    """Read raw note occurrences with FIFO pairing, including duplicate pitches."""
    path = Path(path)
    data = path.read_bytes()
    require(data[:4] == b"MThd" and len(data) >= 14, "Missing MIDI header")
    header_size = int.from_bytes(data[4:8], "big")
    fmt, track_count, ppqn = struct.unpack(">HHH", data[8:14])
    require(fmt in (0, 1) and ppqn > 0 and not ppqn & 0x8000,
            "Only synchronous PPQN MIDI is supported by this oracle")
    offset = 8 + header_size
    events, tempos = [], []
    end_tick = 0
    sequence = 0
    for track in range(track_count):
        require(data[offset:offset + 4] == b"MTrk", "Missing MIDI track")
        length = int.from_bytes(data[offset + 4:offset + 8], "big")
        chunk = data[offset + 8:offset + 8 + length]
        require(len(chunk) == length, "Truncated MIDI track")
        offset += 8 + length
        pos, tick, running = 0, 0, None
        while pos < len(chunk):
            delta, pos = _vlq(chunk, pos)
            tick += delta
            require(pos < len(chunk), "Missing MIDI event")
            if chunk[pos] >= 128:
                status = chunk[pos]
                pos += 1
                if status < 0xf0:
                    running = status
            else:
                require(running is not None, "Running status has no predecessor")
                status = running
            if status == 0xff:
                require(pos < len(chunk), "Truncated MIDI meta event")
                kind = chunk[pos]
                length, pos = _vlq(chunk, pos + 1)
                payload = chunk[pos:pos + length]
                require(len(payload) == length, "Truncated MIDI meta payload")
                pos += length
                if kind == 0x51:
                    require(length == 3, "Invalid MIDI tempo event")
                    tempos.append((tick, sequence, int.from_bytes(payload, "big")))
            elif status in (0xf0, 0xf7):
                length, pos = _vlq(chunk, pos)
                pos += length
                require(pos <= len(chunk), "Truncated MIDI SysEx event")
                running = None
            else:
                require(0x80 <= status < 0xf0, "Unsupported MIDI system event")
                kind, channel = status >> 4, status & 15
                length = 1 if kind in (0xc, 0xd) else 2
                values = chunk[pos:pos + length]
                require(len(values) == length and all(v < 128 for v in values),
                        "Invalid MIDI channel payload")
                pos += length
                if kind in (8, 9):
                    events.append((tick, sequence, track, channel, kind,
                                   values[0], values[1]))
                elif kind == 0xb:
                    require(not (values[0] == 64 and values[1] >= 64),
                            "Sustain pedal requires an explicit acoustic-duration model")
            sequence += 1
            end_tick = max(end_tick, tick)
    require(offset == len(data), "Unexpected bytes after MIDI tracks")
    tempos.sort()

    def seconds_at(tick):
        previous, tempo, seconds = 0, 500000, 0.0
        for at, _, replacement in tempos:
            if at > tick:
                break
            seconds += (at - previous) * tempo / (ppqn * 1_000_000)
            previous, tempo = at, replacement
        return seconds + (tick - previous) * tempo / (ppqn * 1_000_000)

    pending = defaultdict(deque)
    notes = []
    # MIDI event order is retained when pairing equal-pitch note occurrences.
    # The later occupancy oracle uses half-open intervals for release/retrigger.
    for tick, _, track, channel, kind, pitch, velocity in sorted(events):
        key = track, channel, pitch
        if kind == 9 and velocity > 0:
            note = {"id": len(notes), "pitch": pitch, "start_tick": tick,
                    "velocity": velocity, "channel": channel, "track": track}
            notes.append(note)
            pending[key].append(note)
        else:
            require(bool(pending[key]), f"Unmatched note-off for {key} at {tick}")
            note = pending[key].popleft()
            require(tick > note["start_tick"], "Non-positive MIDI note duration")
            note["end_tick"] = tick
    require(not any(pending.values()), "Unreleased raw MIDI note occurrence")
    for note in notes:
        note["start_seconds"] = seconds_at(note["start_tick"])
        note["end_seconds"] = seconds_at(note["end_tick"])
    initial_tempo = 500000
    for tick, _, tempo in tempos:
        if tick == 0:
            initial_tempo = tempo
    return {"notes": notes, "ticks_per_beat": ppqn,
            "tempo_bpm": 60_000_000 / initial_tempo,
            "tempo_values": sorted({tempo for _, _, tempo in tempos} or {500000}),
            "duration_seconds": seconds_at(end_tick),
            "sha256": hashlib.sha256(data).hexdigest()}


def _identity_notes(notes):
    ids = [note["id"] for note in notes]
    require(all(isinstance(i, (str, int)) and not isinstance(i, bool) for i in ids),
            "Note IDs must be strings or integers")
    require(len(set(ids)) == len(ids), "Duplicate source note ID")
    for note in notes:
        for key in ("pitch", "start_tick", "end_tick", "velocity", "channel"):
            require(_integer(note[key]), f"Non-integer original note field {key}")
        require(note["start_tick"] >= 0 and note["end_tick"] > note["start_tick"],
                "Invalid original note clock")
        require(0 <= note["pitch"] <= 127 and 1 <= note["velocity"] <= 127
                and 0 <= note["channel"] <= 15, "Invalid original MIDI field")
    return dict(zip(ids, notes))


def _occurrence(note):
    return tuple(note[k] for k in ("pitch", "start_tick", "end_tick", "velocity", "channel"))


def validate_source(fixture, source_path):
    raw = read_midi_source(source_path)
    expected = EXPECTED_SOURCES.get(fixture["source_filename"])
    require(expected is not None, "Unexpected source fixture")
    require(raw["sha256"] == expected["sha256"], "Raw MIDI differs from frozen source")
    require(fixture["source_sha256"] == raw["sha256"], "Incorrect source SHA-256")
    notes = fixture["notes"]
    _identity_notes(notes)
    require(Counter(map(_occurrence, notes)) == Counter(map(_occurrence, raw["notes"])),
            "Fixture does not preserve every raw MIDI occurrence, clock, and velocity")
    require(len(notes) == expected["note_count"], "Incorrect fixture note population")
    require(len(raw["tempo_values"]) == 1, "Fixture's constant-tempo view is unsupported")
    require(math.isclose(fixture["tempo_bpm"], raw["tempo_bpm"], abs_tol=1e-8),
            "Fixture tempo differs from MIDI")
    require(math.isclose(fixture["duration_seconds"], raw["duration_seconds"], abs_tol=1e-8),
            "Fixture duration differs from MIDI")
    for note in notes:
        for field, tick_field in (("start_seconds", "start_tick"), ("end_seconds", "end_tick")):
            seconds = note[tick_field] / raw["ticks_per_beat"] * 60 / raw["tempo_bpm"]
            require(math.isclose(note[field], seconds, abs_tol=1e-8),
                    f"Incorrect {field} for note {note['id']}")
    return raw


def maximum_open_attacks(notes, *, max_fret=24, max_span=4):
    """Exhaustive independent open-count oracle for these non-overlapping grips.

    It enumerates only physical string choices within each onset, with no movement
    scoring or mapper search code. A cross-onset held note makes this bound invalid
    and is explicitly rejected instead of being quietly ignored.
    """
    groups = defaultdict(list)
    for note in notes:
        groups[note["start_tick"]].append(note)
    total = 0
    for tick, attacks in groups.items():
        require(not any(n["start_tick"] < tick < n["end_tick"] for n in notes),
                "Per-grip open oracle cannot certify cross-onset holds")
        best = -1

        def choose(index, strings, frets, open_count):
            nonlocal best
            if index == len(attacks):
                best = max(best, open_count)
                return
            pitch = attacks[index]["pitch"]
            for string, open_pitch in enumerate(TUNING_HIGH_TO_LOW, 1):
                fret = pitch - open_pitch
                if string in strings or not 0 <= fret <= max_fret:
                    continue
                next_frets = frets + ([fret] if fret > 0 else [])
                if next_frets and max(next_frets) - min(next_frets) > max_span:
                    continue
                choose(index + 1, strings | {string}, next_frets, open_count + (fret == 0))

        choose(0, set(), [], 0)
        require(best >= 0, f"Unplayable attack at tick {tick}")
        total += best
    return total


def validate_version(notes, version, *, ticks_per_beat=960, tempo_bpm=120,
                     max_fret=24, max_span=4, rapid_frets_per_second=8.0,
                     check_metrics=True):
    """Verify each occurrence and sounding interval, then recompute movement."""
    by_id = _identity_notes(notes)
    assignments = version["assignments"]
    assignment_ids = [a["note_id"] for a in assignments]
    require(len(assignment_ids) == len(set(assignment_ids)), "Duplicate assignment ID")
    require(set(assignment_ids) == set(by_id), "Missing or added note assignment")
    mapped = {a["note_id"]: a for a in assignments}
    by_string = defaultdict(list)
    for note_id, a in mapped.items():
        string, fret = a["string_number"], a["fret"]
        require(_integer(string) and 1 <= string <= 8, "Invalid string number")
        require(_integer(fret) and 0 <= fret <= max_fret, "Invalid fret")
        require(TUNING_HIGH_TO_LOW[string - 1] + fret == by_id[note_id]["pitch"],
                f"Pitch/octave changed for note {note_id}")
        by_string[string].append(by_id[note_id])
    for string, sounding in by_string.items():
        previous_end = -1
        for note in sorted(sounding, key=lambda n: (n["start_tick"], n["end_tick"])):
            require(note["start_tick"] >= previous_end,
                    f"Overlapping occurrences occupy string {string} at tick {note['start_tick']}")
            previous_end = note["end_tick"]

    groups = defaultdict(list)
    for note in notes:
        groups[note["start_tick"]].append(note["id"])
    frames = version["positions"]
    ticks = sorted(groups)
    require(len(frames) == len(ticks), "Position frames must cover every attack timestamp")
    last_frame_position = None
    last_fretted = None
    travel = rapid_count = rapid_cost = maximum_jump = shift_count = 0
    maximum_speed = 0.0
    maximum_span = maximum_simultaneous = 0
    for tick, frame in zip(ticks, frames):
        seconds = tick / ticks_per_beat * 60 / tempo_bpm
        require(math.isclose(frame["time_seconds"], seconds, abs_tol=1e-8),
                f"Incorrect position timestamp at tick {tick}")
        require(Counter(frame["attack_note_ids"]) == Counter(groups[tick]),
                f"Incorrect attack IDs at tick {tick}")
        active = {n["id"] for n in notes if n["start_tick"] <= tick < n["end_tick"]}
        require(Counter(frame["active_note_ids"]) == Counter(active),
                f"Incorrect held/active note IDs at tick {tick}")
        maximum_simultaneous = max(maximum_simultaneous, len(active))
        frets = [mapped[n]["fret"] for n in active if mapped[n]["fret"] > 0]
        position = frame["position"]
        if position is None:
            require(not frets and last_fretted is None and last_frame_position is None,
                    "Only initial open notes may have an unestablished hand anchor")
            continue
        require(_integer(position) and 1 <= position <= max_fret,
                "Hand position must be a valid positive fret anchor")
        if frets:
            span = max(frets) - min(frets)
            maximum_span = max(maximum_span, span)
            require(span <= max_span, f"Fretted span exceeds model at tick {tick}")
            require(all(position <= f <= position + max_span for f in frets),
                    f"Declared hand window excludes a sounding fret at tick {tick}")
            if last_fretted is not None:
                old_time, old_position, old_release = last_fretted
                elapsed = seconds - old_time
                require(elapsed > 0, "Fretted position frames are not chronological")
                # A held fretted grip is not free travel time. Count the released
                # interval, then an explicitly declared 125ms transition allowance
                # capped by attack spacing. This remains a timing proxy, not a
                # claim that a player can perform every preserved MIDI endpoint.
                budget = min(elapsed, max(0.0, seconds - old_release) + min(0.125, elapsed))
                distance = abs(position - old_position)
                travel += distance
                shift_count += distance > 0
                maximum_jump = max(maximum_jump, distance)
                maximum_speed = max(maximum_speed, distance / budget)
                excess = max(0.0, distance - rapid_frets_per_second * budget)
                rapid_count += excess > 1e-9
                rapid_cost += round(1000 * excess ** 2 / max(budget, 0.0625))
            release = max(by_id[n]["end_tick"] for n in active if mapped[n]["fret"] > 0)
            last_fretted = seconds, position, release / ticks_per_beat * 60 / tempo_bpm
        elif last_frame_position is not None:
            require(position == last_frame_position,
                    "Open-only frame silently resets or moves the hand anchor")
        last_frame_position = position

    result = {
        "note_count": len(notes),
        "open_note_count": sum(a["fret"] == 0 for a in assignments),
        "open_eligible_note_count": sum(n["pitch"] in TUNING_HIGH_TO_LOW for n in notes),
        "hand_travel_frets": travel,
        "rapid_shift_count": rapid_count,
        "rapid_shift_cost": rapid_cost,
        "position_shift_count": shift_count,
        "max_position_jump_frets": maximum_jump,
        "max_shift_frets_per_second": maximum_speed,
        "max_fretted_span": maximum_span,
        "max_simultaneous_notes": maximum_simultaneous,
    }
    if check_metrics:
        declared = version["metrics"]
        for key in ("hand_travel_frets", "rapid_shift_count", "rapid_shift_cost"):
            require(key in declared, f"Missing independently verifiable metric {key}")
            require(math.isclose(declared[key], result[key], abs_tol=1e-6),
                    f"Incorrect {key}: declared {declared[key]}, independently {result[key]}")
        for key in result.keys() & declared.keys():
            require(math.isclose(declared[key], result[key], abs_tol=1e-6),
                    f"Incorrect declared metric {key}")
        aliases = {
            "attack_count": len(ticks),
            "open_used": result["open_note_count"],
            "open_eligible": result["open_eligible_note_count"],
            "open_exceptions": result["open_eligible_note_count"] - result["open_note_count"],
            "max_shift_frets": result["max_position_jump_frets"],
            "max_fret_span": result["max_fretted_span"],
        }
        for key in aliases.keys() & declared.keys():
            require(math.isclose(declared[key], aliases[key], abs_tol=1e-6),
                    f"Incorrect declared metric {key}")
    return result


def validate_string_export(fixture, version, path):
    """Verify actual exported bytes, including string1→MIDI channel1 routing."""
    exported = read_midi_source(path)
    contacts = {a["note_id"]: a for a in version["assignments"]}
    expected = []
    for note in fixture["notes"]:
        expected.append((note["pitch"], note["start_tick"], note["end_tick"],
                         note["velocity"], contacts[note["id"]]["string_number"] - 1))
    require(Counter(map(_occurrence, exported["notes"])) == Counter(expected),
            "String MIDI export changed note occurrences or disagrees with assigned string channels")
    require(exported["ticks_per_beat"] == fixture.get("ticks_per_beat", 960),
            "String MIDI export changed tick resolution")
    require(len(exported["tempo_values"]) == 1
            and math.isclose(exported["tempo_bpm"], fixture["tempo_bpm"], abs_tol=1e-8),
            "String MIDI export changed tempo")
    require(math.isclose(exported["duration_seconds"], fixture["duration_seconds"], abs_tol=1e-8),
            "String MIDI export changed duration")
    return {"path": str(path), "note_count": len(exported["notes"]),
            "sha256": exported["sha256"], "string_channels_verified": True}


def validate_dataset(dataset, source_dir, export_root=None):
    export_root = Path(export_root or ROOT / "public").resolve()
    require(tuple(dataset["tuning_high_to_low"]) == TUNING_HIGH_TO_LOW,
            "Dataset tuning is not exact 8-string Drop E")
    require(dataset["max_fret"] == 24, "Frozen comparison expects a 24-fret guitar")
    fixtures = dataset["fixtures"]
    require(Counter(f["source_filename"] for f in fixtures) == Counter(EXPECTED_SOURCES.keys()),
            "Dataset must contain exactly both requested raw sources")
    report = []
    for fixture in fixtures:
        filename = fixture["source_filename"]
        raw = validate_source(fixture, Path(source_dir) / filename)
        expected = EXPECTED_SOURCES[filename]
        require(maximum_open_attacks(fixture["notes"]) == expected["feasible_opens"],
                "Frozen open-count feasibility changed")
        require(Counter(v["id"] for v in fixture["versions"]) == Counter({"greedy": 1, "optimized": 1}),
                "Both greedy and optimized versions must be independently checked")
        metrics = {}
        exports = {}
        for version in fixture["versions"]:
            checked = validate_version(fixture["notes"], version,
                                       ticks_per_beat=raw["ticks_per_beat"],
                                       tempo_bpm=fixture["tempo_bpm"])
            require(checked["open_eligible_note_count"] == expected["open_eligible"],
                    "Open-eligible population changed")
            require(checked["open_note_count"] == expected["feasible_opens"],
                    "Tier 1 failed to achieve all physically available open notes")
            metrics[version["id"]] = checked
            export_path = (export_root / version["midi_path"]).resolve()
            require(export_path.is_relative_to(export_root), "Export path leaves its declared root")
            exports[version["id"]] = validate_string_export(fixture, version, export_path)
        require(metrics["optimized"]["rapid_shift_cost"] <= metrics["greedy"]["rapid_shift_cost"],
                "Optimized timing-proxy cost is worse than the valid greedy baseline")
        report.append({"fixture": fixture["id"], "source_sha256": raw["sha256"],
                       "raw_notes_preserved": len(raw["notes"]), "versions": metrics,
                       "string_midi_exports": exports})
    return {"passed": True, "fixtures": report,
            "scope": "Raw-occurrence preservation, geometric playability, open priority, and declared timing proxy; human comfort is unverified."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path,
                        default=ROOT / "public/data/fretboard-efficiency-fixtures.json")
    parser.add_argument("--source-dir", type=Path,
                        default=ROOT / "tests/fixtures/fretboard-efficiency")
    parser.add_argument("--export-root", type=Path, default=ROOT / "public")
    args = parser.parse_args()
    report = validate_dataset(json.loads(args.fixtures.read_text()), args.source_dir, args.export_root)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
