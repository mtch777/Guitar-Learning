import unittest
from aligned_relationship_audit import interval_stream,changes,compare


class AlignedRelationshipTests(unittest.TestCase):
    def event(self,q,d,p):return dict(local_q=q,duration_q=d,root=p)

    def test_joint_interval_motion_survives_constant_role_transposition(self):
        harmony=[self.event('0','1',40),self.event('1','1',42)]
        melody=[self.event('0','1/2',64),self.event('1/2','3/2',67)]
        source=interval_stream(harmony,melody)
        shifted=interval_stream([dict(x,root=x['root']+12) for x in harmony],[dict(x,root=x['root']+7) for x in melody])
        self.assertEqual(changes(source),[('1/2',3),('1',-2)])
        self.assertTrue(compare(source,shifted)['complete_trajectory_equal'])

    def test_gaps_do_not_invent_interval_transitions(self):
        h=[self.event('0','1/2',40),self.event('1','1',42)]
        m=[self.event('0','2',64)]
        self.assertEqual(changes(interval_stream(h,m)),[])

    def test_clock_change_and_overlapping_roots_refused(self):
        a=interval_stream([self.event('0','1',40)],[self.event('0','1',64)])
        with self.assertRaisesRegex(ValueError,'clocks'):compare(a,[dict(a[0],until='2')])
        with self.assertRaisesRegex(ValueError,'Overlapping'):interval_stream([self.event('0','2',40),self.event('1','1',42)],[self.event('0','2',64)])


if __name__=='__main__':unittest.main()
