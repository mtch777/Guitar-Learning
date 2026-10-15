import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch
from benchmarks import analysisgnn_preflight as runner


class PreflightTests(unittest.TestCase):
    def run_fake(self, emit_csv):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'input.musicxml'; source.write_text('<score-partwise/>')
            out=Path(tmp)/'results'
            def process(command, **kwargs):
                if emit_csv:
                    target=Path(command[command.index('--output_dir')+1])/'predictions.csv'
                    columns=runner.TASKS.split(',')
                    target.write_text(','.join(columns)+'\n'+','.join('0' for _ in columns)+'\n')
                return CompletedProcess(command,0,'','')
            with patch.object(runner,'probe_dependency',return_value=dict(importable=True,error=None)), \
                 patch.object(runner.subprocess,'run',side_effect=process), \
                 patch('sys.argv',['preflight',str(source),'--run','--out',str(out)]), \
                 contextlib.redirect_stdout(io.StringIO()):
                if emit_csv: runner.main()
                else:
                    with self.assertRaises(SystemExit) as caught: runner.main()
                    self.assertEqual(caught.exception.code,2)
            return json.loads((out/'manifest.json').read_text())

    def test_success_exit_without_predictions_is_failure(self):
        report=self.run_fake(False)
        self.assertEqual(report['scores'][0]['status'],'failed')
        self.assertFalse(report['accuracy_evaluated'])

    def test_output_provenance_is_collected_without_accuracy_claim(self):
        report=self.run_fake(True); record=report['scores'][0]
        self.assertEqual(record['status'],'predictions_produced')
        self.assertEqual(record['predictions'][0]['rows'],1)
        self.assertIn('--output_dir',record['command'])
        self.assertFalse(report['accuracy_evaluated'])


if __name__=='__main__': unittest.main()
