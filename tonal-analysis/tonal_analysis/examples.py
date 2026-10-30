"""Original synthetic test material, never transcribed from commercial songs.

These small vignettes exercise observable tonal relationships. Their labels are
test-design intentions, not an independently annotated accuracy benchmark.
"""

from copy import deepcopy
from fractions import Fraction


def _score(name, bar_count, section="A"):
    return {
        "schema": "tonal-events/1",
        "source": {"kind": "original_synthetic", "name": name},
        "tracks": [
            {"id": "bass", "name": "Bass", "instrument_id": 33, "tuning": [], "capo": 0},
            {"id": "harmony", "name": "Harmony", "instrument_id": 0, "tuning": [], "capo": 0},
            {"id": "melody", "name": "Melody", "instrument_id": 0, "tuning": [], "capo": 0},
        ],
        "bars": [
            {"bar": i + 1, "start_q": str(4 * i), "duration_q": "4",
             "signature": [4, 4], "section": section}
            for i in range(bar_count)
        ],
        "events": [], "warnings": [], "declarations": [], "coverage": {},
    }


def _event(score, track, onset, duration, midi, *, attack=True, voice=0, eligible=True):
    onset, duration = Fraction(onset), Fraction(duration)
    number = len(score["events"])
    event = {
        "id": f"synthetic:{score['source']['name']}:{number}",
        "track_id": track, "voice": voice, "bar": int(onset // 4) + 1,
        "beat": int(onset % 4), "note": number,
        "onset_q": str(onset), "duration_q": str(duration), "midi": midi,
        "attack": attack, "eligible": eligible,
        "exclusions": [] if eligible else ["percussion"],
        "accent": onset % 4 == 0, "raw_note": {"synthetic": True},
        "raw_beat": {}, "string": None, "fret": None, "tie": not attack,
    }
    score["events"].append(event)
    return event


def _finish(score):
    score["coverage"] = {
        "source_note_occurrences": len(score["events"]),
        "retained_note_occurrences": len(score["events"]),
        "eligible_note_occurrences": sum(e["eligible"] for e in score["events"]),
    }
    return score


def _progression(name, roots, voicings, melodies, repetitions=2):
    score = _score(name, len(roots) * repetitions)
    for bar in range(len(score["bars"])):
        index = bar % len(roots)
        start = 4 * bar
        _event(score, "bass", start, 4, roots[index])
        for pitch in voicings[index]:
            _event(score, "harmony", start, 4, pitch)
        for offset, pitch in enumerate(melodies[index]):
            _event(score, "melody", start + offset, 1, pitch)
    return _finish(score)


def transpose(score, semitones):
    """Return a transposed copy; preserve rhythm, occurrence identities and roles."""
    if type(semitones) is not int:
        raise ValueError("An integer semitone transposition is required")
    result = deepcopy(score)
    for track in result["tracks"]:
        track["tuning"] = [p + semitones for p in track.get("tuning", [])]
    for event in result["events"]:
        if event["midi"] is not None and "percussion" not in event["exclusions"]:
            event["midi"] += semitones
    return result


def duplicate_track(score, track_id):
    """Create a literal extra performance layer for duplication-robustness tests."""
    result = deepcopy(score)
    matching = [t for t in result["tracks"] if t["id"] == track_id]
    if len(matching) != 1:
        raise ValueError("A unique existing track is required")
    new_id = track_id + "_duplicate"
    if any(t["id"] == new_id for t in result["tracks"]):
        raise ValueError("Duplicate fixture track already exists")
    track = deepcopy(matching[0])
    track.update(id=new_id, name=track["name"] + " duplicate")
    result["tracks"].append(track)
    for event in list(result["events"]):
        if event["track_id"] == track_id:
            copy = deepcopy(event)
            copy.update(id=event["id"] + ":duplicate", track_id=new_id)
            result["events"].append(copy)
    return _finish(result)


def example_scores():
    """Return independent normalized-score fixtures suitable for CLI examples."""
    major = _progression(
        "c_major_cadences", [50, 43, 48, 48],
        [[62, 65, 69], [55, 59, 62, 65], [60, 64, 67], [60, 64, 67]],
        [[74, 77, 81, 77], [79, 81, 83, 77], [76, 74, 72, 72], [79, 76, 74, 72]],
    )
    minor = _progression(
        "a_minor_leading_tone", [50, 40, 45, 45],
        [[62, 65, 69], [52, 56, 59, 62], [57, 60, 64], [57, 60, 64]],
        [[74, 77, 81, 77], [76, 77, 80, 74], [72, 71, 69, 69], [76, 72, 71, 69]],
    )
    dorian = _progression(
        "d_dorian", [50, 43, 50, 50],
        [[62, 65, 69], [55, 59, 62], [62, 65, 69], [62, 65, 69]],
        [[74, 77, 81, 83], [79, 83, 81, 79], [81, 84, 76, 74], [77, 76, 72, 74]],
    )
    power = _score("ambiguous_power_chord", 4)
    for bar in range(4):
        _event(power, "bass", 4 * bar, 4, 40)
        for pitch in (52, 59):
            _event(power, "harmony", 4 * bar, 4, pitch)
    _finish(power)

    silence = _finish(_score("silence", 2))
    percussion = _score("percussion_only", 2)
    percussion["tracks"] = [
        {"id": "drums", "name": "Drums", "instrument_id": 128, "tuning": [], "capo": 0}
    ]
    for beat in range(8):
        _event(percussion, "drums", beat, 1, 36 if beat % 2 == 0 else 38, eligible=False)
    _finish(percussion)

    changing = deepcopy(major)
    changing["source"]["name"] = "c_to_d_sections"
    second = transpose(major, 2)
    shift = Fraction(changing["bars"][-1]["start_q"]) + Fraction(changing["bars"][-1]["duration_q"])
    for bar in second["bars"]:
        bar["bar"] += len(major["bars"])
        bar["start_q"] = str(Fraction(bar["start_q"]) + shift)
        bar["section"] = "B"
        changing["bars"].append(bar)
    for event in second["events"]:
        event["id"] += ":section_B"
        event["bar"] += len(major["bars"])
        event["onset_q"] = str(Fraction(event["onset_q"]) + shift)
        changing["events"].append(event)
    _finish(changing)

    passing = deepcopy(major)
    passing["source"]["name"] = "c_major_chromatic_passing"
    # Split the E in bar three into E-F-F#-G: one brief chromatic passing pitch.
    target = next(e for e in passing["events"] if e["track_id"] == "melody" and e["onset_q"] == "8")
    target["duration_q"] = "1/4"
    for offset, pitch in [(Fraction(1, 4), 77), (Fraction(1, 2), 78), (Fraction(3, 4), 79)]:
        _event(passing, "melody", 8 + offset, Fraction(1, 4), pitch)
    _finish(passing)

    pedal = deepcopy(minor)
    pedal["source"]["name"] = "a_minor_dominant_pedal"
    # Frequent low E attacks dominate a naive count while the upper progression
    # and melody repeatedly resolve to A minor. This is an adversarial fixture.
    pedal["events"] = [e for e in pedal["events"] if e["track_id"] != "bass"]
    for subdivision in range(8 * 4 * 4):
        _event(pedal, "bass", Fraction(subdivision, 4), Fraction(1, 4), 40)
    _finish(pedal)
    return {
        "c_major_cadences": major,
        "a_minor_leading_tone": minor,
        "d_dorian": dorian,
        "ambiguous_power_chord": power,
        "silence": silence,
        "percussion_only": percussion,
        "c_to_d_sections": changing,
        "c_major_chromatic_passing": passing,
        "a_minor_dominant_pedal": pedal,
    }
