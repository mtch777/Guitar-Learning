"""Focused behavioral checks of the independent strum/pick optimizer."""
from copy import deepcopy
import unittest

from fretboard_strum_efficiency import optimize_strum_fingering


def note(note_id, pitch, start, end):
    return dict(id=note_id, pitch=pitch, start_tick=start, end_tick=end, velocity=90, channel=0)


def phrase(pitches, starts=None):
    starts = starts or [i * 120 for i in range(len(pitches))]
    return [note(i, pitch, start, start + 60) for i, (pitch, start) in enumerate(zip(pitches, starts))]


class StrumPriorityTests(unittest.TestCase):
    def checked(self, notes, **kwargs):
        before = deepcopy(notes)
        result = optimize_strum_fingering(notes, **kwargs)
        self.assertEqual(notes, before)
        self.assertEqual(result['id'], 'strumPick')
        self.assertEqual(result['metrics']['tier_cost'], result['metrics']['priority_cost'])
        self.assertEqual(len(result['metrics']['priority_cost']), 3)
        self.assertEqual(len(result['metrics']['tie_break_cost']), 5)
        return result

    def test_open_priority_beats_adjacent_strumming(self):
        result = self.checked([note(0, 28, 0, 960), note(1, 40, 0, 960)])
        self.assertEqual(result['metrics']['priority_cost'], [0, 1, 0])
        self.assertEqual(result['metrics']['open_used'], 2)
        self.assertEqual(result['metrics']['chord_attack_count'], 1)
        self.assertEqual(result['metrics']['contiguous_chord_count'], 0)

    def test_chord_gaps_precede_rapid_single_gaps(self):
        # The alternative [0,1,0] makes the following singles contiguous at the
        # expense of one gap in the first chord. The requested order chooses
        # [0,0,1], even though its rapid single pair skips a string.
        result = self.checked([note(0, 40, 0, 96), note(1, 44, 0, 288),
                               note(2, 47, 96, 192), note(3, 60, 192, 288)])
        self.assertEqual(result['metrics']['priority_cost'], [0, 0, 1])
        self.assertEqual(result['metrics']['rapid_single_pair_count'], 1)

    def test_new_single_attack_over_sustain_is_not_a_chord(self):
        result = self.checked([note(0, 28, 0, 960), note(1, 40, 240, 720)])
        self.assertEqual(result['metrics']['chord_attack_count'], 0)
        self.assertEqual(result['metrics']['priority_cost'], [0, 0, 1])
        self.assertEqual(result['metrics']['rapid_single_pair_count'], 1)
        self.assertEqual(result['positions'][1]['active_note_ids'], [0, 1])
        self.assertEqual(result['positions'][1]['attack_note_ids'], [1])

    def test_repeated_and_adjacent_strings_both_cost_zero(self):
        result = self.checked(phrase([28, 35, 35, 40]))
        self.assertEqual(result['metrics']['priority_cost'], [0, 0, 0])
        self.assertEqual(result['metrics']['rapid_single_pair_count'], 3)
        self.assertEqual(result['metrics']['rapid_run_direction_reversals'], 0)

    def test_repeat_retains_last_nonzero_direction(self):
        result = self.checked(phrase([28, 35, 35, 28]))
        self.assertEqual(result['metrics']['rapid_single_skipped_strings'], 0)
        self.assertEqual(result['metrics']['rapid_run_direction_reversals'], 1)

    def test_chord_and_long_gap_reset_direction(self):
        chord = phrase([28, 35], [0, 120]) + [note(2, 28, 240, 300), note(3, 40, 240, 300)] \
            + [note(4, 40, 360, 420), note(5, 35, 480, 540)]
        result = self.checked(chord)
        self.assertEqual(result['metrics']['rapid_run_direction_reversals'], 0)
        self.assertEqual(result['metrics']['rapid_single_pair_count'], 2)
        self.assertEqual(result['positions'][2]['picking_order'], [8, 6])
        result = self.checked(phrase([28, 35, 40, 35], [0, 120, 960, 1080]))
        self.assertEqual(result['metrics']['rapid_run_direction_reversals'], 0)
        self.assertEqual(result['metrics']['rapid_single_pair_count'], 2)

    def test_rapid_cutoff_includes_exact_boundary(self):
        within = self.checked(phrase([28, 40], [0, 480]))
        outside = self.checked(phrase([28, 40], [0, 481]))
        self.assertEqual(within['metrics']['rapid_single_skipped_strings'], 1)
        self.assertEqual(within['metrics']['rapid_single_pair_count'], 1)
        self.assertEqual(outside['metrics']['rapid_single_skipped_strings'], 0)
        self.assertEqual(outside['metrics']['rapid_single_pair_count'], 0)

    def test_duplicate_open_pitch_preserves_both_occurrences(self):
        result = self.checked([note(0, 59, 0, 960), note(1, 59, 0, 960)])
        self.assertEqual(result['metrics']['priority_cost'], [1, 0, 0])
        self.assertEqual(result['metrics']['open_used'], 1)
        self.assertEqual(len(result['assignments']), 2)
        self.assertEqual(len({a['string_number'] for a in result['assignments']}), 2)

    def test_repeated_dyad_keeps_shape_through_open_string_interlude(self):
        notes = [note(0, 60, 0, 120), note(1, 76, 60, 180),
                 note(2, 83, 120, 180), note(3, 35, 240, 300),
                 note(4, 76, 360, 480), note(5, 83, 360, 480)]
        result = self.checked(notes)
        assigned = {a['note_id']: (a['string_number'], a['fret'])
                    for a in result['assignments']}
        self.assertEqual((assigned[1], assigned[2]), (assigned[4], assigned[5]))
        self.assertEqual(result['metrics']['repeated_shape_remaps'], 0)

    def test_held_open_exception_is_global_and_exact(self):
        result = self.checked([note(0, 64, 0, 1920), note(1, 88, 960, 1920)])
        self.assertEqual(result['metrics']['open_used'], 0)
        contacts = {a['note_id']: (a['string_number'], a['fret']) for a in result['assignments']}
        self.assertEqual(contacts, {0: (6, 24), 1: (1, 24)})

    def test_impossible_hold_and_invalid_cutoff_fail_without_rewriting(self):
        notes = [note(0, 28, 0, 1920), note(1, 29, 960, 1920)]
        before = deepcopy(notes)
        with self.assertRaises(ValueError):
            optimize_strum_fingering(notes)
        self.assertEqual(notes, before)
        for value in (0, -1, float('inf'), float('nan'), True, '0.25'):
            with self.assertRaises(ValueError):
                optimize_strum_fingering(phrase([28]), rapid_max_gap_seconds=value)

    def test_equal_results_are_deterministic_under_input_order(self):
        notes = phrase([54, 52, 54, 52])
        first = self.checked(notes)
        second = self.checked(list(reversed(notes)))
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
