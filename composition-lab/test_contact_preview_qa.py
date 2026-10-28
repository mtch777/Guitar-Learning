import json,tempfile,unittest
from pathlib import Path
from test_inner_voicing import fixture
from run_contact_preview_qa import run,sha


class PreviewQATests(unittest.TestCase):
    def test_actual_stripped_workers_and_independent_source_audit(self):
        docs,_,_=fixture()
        # Remove the unrelated whole-shape witness. The musical source
        # component remains, and the old policy must still refuse it.
        for note,fret in zip(docs['track-0.json']['measures'][4]['voices'][0]['beats'][2]['notes'],[8,10,9,7]):note['fret']=fret
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);capture=root/'capture';capture.mkdir()
            for name,value in docs.items():(capture/name).write_text(json.dumps(value))
            code=Path(__file__).with_name('inner_voicing.py')
            freeze=root/'freeze.json';freeze.write_text(json.dumps({'code_hashes':{str(code):sha(code)}}))
            result=run(capture,root/'qa',freeze)
            self.assertEqual(result['status'],'PASS_PROVISIONAL_CONTACT_PREVIEW_QA',result)
            self.assertTrue(result['changed_demonstration'])
            self.assertEqual(result['counts']['legacy_changed_layouts'],0)
            self.assertEqual(result['human_playability'],'UNVERIFIED')
            self.assertEqual(result['creative_gateway'],'NOT_PASSED')
            demo=json.loads((root/'qa/demonstration.json').read_text())
            self.assertEqual(demo['actual_worker_audit']['status'],'PASS_PROVISIONAL_INNER_CONTACTS')


if __name__=='__main__':unittest.main()
