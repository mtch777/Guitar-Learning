import unittest
from fractions import Fraction as F
from contextual_bends import choose, target_scores, trajectory, segment_properties, interpolate
from bend_analysis import bend_shape


def note(ident,start,end,pitch):
    return dict(id=ident,start=F(start),end=F(end),midi=pitch,voice=0)


class ContextualBendTests(unittest.TestCase):
    def test_support_changes_target_choice(self):
        n=note('a',0,2,60)
        one=target_scores(n,None,[note('s',0,2,61)])
        two=target_scores(n,None,[note('s',0,2,62)])
        self.assertGreater(one[1],one[2]);self.assertGreater(two[2],two[1])
    def test_held_overlap_prevents_bend(self):
        lead=[note('a',0,2,60),note('b',1,3,64)]
        self.assertEqual(choose(lead,[note('s',0,4,62)]),{})
    def test_variation_has_continuous_tie_boundary(self):
        points=trajectory(2,F(3,2),True)
        a=segment_properties(points,F(0),F(1,2));b=segment_properties(points,F(1,2),F(1))
        x=bend_shape('<Note><Properties>'+''.join(a)+'</Properties></Note>')
        y=bend_shape('<Note><Properties>'+''.join(b)+'</Properties></Note>')
        self.assertEqual(x['end_semitones'],y['start_semitones'])
        self.assertEqual(interpolate(points,F(1)),0)
    def test_single_segment_curves_are_representable(self):
        for d in (F(1,2),F(3,2),F(3)):
            p=trajectory(2,d,True);segment_properties(p,F(0),F(1))


if __name__=='__main__':unittest.main()
