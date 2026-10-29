import hashlib,json,tempfile,unittest
from pathlib import Path
from test_check_unlabeled_inner import unlabeled_fixture
from run_unlabeled_inner_qa import run
try:
    import music21
except ImportError:music21=None

@unittest.skipUnless(music21,'Pinned native oracle unavailable')
class UnlabeledRunnerTests(unittest.TestCase):
    def invoke(self,root,*,max_targets=None):
        capture=root/'capture';capture.mkdir();docs,_=unlabeled_fixture()
        for name,value in docs.items():(capture/name).write_text(json.dumps(value))
        # Authored runner integration smoke, not a real-source QA1 freeze.
        path=Path(__file__).parent/'run_unlabeled_inner_qa.py';freeze=root/'freeze.json'
        freeze.write_text(json.dumps(dict(code_hashes={str(path):hashlib.sha256(path.read_bytes()).hexdigest()},native_hashes={})))
        return run(capture,root/'qa',freeze,max_targets=max_targets)
    def test_actual_fullsource_policyzero_and_changed_workers(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);r=self.invoke(root)
            self.assertEqual(r['status'],'PASS_PROVISIONAL_UNLABELED_INNER_QA',r)
            self.assertTrue(r['changed_demonstration']);self.assertFalse(r['demonstration_has_source_label'])
            self.assertEqual(r['untested_targets'],0)
            self.assertEqual(r['counts']['admitted_changed_layouts'],r['counts']['independently_checked_changed_layouts'])
            demo=json.loads((root/'qa/demonstration.json').read_text())
            self.assertNotIn('roles',demo['target']);self.assertNotIn('roles',demo['chosen'])
            self.assertTrue(demo['target']['conditional_roles_before'])
            self.assertTrue((root/'qa/changed-isolated/worker/output.json').exists())
            self.assertEqual(demo['human_playability'],'UNVERIFIED')
    def test_declared_resource_stop_is_not_a_full_pass(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);r=self.invoke(root,max_targets=1)
            self.assertEqual(r['status'],'INCOMPLETE_RETAINED_RESOURCE_LIMIT',r)
            self.assertEqual(r['tested_targets'],1);self.assertGreater(r['untested_targets'],0)
            self.assertTrue((root/'qa/zero-and-pair/zero-isolated/worker/output.json').exists())
            self.assertEqual(len(json.loads((root/'qa/untested-targets.json').read_text())),r['untested_targets'])

if __name__=='__main__':unittest.main()
