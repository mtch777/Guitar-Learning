import unittest
from copy import deepcopy
from conditional_harmony_pilot import draw,redact,propose,PilotFitError


class PilotTests(unittest.TestCase):
    def fixture(self):
        note=dict(midi=32,string=0,fret=0,tie=None,technique_tags=[])
        events=[dict(local_onset_q=str(i),onset_q=str(i),duration_q='1',notes=[deepcopy(note)]) for i in range(2)]
        score=dict(tracks=[dict(tunings=[[32]],measures=[dict(onset_q='0',voices=[events])])])
        records=[dict(bar=1,local_q=str(i),voicing_intervals=[0],uniform=u,step_order=[0],step_weights=[1]) for i,u in enumerate((.1,.99))]
        model=dict(global_probs=[.5 if s in (0,127) else 0 for s in range(-127,128)],contexts={})
        # Production distribution requires positive mass everywhere.
        model['global_probs']=[p*.999999+1e-6/255 for p in model['global_probs']]
        return score,records,model

    def test_null_and_reference_redaction(self):
        score,records,model=self.fixture();out,audit=propose(redact(score),[[0,0]],records,32,model,historical_null=True)
        self.assertEqual(out,score);self.assertEqual(len(audit),2)
        other=deepcopy(score)
        for e in other['tracks'][0]['measures'][0]['voices'][0]:e['notes'][0].update(midi=45,fret=13)
        self.assertEqual(redact(score),redact(other))
        with self.assertRaisesRegex(ValueError,'removed'):propose(score,[[0,0]],records,32,model)

    def test_failure_preserves_exact_draw_and_partial_history(self):
        score,records,model=self.fixture();original=deepcopy(score)
        with self.assertRaises(PilotFitError) as caught:propose(redact(score),[[0,0]],records,32,model)
        failure=caught.exception
        self.assertEqual(failure.failure['sampled_step'],127)
        self.assertEqual(failure.failure['target_before_fit'],159)
        self.assertEqual(len(failure.decisions),1)
        self.assertEqual(failure.failure['previous_id'],(0,'0'))
        self.assertEqual(failure.failure['shifts_attempted'],[0,-1,1,-2,2,-3,3,-4,4,-5,5])
        self.assertEqual(score,original)

    def test_draw_boundaries_and_invalid_mass(self):
        self.assertEqual(draw([5,7],[1,1],0),5)
        self.assertEqual(draw([5,7],[1,1],.5),7)
        self.assertEqual(draw([5,7],[1,1],.999999),7)
        for weights in ([0,0],[-1,2],[float('nan'),1]):
            with self.assertRaises(ValueError):draw([5,7],weights,.5)

    def test_recurrence_copies_candidate_and_updates_history(self):
        score,records,model=self.fixture();score['tracks'][0]['measures'].append(deepcopy(score['tracks'][0]['measures'][0]))
        score['tracks'][0]['measures'][1]['onset_q']='2'
        for e in score['tracks'][0]['measures'][1]['voices'][0]:e['onset_q']=str(2+int(e['local_onset_q']))
        out,audit=propose(redact(score),[[0,0],[0,0]],records,32,model,historical_null=True)
        self.assertEqual(out,score);self.assertEqual(len(audit),2)


if __name__=='__main__':unittest.main()
