from fractions import Fraction as F
import unittest
from bend_timing import schedule,pitch_support
from contextual_bends import segment_properties,interpolate
from bend_analysis import bend_shape


class BendTimingTests(unittest.TestCase):
    def note(self):
        return dict(id='a',midi=60,start=F(0),end=F(4),segments=[dict(id='0',start=F(0),duration=F(2)),dict(id='1',start=F(2),duration=F(2))])
    def test_arrival_is_within_segment_and_before_note_end(self):
        for mode in ('pulse','delayed','response'):
            points,detail=schedule(self.note(),2,[],[dict(onset_q='0',time_signature='4/4')],mode)
            self.assertGreater(F(detail['arrival_q']),F(detail['begin_q']))
            self.assertLessEqual(F(detail['arrival_q']),2)
            self.assertEqual(max(v for x,v in points),2)
    def test_track_normalization_avoids_dense_track_domination(self):
        support=[dict(track=0,midi=62,start=F(0),end=F(4))]+[dict(track=1,midi=60,start=F(0),end=F(4)) for _ in range(10)]
        self.assertEqual(pitch_support(62,F(1),support),.5)
    def test_delay_and_release_encode_without_losing_curve(self):
        points=[(F(0),F(0)),(F(1,4),F(0)),(F(1,2),F(2)),(F(3,4),F(2)),(F(1),F(0))]
        props=segment_properties(points,F(0),F(1))
        curve=bend_shape('<Note><Properties>'+''.join(props)+'</Properties></Note>')
        decoded=[(F(p['offset_fraction']),F(p['semitones'])) for p in curve['points']]
        for i in range(21):self.assertAlmostEqual(float(interpolate(points,F(i,20))),float(interpolate(decoded,F(i,20))),places=8)
    def test_tied_seams_have_exact_quartertone_pitch(self):
        n=self.note()
        for mode in ('pulse','delayed','response'):
            points,_=schedule(n,2,[],[dict(onset_q='0',time_signature='4/4')],mode)
            self.assertEqual((interpolate(points,F(1,2))*2).denominator,1)
            for left,right in ((F(0),F(1,2)),(F(1,2),F(1))):segment_properties(points,left,right)

    def test_delayed_hold_is_zero_before_origin_offset(self):
        points=[(F(0),F(0)),(F(1,4),F(0)),(F(3,4),F(2)),(F(1),F(2))]
        props=segment_properties(points,F(0),F(1))
        curve=bend_shape('<Note><Properties>'+''.join(props)+'</Properties></Note>')
        decoded=[(F(p['offset_fraction']),F(p['semitones'])) for p in curve['points']]
        self.assertEqual(interpolate(decoded,F(0)),0)
        self.assertEqual(interpolate(decoded,F(1)),2)


if __name__=='__main__':unittest.main()
