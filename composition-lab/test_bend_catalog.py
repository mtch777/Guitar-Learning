import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
from catalog_csv_corpus import copy_score_pair


class BendCatalogTests(unittest.TestCase):
    def fixture(self,root):
        source=root/'score.gp';source.write_bytes(b'synthetic score')
        companion=source.with_suffix('.exact-model-bends.json')
        companion.write_text(json.dumps(dict(schema='composition-lab.exact-model-bends.v1',gp_sha256=hashlib.sha256(source.read_bytes()).hexdigest())))
        return source,companion,root/'Renamed.gp'

    def test_renamed_catalog_pair_and_safe_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,companion,target=self.fixture(Path(tmp))
            result=copy_score_pair(source,target)
            self.assertEqual(result.name,'Renamed.exact-model-bends.json')
            self.assertEqual(result.read_bytes(),companion.read_bytes())
            self.assertEqual(target.read_bytes(),source.read_bytes())
            self.assertEqual(copy_score_pair(source,target),result)

    def test_bad_source_companion_does_not_copy_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,companion,target=self.fixture(Path(tmp));source.write_bytes(b'changed')
            with self.assertRaises(ValueError):copy_score_pair(source,target)
            self.assertFalse(target.exists())

    def test_conflicting_catalog_companion_preserves_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,companion,target=self.fixture(Path(tmp))
            result=copy_score_pair(source,target);result.write_text('existing different companion')
            with self.assertRaises(FileExistsError):copy_score_pair(source,target)
            self.assertEqual(target.read_bytes(),source.read_bytes())
            self.assertEqual(result.read_text(),'existing different companion')


if __name__=='__main__':unittest.main()
