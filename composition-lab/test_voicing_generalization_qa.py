"""Nonzero absence never bypasses the exact inverse or independent source audit."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_voicing_register import documents
from source_fact_tier1 import extract_documents
from run_voicing_generalization_qa import run,save_capture


class GeneralizationRunnerTests(unittest.TestCase):
    def test_no_alternative_still_runs_actual_stripped_worker(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'local-artifacts';root.mkdir();capture=root/'capture'
            docs=documents();docs['track-0.json']['measures']=docs['track-0.json']['measures'][:1]
            save_capture(extract_documents(docs),capture)
            freeze=root/'freeze.json';freeze.write_text(json.dumps(dict(code_hashes={})),encoding='utf-8')
            result=run(capture,root/'qa',freeze)
            self.assertEqual(result['status'],'PASS_BOUNDED_PORTABILITY_AND_REVERSAL',result)
            self.assertEqual(result['qa2']['zero']['status'],'PASS')
            self.assertEqual(result['nonzero_acceptance'],'OPEN_NO_SUPPORTED_CHANGED_DRAW')
            self.assertIsNone(result['qa2']['changed'])
            self.assertEqual(result['qa3']['independent_denominator_check']['status'],'PASS_INDEPENDENT_POLICY')

    def test_frozen_logic_change_rejected_before_analysis(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'local-artifacts';root.mkdir();source=root/'code.py';source.write_text('changed')
            freeze=root/'freeze.json';freeze.write_text(json.dumps(dict(code_hashes={str(source):'wrong'})))
            with self.assertRaisesRegex(ValueError,'Frozen logic changed'):run(root/'capture',root/'qa',freeze)
            self.assertFalse((root/'qa').exists())


if __name__=='__main__':unittest.main()
