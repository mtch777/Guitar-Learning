import copy
import unittest
from recording_review_export import export_recording_review as export


class ReviewTests(unittest.TestCase):
    def segment(self, **kw):
        value = dict(id='a', start_seconds=0, end_seconds=2,
                     candidate_weights={'verse': .6, 'chorus': .4})
        value.update(kw)
        return value

    def test_same_winner_preserves_boundaries_and_alternatives(self):
        source = [self.segment(), self.segment(id='b', start_seconds=2, end_seconds=4,
                  candidate_weights={'verse': .9, 'chorus': .1})]
        result = export(source, recording_duration=4)
        self.assertEqual(result['segments'], source)
        self.assertEqual(len(result['timeline']), 2)
        self.assertEqual(result['timeline'][1]['segment'], source[1])

    def test_gaps_and_unknown(self):
        s = self.segment(start_seconds=1, end_seconds=2, candidate_weights={}, status='unknown')
        r = export([s, self.segment(id='b', start_seconds=3, end_seconds=4)], recording_duration=5)
        self.assertEqual([x['kind'] for x in r['timeline']],
                         ['gap', 'detected_segment', 'gap', 'detected_segment', 'gap'])
        self.assertEqual(r['segments'][0], s)

    def test_empty_is_all_gap(self):
        r = export([], recording_duration=5)
        self.assertEqual(r['segments'], [])
        self.assertEqual(r['timeline'][0]['end_seconds'], 5)

    def test_no_mutation_or_alias(self):
        s = [self.segment(metadata={'origin': ['original']})]
        before = copy.deepcopy(s)
        r = export(s, recording_duration=2)
        self.assertEqual(s, before)
        r['segments'][0]['candidate_weights']['verse'] = 0
        r['timeline'][0]['segment']['metadata']['origin'].append('changed')
        self.assertEqual(s, before)

    def test_bad_distribution(self):
        for weights in ({}, {'verse': .5}, {'verse': -1, 'chorus': 2},
                        {'verse': float('nan')}, {'verse': float('inf')},
                        {'verse': True}, {'': 1}, {'verse': '1'}):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                export([self.segment(candidate_weights=weights)], recording_duration=2)

    def test_bad_times(self):
        for a, b in ((-1, 1), (2, 1), (1, 1), (0, 3), (True, 2),
                     (float('nan'), 2), (0, float('inf'))):
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                export([self.segment(start_seconds=a, end_seconds=b)], recording_duration=2)

    def test_overlap_unsorted_duplicate(self):
        for second in (self.segment(id='b', start_seconds=1),
                       self.segment(id='b', start_seconds=0),
                       self.segment(start_seconds=2, end_seconds=3)):
            with self.assertRaises(ValueError):
                export([self.segment(), second], recording_duration=4)

    def test_bad_id_duration_and_shape(self):
        for sid in (None, '', ' ', 1):
            with self.assertRaises(ValueError):
                export([self.segment(id=sid)], recording_duration=2)
        for duration in (0, -1, True, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                export([], recording_duration=duration)
        for s in (None, {}, self.segment(candidate_weights=None)):
            with self.assertRaises(ValueError):
                export([s], recording_duration=2)


if __name__ == '__main__':
    unittest.main()
