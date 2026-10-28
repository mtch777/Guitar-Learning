import json
from pathlib import Path
import tempfile
import unittest
from test_inner_voicing import fixture
from run_harmonic_evidence_qa import run,sha


class CompleteCommonGateTests(unittest.TestCase):
    def test_full_raw_source_and_isolated_relation_gate(self):
        docs,_,_=fixture();root=Path(__file__).parent
        with tempfile.TemporaryDirectory()as tmp:
            out=Path(tmp);capture=out/'capture';capture.mkdir()
            for name,value in docs.items():(capture/name).write_text(json.dumps(value),encoding='utf-8')
            freeze=out/'freeze.json';freeze.write_text(json.dumps(dict(code_hashes={str(p):sha(p)for p in root.glob('*.py')})))
            result=run(capture,out/'qa',freeze)
            self.assertEqual(result['status'],'PASS_BOUNDED_COMMON_HARMONY_QA',result)
            self.assertEqual(result['qa2']['whole_source'],'PASS');self.assertEqual(result['qa2']['common_relationships'],'PASS')


if __name__=='__main__':unittest.main()
