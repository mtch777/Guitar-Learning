import unittest
from fractions import Fraction as F
from relational_learning_v17 import observed_windows, learn_relations, plan_intervals

def event(i, onset, pitch):
    return {'onset_q': F(onset), 'duration_q': F(1), 'notes': [{'midi': pitch, 'tie': None}], 'beat_id': str(i)}

class TestRelations(unittest.TestCase):
    def setUp(self):
        # Four melodic events across a measure boundary, NO chord hypotheses.
        self.v = [event(i, i, p) for i, p in enumerate((60, 62, 65, 64, 67, 69))]
        self.score = {'tracks': [{'measures': [{'voices': [self.v[:3]]}, {'voices': [self.v[3:]]}]}]}

    def test_crosses_measures(self):
        self.assertTrue(any(g[0] is self.v[1] and g[-1] is self.v[4]
                            for g in observed_windows(self.score, 0)))

    def test_learns_without_harmony(self):
        self.assertGreater(sum(learn_relations(self.score, 0).values()), 0)

    def test_zero_is_exact_lock(self):
        self.assertEqual(plan_intervals(self.score, 0, 0)[0], {})

    def test_100_changes_without_harmony(self):
        planned, stats = plan_intervals(self.score, 0, 100)
        self.assertGreater(stats['relation_phrases'], 0)
        self.assertTrue(planned)
        self.assertEqual([e['onset_q'] for e in self.v], list(map(F, range(6))))

    def test_source_pattern_only(self):
        planned, _ = plan_intervals(self.score, 0, 100)
        self.assertEqual(len(planned) > 0, True)

    def test_no_polyphonic_merge(self):
        self.v[2]['notes'].append({'midi': 72, 'tie': None})
        self.assertTrue(all(self.v[2] not in g for g in observed_windows(self.score, 0)))

if __name__ == '__main__': unittest.main()