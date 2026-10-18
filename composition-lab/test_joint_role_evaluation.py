import copy,unittest
from joint_role_evaluation import evaluate,balanced

class JointRoleTests(unittest.TestCase):
    def fixture(self):
        records=[]
        for role,shift in [('harmony',0),('melody',12),('bass',-12)]:
            records.append((role,dict(part_id=0,song_id=2,bar=1,root_events=[dict(root=40+i%4+shift,local_q=str(i),duration_q='1') for i in range(40)])))
        held=dict(training_songs=[2],parts={r:{'held':[p]} for r,p in records})
        trained=dict(training_songs=[1],parts={r:{'f':[dict(p,song_id=1)]} for r,p in records},
            joint_offsets={'melody':{'f':{'1':{'12':40}}},'bass':{'f':{'1':{'-12':40}}}})
        return trained,held

    def test_known_relation_beats_shuffled_anchor(self):
        train,held=self.fixture();result=evaluate(train,held)
        for role,m in result['equal_song'].items():self.assertLess(m['joint'],m['shuffled_harmony'])
        self.assertTrue(all(r['shuffled_anchor_changed'] for r in result['by_song']))

    def test_leakage_rejected(self):
        train,held=self.fixture();held['training_songs']=[1]
        with self.assertRaises(ValueError):evaluate(train,held)

    def test_family_song_balance(self):
        self.assertEqual(balanced({'a':{'1':{'0':100},'2':{'1':1}},'b':{'3':{'2':1}}}),{0:.25,1:.25,2:.5})

if __name__=='__main__':unittest.main()
