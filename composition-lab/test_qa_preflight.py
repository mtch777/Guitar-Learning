"""Cheap runner failures must not masquerade as failed musical experiments."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from qa_isolation_harness import execute

CODE = 'def reconstruct(upper, controls):\n    return {"answer": 1}\n'


class QAPreflightTests(unittest.TestCase):
    def test_invalid_prerequisites_never_launch_worker(self):
        cases = [dict(purpose='misspelled_purpose'),
                 dict(expected_runtime={'version': [0, 0, 0]}),
                 dict(expected_operator_sha256='0' * 64),
                 dict(operator_code='def broken('),
                 dict(controls={'change': 50})]
        with tempfile.TemporaryDirectory() as temp:
            for i, case in enumerate(cases):
                args = dict(operator_code=CODE, upper={}, controls={'change': 0},
                            expected={'answer': 1}, output=Path(temp) / str(i))
                args.update(case)
                with patch('qa_isolation_harness.subprocess.run', side_effect=AssertionError('Worker launched')):
                    report = execute(**args)
                self.assertEqual(report['status'], 'FAIL')
                self.assertEqual(report['failure_stage'], 'preflight')
                self.assertFalse(report['reconstruction_started'])
                self.assertFalse((args['output'] / 'worker/output.json').exists())

    def test_utf8_line_endings_are_frozen_as_exact_bytes(self):
        runtime = dict(implementation=sys.implementation.name, version=list(sys.version_info[:3]),
                       executable=str(Path(sys.executable).resolve()))
        with tempfile.TemporaryDirectory() as temp:
            for i, code in enumerate((CODE, CODE.replace('\n', '\r\n'))):
                out = Path(temp) / str(i)
                fingerprint = hashlib.sha256(code.encode('utf-8')).hexdigest()
                report = execute(code, {}, {'change': 0}, {'answer': 1}, out,
                                 expected_runtime=runtime, expected_operator_sha256=fingerprint)
                self.assertEqual(report['status'], 'PASS', report)
                self.assertEqual((out / 'worker/relationships.py').read_bytes(), code.encode('utf-8'))
                self.assertEqual(report['frozen_files']['relationships.py'], fingerprint)

    def test_import_operator_error_and_wrong_answer_have_distinct_phases(self):
        cases = [('import unavailable_module_xyz\n' + CODE, 'module_import'),
                 ('def reconstruct(u,c): raise ValueError("unsupported fixture")', 'reconstruction'),
                 (CODE, 'comparison')]
        with tempfile.TemporaryDirectory() as temp:
            for i, (code, phase) in enumerate(cases):
                report = execute(code, {}, {'change': 0}, {'answer': 2}, Path(temp) / str(i))
                self.assertEqual(report['status'], 'FAIL')
                self.assertEqual(report['failure_stage'], phase, report)


if __name__ == '__main__': unittest.main()
