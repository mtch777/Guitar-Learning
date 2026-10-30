"""Exercise the actual complete-source isolated QA runner on authored fixtures."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from test_palm_mute_opportunity_census import documents
from run_palm_mute_qa import run


class PalmRunnerTests(unittest.TestCase):
    def capture(self,folder,docs):
        path=Path(folder)/'capture';path.mkdir()
        for name,value in docs.items():(path/name).write_text(json.dumps(value),encoding='utf-8')
        return path

    def test_actual_zero_half_and_changed_workers(self):
        with TemporaryDirectory()as folder:
            output=Path(folder)/'qa';result=run(self.capture(folder,documents()),output)
            self.assertEqual(result['status'],'PASS_SOURCE_PALM_MUTE_CHANGE',result)
            self.assertEqual(result['rates']['0']['changed'],0)
            self.assertEqual(result['rates']['100']['draws'],result['rates']['100']['released'])
            self.assertTrue(result['rates']['100']['mute_changed'])
            self.assertEqual({r['case']for r in result['workers']},{'zero','half-isolated','changed-isolated'})
            demo=json.loads((output/'demonstration.json').read_bytes())
            self.assertTrue(demo['chosen']['mute_changed'])
            self.assertEqual(demo['independent_source_check']['status'],'PASS_INDEPENDENT_PALM_MUTE_SOURCE_SCOPE')
            self.assertEqual(result['native_gp_midi_audio'],'PENDING')
            self.assertEqual(len((output/'draws.jsonl').read_text().splitlines()),result['counts']['coattacks'])

    def test_empty_choice_space_is_retained_not_replaced(self):
        docs=documents()
        for measure in docs['track-0.json']['measures']:
            for beat in measure['voices'][0]['beats']:beat.pop('palmMute',None)
        with TemporaryDirectory()as folder:
            output=Path(folder)/'qa';result=run(self.capture(folder,docs),output)
            self.assertEqual(result['status'],'PASS_SOURCE_PALM_MUTE_NO_CHOICE',result)
            self.assertEqual(result['counts']['with_on_off_choices'],0)
            self.assertEqual({r['case']for r in result['workers']},{'zero','no-choice'})
            self.assertFalse((output/'demonstration.json').exists())
            self.assertEqual(result['full_palm_mute_lever'],'OPEN')

    def test_invalid_frozen_protocol_is_retained_before_analysis(self):
        with TemporaryDirectory()as folder:
            source=self.capture(folder,documents());freeze=Path(folder)/'freeze.json'
            freeze.write_text(json.dumps(dict(code_hashes={},policy='wrong')),encoding='utf-8')
            output=Path(folder)/'qa';result=run(source,output,freeze)
            self.assertEqual(result['status'],'FAIL_RETAINED')
            self.assertEqual(result,json.loads((output/'result.json').read_bytes()))
            self.assertFalse((output/'stripped-tier2.json').exists())


if __name__=='__main__':unittest.main()
