import unittest
from copy import deepcopy
from voicing_frames import relationship,pitches


def roles(*pairs):return [dict(degree_token=t,relative_octaves=o) for t,o in pairs]


class FrameTests(unittest.TestCase):
    def test_roots_share_same_pattern_and_keep_exact_register(self):
        source=roles(('1',4),('-3',4),('5',4))
        for root in range(12):
            frame=relationship(root,'minor',roles=source)
            self.assertEqual(frame,dict(frame_octave=4,components=[dict(degree_token=t,octave_offset=0) for t in ('1','-3','5')]))
            self.assertEqual(relationship(root,'minor',framed=frame),source)
            self.assertEqual(pitches(root,'minor',source),[root+48,root+51,root+55])

    def test_inversion_and_doubling_recover_member_order(self):
        source=roles(('5',4),('1',5),('3',4),('1',5))
        frame=relationship(0,'major',roles=source)
        self.assertEqual([c['octave_offset'] for c in frame['components']],[0,1,0,1])
        self.assertEqual(relationship(0,'major',framed=frame),source)

    def test_compound_degree_keeps_negative_offset(self):
        source=roles(('9',3),('1',5),('3',4),('5',4),('-7',4))
        frame=relationship(0,'dominant-ninth',roles=source)
        self.assertEqual(frame['frame_octave'],4)
        self.assertEqual(frame['components'][0],dict(degree_token='9',octave_offset=-1))
        self.assertEqual(relationship(0,'dominant-ninth',framed=frame),source)

    def test_floor_and_octave_equivariance(self):
        source=roles(('5',-1),('1',0),('3',0))
        frame=relationship(11,'major',roles=source)
        self.assertEqual(frame['frame_octave'],-1)
        raised=[dict(r,relative_octaves=r['relative_octaves']+2) for r in source]
        other=relationship(11,'major',roles=raised)
        self.assertEqual(other['components'],frame['components'])
        self.assertEqual(other['frame_octave'],frame['frame_octave']+2)
        self.assertEqual(relationship(11,'major',framed=frame),source)

    def test_types_and_noncanonical_frame_are_rejected(self):
        source=roles(('1',4),('3',4),('5',4))
        good=relationship(0,'major',roles=source)
        bad=[]
        for key,value in [('frame_octave',True),('components',[]),('extra','raw note')]:
            x=deepcopy(good);x[key]=value;bad.append(x)
        x=deepcopy(good);x['frame_octave']+=1
        for c in x['components']:c['octave_offset']-=1
        bad.append(x)
        for value in bad:
            with self.assertRaises(ValueError):relationship(0,'major',framed=value)
        for root in (True,12,0.0):
            with self.assertRaises(ValueError):relationship(root,'major',roles=source)
        with self.assertRaises(ValueError):relationship(0,'major',roles=source,framed=good)


if __name__=='__main__':unittest.main()
