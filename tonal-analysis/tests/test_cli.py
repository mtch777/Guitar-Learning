"""CLI behavior against synthetic captures; no private music or network needed."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_songsterr import beat, documents, measure, note, part


SCRIPT = Path(__file__).resolve().parents[1] / "analyze.py"


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def capture(self, path=None):
        path = path or self.root / "capture"
        path.mkdir(parents=True)
        source = documents(part(
            measure(beat(note(20), note(19, string=1), note(17, string=2)), signature=(1, 4)),
            measure(beat(note(15), note(14, string=1), note(12, string=2)), signature=None),
            measure(beat(note(20), note(19, string=1), note(17, string=2)), signature=None),
        ))
        for filename, content in source.items():
            (path / filename).write_text(json.dumps(content), encoding="utf-8")
        return path

    def run_cli(self, *arguments):
        # An unrelated working directory verifies that the launcher locates its
        # package without relying on PYTHONPATH or the repository's current cwd.
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, arguments)],
                              cwd=self.root, capture_output=True, text=True,
                              encoding="utf-8", timeout=60)

    def assert_exit(self, result, code):
        self.assertEqual(result.returncode, code, msg=f"stdout={result.stdout}\nstderr={result.stderr}")

    @staticmethod
    def snapshot(path):
        return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}

    def read_object(self, path):
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def test_examples_create_parseable_reports_events_and_manifests(self):
        output = self.root / "public-examples"
        result = self.run_cli("examples", "--output", output, "--window-bars", "2", "--top", "3")
        self.assert_exit(result, 0)
        reports = list(output.glob("*/report.json"))
        self.assertGreater(len(reports), 0)
        for report in reports:
            self.read_object(report)
            events = self.read_object(report.with_name("events.json"))
            self.assertEqual(events["schema"], "tonal-events/1")
            self.read_object(report.with_name("manifest.json"))

    def test_analyze_writes_three_artifacts_and_leaves_capture_unchanged(self):
        capture = self.capture()
        original = self.snapshot(capture)
        output = self.root / ".local" / "analysis"
        result = self.run_cli("analyze", capture, "--output", output, "--window-bars", "2", "--top", "3")
        self.assert_exit(result, 0)
        self.read_object(output / "report.json")
        self.read_object(output / "manifest.json")
        events = self.read_object(output / "events.json")
        self.assertEqual(events["schema"], "tonal-events/1")
        self.assertEqual(events["coverage"]["source_nonrest_notes"], 9)
        self.assertEqual(len(events["events"]), 9)
        self.assertEqual(self.snapshot(capture), original)

    def test_check_capture_writes_verification_and_manifest_without_source_changes(self):
        capture = self.capture()
        original = self.snapshot(capture)
        output = self.root / "local-artifacts" / "verification"
        result = self.run_cli("check-capture", capture, "--output", output)
        self.assert_exit(result, 0)
        self.read_object(output / "verification.json")
        self.read_object(output / "manifest.json")
        self.assertEqual(self.snapshot(capture), original)

    def test_private_path_recognition_is_case_insensitive(self):
        capture = self.capture()
        result = self.run_cli("analyze", capture, "--output", self.root / ".LoCaL" / "analysis")
        self.assert_exit(result, 0)
        self.assertTrue((self.root / ".LoCaL" / "analysis" / "report.json").is_file())

    def test_source_derived_outputs_require_a_private_ancestor_component(self):
        capture = self.capture()
        for command in ("analyze", "check-capture"):
            for parent in ("public", "not.local", "local-artifacts-public"):
                with self.subTest(command=command, parent=parent):
                    output = self.root / parent / command
                    self.assert_exit(self.run_cli(command, capture, "--output", output), 2)
                    self.assertFalse(output.exists())

    def test_no_command_overwrites_an_existing_output_directory(self):
        capture = self.capture()
        for command in ("analyze", "check-capture", "examples"):
            with self.subTest(command=command):
                output = self.root / ".local" / command
                output.mkdir(parents=True)
                (output / "existing.bin").write_bytes(b"retain this result\x00")
                before = self.snapshot(output)
                args = [command] + ([] if command == "examples" else [capture])
                self.assert_exit(self.run_cli(*args, "--output", output), 2)
                self.assertEqual(self.snapshot(output), before)

    def test_analysis_and_verification_cannot_write_inside_the_capture(self):
        capture = self.capture(self.root / ".local" / "capture")
        before = self.snapshot(capture)
        for command in ("analyze", "check-capture"):
            with self.subTest(command=command):
                output = capture / command
                self.assert_exit(self.run_cli(command, capture, "--output", output), 2)
                self.assertFalse(output.exists())
                self.assertEqual(self.snapshot(capture), before)

    def test_missing_input_and_invalid_json_return_argument_error_status(self):
        output = self.root / ".local" / "missing"
        self.assert_exit(self.run_cli("analyze", self.root / "absent", "--output", output), 2)
        capture = self.capture()
        (capture / "metadata.json").write_text("{broken JSON", encoding="utf-8")
        before = self.snapshot(capture)
        self.assert_exit(self.run_cli("check-capture", capture, "--output", self.root / ".local" / "invalid"), 2)
        self.assertEqual(self.snapshot(capture), before)

    def test_invalid_numeric_options_and_missing_required_arguments_return_two(self):
        for option in ("--window-bars", "--top"):
            for value in ("0", "-1", "not-an-integer"):
                with self.subTest(option=option, value=value):
                    output = self.root / f"invalid-{option.strip('-')}-{value}"
                    self.assert_exit(self.run_cli("examples", "--output", output, option, value), 2)
                    self.assertFalse(output.exists())
        for args in ([], ["examples"], ["analyze"], ["check-capture"]):
            with self.subTest(args=args):
                self.assert_exit(self.run_cli(*args), 2)


if __name__ == "__main__":
    unittest.main()
