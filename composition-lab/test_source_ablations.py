from copy import deepcopy
import unittest
from controlled_generation import demo_plan,realize
from source_ablations import learn_parts,make_score,source_period


class AblationTests(unittest.TestCase):
    def test_features_added_without_changing_shared_harmony(self):
        source=realize(demo_plan()); before=deepcopy(source)
        indices=dict(harmony=1,melody=0,bass=2)
        parts,evidence,meter=learn_parts(source,indices,4,17)
        period,_=source_period(source['tracks'][0],4)
        stages=[make_score(source,indices,parts,meter,s,period) for s in range(1,5)]
        self.assertEqual([len(s['tracks']) for s in stages],[1,1,2,3])
        self.assertEqual(stages[1]['tracks'][0],stages[2]['tracks'][0])
        # Last stage adds source-derived motif section labels, while notes and
        # timing of the common accompaniment stay identical.
        for a,b in zip(stages[2]['tracks'][0]['measures'],stages[3]['tracks'][0]['measures']):
            self.assertEqual(a['voices'],b['voices'])
        self.assertEqual(stages[3]['tracks'][2]['tunings'],source['tracks'][2]['tunings'])
        self.assertEqual([t['program'] for t in stages[3]['tracks']],
                         [source['tracks'][i]['program'] for i in [1,0,2]])
        self.assertEqual(source,before)
        self.assertEqual(parts,learn_parts(source,indices,4,17)[0])


if __name__=='__main__':unittest.main()
