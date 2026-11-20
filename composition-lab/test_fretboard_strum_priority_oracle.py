"""Independent, source-backed adversaries for the separate picking priorities."""
from copy import deepcopy
import hashlib
import importlib
from itertools import product
import json
import unittest

from check_fretboard_efficiency import (
    ROOT, TUNING_HIGH_TO_LOW, ValidationError, minimum_fretting_contacts,
    read_midi_source, strum_pick_metrics, validate_dataset, validate_version,
)


def note(note_id, pitch, start=0, end=96):
    return dict(id=note_id, pitch=pitch, start_tick=start, end_tick=end,
                velocity=90, channel=0)


def assignment(notes, contacts):
    return [dict(note_id=n["id"], string_number=s, fret=f)
            for n, (s, f) in zip(notes, contacts)]


def metric_phrase(strings, ticks=None):
    ticks = ticks or [96 * i for i in range(len(strings))]
    notes = [note(i, TUNING_HIGH_TO_LOW[s - 1] + 1, t, t + 24)
             for i, (s, t) in enumerate(zip(strings, ticks))]
    return notes, assignment(notes, [(s, 1) for s in strings])


def exhaustive_primary_and_direction(notes):
    """Cartesian-product oracle, independent of the optimizer's state search.

    The authored phrases are small. Assign each complete original occurrence
    once, reject physical overlap/span violations, then compare the three primary
    costs and first tie-break. No beam, local pruning, hand anchors, or core
    candidate/transition helpers participate.
    """
    choices = [[(s, n["pitch"] - p) for s, p in enumerate(TUNING_HIGH_TO_LOW, 1)
                if 0 <= n["pitch"] - p <= 24] for n in notes]
    best = None
    for contacts in product(*choices):
        feasible = True
        for tick in {n["start_tick"] for n in notes}:
            active = [contacts[i] for i, n in enumerate(notes)
                      if n["start_tick"] <= tick < n["end_tick"]]
            frets = [f for _, f in active if f]
            if (len({s for s, _ in active}) != len(active)
                    or (frets and max(frets) - min(frets) > 4)
                    or minimum_fretting_contacts(active) > 4):
                feasible = False
                break
        if feasible:
            metrics = strum_pick_metrics(notes, assignment(notes, contacts))
            cost = (*metrics["priority_cost"], metrics["rapid_run_direction_reversals"])
            best = cost if best is None else min(best, cost)
    return best


def full_source_primary_optimum(notes, *, ticks_per_beat, tempo_bpm):
    """Independent complete-source proof of the three primary costs only.

    Enumerate new attacks against already reserved held contacts, then retain
    only the held contacts and last singleton string that can affect the next
    onset. No optimizer helpers, hand anchors, direction tie-break, or incumbent
    result are read. Discarding a higher-cost prefix with the identical future
    reservation is exact because all three remaining costs are additive.
    """
    groups = {}
    by_id = {n["id"]: n for n in notes}
    order = {n["id"]: i for i, n in enumerate(notes)}
    for n in notes:
        groups.setdefault(n["start_tick"], []).append(n)
    ticks = sorted(groups)
    # (held occurrence/string/fret tuple, previous singleton string) -> cost.
    states = {((), None): (0, 0, 0)}
    examined = 0
    peak_states = 1
    for index, tick in enumerate(ticks):
        attacks = groups[tick]
        next_tick = ticks[index + 1] if index + 1 < len(ticks) else None
        rapid = (index > 0 and len(attacks) == len(groups[ticks[index - 1]]) == 1
                 and (tick - ticks[index - 1]) * 60 / (ticks_per_beat * tempo_bpm) <= .25 + 1e-9)
        choices = [[(s, n["pitch"] - p) for s, p in enumerate(TUNING_HIGH_TO_LOW, 1)
                    if 0 <= n["pitch"] - p <= 24] for n in attacks]
        following = {}
        for (held, previous_string), cost in states.items():
            for new_contacts in product(*choices):
                examined += 1
                whole = [*held, *((n["id"], s, f) for n, (s, f) in zip(attacks, new_contacts))]
                placements = [(s, f) for _, s, f in whole]
                frets = [f for _, f in placements if f]
                if (len({s for s, _ in placements}) != len(placements)
                        or (frets and max(frets) - min(frets) > 4)
                        or minimum_fretting_contacts(placements) > 4):
                    continue
                missed = sum(n["pitch"] in TUNING_HIGH_TO_LOW and f != 0
                             for n, (_, f) in zip(attacks, new_contacts))
                strings = {s for s, _ in new_contacts}
                chord = sum(s not in strings for s in range(min(strings), max(strings) + 1)) if len(attacks) > 1 else 0
                current_string = new_contacts[0][0] if len(attacks) == 1 else None
                skipped = len(range(min(previous_string, current_string) + 1,
                                    max(previous_string, current_string))) if rapid else 0
                total = tuple(a + b for a, b in zip(cost, (missed, chord, skipped)))
                reserved = tuple(sorted((contact for contact in whole
                                        if next_tick is not None and by_id[contact[0]]["end_tick"] > next_tick),
                                       key=lambda contact: order[contact[0]]))
                key = reserved, current_string
                if key not in following or total < following[key]:
                    following[key] = total
        assert following, f"Independent primary oracle found no feasible contacts at tick {tick}"
        states = following
        peak_states = max(peak_states, len(states))
    return {"primary_cost": min(states.values()), "candidates_examined": examined,
            "peak_states": peak_states}


class PickingMetricOracleTests(unittest.TestCase):
    def test_barre_count_uses_active_regions_and_lower_obstructions(self):
        self.assertEqual(minimum_fretting_contacts([(1, 3), (2, 5), (3, 3)]), 2)
        self.assertEqual(minimum_fretting_contacts([(1, 5), (2, 3), (3, 5)]), 3)
        self.assertEqual(minimum_fretting_contacts([(1, 3), (2, 0), (3, 3)]), 2)
        self.assertEqual(minimum_fretting_contacts([(1, 3), (3, 3)]), 2)

    def test_chord_cost_counts_missing_interior_strings(self):
        notes = [note(i, TUNING_HIGH_TO_LOW[s - 1] + 3) for i, s in enumerate((1, 3, 6))]
        metrics = strum_pick_metrics(notes, assignment(notes, [(1, 3), (3, 3), (6, 3)]))
        self.assertEqual(metrics["chord_skipped_strings"], 3)
        self.assertEqual(metrics["chord_attack_count"], 1)
        self.assertEqual(metrics["contiguous_chord_count"], 0)
        self.assertEqual(metrics["rapid_single_pair_count"], 0)

    def test_held_middle_string_does_not_become_a_new_chord_attack(self):
        notes = [note("held-b3", 59, 0, 1440), note("new-e4", 64, 480, 960),
                 note("new-g3", 55, 480, 960)]
        metrics = strum_pick_metrics(notes, assignment(notes, [(2, 0), (1, 0), (3, 0)]))
        self.assertEqual(metrics["priority_cost"], [0, 1, 0])
        self.assertEqual(metrics["chord_attack_count"], 1)

    def test_same_and_adjacent_strings_have_zero_skips(self):
        notes, contacts = metric_phrase([4, 4, 5])
        metrics = strum_pick_metrics(notes, contacts)
        self.assertEqual(metrics["rapid_single_pair_count"], 2)
        self.assertEqual(metrics["rapid_single_skipped_strings"], 0)
        self.assertEqual(metrics["rapid_single_skip_transition_count"], 0)

    def test_repeat_retains_last_nonzero_crossing_direction(self):
        notes, contacts = metric_phrase([1, 3, 3, 2])
        metrics = strum_pick_metrics(notes, contacts)
        self.assertEqual(metrics["rapid_single_skipped_strings"], 1)
        self.assertEqual(metrics["rapid_run_direction_reversals"], 1)

    def test_chord_breaks_single_note_chain_and_direction(self):
        strings = [1, 3, 2, 4, 3, 2]
        notes, contacts = metric_phrase(strings, [0, 96, 192, 192, 288, 384])
        metrics = strum_pick_metrics(notes, contacts)
        self.assertEqual(metrics["rapid_single_pair_count"], 2)
        self.assertEqual(metrics["rapid_run_direction_reversals"], 0)
        self.assertEqual(metrics["chord_skipped_strings"], 1)

    def test_long_gap_breaks_direction_without_compressing_time(self):
        notes, contacts = metric_phrase([1, 3, 2, 1], [0, 96, 1000, 1096])
        metrics = strum_pick_metrics(notes, contacts)
        self.assertEqual(metrics["rapid_single_pair_count"], 2)
        self.assertEqual(metrics["rapid_run_direction_reversals"], 0)

    def test_exact_cutoff_and_source_ppqn_are_respected(self):
        for ppqn in (96, 960):
            boundary = ppqn // 2
            notes = [note("low", 28, 0, 1), note("high", 64, boundary, boundary + 1)]
            contacts = assignment(notes, [(8, 0), (1, 0)])
            on_boundary = strum_pick_metrics(notes, contacts, ticks_per_beat=ppqn)
            self.assertEqual(on_boundary["rapid_single_skipped_strings"], 6)
            self.assertEqual(on_boundary["rapid_single_pair_count"], 1)
            notes[1]["start_tick"] += 1
            notes[1]["end_tick"] += 1
            after = strum_pick_metrics(notes, contacts, ticks_per_beat=ppqn)
            self.assertEqual(after["rapid_single_pair_count"], 0)
            self.assertEqual(after["rapid_single_skipped_strings"], 0)


class PickingOptimizerIndependentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapper = importlib.import_module("fretboard_strum_efficiency")

    def checked(self, notes):
        original = deepcopy(notes)
        version = self.mapper.optimize_strum_fingering(notes)
        self.assertEqual(notes, original)
        metrics = validate_version(notes, version)
        self.assertEqual((*metrics["priority_cost"], metrics["rapid_run_direction_reversals"]),
                         exhaustive_primary_and_direction(notes))
        return version, metrics

    def test_opens_outrank_a_more_contiguous_chord(self):
        notes = [note("e1", 28), note("e4", 64)]
        version, metrics = self.checked(notes)
        self.assertEqual(metrics["priority_cost"], [0, 6, 0])
        self.assertEqual({(a["string_number"], a["fret"]) for a in version["assignments"]},
                         {(8, 0), (1, 0)})

    def test_opens_outrank_reducing_rapid_string_skips(self):
        _, metrics = self.checked([note("e1", 28), note("e4", 64, 96, 192)])
        self.assertEqual(metrics["priority_cost"], [0, 0, 6])

    def test_chord_priority_wins_a_real_held_note_tradeoff(self):
        notes = [note("e2", 40), note("held-gsharp2", 44, 0, 288),
                 note("b2", 47, 96, 192), note("c4", 60, 192, 288)]
        version, metrics = self.checked(notes)
        self.assertEqual(metrics["priority_cost"], [0, 0, 1])
        held = next(a for a in version["assignments"] if a["note_id"] == "held-gsharp2")
        self.assertEqual((held["string_number"], held["fret"]), (7, 9))
        alternative = assignment(notes, [(6, 0), (8, 16), (7, 12), (6, 20)])
        self.assertEqual(strum_pick_metrics(notes, alternative)["priority_cost"], [0, 1, 0])

    def test_single_note_priority_can_choose_a_higher_fret(self):
        version, metrics = self.checked([note("fsharp4", 66), note("e1", 28, 96, 192)])
        self.assertEqual(metrics["priority_cost"], [0, 0, 2])
        first = next(a for a in version["assignments"] if a["note_id"] == "fsharp4")
        self.assertEqual((first["string_number"], first["fret"]), (5, 21))

    def test_direction_tie_break_matches_full_assignment_enumeration(self):
        notes = [note(i, pitch, i * 96, (i + 1) * 96)
                 for i, pitch in enumerate((47, 60, 73, 60, 47))]
        _, metrics = self.checked(notes)
        self.assertEqual(metrics["priority_cost"], [0, 0, 0])
        self.assertEqual(metrics["rapid_run_direction_reversals"], 1)

    def test_future_held_note_can_make_an_open_physically_unavailable(self):
        _, metrics = self.checked([note("held-e4", 64, 0, 1920),
                                   note("later-e6", 88, 960, 1920)])
        self.assertEqual(metrics["open_note_count"], 0)
        self.assertEqual(metrics["priority_cost"][0], 1)


# A/B retain their original hand-optimizer versions. C intentionally uses the
# replacement MIDI and is checked against its new raw source and optimum below.
LEGACY_DIGESTS = {
    ("cfa029a2", "greedy"): "f747ffc330cac8722acb6c0555c1649c8477149fa902314026284717944a3d4d",
    ("cfa029a2", "optimized"): "2e1fd41b989455a5402e8a24e8ac8c17c780a7ad424f6da14050d0d8132e4c8c",
    ("da80eca9", "greedy"): "841aa40db82392b29fc9a197efd1af43c92d07f4187f23567d12d692d8ef2531",
    ("da80eca9", "optimized"): "1e9cb51065f4ef9f115286ecc4ce97fa5fc6b9cc18488638f3ff36ea22c70a37",
}
LEGACY_PICKING_COSTS = {
    ("cfa029a2", "greedy"): [4, 3, 53], ("cfa029a2", "optimized"): [4, 9, 84],
    ("da80eca9", "greedy"): [4, 15, 23], ("da80eca9", "optimized"): [4, 33, 72],
}


class FrozenPickingFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "public/data/fretboard-efficiency-fixtures.json").read_text())
        cls.source_dir = ROOT / "tests/fixtures/fretboard-efficiency"

    def test_all_three_profiles_and_actual_exports_pass_the_independent_oracle(self):
        report = validate_dataset(self.data, self.source_dir)
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["fixtures"]), 4)
        self.assertTrue(all(set(f["versions"]) == (
                            {"greedy", "optimized", "strumPick", "stable"} if f["fixture"] == "186bfd78"
                            else {"greedy", "optimized", "strumPick"})
                            for f in report["fixtures"]))

    def test_november_twenty_stable_frets_minimizes_neck_travel_without_chord_gaps(self):
        fixture = next(f for f in self.data["fixtures"] if f["id"] == "186bfd78")
        versions = {v["id"]: v for v in fixture["versions"]}
        old = versions["strumPick"]["metrics"]
        stable = versions["stable"]["metrics"]
        self.assertEqual(stable["open_used"], old["open_used"])
        self.assertEqual(stable["chord_skipped_strings"], old["chord_skipped_strings"])
        self.assertLess(stable["hand_travel_frets"], old["hand_travel_frets"])
        self.assertLessEqual(stable["rapid_shift_cost"], old["rapid_shift_cost"])

    def test_c_repeated_high_dyads_keep_the_same_fretted_shape(self):
        fixture = next(f for f in self.data["fixtures"] if f["id"] == "c5a35486")
        version = next(v for v in fixture["versions"] if v["id"] == "strumPick")
        positions = {a["note_id"]: (a["string_number"], a["fret"])
                     for a in version["assignments"]}
        for first, repeat in (((30, 31), (33, 34)), ((99, 100), (102, 103))):
            self.assertEqual([positions[n] for n in first],
                             [positions[n] for n in repeat])
        self.assertEqual(version["metrics"]["repeated_shape_remaps"], 0)

    def test_full_fixture_primary_costs_are_independently_optimal(self):
        for fixture in self.data["fixtures"]:
            with self.subTest(fixture=fixture["id"]):
                raw = read_midi_source(self.source_dir / fixture["source_filename"])
                proof = full_source_primary_optimum(raw["notes"], ticks_per_beat=raw["ticks_per_beat"],
                                                    tempo_bpm=raw["tempo_bpm"])
                actual = next(v for v in fixture["versions"] if v["id"] == "strumPick")
                self.assertEqual(tuple(actual["metrics"]["priority_cost"]), proof["primary_cost"])

    def test_existing_ab_hand_version_objects_are_unchanged(self):
        seen = set()
        for fixture in self.data["fixtures"]:
            for version in fixture["versions"]:
                key = fixture["id"], version["id"]
                if key in LEGACY_DIGESTS:
                    digest = hashlib.sha256(json.dumps(version, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                    self.assertEqual(digest, LEGACY_DIGESTS[key], key)
                    seen.add(key)
        self.assertEqual(seen, set(LEGACY_DIGESTS))

    def test_old_ab_version_picking_measurements_come_from_source_attacks(self):
        for fixture in self.data["fixtures"]:
            for version in fixture["versions"]:
                key = fixture["id"], version["id"]
                if key in LEGACY_PICKING_COSTS:
                    measured = strum_pick_metrics(fixture["notes"], version["assignments"],
                                                  ticks_per_beat=fixture["ticks_per_beat"],
                                                  tempo_bpm=fixture["tempo_bpm"])
                    self.assertEqual(measured["priority_cost"], LEGACY_PICKING_COSTS[key], key)

    def test_legacy_two_version_bundle_requires_explicit_opt_in(self):
        legacy = deepcopy(self.data)
        for fixture in legacy["fixtures"]:
            fixture["versions"] = [v for v in fixture["versions"] if v["id"] != "strumPick"]
        with self.assertRaisesRegex(ValidationError, "legacy bundles"):
            validate_dataset(legacy, self.source_dir)
        self.assertTrue(validate_dataset(legacy, self.source_dir, allow_legacy_versions=True)["passed"])

    def test_forged_picking_metric_is_rejected(self):
        fixture = deepcopy(next(f for f in self.data["fixtures"] if f["id"] == "c5a35486"))
        version = next(v for v in fixture["versions"] if v["id"] == "strumPick")
        version["metrics"]["rapid_single_skipped_strings"] += 1
        with self.assertRaisesRegex(ValidationError, "independent picking metric"):
            validate_version(fixture["notes"], version, ticks_per_beat=96)


if __name__ == "__main__":
    unittest.main()
