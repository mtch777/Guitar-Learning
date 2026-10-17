import unittest
from fractions import Fraction as F
from pedal_patterns import detect,detect_bursts


def rows(groups,times=None):
    out=[]
    for i,pitches in enumerate(groups):
        for j,p in enumerate(pitches):out.append(dict(occurrence=f'{i}:{j}',onset_q=str(i if times is None else times[i]),duration_q='1/2',tie_destination=False,midi=p,bar=i//4+1,section='A'))
    return out


class PedalPatternTests(unittest.TestCase):
    def test_polyphonic_returns_do_not_require_highest_note_projection(self):
        r=rows([[40,47],[64,65],[40,47],[67,69],[40,47],[38,39]])
        candidates,_=detect(r)
        self.assertTrue(any(c['anchor_midi']==40 for c in candidates))
    def test_constant_chord_root_is_not_returning_anchor(self):
        r=rows([[40,64],[40,65],[40,67],[40,69],[40,71],[40,72]])
        self.assertEqual(detect(r)[0],[])
    def test_period_sensitivity_is_explicit(self):
        r=rows([[40],[64],[40],[67],[40],[69]],[0,1,2,3,6,7])
        self.assertEqual(detect(r,F(0))[0],[])
        self.assertTrue(detect(r,F(1,2))[0])
    def test_recurrence_retains_member_evidence(self):
        r=rows([[40],[64],[40],[67],[40],[69]]*2)
        candidates,recurrences=detect(r)
        self.assertTrue(recurrences);self.assertEqual(len(candidates[0]['members']),6)
    def test_multiple_anchor_attacks_then_fills(self):
        r=rows([[40,47],[40,47],[64],[40,47],[40,47],[67],[40,47],[40,47],[69]])
        c=detect_bursts(r)
        self.assertTrue(any(x['anchor_midi']==40 and x['burst_attack_counts']==[2,1,2,1,2,1] for x in c))
    def test_bursts_do_not_cross_annotated_section_boundary(self):
        r=rows([[40],[64],[40],[67],[40],[69]])
        for n in r[4:]:n['section']='B'
        self.assertEqual(detect_bursts(r),[])


if __name__=='__main__':unittest.main()
