from copy import deepcopy
from fractions import Fraction as F
import unittest
from diagnose_tonal_subdivision import split,join,compare


def observations():
    return [dict(id=1,mask=145,previous_mask=None,sequence=0,start_q='0',end_q='1/3'),dict(id=2,mask=146,previous_mask=145,sequence=0,start_q='1/3',end_q='1'),dict(id=3,mask=145,previous_mask=None,sequence=9,start_q='2',end_q='3')]


class SubdivisionTests(unittest.TestCase):
    def test_exact_rational_join_gaps_and_predecessors(self):
        rows=observations();old=deepcopy(rows);halves,mapping=split(rows)
        self.assertEqual(rows,old);self.assertEqual(join(halves,mapping),rows)
        self.assertEqual(halves[0]['end_q'],'1/6')
        self.assertIsNone(halves[4]['previous_mask']);self.assertEqual(halves[5]['previous_mask'],145)
        self.assertEqual(sum((F(r['end_q'])-F(r['start_q']) for r in rows),F(0)),sum((F(r['end_q'])-F(r['start_q']) for r in halves),F(0)))

    def test_duplicates_bad_predecessor_targets_and_missing_members_fail(self):
        rows=observations()
        for alter in ('duplicate','target','previous'):
            bad=deepcopy(rows)
            if alter=='duplicate':bad[1]['id']=1
            elif alter=='target':bad[0]['target']=dict(state=0)
            else:bad[1]['previous_mask']=0
            with self.assertRaises(ValueError):split(bad)
        halves,mapping=split(rows)
        with self.assertRaises(ValueError):join(halves,mapping[:-1])
        halves[1]['mask']=5
        with self.assertRaises(ValueError):join(halves,mapping)

    def test_averaged_posterior_nll_is_distinct_from_half_average(self):
        rows=observations()[:1];halves,mapping=split(rows)
        def pred(row,p):return dict(observation_ref=row['id'],start_q=row['start_q'],end_q=row['end_q'],posterior=[p]+[(1-p)/23]*23)
        result=compare([pred(rows[0],.5)],[pred(halves[0],.2),pred(halves[1],.8)],mapping,{1:dict(target=dict(state=0))})
        d=result['duration_weighted']
        self.assertAlmostEqual(d['baseline_nll'],d['averaged_posterior_nll'])
        self.assertGreater(d['average_half_nll'],d['averaged_posterior_nll'])
        self.assertAlmostEqual(d['tv'],0)

    def test_prediction_denominator_and_nonfinite_rejected(self):
        rows=observations()[:1];halves,mapping=split(rows)
        def pred(row):return dict(observation_ref=row['id'],start_q=row['start_q'],end_q=row['end_q'],posterior=[1/24]*24)
        with self.assertRaises(ValueError):compare([pred(rows[0])],[pred(halves[0])],mapping,{1:dict(target=dict(state=0))})
        bad=[pred(r) for r in halves];bad[0]['posterior'][0]=float('nan')
        with self.assertRaises(ValueError):compare([pred(rows[0])],bad,mapping,{1:dict(target=dict(state=0))})


if __name__=='__main__':unittest.main()
