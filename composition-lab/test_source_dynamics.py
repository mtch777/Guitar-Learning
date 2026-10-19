import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'songsterr_automation' / 'songsterr_api'))
from source_dynamics import dynamic_observations


def measure(*voices):
    return {'voices': [{'beats': beats} for beats in voices]}


def beat(velocity=None, **note):
    result = {'notes': [note]}
    if velocity is not None:
        result['velocity'] = velocity
    return result


class SourceDynamicsTests(unittest.TestCase):
    def test_inherits_across_rest_and_bar_but_not_between_voices(self):
        part = {'measures': [measure([beat('p', rest=True)], [beat(ghost=True)]),
                             measure([beat(ghost=True)], [beat(ghost=True)])]}
        rows = dynamic_observations(part)
        self.assertEqual([r['marking'] for r in rows], [None, 'p', None])
        self.assertEqual(rows[1]['provenance'], 'inherited_explicit')
        self.assertEqual(rows[1]['marking_origin'], {'bar': 1, 'voice': 0, 'beat': 0})

    def test_note_override_does_not_change_inherited_voice_dynamic(self):
        part = {'measures': [measure([beat('mf'),
                            {'notes': [{'velocity': 'pp', 'ghost': True}, {}]}, beat()])]}
        rows = dynamic_observations(part)
        self.assertEqual([r['marking'] for r in rows], ['mf', 'pp', 'mf', 'mf'])
        self.assertEqual(rows[1]['provenance'], 'note_explicit')

    def test_grace_and_following_marking_use_written_order(self):
        part = {'measures': [measure([dict(beat(), graceNote=True), beat('f'), beat()])]}
        rows = dynamic_observations(part)
        self.assertIsNone(rows[0]['marking'])
        self.assertTrue(rows[0]['grace'])
        self.assertEqual([r['provenance'] for r in rows],
                         ['unspecified', 'beat_explicit', 'inherited_explicit'])

    def test_unknown_marking_is_retained_without_fabricated_inheritance(self):
        part = {'measures': [measure([beat('p'), beat('unknown'), beat()])]}
        rows = dynamic_observations(part)
        self.assertEqual([r['marking'] for r in rows], ['p', None, None])
        self.assertEqual(rows[2]['raw_value'], 'unknown')
        self.assertFalse(rows[2]['known'])

    def test_state_is_not_shared_between_tracks(self):
        dynamic_observations({'measures': [measure([beat('ff')])]})
        row = dynamic_observations({'measures': [measure([beat(ghost=True)])]})[0]
        self.assertEqual(row['provenance'], 'unspecified')
        self.assertIsNone(row['marking'])


if __name__ == '__main__':
    unittest.main()
