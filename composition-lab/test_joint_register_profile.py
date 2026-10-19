import unittest
from copy import deepcopy
from joint_register_profile import fit,score,evaluate,distribution


class JointProfileTests(unittest.TestCase):
    def rows(self):
        return [dict(family=str(f),song_id=f,melody_part=1,onset_q=str(i),R=20+i%2*12,harmony_own_register=i%2*12,tuning_offset=0) for f in range(5) for i in range(20)]

    def test_recover_signal_with_disjoint_family_validation(self):
        result=evaluate(self.rows());self.assertTrue(result['gate_pass']);self.assertEqual(result['families'],5)

    def test_shuffle_preserves_baseline_and_exposes_noops(self):
        rows=self.rows();a,b=fit(rows),fit(rows,True)
        self.assertEqual(distribution(a,0,0,False)[0],distribution(b,0,0,False)[0]);self.assertGreater(b['changed_targets'],0)
        for r in rows:r['harmony_own_register']=0
        no_op=fit(rows,True);self.assertEqual(no_op['shufflable_rows'],0);self.assertEqual(no_op['shuffle_coverage']['unchanged_joint_rows'],len(rows))

    def test_leakage_duplicates_and_unknown_context(self):
        rows=self.rows();model=fit(rows)
        with self.assertRaisesRegex(ValueError,'leakage'):score(rows,model)
        with self.assertRaisesRegex(ValueError,'Duplicate'):fit(rows+[deepcopy(rows[0])])
        ps,support=distribution(model,127,-8);self.assertTrue(support['context_absent']);self.assertTrue(support['tuning_absent']);self.assertAlmostEqual(sum(ps),1);self.assertTrue(all(p>0 for p in ps))


if __name__=='__main__':unittest.main()
