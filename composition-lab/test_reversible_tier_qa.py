"""Independent extraction and audited stripped-input inverse gates."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from run_reversible_tier_qa import run,extract
from check_reversible_source import check
from test_tiered_song import fixture


class ContinuousTierQATests(unittest.TestCase):
    def test_source_checked_isolated_roundtrip_and_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);capture=root/"capture";capture.mkdir();fixture(capture)
            report=run(capture,root/"qa")
            self.assertEqual(report["status"],"pass_declared_scope")
            self.assertEqual(report["independent_raw_source_check"]["status"],"pass_declared_raw_source_fields")
            trace=json.loads((root/"qa/isolated/read-audit.json").read_text())
            self.assertTrue(trace["open_events"])
            self.assertFalse(any(str(capture.resolve()) in event["path"] for event in trace["open_events"]))
            events=json.loads((root/"qa/isolated/reconstructed.json").read_text())["events"]
            events[0]["onset_q"]="999"
            self.assertEqual(check(capture,events)["status"],"fail")

    def test_topology_stripped_worker_and_independent_corruption_check(self):
        from test_reversible_topology import capture as topology_capture
        from check_reversible_source import check_topology
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);capture=root/"capture";capture.mkdir();topology_capture(capture)
            report=run(capture,root/"qa",topology=True)
            self.assertEqual(report["status"],"pass_declared_scope")
            self.assertEqual(report["independent_topology_check"]["status"],"pass_declared_topology")
            output=json.loads((root/"qa/isolated/reconstructed.json").read_text())
            trace=json.loads((root/"qa/isolated/read-audit.json").read_text())
            self.assertFalse(any(str(capture.resolve()) in event["path"] for event in trace["open_events"]))
            output["topology"]["beats"][0]["written_duration_q"]="77"
            self.assertEqual(check_topology(capture,output["topology"])["status"],"fail")

    def test_positions_stripped_worker_and_independent_field_check(self):
        from test_reversible_topology import capture as topology_capture
        from check_reversible_source import check_positions
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);capture=root/"capture";capture.mkdir();topology_capture(capture)
            report=run(capture,root/"qa",positions=True)
            self.assertEqual(report["status"],"pass_declared_scope")
            self.assertEqual(report["independent_position_check"]["status"],"pass_declared_physical_fields")
            upper=json.loads((root/"qa/isolated/tier2-only.json").read_text())
            self.assertNotIn("pitch_patterns",upper["topology"])
            output=json.loads((root/"qa/isolated/reconstructed.json").read_text())
            output["physical"]["positions"][0]["string"]["value"]="99"
            self.assertEqual(check_positions(capture,output["physical"])["status"],"fail")

    def test_guard_rejects_lower_file_read_and_arbitrary_write(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/"tier1.json";target.write_text('{"source":"must not read"}')
            code="from reverse_tier_worker import install_guard\nfrom pathlib import Path\nimport sys\naccess=[]\ninstall_guard({},Path(sys.base_prefix).resolve(),access)\ntry:\n open(sys.argv[1],sys.argv[2])\nexcept PermissionError:\n print(access[-1]['allowed'])\nelse:\n raise AssertionError('lower/source read or unauthorized write was allowed')"
            for mode in ("r","w"):
                result=subprocess.run([sys.executable,"-c",code,str(target),mode],cwd=Path(__file__).parent,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn("False",result.stdout)
            self.assertEqual(json.loads(target.read_text()),{"source":"must not read"})


if __name__=="__main__":unittest.main()
