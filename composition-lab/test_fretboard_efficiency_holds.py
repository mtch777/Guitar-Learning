"""Greedy comparison must keep a complete legal path through held contacts."""
from copy import deepcopy
import unittest

from fretboard_efficiency import DROP_E, greedy_fingering


def note(note_id, pitch, start, end):
    return dict(id=note_id, pitch=pitch, start_tick=start, end_tick=end,
                velocity=90, channel=0)


class GreedyHeldContinuationTests(unittest.TestCase):
    def test_dead_end_is_removed_through_an_intermediate_attack(self):
        # Lowest-fret C4 (S2/F1) fits the middle open E1 but strands the later
        # E5. A one-step-only filter cannot see this; backward feasibility must
        # retain the same C4 occurrence across all three attacks at S4/F10.
        notes = [note('held-c4', 60, 0, 2880),
                 note('middle-e1', 28, 960, 1920),
                 note('later-e5', 76, 1920, 2880)]
        before = deepcopy(notes)
        result = greedy_fingering(notes)
        self.assertEqual(notes, before)
        contacts = {a['note_id']: (a['string_number'], a['fret'])
                    for a in result['assignments']}
        self.assertEqual(contacts, {'held-c4': (4, 10),
                                    'middle-e1': (8, 0), 'later-e5': (1, 12)})
        self.assertEqual([p['active_note_ids'] for p in result['positions']],
                         [['held-c4'], ['held-c4', 'middle-e1'], ['held-c4', 'later-e5']])
        for source in notes:
            string, fret = contacts[source['id']]
            self.assertEqual(DROP_E[string - 1] + fret, source['pitch'])

    def test_released_contact_does_not_trigger_future_cost_lookahead(self):
        notes = [note('released-c4', 60, 0, 960), note('later-e5', 76, 960, 1920)]
        result = greedy_fingering(notes)
        contacts = {a['note_id']: (a['string_number'], a['fret'])
                    for a in result['assignments']}
        self.assertEqual(contacts['released-c4'], (2, 1),
                         'A released low-fret grip remains the local choice despite the later shift.')
        self.assertEqual(contacts['later-e5'], (1, 12))

    def test_impossible_held_string_is_refused_without_rewriting_notes(self):
        notes = [note('held-e1', 28, 0, 1920), note('later-f1', 29, 960, 1920)]
        before = deepcopy(notes)
        with self.assertRaises(ValueError):
            greedy_fingering(notes)
        self.assertEqual(notes, before)


if __name__ == '__main__':
    unittest.main()
