from pathlib import Path
import json,tempfile,unittest,wave
from test_joint_gp_artifacts import JointGPArtifactTests,score
from check_voicing_artifacts import check,written_pitch


class InnerGPAuditTests(unittest.TestCase):
    def exercise(self,*,wrong_spelling=False,allow=True,corruption=None):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            xml=score(5,3,midi=67).replace('<Step>E</Step>','<Step>F</Step>' if wrong_spelling else '<Step>G</Step>')
            if corruption=='accidental':xml=xml.replace('<Accidental></Accidental>','<Accidental>#</Accidental>')
            if corruption=='midi':xml=xml.replace('<Number>67</Number>','<Number>68</Number>')
            if corruption=='articulation':xml=xml.replace('<InstrumentArticulation>0</InstrumentArticulation>','<InstrumentArticulation>1</InstrumentArticulation>')
            qa=JointGPArtifactTests().fixture(root,xml)
            p=qa/'changed-capture/track-0.json';doc=json.loads(p.read_text());doc['measures'][0]['voices'][0]['beats'][0]['notes'][0]={'string':0,'fret':3};p.write_text(json.dumps(doc))
            for mode in ('focused','ensemble'):
                with wave.open(str(root/'changed'/(mode+'.wav')),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\1\0'*80)
            return check(root,qa,allow_inner_degree_changes=allow)

    def test_exact_dependent_spelling_change(self):
        result=self.exercise()
        self.assertEqual(result['status'],'PASS_NATIVE_GP_AND_AUDIO_CHANGE',result)
        self.assertEqual(result['human_playability'],'UNVERIFIED')

    def test_wrong_spelling_fails_even_if_midi_right(self):
        self.assertEqual(self.exercise(wrong_spelling=True)['status'],'FAIL')

    def test_old_register_only_audit_still_refuses_degree_change(self):
        self.assertEqual(self.exercise(allow=False)['status'],'FAIL')

    def test_accidental_midi_and_unrelated_note_field_cannot_change(self):
        for kind in ('accidental','midi','articulation'):
            self.assertEqual(self.exercise(corruption=kind)['status'],'FAIL',kind)


if __name__=='__main__':unittest.main()
