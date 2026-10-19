import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_relationship_profile as runner
from test_artist_relationship_profiles import song, row


class BuildTests(unittest.TestCase):
    def fixtures(self, root):
        report=root/'report.json';pedals=root/'pedals.json'
        report.write_text(json.dumps(dict(songs=[song(1,[row(0,0)]),song(2,[row(0,0)],'held_out')])))
        pedals.write_text('{"tracks":[]}')
        return report,pedals

    def test_private_sealed_products_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report,pedals=self.fixtures(root);out=root/'local-artifacts'/'profile'
            manifest=runner.run(report,pedals,out,'A')
            self.assertTrue(manifest['complete'])
            self.assertFalse(manifest['musical_acceptance'])
            for name,digest in manifest['products'].items():self.assertEqual(runner.sha(out/name),digest)
            with self.assertRaises(ValueError):runner.run(report,pedals,out,'A')
            with self.assertRaises(ValueError):runner.run(report,pedals,root/'public','A')

    def test_code_or_input_mutation_never_marks_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report,pedals=self.fixtures(root);out=root/'local-artifacts'/'profile'
            original=runner.artist_relationship_profiles.build_relationship_profile
            def mutate(*args,**kwargs):
                result=original(*args,**kwargs)
                report.write_text(report.read_text()+' ')
                return result
            with patch.object(runner.artist_relationship_profiles,'build_relationship_profile',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'changed'):runner.run(report,pedals,out,'A')
            self.assertFalse((out/'manifest.json').exists())

    def test_duplicate_programs_and_empty_artist_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report,pedals=self.fixtures(root);out=root/'local-artifacts'/'profile'
            p=root/'programs.json';p.write_text(json.dumps([dict(song_id=1,part_id=0,program=30)]*2))
            with self.assertRaisesRegex(ValueError,'Unique'):runner.run(report,pedals,out,'A',p)
            with self.assertRaisesRegex(ValueError,'Nonempty'):runner.run(report,pedals,out,'missing')
            self.assertFalse(out.exists())

    def test_duplicate_json_keys_and_orphan_programs_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report,pedals=self.fixtures(root);out=root/'local-artifacts'/'profile'
            p=root/'programs.json';p.write_text('[{"song_id":999,"part_id":0,"program":30}]')
            with self.assertRaisesRegex(ValueError,'outside'):runner.run(report,pedals,out,'A',p)
            pedals.write_text('{"tracks":[],"tracks":[]}')
            with self.assertRaisesRegex(ValueError,'Duplicate JSON'):runner.run(report,pedals,out,'A')
            self.assertFalse(out.exists())

    def test_nonfinite_json_and_boolean_identity_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report,pedals=self.fixtures(root);out=root/'local-artifacts'/'profile'
            p=root/'programs.json';p.write_text('[{"song_id":true,"part_id":0,"program":30}]')
            with self.assertRaisesRegex(ValueError,'integer program identities'):runner.run(report,pedals,out,'A',p)
            pedals.write_text('{"tracks":[],"bad":NaN}')
            with self.assertRaisesRegex(ValueError,'Nonfinite JSON'):runner.run(report,pedals,out,'A')
            self.assertFalse(out.exists())

    def test_empty_temporal_coverage_is_not_a_completed_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report,pedals=self.fixtures(root);out=root/'local-artifacts'/'profile'
            data=json.loads(report.read_text())
            for s in data['songs']:s['tracks'][0]['temporal_relationships_eligible']=False
            report.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'No eligible observations'):runner.run(report,pedals,out,'A')
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
