"""Extract linked musical events from GP7 GPIF, without the web or audio pipeline.

Read-only semantic extraction. Modern GPIF writing/editing is NOT implemented.
"""
from __future__ import annotations
import argparse
import json
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

def _ids(element, tag):
    return (element.findtext(tag) or "").split()

def _property(note, key, child):
    return note.findtext(f"./Properties/Property[@name='{key}']/{child}")

def _numeric(text):
    try:
        return int(text) if text is not None else None
    except ValueError:
        return None

def extract_score(path: str | Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("Content/score.gpif"))
    def index(parent, tag):
        return {node.get("id"): node for node in root.findall(f"./{parent}/{tag}")}
    bars = index("Bars", "Bar")
    voices = index("Voices", "Voice")
    beats = index("Beats", "Beat")
    notes = index("Notes", "Note")
    rhythms = index("Rhythms", "Rhythm")
    tracks = root.findall("./Tracks/Track")
    measures = root.findall("./MasterBars/MasterBar")
    result = {
        "source_file": Path(path).name,
        "measure_count": len(measures),
        "tracks": [],
    }
    for ti, track in enumerate(tracks):
        staves = track.findall("./Staves/Staff")
        tunings = []
        for staff in staves:
            pitches = staff.findtext("./Properties/Property[@name='Tuning']/Pitches")
            tunings.append([int(v) for v in pitches.split()] if pitches else [])
        item = {
            "index": ti, "name": track.findtext("Name"),
            "tunings": tunings, "measures": [],
        }
        for mi, master in enumerate(measures):
            bar_ids = _ids(master, "Bars")
            if ti >= len(bar_ids):
                raise ValueError(f"Missing bar for track {ti} at measure {mi}")
            bar = bars[bar_ids[ti]]
            measure = {
                "number": mi + 1,
                "time_signature": master.findtext("Time"),
                "section": master.findtext("./Section/Text"),
                "voices": [],
            }
            for voice_id in _ids(bar, "Voices"):
                voice = voices[voice_id]
                events = []
                for beat_id in _ids(voice, "Beats"):
                    beat = beats[beat_id]
                    rhythm_id = beat.find("Rhythm")
                    rhythm = rhythms.get(rhythm_id.get("ref")) if rhythm_id is not None else None
                    event = {
                        "rhythm": rhythm.findtext("NoteValue") if rhythm is not None else None,
                        "dots": rhythm.findtext("AugmentationDot") if rhythm is not None else None,
                        "tuplet": ET.tostring(rhythm.find("PrimaryTuplet"), encoding="unicode")
                            if rhythm is not None and rhythm.find("PrimaryTuplet") is not None else None,
                        "notes": [],
                    }
                    for note_id in _ids(beat, "Notes"):
                        note = notes[note_id]
                        props = note.find("Properties")
                        event["notes"].append({
                            "string": _numeric(_property(note, "String", "String")),
                            "fret": _numeric(_property(note, "Fret", "Fret")),
                            "midi": _numeric(_property(note, "Midi", "Number")),
                            "technique_tags": [n.tag for n in note if n.tag not in ("Properties",)],
                            "property_names": [p.get("name") for p in props] if props is not None else [],
                        })
                    events.append(event)
                measure["voices"].append(events)
            item["measures"].append(measure)
        result["tracks"].append(item)
    return result

def summarize(score: dict) -> dict:
    tracks = []
    for track in score["tracks"]:
        events = [beat for m in track["measures"] for voice in m["voices"] for beat in voice]
        note_list = [note for beat in events for note in beat["notes"]]
        tracks.append({
            "name": track["name"],
            "tunings": track["tunings"],
            "beats": len(events),
            "notes": len(note_list),
            "fretted_notes": sum(n["fret"] is not None for n in note_list),
            "rhythms": dict(Counter(b["rhythm"] for b in events)),
        })
    return {"source_file": score["source_file"], "measures": score["measure_count"], "tracks": tracks}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--export-json", type=Path, help="Write all extracted events (one input file only)")
    args = parser.parse_args()
    if args.export_json and len(args.files) != 1:
        parser.error("--export-json requires exactly one input")
    scores = [extract_score(path) for path in args.files]
    if args.export_json:
        args.export_json.parent.mkdir(parents=True, exist_ok=True)
        args.export_json.write_text(json.dumps(scores[0], indent=2), encoding="utf-8")
    print(json.dumps([summarize(score) for score in scores], indent=2))

if __name__ == "__main__":
    main()
