import unittest
from performance_sampling_audit import summarize


class SamplingAuditTests(unittest.TestCase):
    def test_exact_moments_and_release_filter(self):
        rows=[dict(family='bend',probability=p,released=True,proposed_selected=s) for p,s in [(0,False),(1,True),(.5,True)]]
        rows.append(dict(family='bend',probability=1,released=False,proposed_selected=True))
        r=summarize(rows)['bend']
        self.assertEqual(r['released_eligible_decisions'],3)
        self.assertEqual(r['nominal_expected_selections'],1.5)
        self.assertEqual(r['selected_proposals'],2)
        self.assertEqual(r['bernoulli_reference_sd'],.5)
        self.assertEqual(r['backoff_known'],0)

    def test_rejects_invalid_probabilities(self):
        for p in (True,float('nan'),float('inf'),-1,1.1):
            with self.assertRaises(ValueError):summarize([dict(probability=p,released=True)])


if __name__=='__main__':unittest.main()
