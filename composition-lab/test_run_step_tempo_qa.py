"""Actual source-denied runner, including honest no-choice outcomes."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from test_tempo_source_census import tempo_documents
from run_step_tempo_qa import run


class TempoRunnerTests(unittest.TestCase):
    def capture(self,folder,docs):
        path=Path(folder)/'capture';path.mkdir()
        for name,value in docs.items():(path/name).write_text(json.dumps(value),encoding='utf-8')
        return path

    def test_actual_zero_half_changed_workers_keep_partial_claim(self):
        with TemporaryDirectory()as folder:
            output=Path(folder)/'qa';result=run(self.capture(folder,tempo_documents()),output)
            self.assertEqual(result['status'],'PASS_PARTIAL_SOURCE_COMPONENT_TEMPO_CHANGE',result)
            self.assertEqual(result['rates']['0']['changed'],0)
            self.assertEqual(result['rates']['100']['draws'],result['rates']['100']['released'])
            self.assertTrue(result['rates']['100']['changed'])
            self.assertTrue({'zero','half-isolated','changed-isolated'}.issubset({r['case']for r in result['workers']}))
            demo=json.loads((output/'demonstration.json').read_bytes());self.assertEqual(demo['evidence_label'],'PARTIAL')
            self.assertEqual(demo['target']['full_influence_musical_suitability'],'NOT_ESTABLISHED_BY_ENTRY_BAR')
            self.assertNotEqual(demo['chosen']['quarter_bpm'],demo['target']['quarter_bpm'])
            self.assertEqual(result['native_gp_midi_audio'],'PENDING');self.assertEqual(result['human_fit'],'NOT_ESTABLISHED')
            self.assertEqual(len((output/'draws.jsonl').read_text().splitlines()),result['counts']['components'])

    def test_no_choices_remain_visible_without_target_or_source_replacement(self):
        docs=tempo_documents()
        for event in docs['track-0.json']['automations']['tempo']:event['bpm']=120
        with TemporaryDirectory()as folder:
            output=Path(folder)/'qa';result=run(self.capture(folder,docs),output)
            self.assertEqual(result['status'],'PASS_SOURCE_TEMPO_NO_CHOICE',result)
            self.assertEqual(result['counts']['with_choices'],0);self.assertEqual(result['rates']['100']['changed'],0)
            self.assertEqual({r['case']for r in result['workers']},{'zero','no-choice'})
            self.assertFalse((output/'demonstration.json').exists());self.assertEqual(result['full_tempo_lever'],'OPEN')

    def test_wrong_frozen_protocol_is_retained_before_analysis(self):
        with TemporaryDirectory()as folder:
            capture=self.capture(folder,tempo_documents());freeze=Path(folder)/'freeze.json';freeze.write_text(json.dumps(dict(code_hashes={},policy='wrong')))
            output=Path(folder)/'qa';result=run(capture,output,freeze)
            self.assertEqual(result['status'],'FAIL_RETAINED');self.assertEqual(result,json.loads((output/'result.json').read_bytes()))
            self.assertFalse((output/'stripped-tier2.json').exists())


if __name__=='__main__':unittest.main()
