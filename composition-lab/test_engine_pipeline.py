import unittest
from copy import deepcopy
from fractions import Fraction as F
from joint_roles import JointRoleModel
from structural_learning import FormModel
from composition_engine import make_voicing,to_bars,note_event
from engine_controls import vary,distance
from batch_validation import constraints,fingerprint


def fixture():
    tracks=[]
    for ti in range(3):
        info=dict(tunings=[[64,59,55,50,45,40]],program=25)
        events=[note_event(i,1,[(60+ti,4,15+ti)]) for i in range(4)]
        t=to_bars(events,info,1,str(ti));t['index']=ti;tracks.append(t)
    return dict(tracks=tracks)


POOL=[dict(notes=[dict(bar=0,position='0',duration='1/2',pitch=62),dict(bar=0,position='1/2',duration='3/2',pitch=64),dict(bar=0,position='2',duration='1/2',pitch=65),dict(bar=0,position='5/2',duration='3/2',pitch=67)])]


class EngineTests(unittest.TestCase):
    def test_locks_and_neural_rhythm_profile_for_uniform_bars(self):
        base=fixture();old=deepcopy(base)
        for dimension in ('harmony','melody','rhythm'):
            changed,report=vary(base,{dimension:100},POOL)
            self.assertEqual(report['actual'][dimension],100)
            self.assertFalse(constraints(changed)['violations'])
            for other in ('harmony','melody','rhythm','structure'):
                if other!=dimension:self.assertEqual(distance(base,changed,other),0)
        self.assertEqual(base,old)

    def test_zero_identity_and_explicit_infeasibility(self):
        base=fixture();changed,unused=vary(base,{},POOL);self.assertEqual(base,changed)
        with self.assertRaises(ValueError):vary(base,{'structure':25},POOL)
        with self.assertRaises(ValueError):vary(base,{'roles':25},POOL)

    def test_joint_distribution_is_fitted_and_conditional(self):
        a=((0,4,7),0);b=((0,3,7),7)
        model=JointRoleModel().fit([((0,0),a)]*10+[((7,0),b)]*10)
        self.assertEqual(model.distribution((0,0))[a],10)
        self.assertEqual(model.distribution((7,0))[b],10)
        r=model.evaluate([((0,0),a),((7,0),b)])
        self.assertLess(r['conditional_nll'],r['independent_nll'])

    def test_form_learning_uses_sequence_evidence(self):
        model=FormModel()
        for i in range(20):model.add([(0,2),(1,2),(0,2),(2,4)])
        self.assertEqual(model.distribution([(0,2)],.25)[(1,2)],20)

    def test_voicing_constraints_and_transposition_fingerprint(self):
        positions=make_voicing((0,4,7),60,[64,59,55,50,45,40])
        self.assertEqual(len({s for p,s,f in positions}),len(positions))
        x=[('1',(60,64)),('1/2',(62,))];y=[('1',(65,69)),('1/2',(67,))]
        self.assertEqual(fingerprint(x),fingerprint(y))


if __name__=='__main__':unittest.main()
