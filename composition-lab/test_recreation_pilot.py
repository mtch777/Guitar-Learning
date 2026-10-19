import json
from pathlib import Path
import tempfile
import unittest

from engine_contract import sha
from gp_author import write_gp
from recreation_pilot import run,validate_partition
from test_learned_performance import fixture


class RecreationPilotTests(unittest.TestCase):
    def test_family_and_shape_leakage_are_refused(self):
        _,model,shapes=fixture()
        for family,song in [('f',2),('new-family',1)]:
            with self.assertRaises(ValueError):validate_partition(dict(family=family,song_id=song,feature='bend'),model,shapes)
        model['training_families']=[];model['training_songs']=[]
        with self.assertRaises(ValueError):validate_partition(dict(family='f',song_id=2,feature='bend'),model,shapes)

    def test_full_hidden_target_runner_reports_errors_without_claiming_native_acceptance(self):
        score,model,shapes=fixture()
        for table in model['tables']:table['artist']='Invent Animate'
        shapes['artist']='Invent Animate'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'source.gp')
            (p/'model.json').write_text(json.dumps(model));(p/'shapes.json').write_text(json.dumps(shapes))
            case=dict(song_id=2,family='held-out-fixture-family',feature='bend',window=[0,1,2],seed=17,
                      source=str(p/'source.gp'),source_sha256=sha(p/'source.gp'),
                      model_sha256=sha(p/'model.json'),shapes_sha256=sha(p/'shapes.json'))
            result=run(case,p/'run',p/'model.json',p/'shapes.json',p/'model.json')
            self.assertTrue(result['target_perturbation_invariant'])
            self.assertEqual(result['confusion']['FP'],4)
            self.assertEqual(result['confusion']['TP'],0)
            self.assertEqual(result['native_validation'],'pending')
            self.assertFalse(result['musical_acceptance'])
            self.assertEqual(sha(p/'source.gp'),case['source_sha256'])
            with self.assertRaises(FileExistsError):run(case,p/'run',p/'model.json',p/'shapes.json',p/'model.json')


if __name__=='__main__':unittest.main()
