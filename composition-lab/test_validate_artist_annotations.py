import tempfile,unittest
from pathlib import Path
from test_learned_performance import fixture
from gp_author import write_gp
from learned_performance import apply,FAMILIES
from exact_score import extract_score
from validate_artist_annotations import generated,compare

class AnnotationValidationTests(unittest.TestCase):
    def test_rejects_incompatible_denominators(self):
        for model in ({},{'schema':'artist-conditional-notation-v1','weighting':'pooled'}):
            with self.assertRaisesRegex(ValueError,'family-weighted'):compare(model,[],'Artist')

    def test_rejects_unknown_pitch(self):
        score,_,_=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'base.gp';write_gp(score,p);extracted=extract_score(p)
            extracted['tracks'][0]['measures'][0]['voices'][0][0]['notes'][0]['midi']=None
            with self.assertRaisesRegex(ValueError,'known pitched'):generated(extracted,'Artist')

    def test_observes_encoded_features_and_marks_unmeasured_unknown(self):
        score,model,shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp');apply(p/'base.gp',p/'out.gp',model,shapes,'Artist',{f:100 for f in FAMILIES})
            events=generated(extract_score(p/'out.gp'),'Artist');labels={f for e in events for f in e['labels']}
            self.assertTrue({'bend','finger_vibrato','hammer_on_from_open','pull_off_to_open'}<=labels)
            self.assertFalse(any('pedal_call' in e['known'] or 'slide' in e['known'] for e in events))
            self.assertEqual(len(events),8)

if __name__=='__main__':unittest.main()
