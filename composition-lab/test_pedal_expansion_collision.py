"""Regression for two differently anchored phrases expanding into one gap."""
import copy
import unittest
from fractions import Fraction as F
from pedal_expansion import _merge, expand_phrases
from test_pedal_expansion import fixture


class ExpansionCollisionTests(unittest.TestCase):
    def collision(self):
        groups = [[p] for p in (40,55,40,58,40,50,60,40,50,61,40,50,65,50,68,50)]
        return fixture(groups, [(0,4,40),(11,15,50)])

    def test_expanded_neighbor_is_a_barrier_and_all_cycle_roles_survive(self):
        data, seeds = self.collision()
        snapshot = copy.deepcopy((data, seeds))
        result = expand_phrases(data, seeds)
        self.assertEqual([(r['start_q'], r['end_q']) for r in result], [('0','11'),('11','16')])
        self.assertEqual((data, seeds), snapshot)
        self.assertEqual(sorted(i for r in result for i in r['seed_ids']), ['0','1'])
        for region in result:
            for cycle in region['cycles']:
                for key, role in (('call_members','call'), ('response_members','response')):
                    self.assertTrue(all(region['roles'].get(k) == role for k in cycle[key]))
        self.assertTrue(set(result[0]['members']).isdisjoint(result[1]['members']))

    def test_full_existing_expansion_evaluator_accepts_collision_regression(self):
        from evaluate_pedal_expansion import evaluate
        data, seeds = self.collision()
        report = dict(songs=[dict(song_id=1, tracks=[dict(part_id=0, rows=data)])])
        analysis = dict(song_id=1, part_id=0, section_start=1, accepted=True,
            roles={k:v for s in seeds for k,v in s['roles'].items()},
            cycles=[c for s in seeds for c in s['cycles']], anchor_pitches=[40,50])
        result = evaluate(report, [analysis])
        self.assertEqual(len(result['tracks'][0]['phrases']), 2)
        self.assertGreater(result['counts']['added_exchanges'], 0)

    def test_merge_rejects_conflicting_roles_without_mutating_inputs(self):
        a = dict(start_q='0',end_q='3',seed_ids=['a'],members={'x'},roles={'x':'response'},cycles=[],added_cycles=[])
        b = dict(start_q='2',end_q='5',seed_ids=['b'],members={'x'},roles={'x':'call'},cycles=[],added_cycles=[])
        before = copy.deepcopy([a,b])
        with self.assertRaisesRegex(ValueError, 'Conflicting pedal roles'):
            _merge([a,b])
        self.assertEqual([a,b], before)

    def test_merge_still_joins_compatible_roles_and_retains_cycles(self):
        cycle = dict(call_start_q='0',response_start_q='1',return_q='2',call_members=['a'],response_members=['b'])
        a = dict(start_q='0',end_q='3',seed_ids=['a'],members={'a','b'},roles={'a':'call','b':'response'},cycles=[cycle],added_cycles=[cycle])
        b = dict(start_q='2',end_q='5',seed_ids=['b'],members={'b','c'},roles={'b':'response','c':'call'},cycles=[],added_cycles=[])
        result = _merge([a,b])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['roles'],{'a':'call','b':'response','c':'call'})
        self.assertEqual(result[0]['added_cycles'],[cycle])


if __name__ == '__main__':
    unittest.main()
