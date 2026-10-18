import unittest
from fractions import Fraction as F
from pedal_evidence import analyze_evidence, finalize
from evaluate_pedal_evidence import verify
from test_pedal_regions import rows


class EvidenceAuditTests(unittest.TestCase):
    def test_remote_register_extremes_cannot_change_local_eligibility(self):
        data=rows([[65],[69],[65],[71],[65],[56]])
        for n in data:n['bar']=2;n['onset_q']=str(F(n['onset_q'])+10)
        extra=rows([[35],[95]])
        for n in extra:n['bar']=1;n['occurrence']='earlier:'+n['occurrence']
        self.assertFalse(analyze_evidence(data)['accepted'])
        result=analyze_evidence(extra+data)
        self.assertFalse(any(result['roles'].get(n['occurrence'])=='call' for n in data))

    def test_final_pruning_cannot_leave_an_isolated_exchange(self):
        data=rows([[40],[55],[40],[32],[58],[32]])
        events=[dict(onset_q=str(i),notes=[n]) for i,n in enumerate(data)]
        roles={n['occurrence']:('response' if n['midi']>40 else 'call') for n in data}
        final,cycles=finalize(events,roles)
        self.assertEqual(final,{})
        self.assertEqual(cycles,[])

    def test_written_chord_stays_chord_when_ties_change_attack_subset(self):
        data=rows([[40,44,47]]*12)
        for n in data:
            if int(n['occurrence'].split(':')[0])%3 != int(n['occurrence'].split(':')[1]):n['tie_destination']=True
        self.assertFalse(analyze_evidence(data)['accepted'])

    def test_uniform_arpeggio_inside_varied_context_is_not_evidence(self):
        data=rows([[30],[31]]+[[40],[44],[47],[44]]*4+[[60],[62]])
        self.assertFalse(analyze_evidence(data)['accepted'])

    def test_occurrence_and_timing_audit(self):
        data=rows([[40],[55],[40],[59],[40]])
        result=analyze_evidence(data)
        self.assertTrue(verify(data,result))
        result['roles']['0:0']='response'
        with self.assertRaises(AssertionError):verify(data,result)

    def test_unknown_pitch_in_local_arpeggio_probe_does_not_crash(self):
        data=rows([[40],[None],[40],[55],[40],[59],[40]])
        data[1]['effects']=['dead']
        self.assertTrue(verify(data,analyze_evidence(data)))


if __name__=='__main__':unittest.main()
