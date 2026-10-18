import copy
import unittest
from generation_freedom import mix,validate,DIMENSIONS


def score(pitch=40,durations=('1','1'),meter='2/4'):
    from fractions import Fraction as F
    events=[];q=F(0)
    for d in durations:
        events.append(dict(onset_q=str(q),local_onset_q=str(q),duration_q=d,
            notes=[dict(midi=pitch,string=0,fret=pitch-40,tie=None,technique_tags=[])]));q+=F(d)
    return dict(tracks=[dict(index=0,name='melody',program=25,tunings=[[40]],measures=[dict(number=1,onset_q='0',time_signature=meter,voices=[events])])])


class FreedomTests(unittest.TestCase):
    def test_zero_is_literal_identity_without_reading_proposal(self):
        reference=score();snapshot=copy.deepcopy(reference)
        out,report=mix(reference,None,{},['melody'])
        self.assertEqual(out,reference);self.assertEqual(reference,snapshot)

    def test_100_allows_coincidence(self):
        reference=score();out,_=mix(reference,score(),{'melody':100},['melody'])
        self.assertEqual(out,reference)

    def test_100_does_not_read_reference_pitch_values(self):
        proposal=score(47)
        a,_=mix(score(40),proposal,{'melody':100},['melody'])
        b,_=mix(score(44),proposal,{'melody':100},['melody'])
        self.assertEqual(a,b)

    def test_rhythm_variation_preserves_pitches_and_expression(self):
        reference=score();proposal=score(47,('1/2','3/2'))
        out,report=mix(reference,proposal,{'rhythm':100},['melody'])
        self.assertEqual([e['duration_q'] for e in out['tracks'][0]['measures'][0]['voices'][0]],['1/2','3/2'])
        self.assertTrue(all(e['notes'][0]['midi']==40 for e in out['tracks'][0]['measures'][0]['voices'][0]))
        self.assertEqual(report['units']['rhythm']['released'],1)

    def test_incompatible_topology_rejects_instead_of_discarding_notes(self):
        with self.assertRaises(ValueError):mix(score(),score(47,('2',)),{'rhythm':100},['melody'])

    def test_arbitrary_meter_and_global_timing(self):
        self.assertTrue(validate(score(durations=('1','3/2'),meter='5/8')))
        broken=score();broken['tracks'][0]['measures'][0]['voices'][0][1]['onset_q']='99'
        with self.assertRaises(ValueError):validate(broken)

    def test_bad_strengths_and_unknown_dimensions_fail_closed(self):
        for value in (True,False,float('nan'),.5,-1,101):
            with self.assertRaises(ValueError):mix(score(),score(),{'melody':value},['melody'])
        with self.assertRaises(ValueError):mix(score(),score(),{'made_up':100},['melody'])

    def test_all_freedom_can_regenerate_form(self):
        proposal=score(47,('1','3/2'),meter='5/8')
        out,_=mix(score(),proposal,{d:100 for d in DIMENSIONS},['melody'])
        self.assertEqual(out,proposal)

    def test_invalid_midi_tuning_program_and_unsupported_performance_reject(self):
        cases=[]
        invalid=score();invalid['tracks'][0]['tunings']=[[200]];invalid['tracks'][0]['measures'][0]['voices'][0][0]['notes'][0]['midi']=200;cases.append(invalid)
        invalid=score();invalid['tracks'][0]['program']=128;cases.append(invalid)
        invalid=score();invalid['tracks'][0]['tunings']=[[True]];cases.append(invalid)
        for field,value in [('tie',True),('technique_tags',['invented'])]:
            invalid=score();invalid['tracks'][0]['measures'][0]['voices'][0][0]['notes'][0][field]=value;cases.append(invalid)
        for invalid in cases:
            with self.assertRaises(ValueError):validate(invalid)


if __name__=='__main__':unittest.main()
