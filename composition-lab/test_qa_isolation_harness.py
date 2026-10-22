"""Guard mechanics only; synthetic rational relation is NOT a musical tier."""
import json
from pathlib import Path
import tempfile
import unittest

from qa_isolation_harness import execute, strict_json

CODE = '''from fractions import Fraction as F
def reconstruct(upper, controls):
    return {upper["id"]: str(F(upper["anchor"]) + F(upper["offset"]))}
'''


class IsolationHarnessTests(unittest.TestCase):
    def test_actual_execution_changed_input_arbitrary_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for i, (ident, anchor, offset, answer) in enumerate((
                    ("a", "1/3", "2/3", "1"), ("renamed", "5/4", "-1/2", "3/4"))):
                report = execute(CODE, dict(id=ident, anchor=anchor, offset=offset), {"change": 0},
                                 {ident: answer}, root / str(i))
                self.assertEqual(report["status"], "PASS", report)
                self.assertFalse((root / str(i) / "worker/expected.json").exists())
                frozen = json.loads((root / str(i) / "freeze.json").read_text())
                self.assertEqual(set(frozen), {"worker.py", "relationships.py", "input.json"})

    def test_actual_denial_challenges(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            secret = root / "forbidden.py"; secret.write_text("hidden = 123")
            for kind in ("open", "os_open", "write", "network", "process", "system", "repo_import",
                         "remove", "rename", "listdir", "chdir"):
                report = execute(CODE, {}, {"change": 0}, None, root / kind, challenge=kind, forbidden=secret)
                self.assertEqual(report["status"], "PASS", report)
                audit = json.loads((root / kind / "worker/audit.json").read_text())
                self.assertEqual(audit["attempted_challenge"], kind)
                self.assertTrue(any(e["denied"] for e in audit["events"]))
            self.assertEqual(secret.read_text(), "hidden = 123")

    def test_caught_forbidden_read_cannot_use_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); secret = root / "source.json"; secret.write_text("123")
            code = f'''def reconstruct(upper, controls):
    try:
        open({str(secret)!r}).read()
    except PermissionError:
        return {{"cached": 123}}
'''
            report = execute(code, {}, {"change": 0}, {"cached": 123}, root / "qa")
            self.assertEqual(report["status"], "FAIL")

    def test_caught_delete_cannot_pass_or_remove_sentinel(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); sentinel = root / "sentinel"; sentinel.write_text("preserve")
            code = f'''import os
def reconstruct(upper, controls):
    try:
        os.remove({str(sentinel)!r})
    except PermissionError:
        return {{}}
'''
            self.assertEqual(execute(code, {}, {"change": 0}, {}, root / "qa")["status"], "FAIL")
            self.assertEqual(sentinel.read_text(), "preserve")

    def test_wrong_types_cached_answer_and_stdout_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cases = [("def reconstruct(u,c): return {'x':False}", {"x": 0}),
                     ("def reconstruct(u,c): return {'x':1}", {"x": 2}),
                     ("def reconstruct(u,c):\n print('extra'); return {}", {})]
            for i, (code, expected) in enumerate(cases):
                self.assertEqual(execute(code, {}, {"change": 0}, expected, root / str(i))["status"], "FAIL")

    def test_nonzero_controls_crash_timeout_and_stale_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = execute(CODE, {}, {"change": 50}, {}, root / "nonzero")
            self.assertEqual(report["status"], "FAIL")
            report = execute("def reconstruct(u,c): raise ValueError('broken')", {}, {"change": 0}, {}, root / "crash")
            self.assertEqual(report["status"], "FAIL")
            report = execute("def reconstruct(u,c):\n while True: pass", {}, {"change": 0}, {}, root / "timeout", timeout=0.2)
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue((root / "timeout/result.json").is_file())
            with self.assertRaises(ValueError):
                execute(CODE, {}, {"change": 0}, {}, root / "crash")

    def test_strict_json(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', '{"x":-1e999}', 'notjson'):
            with self.assertRaises(ValueError):
                strict_json(text)

    def test_invalid_input_preparation_retains_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = execute(CODE, {"x": float("nan")}, {"change": 0}, {}, root / "qa")
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue((root / "qa/result.json").is_file())


if __name__ == "__main__":
    unittest.main()
