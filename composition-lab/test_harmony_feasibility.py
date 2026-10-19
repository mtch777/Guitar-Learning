import unittest
from harmony_feasibility import realization,mask,condition,choose
from conditional_harmony_steps import STEPS


class FeasibilityTests(unittest.TestCase):
    def test_original_failure_excluded_and_every_retained_action_realized(self):
        tuning=[58,53,49,44,39,32];allowed=mask(60,[0,1],tuning)
        self.assertFalse(allowed[101+127])
        self.assertTrue(allowed[127]) # zero step
        for step,ok in zip(STEPS,allowed):
            fit=realization(60,step,[0,1],tuning)
            self.assertEqual(fit is not None,ok)
            if fit:
                self.assertEqual(len(set(s for s,f in fit['positions'])),2)
                self.assertEqual(fit['pitches'],[tuning[s]+f for s,f in fit['positions']])

    def test_normalization_preserves_relative_mass_without_dropping_feasible_floor(self):
        ps=[1/255]*255;allowed=[s in (0,1) for s in STEPS];out,mass=condition(ps,allowed)
        self.assertAlmostEqual(mass,2/255);self.assertEqual(out[127:129],[.5,.5]);self.assertAlmostEqual(sum(out),1)
        chosen,audit=choose(ps,allowed,list(STEPS),.75)
        self.assertEqual(chosen,1);self.assertAlmostEqual(audit['removed_mass'],253/255)

    def test_zero_mass_refused_and_category_order_explicit(self):
        ps=[0]*255;ps[127]=1
        with self.assertRaisesRegex(ValueError,'No feasible'):condition(ps,[False]*255)
        with self.assertRaises(ValueError):choose(ps,[True]*255,[0],.5)


if __name__=='__main__':unittest.main()
