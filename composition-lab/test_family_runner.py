"""End-to-end QA tooling on an authored contract, never artist evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from test_family_integration import documents


class FamilyRunnerTests(unittest.TestCase):
    def test_frozen_synthetic_full_pipeline_and_independent_gates(self):
        from run_voicing_generalization_qa import run
        root=Path(__file__).parent
        files=list(root.glob('*.py'))+list((root/'songsterr_automation/songsterr_api').glob('*.py'))
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)/'local-artifacts';base.mkdir();capture=base/'capture';capture.mkdir()
            for name,value in documents().items():(capture/name).write_text(json.dumps(value),encoding='utf-8')
            manifest=base/'freeze.json';manifest.write_text(json.dumps(dict(policy='transposed_voicing_family',study_kind='DEVELOPMENT_SYNTHETIC_CONTRACT',code_hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})),encoding='utf-8')
            result=run(capture,base/'qa',manifest)
        self.assertEqual(result['status'],'PASS_BOUNDED_DEVELOPMENT_AND_REVERSAL',result.get('error',result))
        self.assertTrue(result['decision']['changed'])
        self.assertEqual(result['qa2']['locks']['status'],'PASS_LOCKED_DIMENSIONS')
        self.assertEqual(result['qa3']['family_ownership']['pair_worker']['status'],'PASS')
        self.assertEqual(result['control_counts']['0']['changed'],0)
        self.assertEqual(result['control_counts']['50']['draws'],20)
        self.assertEqual(result['control_counts']['100']['draws'],20)


if __name__=='__main__':unittest.main()
