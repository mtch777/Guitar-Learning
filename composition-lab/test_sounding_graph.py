import unittest
from copy import deepcopy
from fractions import Fraction as F
from sounding_graph import build_sounding,audit_sounding


def score(events,meter='4/4'):
    return dict(tracks=[dict(index=0,measures=[dict(time_signature=meter,onset_q='0',voices=[events])])])


def event(onset,duration,pitches,ties=None,grace=None):
    return dict(onset_q=str(onset),duration_q=str(duration),grace_type=grace,notes=[dict(midi=p,string=i,tie=ties) for i,p in enumerate(pitches)])


class SoundingTests(unittest.TestCase):
    def test_30_rational_polyphony_and_gap_cases(self):
        # Distinct duration/polyphony/gap combinations, including tuplets.
        for i in range(30):
            with self.subTest(case=i):
                d=F(1,[1,2,3,4,6,8][i%6]);count=1+i%5
                s=score([event(0,d,list(range(60,60+count))),event(d*2,d,[72])]);original=deepcopy(s)
                g=build_sounding(s);a=audit_sounding(s,g)
                self.assertEqual(a['written_occurrences'],count+1);self.assertEqual(a['lane_count'],count)
                self.assertEqual(s,original);self.assertEqual(a['occurrence_coverage'],1)

    def test_exact_tie_chain_includes_all_occurrences(self):
        s=score([event(0,F(1,3),[60],dict(origin='true')),event(F(1,3),F(2,3),[60],dict(origin='true',destination='true')),event(1,2,[60],dict(destination='true'))])
        g=build_sounding(s);a=audit_sounding(s,g)
        self.assertEqual(a['sounding_events'],1);self.assertEqual(next(iter(g['sustains'].values()))['duration_q'],'3')
        self.assertFalse(g['warnings'])

    def test_unmatched_tie_is_retained_not_invented(self):
        g=build_sounding(score([event(0,1,[60],dict(destination='true'))]))
        self.assertEqual(len(g['occurrences']),1);self.assertEqual(g['warnings'][0]['type'],'unresolved_tie_destination')

    def test_grace_unknown_pitch_and_original_voice_identity(self):
        s=score([event(0,0,[None],grace='BeforeBeat'),event(0,1,[60,64])])
        s['tracks'][0]['measures'][0]['voices']+=[[],[event(0,2,[48])]]
        g=build_sounding(s);a=audit_sounding(s,g)
        self.assertEqual(a['written_occurrences'],4);self.assertTrue(any(n['voice']==2 for n in g['sustains'].values()))


if __name__=='__main__':unittest.main()
