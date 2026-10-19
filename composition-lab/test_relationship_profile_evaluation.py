import math
import unittest
from copy import deepcopy
from relationship_profile_evaluation import evaluate_boolean_relationships


def table(context, positive, negative, feature='bend'):
    return dict(kind='technique_given_context', condition=dict(feature=feature,value=context),
        eligible_count=positive+negative, outcomes=[dict(outcome=bool(y),weight=n,count=n)
        for y,n in [(1,positive),(0,negative)] if n])


def pair():
    dev=dict(scope='development_fit',artist='A',training_songs=[1],training_families=['a'],
             tables=[table('long',9,1),table('short',1,9)])
    held=dict(scope='heldout_descriptive_only',artist='A',observed_songs=[2],observed_families=['b'],
              tables=[table('long',9,1),table('short',1,9)])
    return dev,held


class EvaluationTests(unittest.TestCase):
    def test_predictive_relationship_beats_marginal_without_mutating_fit(self):
        d,h=pair();before=deepcopy(d)
        r=evaluate_boolean_relationships(d,h)['results'][0]
        self.assertGreater(r['log_loss_improvement'],0)
        self.assertGreater(r['brier_improvement'],0)
        self.assertEqual(d,before)

    def test_unseen_context_backs_off_without_inventing_support(self):
        d,h=pair();h['tables']=[table('unseen',1,1)]
        r=evaluate_boolean_relationships(d,h)['results'][0]
        self.assertEqual(r['backoff_mass'],2)
        self.assertEqual(r['fitted_context_mass'],0)
        self.assertEqual(r['log_loss_improvement'],0)

    def test_unsupported_feature_is_not_scored_as_negative(self):
        d,h=pair();h['tables']=[table('long',1,1,feature='slide')]
        r=evaluate_boolean_relationships(d,h)['results'][0]
        self.assertEqual(r['unsupported_mass'],2)
        self.assertIsNone(r['baseline_log_loss'])

    def test_family_leakage_and_invalid_weights_fail(self):
        d,h=pair();h['observed_families']=['a']
        with self.assertRaises(ValueError):evaluate_boolean_relationships(d,h)
        d,h=pair();d['tables'][0]['outcomes'][0]['weight']=math.nan
        with self.assertRaises(ValueError):evaluate_boolean_relationships(d,h)

    def test_fixed_parameter_validation_and_reversed_relation(self):
        d,h=pair();h['tables']=[table('long',1,9),table('short',9,1)]
        self.assertLess(evaluate_boolean_relationships(d,h)['results'][0]['log_loss_improvement'],0)
        for value in (0,-1,True,math.nan,math.inf):
            with self.assertRaises(ValueError):evaluate_boolean_relationships(d,h,prior_mass=value)
        for value in (0,.5,True,math.nan):
            with self.assertRaises(ValueError):evaluate_boolean_relationships(d,h,epsilon=value)

    def test_family_sensitivity_exposes_opposing_results(self):
        d,h=pair();h['observed_songs']=[2,3];h['observed_families']=['b','c']
        for t in h['tables']:
            for o in t['outcomes']:
                o['song_counts']=[dict(song_id=2,family='b',count=o['count']),
                    dict(song_id=3,family='c',count=10-o['count'])]
                o['count']=10;o['weight']=1
            t['eligible_count']=20
        r=evaluate_boolean_relationships(d,h)
        s=r['results'][0]['family_sensitivity']
        self.assertEqual(s['families'],2)
        self.assertEqual(s['improving_families'],1)
        self.assertLess(s['minimum_leave_one_family_out_improvement'],0)
        self.assertGreater(s['maximum_leave_one_family_out_improvement'],0)
        self.assertEqual(len(r['per_song']),2)

    def test_per_song_evidence_cannot_invent_support(self):
        d,h=pair();o=h['tables'][0]['outcomes'][0]
        o['song_counts']=[dict(song_id=2,family='b',count=999)]
        with self.assertRaisesRegex(ValueError,'reconcile'):evaluate_boolean_relationships(d,h)
        o['song_counts']=[dict(song_id=999,family='b',count=o['count'])]
        with self.assertRaisesRegex(ValueError,'outside'):evaluate_boolean_relationships(d,h)


if __name__=='__main__':unittest.main()
