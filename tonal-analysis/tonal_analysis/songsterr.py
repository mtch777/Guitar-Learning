"""Conservative, read-only Songsterr capture adapter (standard library only).

Input is the captured metadata plus every index-addressed ``track-N.json``.
Duration fractions are already dotted/tupleted: multiply by four exactly once.
The output clock is the written score, not expanded repeats or recorded audio.
Only ordinary integer fretted pitches with known timing enter tonal inference.
Unsupported pitch mechanics and malformed timed occurrences remain in ``events``
with explicit exclusions; key declarations never become inferred key labels.
"""

from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path


SCHEMA = "tonal-events/1"
PERCUSSION_IDS = {128, 1024}
PITCH_EFFECTS = ("bend", "harmonic", "slide")


def _integer(value, minimum=0, maximum=None):
    return type(value) is int and value >= minimum and (maximum is None or value <= maximum)


def _object(value, context):
    if type(value) is not dict:
        raise ValueError(f"{context} must be an object")
    return value


def _list(value, context):
    if type(value) is not list:
        raise ValueError(f"{context} must be a list")
    return value


def _duration(beat):
    value = beat.get("duration")
    if (type(value) is not list or len(value) != 2
            or not all(_integer(x, 1) for x in value)):
        return None
    return Fraction(*value) * 4


def _present(value):
    return value is not None and value is not False and value != 0


def _grace(beat):
    value = beat.get("graceNote")
    if value is None or type(value) is bool:
        return value is True, False
    if type(value) is str and value in ("beforeBeat", "onBeat"):
        return True, False
    return False, True


def _whole_rest(measure, voice):
    beats = voice.get("beats", [])
    if measure.get("rest") is not True or voice.get("rest") is not True or len(beats) != 1:
        return False
    beat = beats[0]
    return (beat.get("rest") is True and type(beat.get("type")) is int and beat["type"] == 1
            and beat.get("duration") == [1, 1] and bool(beat.get("notes"))
            and all(n.get("rest") is True for n in beat["notes"])
            and not any(beat.get(k) for k in ("graceNote", "dots", "tuplet", "tupletStart", "tupletStop")))


def _validate_structure(part, filename):
    for mi, measure in enumerate(_list(part.get("measures"), filename + ".measures")):
        _object(measure, f"{filename}.measures[{mi}]")
        for vi, voice in enumerate(_list(measure.get("voices", []), "measure.voices")):
            _object(voice, "voice")
            for bi, beat in enumerate(_list(voice.get("beats", []), "voice.beats")):
                _object(beat, "beat")
                for note in _list(beat.get("notes", []), "beat.notes"):
                    _object(note, "note")


def _layout(parts, warnings):
    bars, declarations = [], []
    count = max((len(p["measures"]) for p in parts), default=0)
    for part in parts:
        if "anacrusis" in part and type(part["anacrusis"]) is not bool:
            raise ValueError("Unsupported pickup encoding; anacrusis must be boolean")
    pickup = any(p.get("anacrusis") is True for p in parts)
    pickup_span = Fraction(0)
    if pickup and count:
        for part in parts:
            if not part["measures"]:
                continue
            measure = part["measures"][0]
            for voice in measure.get("voices", []):
                if _whole_rest(measure, voice):
                    continue
                span = Fraction(0)
                for beat in voice.get("beats", []):
                    grace, invalid_grace = _grace(beat)
                    if invalid_grace:
                        raise ValueError("Malformed grace marker prevents pickup geometry")
                    duration = _duration(beat)
                    if duration is None:
                        raise ValueError("Malformed duration prevents pickup geometry")
                    if not grace:
                        span += duration
                pickup_span = max(pickup_span, span)

    signature, offset, section = None, Fraction(0), None
    for mi in range(count):
        measures = [(p, p["measures"][mi]) for p in parts if mi < len(p["measures"])]
        signatures = set()
        markers = set()
        for part, measure in measures:
            if "signature" in measure and measure["signature"] is not None:
                value = measure["signature"]
                if type(value) is not list or len(value) != 2 or not all(_integer(x, 1) for x in value):
                    raise ValueError(f"Invalid meter in bar {mi + 1}")
                signatures.add(tuple(value))
            marker = measure.get("marker")
            if marker is not None:
                text = marker.get("text") if isinstance(marker, dict) else marker
                if isinstance(text, str) and text.strip():
                    markers.add(text.strip())
                elif marker:
                    warnings.append(dict(reason="unsupported_section_marker", track_id=str(part["partId"]), bar=mi + 1))
            for field in ("keySignature", "repeatStart", "repeat", "alternateEnding", "marker"):
                if field in measure:
                    declarations.append(dict(track_id=str(part["partId"]), bar=mi + 1, onset_q=str(offset),
                                             field=field, value=deepcopy(measure[field]),
                                             source_pointer=f"track-{part['partId']}.json#/measures/{mi}/{field}"))
        if len(signatures) > 1:
            raise ValueError(f"Conflicting track meters in bar {mi + 1}")
        if signatures:
            signature = next(iter(signatures))
        if signature is None:
            raise ValueError("Missing initial meter; no invented 4/4 geometry")
        nominal = Fraction(4 * signature[0], signature[1])
        span = nominal
        if mi == 0 and pickup:
            if not 0 < pickup_span <= nominal:
                raise ValueError("Pickup fill does not define a positive span within the meter")
            span = pickup_span
        if len(markers) == 1:
            section = next(iter(markers))
        elif len(markers) > 1:
            section = None
            warnings.append(dict(reason="conflicting_section_markers", bar=mi + 1))
        bars.append(dict(bar=mi + 1, start_q=str(offset), duration_q=str(span),
                         signature=list(signature), section=section, pickup=span != nominal,
                         meter_source="explicit" if signatures else "inherited"))
        offset += span
    return bars, declarations


def _pitch(part, note):
    reasons = []
    instrument = part.get("instrumentId")
    if _integer(instrument) and instrument in PERCUSSION_IDS:
        reasons.append("unpitched_percussion")
    elif not _integer(instrument, 0, 127):
        reasons.append("unsupported_instrument")
    tuning = part.get("tuning")
    if type(tuning) is not list or not tuning or not all(_integer(x, 0, 127) for x in tuning):
        reasons.append("invalid_tuning")
    capo = part.get("capo", 0)
    if not _integer(capo, 0, 127):
        reasons.append("invalid_capo")
    string, fret = note.get("string"), note.get("fret")
    if not _integer(string) or not isinstance(tuning, list) or not 0 <= string < len(tuning):
        reasons.append("invalid_string")
    if not _integer(fret):
        reasons.append("invalid_fret")
    if note.get("dead") is True:
        reasons.append("dead_note")
    elif "dead" in note and type(note["dead"]) is not bool:
        reasons.append("invalid_dead_flag")
    if reasons:
        return None, reasons
    midi = tuning[string] + fret + capo
    if not 0 <= midi <= 127:
        return None, ["pitch_out_of_midi_range"]
    return midi, []


def _unsupported_pitch_settings(part):
    reasons = []
    for field in ("transpose", "transposition", "pitchShift"):
        if field in part and part[field] not in (None, 0):
            reasons.append("unsupported_transposition")
    # Tempo/sound automations are harmless here. Explicit pitch-setting changes
    # require a setting timeline this adapter does not pretend to implement.
    def visit(value):
        if isinstance(value, dict):
            if any(k in value for k in ("tuning", "transpose", "transposition", "pitchShift")):
                return True
            if str(value.get("type", "")).lower() in ("tuning", "transpose", "transposition", "pitchshift"):
                return True
            return any(visit(v) for v in value.values())
        return isinstance(value, list) and any(visit(v) for v in value)
    if visit(part.get("automations")) or visit(part.get("trackAutomations")):
        reasons.append("unsupported_pitch_automation")
    return sorted(set(reasons))


def _track_events(part, bars, warnings):
    result, rest_count = [], 0
    pid = str(part["partId"])
    settings_reasons = _unsupported_pitch_settings(part)
    for mi, measure in enumerate(part["measures"]):
        bar = bars[mi]
        start, span = Fraction(bar["start_q"]), Fraction(bar["duration_q"])
        for vi, voice in enumerate(measure.get("voices", [])):
            local, voice_events = Fraction(0), []
            invalid_clock = False
            for bi, beat in enumerate(voice.get("beats", [])):
                written = _duration(beat)
                grace, invalid_grace = _grace(beat)
                duration = span if _whole_rest(measure, voice) else written
                if duration is None or invalid_grace:
                    warnings.append(dict(reason="invalid_duration" if duration is None else "invalid_grace_flag",
                                         track_id=pid, bar=mi + 1, voice=vi, beat=bi))
                rest_reasons = []
                for node, label in ((measure, "measure"), (voice, "voice"), (beat, "beat")):
                    if "rest" in node and type(node["rest"]) is not bool:
                        rest_reasons.append("invalid_" + label + "_rest_flag")
                    elif node.get("rest") is True:
                        rest_reasons.append(label + "_rest_conflicts_with_note")
                for ni, note in enumerate(beat.get("notes", [])):
                    if note.get("rest") is True:
                        rest_count += 1
                        continue
                    midi, reasons = _pitch(part, note)
                    reasons += settings_reasons + rest_reasons
                    if "rest" in note and type(note["rest"]) is not bool:
                        reasons.append("invalid_note_rest_flag")
                    if invalid_clock:
                        reasons.append("unknown_onset_after_invalid_timing")
                    if duration is None:
                        reasons.append("invalid_duration")
                    if invalid_grace:
                        reasons.append("invalid_grace_flag")
                    if grace:
                        reasons.append("grace_note_unresolved_timing")
                    for field in PITCH_EFFECTS:
                        if field in note and _present(note[field]):
                            reasons.append("unresolved_" + field)
                    for field in ("tremoloBar", "harmonic", "slide"):
                        if field in beat and _present(beat[field]):
                            reasons.append("unresolved_" + field)
                    if "tie" in note and type(note["tie"]) is not bool:
                        reasons.append("invalid_tie_flag")
                    event = dict(id=f"track:{pid}:bar:{mi + 1}:voice:{vi}:beat:{bi}:note:{ni}",
                                 track_id=pid, voice=vi, bar=mi + 1, beat=bi, note=ni,
                                 onset_q=None if invalid_clock else str(start + local),
                                 duration_q="0" if grace else (str(duration) if duration is not None else None),
                                 written_duration_q=str(written) if written is not None else None,
                                 midi=midi, attack=False, eligible=False, exclusions=sorted(set(reasons)),
                                 accent=note.get("accentuated") is True or
                                        (type(note.get("accentuated")) is int and note["accentuated"] > 0),
                                 raw_note=deepcopy(note), raw_beat=deepcopy({k: v for k, v in beat.items() if k != "notes"}),
                                 string=note.get("string"), fret=note.get("fret"), tie=note.get("tie") is True,
                                 source_pointer=f"track-{pid}.json#/measures/{mi}/voices/{vi}/beats/{bi}/notes/{ni}")
                    voice_events.append(event)
                if duration is None or invalid_grace:
                    invalid_clock = True
                elif not grace and not invalid_clock:
                    local += duration
            if local > span:
                warnings.append(dict(reason="voice_overflows_bar", track_id=pid, bar=mi + 1, voice=vi,
                                     filled_q=str(local), span_q=str(span)))
                for event in voice_events:
                    event["exclusions"] = sorted(set(event["exclusions"] + ["voice_overflows_bar"]))
            elif not invalid_clock and local < span and voice.get("beats"):
                warnings.append(dict(reason="voice_underfills_bar", track_id=pid, bar=mi + 1, voice=vi,
                                     filled_q=str(local), span_q=str(span)))
            result.extend(voice_events)

    predecessors = {}
    for event in result:
        lane = (event["voice"], event["string"]) if type(event["string"]) is int else None
        previous = predecessors.get(lane)
        if event["tie"]:
            valid = (previous is not None and previous["eligible"] and not event["exclusions"]
                     and previous["midi"] == event["midi"] and event["onset_q"] is not None
                     and Fraction(previous["onset_q"]) + Fraction(previous["duration_q"]) == Fraction(event["onset_q"]))
            if valid:
                event["tie_from"] = previous["id"]
            else:
                event["exclusions"] = sorted(set(event["exclusions"] + ["unresolved_tie"]))
        event["eligible"] = not event["exclusions"]
        event["attack"] = event["eligible"] and not event["tie"]
        if lane is not None:
            predecessors[lane] = event
    return result, rest_count


def normalize_documents(documents):
    """Normalize captured documents without modifying any source object.

    Structural identity/geometry errors fail closed. Individual notes with
    unsupported pitch or timing remain present, explicitly ineligible.
    Metadata track order is the API's part index, not an inferred instrument role.
    """
    _object(documents, "documents")
    if any(type(name) is not str for name in documents):
        raise ValueError("Document names must be strings")
    meta = _object(documents.get("metadata.json"), "metadata.json")
    for field in ("songId", "revisionId"):
        if not _integer(meta.get(field)):
            raise ValueError(f"metadata.{field} must be a nonnegative integer")
    catalog = _list(meta.get("tracks"), "metadata.tracks")
    expected = {f"track-{i}.json" for i in range(len(catalog))}
    actual = {name for name in documents if name.startswith("track-")}
    if actual != expected:
        raise ValueError("Capture must contain exactly every metadata track index")
    parts, tracks, warnings, declarations = [], [], [], []
    for i, description in enumerate(catalog):
        _object(description, f"metadata.tracks[{i}]")
        filename = f"track-{i}.json"
        part = _object(documents[filename], filename)
        if type(part.get("partId")) is not int or part["partId"] != i:
            raise ValueError(f"Part identity differs in {filename}")
        for field in ("songId", "revisionId"):
            if field in part and (type(part[field]) is not int or part[field] != meta[field]):
                raise ValueError(f"Source {field} identity differs in {filename}")
        if "partId" in description and (type(description["partId"]) is not int or description["partId"] != i):
            raise ValueError("Metadata part identity differs from index")
        if "instrumentId" in description and "instrumentId" in part and description["instrumentId"] != part["instrumentId"]:
            raise ValueError("Metadata and captured instrument identity differ")
        _validate_structure(part, filename)
        parts.append(part)
        tracks.append(dict(id=str(i), name=deepcopy(part.get("name", description.get("name"))),
                           instrument_id=deepcopy(part.get("instrumentId")), tuning=deepcopy(part.get("tuning")),
                           capo=deepcopy(part.get("capo", 0)),
                           raw_settings={k: deepcopy(v) for k, v in part.items() if k != "measures"}))
        for field in ("key", "keySignature", "anacrusis", "transpose", "transposition", "pitchShift"):
            if field in part:
                declarations.append(dict(track_id=str(i), bar=None, onset_q="0", field=field,
                                         value=deepcopy(part[field]), source_pointer=filename + "#/" + field))
    bars, measure_declarations = _layout(parts, warnings)
    declarations += measure_declarations
    events, rests = [], 0
    for part in parts:
        rows, rest_count = _track_events(part, bars, warnings)
        events.extend(rows)
        rests += rest_count
    expected_notes = sum(note.get("rest") is not True for part in parts
                         for measure in part["measures"] for voice in measure.get("voices", [])
                         for beat in voice.get("beats", []) for note in beat.get("notes", []))
    if len(events) != expected_notes:
        raise AssertionError("Incomplete source note occurrence coverage")
    if len({e["id"] for e in events}) != len(events):
        raise AssertionError("Duplicate source occurrence identity")
    files = ["metadata.json"] + sorted(expected)
    hashes = {name: hashlib.sha256(json.dumps(documents[name], sort_keys=True, ensure_ascii=False,
                                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
              for name in files}
    exclusions = Counter(reason for e in events for reason in e["exclusions"])
    eligible = sum(e["eligible"] for e in events)
    return dict(schema=SCHEMA,
                source=dict(format="songsterr_json", song_id=meta["songId"], revision_id=meta["revisionId"],
                            id=f"songsterr:{meta['songId']}:{meta['revisionId']}", document_sha256=hashes,
                            hash_semantics="canonical_json_sha256", clock="written_not_repeat_expanded",
                            pitch_semantics="ordinary_fretted_base_pitch_not_recorded_audio"),
                tracks=tracks, bars=bars, events=events, warnings=warnings, declarations=declarations,
                coverage=dict(tracks=len(tracks), source_nonrest_notes=expected_notes, events=len(events),
                              source_rest_notes=rests, eligible_events=eligible, excluded_events=len(events) - eligible,
                              attacks=sum(e["attack"] for e in events), exclusions=dict(sorted(exclusions.items()))),
                limitations=["Written score durations, not physical sustain or recorded performance.",
                             "Repeats/endings are retained declarations; this view does not expand playback.",
                             "Pitch-changing techniques and untyped non-fretted pitches are excluded, not guessed.",
                             "Key/chord/section declarations are source annotations, not verified musical truth.",
                             "Missing timing excludes affected occurrences; source note witnesses are retained."])


def load_capture(path):
    """Read a local complete capture; source files are never written."""
    root = Path(path)
    if not root.is_dir():
        raise ValueError("Capture input must be a directory")
    paths = [root / "metadata.json"] + sorted(root.glob("track-*.json"))
    documents, file_hashes = {}, {}
    for item in paths:
        data = item.read_bytes()
        documents[item.name] = json.loads(data.decode("utf-8-sig"))
        file_hashes[item.name] = hashlib.sha256(data).hexdigest()
    result = normalize_documents(documents)
    result["source"]["file_sha256"] = file_hashes
    return result
