import json,tempfile,unittest
from pathlib import Path
import test_compose_controlled
from run_controlled_batch import batch
from unittest.mock import patch


class ControlledBatchTests(unittest.TestCase):
    def test_input_mutation_between_strengths_is_not_a_completed_comparison(self):
        for field in ('source_sha256','source_expected_sha256','form_plan_sha256'):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);src=root/'inputs';src.mkdir();(src/'base.gp').write_bytes(b'fixture')
                first=dict(source_sha256='before',source_expected_sha256='canonical',form_plan_sha256='plan',code_sha256={'code':'fixed'},
                    model_sha256={},output_sha256='output',all_zero_byte_identity=True)
                second=dict(first,**{field:'after'})
                with patch('run_controlled_batch.run',side_effect=[first,second]):
                    result=batch(src,{},root/'out',[0,100])
                self.assertFalse(result['complete']);self.assertEqual(len(result['outputs']),1)
                self.assertIn('Input changed',result['failures'][0]['reason'])

    def test_failure_is_recorded_and_independent_zero_case_completes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'inputs';src.mkdir()
            (src/'a-bad.gp').write_bytes(b'not a GP')
            test_compose_controlled.ControlledPipelineTests().core(src/'b-good.gp')
            result=batch(src,{},root/'out',[0])
            self.assertFalse(result['complete']);self.assertEqual(len(result['failures']),1)
            self.assertEqual(len(result['outputs']),1);self.assertTrue(result['outputs'][0]['zero_identity'])
            self.assertEqual(json.loads((root/'out/batch.json').read_text()),result)

    def test_invalid_batch_controls_fail_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for config,strengths in [({'dimensions':['form']},[0]),({},[True]),({},[0,0]),({'controls':{}},[0])]:
                with self.assertRaises(ValueError):batch(root,config,root/'out',strengths)
                self.assertFalse((root/'out').exists())


if __name__=='__main__':unittest.main()
