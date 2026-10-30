"""Synthetic, redistributable adversarial tests for the raw capture boundary."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tonal_analysis.songsterr import load_capture, normalize_documents


def note(fret=0, string=0, **kwargs):
    return dict(fret=fret, string=string, **kwargs)


def beat(*notes, duration=(1, 4), **kwargs):
    return dict(notes=list(notes), duration=list(duration), **kwargs)


def measure(*beats, signature=(4, 4), **kwargs):
    value = dict(voices=[dict(beats=list(beats))], **kwargs)
    if signature is not None:
        value["signature"] = list(signature)
    return value


def part(*measures, **kwargs):
    return dict(tuning=[40, 45, 50], instrumentId=30, measures=list(measures), **kwargs)


def documents(*parts):
    data = {"metadata.json": dict(songId=123, revisionId=456, tracks=[])}
    for index, value in enumerate(parts):
        value = deepcopy(value)
        value.update(partId=index, songId=123, revisionId=456)
        data[f"track-{index}.json"] = value
        data["metadata.json"]["tracks"].append(dict(instrumentId=value["instrumentId"], name=f"Part {index}"))
    return data


class SongsterrAdapterTests(unittest.TestCase):
    def normalize(self, *parts):
        return normalize_documents(documents(*parts))

    def test_pitch_and_exact_tuplet_clock_without_redotting(self):
        score = part(measure(beat(note(fret=3), duration=(1, 12), tuplet=3),
                             beat(note(string=1), duration=(1, 12)),
                             beat(note(string=2), duration=(1, 12)), signature=(1, 4)),
                     measure(beat(note(), duration=(3, 8), dots=1), signature=(3, 8)), capo=2)
        result = self.normalize(score)
        self.assertEqual([e["midi"] for e in result["events"]], [45, 47, 52, 42])
        self.assertEqual([e["onset_q"] for e in result["events"]], ["0", "1/3", "2/3", "1"])
        self.assertEqual([e["duration_q"] for e in result["events"]], ["1/3", "1/3", "1/3", "3/2"])
        self.assertEqual(result["coverage"]["eligible_events"], 4)

    def test_source_documents_and_witnesses_are_not_mutated_or_aliased(self):
        data = documents(part(measure(beat(note(bend={"points": [{"position": 30, "tone": 50}]})))))
        before = deepcopy(data)
        result = normalize_documents(data)
        self.assertEqual(data, before)
        result["events"][0]["raw_note"]["bend"]["points"][0]["tone"] = 999
        result["tracks"][0]["raw_settings"]["tuning"][0] = 0
        self.assertEqual(data, before)

    def test_grace_is_retained_without_advancing_the_written_clock(self):
        result = self.normalize(part(measure(beat(note(2), duration=(1, 32), graceNote=True),
                                             beat(note(4)), signature=(1, 4))))
        grace, regular = result["events"]
        self.assertEqual((grace["onset_q"], grace["duration_q"], grace["written_duration_q"]), ("0", "0", "1/8"))
        self.assertFalse(grace["eligible"])
        self.assertEqual(regular["onset_q"], "0")
        self.assertTrue(regular["attack"])

    def test_songsterr_beforebeat_and_onbeat_grace_enums_have_zero_written_span(self):
        for marker in ("beforeBeat", "onBeat"):
            with self.subTest(marker=marker):
                result = self.normalize(part(measure(beat(note(2), duration=(1, 16), graceNote=marker),
                                                     beat(note(4)), signature=(1, 4))))
                self.assertEqual([e["onset_q"] for e in result["events"]], ["0", "0"])
                self.assertEqual(result["events"][0]["duration_q"], "0")
                self.assertTrue(result["events"][1]["eligible"])
                self.assertEqual(result["warnings"], [])

    def test_unknown_grace_enum_does_not_guess_later_onsets(self):
        result = self.normalize(part(measure(beat(note(), graceNote="new-enum"), beat(note(1)))))
        self.assertIn("invalid_grace_flag", result["events"][0]["exclusions"])
        self.assertIsNone(result["events"][1]["onset_q"])

    def test_tie_continuation_preserves_occurrence_without_new_attack(self):
        result = self.normalize(part(measure(beat(note()), signature=(1, 4)),
                                     measure(beat(note(tie=True)), signature=None)))
        a, b = result["events"]
        self.assertTrue(a["attack"])
        self.assertTrue(b["eligible"])
        self.assertFalse(b["attack"])
        self.assertEqual(b["tie_from"], a["id"])
        self.assertEqual(result["coverage"]["attacks"], 1)

    def test_ties_cannot_jump_rest_change_pitch_or_use_other_voice(self):
        cases = [measure(beat(note()), beat(dict(rest=True)), beat(note(tie=True))),
                 measure(beat(note()), beat(note(1, tie=True))),
                 dict(signature=[1, 4], voices=[dict(beats=[beat(note())]), dict(beats=[beat(note(tie=True))])])]
        for score in cases:
            with self.subTest(score=score):
                result = self.normalize(part(score))
                tied = [e for e in result["events"] if e["tie"]][0]
                self.assertFalse(tied["eligible"])
                self.assertIn("unresolved_tie", tied["exclusions"])

    def test_incomplete_capture_and_source_identity_mismatch_fail(self):
        original = documents(part(measure(beat(note()))), part(measure(beat(note()))))
        for change in ("missing", "extra", "part", "revision", "boolean_part", "song"):
            data = deepcopy(original)
            if change == "missing":
                del data["track-1.json"]
            elif change == "extra":
                data["track-2.json"] = deepcopy(data["track-1.json"])
            elif change == "part":
                data["track-1.json"]["partId"] = 0
            elif change == "revision":
                data["track-1.json"]["revisionId"] = 789
            elif change == "song":
                data["track-1.json"]["songId"] = 789
            else:
                data["track-1.json"]["partId"] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                normalize_documents(data)

    def test_missing_and_conflicting_meters_fail_without_guessing(self):
        with self.assertRaisesRegex(ValueError, "Missing initial meter"):
            self.normalize(part(measure(beat(note()), signature=None)))
        with self.assertRaisesRegex(ValueError, "Conflicting track meters"):
            self.normalize(part(measure(beat(note()), signature=(3, 4))),
                           part(measure(beat(note()), signature=(4, 4))))
        invalid = part(measure(beat(note())))
        invalid["measures"][0]["signature"] = [True, 4]
        with self.assertRaises(ValueError):
            self.normalize(invalid)

    def test_shared_meter_inheritance_is_exact(self):
        result = self.normalize(part(measure(beat(note()), signature=(5, 8)), measure(beat(note()), signature=None)),
                                part(measure(beat(note()), signature=None), measure(beat(note()), signature=None)))
        self.assertEqual(result["bars"][1]["start_q"], "5/2")
        self.assertEqual(result["bars"][1]["meter_source"], "inherited")

    def test_pickup_uses_longest_written_voice_and_ignores_whole_rest_sentinel(self):
        rest = dict(signature=[3, 4], rest=True,
                    voices=[dict(rest=True, beats=[beat(dict(rest=True), duration=(1, 1), rest=True, type=1)])])
        result = self.normalize(part(measure(beat(note()), signature=(3, 4)),
                                     measure(beat(note(), duration=(3, 4)), signature=None), anacrusis=True),
                                part(rest, deepcopy(rest)))
        self.assertEqual(result["bars"][0]["duration_q"], "1")
        self.assertTrue(result["bars"][0]["pickup"])
        self.assertEqual(result["bars"][1]["start_q"], "1")
        self.assertNotIn("voice_overflows_bar", [w["reason"] for w in result["warnings"]])
        self.assertEqual(result["coverage"]["source_rest_notes"], 2)

    def test_invalid_pickup_data_fails_instead_of_shifting_all_later_bars(self):
        invalid = part(measure(beat(note(), duration=(0, 4))), anacrusis=True)
        with self.assertRaisesRegex(ValueError, "pickup"):
            self.normalize(invalid)

    def test_bad_duration_retains_notes_and_quarantines_unknown_following_onsets(self):
        malformed = beat(note(2))
        del malformed["duration"]
        result = self.normalize(part(measure(beat(note()), malformed, beat(note(4))),
                                     measure(beat(note(5)), signature=None)))
        events = result["events"]
        self.assertEqual(len(events), 4)
        self.assertEqual([e["onset_q"] for e in events], ["0", "1", None, "4"])
        self.assertIsNone(events[1]["duration_q"])
        self.assertFalse(events[1]["eligible"])
        self.assertFalse(events[2]["eligible"])
        self.assertTrue(events[3]["eligible"])

    def test_overflow_quarantines_whole_voice_bar_without_stretching_next_bar(self):
        result = self.normalize(part(measure(beat(note(), duration=(1, 2)), beat(note()), signature=(1, 4)),
                                     measure(beat(note()), signature=None)))
        self.assertEqual([e["eligible"] for e in result["events"]], [False, False, True])
        self.assertEqual(result["events"][-1]["onset_q"], "1")
        self.assertEqual(len(result["events"]), 3)

    def test_pitch_effects_retain_raw_data_and_exclude_base_pitch_from_inference(self):
        result = self.normalize(part(measure(beat(note(bend={"points": []})),
                                             beat(note(harmonic=1)), beat(note(slide=1)),
                                             beat(note(), tremoloBar={"points": []}))))
        self.assertEqual(result["coverage"]["excluded_events"], 4)
        self.assertEqual([e["midi"] for e in result["events"]], [40] * 4)
        self.assertEqual(result["events"][0]["raw_note"]["bend"], {"points": []})

    def test_percussion_dead_and_nonfretted_notes_never_become_pitch_classes(self):
        for instrument in (128, 1024):
            score = part(measure(beat(note())))
            score["instrumentId"] = instrument
            result = self.normalize(score)
            self.assertIsNone(result["events"][0]["midi"])
            self.assertIn("unpitched_percussion", result["events"][0]["exclusions"])
        result = self.normalize(part(measure(beat(note(dead=True)), beat(dict(pitch=60)))))
        self.assertTrue(all(e["midi"] is None and not e["eligible"] for e in result["events"]))

    def test_strict_pitch_types_do_not_accept_booleans_fractional_frets_or_strings(self):
        for bad in (note(fret=True), note(fret=1.5), note(string=True), note(string=-1), note(fret="3")):
            with self.subTest(bad=bad):
                result = self.normalize(part(measure(beat(bad))))
                self.assertFalse(result["events"][0]["eligible"])
        for field, value in (("tuning", [True]), ("capo", "2"), ("capo", None)):
            score = part(measure(beat(note())))
            score[field] = value
            with self.subTest(field=field, value=value):
                self.assertFalse(self.normalize(score)["events"][0]["eligible"])

    def test_malformed_instrument_values_are_explicitly_excluded(self):
        for value in (True, [], {}, "30", None):
            score = part(measure(beat(note())))
            score["instrumentId"] = value
            with self.subTest(value=value):
                event = self.normalize(score)["events"][0]
                self.assertFalse(event["eligible"])
                self.assertIn("unsupported_instrument", event["exclusions"])

    def test_source_key_annotations_never_control_eligibility_or_pitch(self):
        data = documents(part(measure(beat(note()), keySignature="not a parsed key"), key="also unparsed"))
        original = normalize_documents(data)
        data["track-0.json"]["key"] = "C major"
        data["track-0.json"]["measures"][0]["keySignature"] = "B minor"
        changed = normalize_documents(data)
        self.assertEqual(original["events"], changed["events"])
        self.assertEqual(len(original["declarations"]), 2)
        self.assertNotEqual(original["source"]["document_sha256"], changed["source"]["document_sha256"])

    def test_source_sections_and_conflicts_are_explicit(self):
        score = part(measure(beat(note()), marker={"text": "Verse"}), measure(beat(note()), signature=None))
        result = self.normalize(score)
        self.assertEqual([b["section"] for b in result["bars"]], ["Verse", "Verse"])
        other = deepcopy(score)
        other["measures"][0]["marker"] = "Chorus"
        result = self.normalize(score, other)
        self.assertIsNone(result["bars"][0]["section"])
        self.assertIn("conflicting_section_markers", [w["reason"] for w in result["warnings"]])

    def test_repeat_declarations_do_not_silently_duplicate_occurrences(self):
        result = self.normalize(part(measure(beat(note()), repeatStart=True),
                                     measure(beat(note()), signature=None, repeat=3, alternateEnding=[1, 2])))
        self.assertEqual(len(result["events"]), 2)
        self.assertEqual({d["field"] for d in result["declarations"]}, {"repeatStart", "repeat", "alternateEnding"})
        self.assertEqual(result["source"]["clock"], "written_not_repeat_expanded")

    def test_rest_conflicts_and_invalid_markers_are_not_truthiness_coerced(self):
        result = self.normalize(part(measure(beat(note()), rest=True),
                                     measure(beat(note(tie="false")), signature=None),
                                     measure(beat(note(rest="false")), signature=None)))
        self.assertEqual(len(result["events"]), 3)
        self.assertTrue(all(not e["eligible"] for e in result["events"]))
        self.assertIn("measure_rest_conflicts_with_note", result["events"][0]["exclusions"])
        self.assertIn("invalid_tie_flag", result["events"][1]["exclusions"])

    def test_unknown_pitch_settings_exclude_instead_of_ignoring_transposition(self):
        score = part(measure(beat(note())), transpose=2)
        self.assertIn("unsupported_transposition", self.normalize(score)["events"][0]["exclusions"])
        score.pop("transpose")
        score["automations"] = [{"type": "tuning", "value": [38, 45, 50]}]
        self.assertIn("unsupported_pitch_automation", self.normalize(score)["events"][0]["exclusions"])
        score["automations"] = [{"type": "tempo", "value": 120}]
        self.assertTrue(self.normalize(score)["events"][0]["eligible"])

    def test_occurrence_count_conservation_including_excluded_notes_and_voices(self):
        data = documents(part(measure(beat(note(), note(string=1), dict(rest=True)), beat(note(dead=True)))),
                         part(measure(beat(note(harmonic=1)), beat(dict(pitch=60)))))
        expected = sum(n.get("rest") is not True for p in list(data.values())[1:]
                       for m in p["measures"] for v in m["voices"] for b in v["beats"] for n in b["notes"])
        result = normalize_documents(data)
        self.assertEqual(len(result["events"]), expected)
        self.assertEqual(result["coverage"]["eligible_events"] + result["coverage"]["excluded_events"], expected)
        self.assertEqual(len({e["id"] for e in result["events"]}), expected)

    def test_empty_capture_has_no_fabricated_meter_or_notes(self):
        result = normalize_documents(documents())
        self.assertEqual(result["events"], [])
        self.assertEqual(result["bars"], [])
        self.assertEqual(result["coverage"]["eligible_events"], 0)

    def test_load_capture_records_byte_hashes_and_never_writes_sources(self):
        data = documents(part(measure(beat(note()))))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, document in data.items():
                (root / name).write_text(json.dumps(document), encoding="utf-8-sig")
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            result = load_capture(root)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            self.assertEqual(result["source"]["file_sha256"],
                             {name: hashlib.sha256(value).hexdigest() for name, value in before.items()})


if __name__ == "__main__":
    unittest.main()
