import copy,unittest
from test_corpus_composer import fixture,model_for
from corpus_composer import generate
from role_pitch_model import fit,observations
from role_pitch_transfer import apply,locked_context
from artist_profiles import stable_hash

class TransferTests(unittest.TestCase):
    def setup(self):
        report,raw=fixture();composer=model_for(report,raw);reference,_=generate(composer,2,23)
        model=fit(observations(composer));model.update(artist='Artist',source_composer_sha256=stable_hash(composer),weights={'melody':[0,.5,.5],'bass':[0,.5,.5]})
        return composer,reference,model,['harmony','melody','bass']

    def test_literal_zero_and_harmony_rhythm_locked(self):
        composer,ref,model,roles=self.setup()
        out,a=apply(ref,roles,None,None,0);self.assertEqual(out,ref)
        out,a=apply(ref,roles,composer,model);self.assertEqual(out['tracks'][0],ref['tracks'][0])
        for before,after in zip(ref['tracks'][1:],out['tracks'][1:]):
            for x,y in zip(before['measures'],after['measures']):
                self.assertEqual([(e['onset_q'],e['duration_q']) for e in x['voices'][0]],[(e['onset_q'],e['duration_q']) for e in y['voices'][0]])

    def test_100_target_pitch_reference_invariance(self):
        composer,ref,model,roles=self.setup();other=copy.deepcopy(ref)
        for t in other['tracks'][1:]:
            for m in t['measures']:
                for e in m['voices'][0]:
                    for n in e['notes']:n['midi']+=1;n['fret']+=1
        self.assertEqual(locked_context(ref,roles),locked_context(other,roles))
        self.assertEqual(apply(ref,roles,composer,model)[0],apply(other,roles,composer,model)[0])

    def test_invalid_freedom(self):
        composer,ref,model,roles=self.setup()
        for value in (False,-1,101,float('nan')):
            with self.assertRaises(ValueError):apply(ref,roles,composer,model,value)

    def test_unsupported_voice_and_provenance_rejected(self):
        composer,ref,model,roles=self.setup();changed=copy.deepcopy(composer);changed['artist']='Other'
        with self.assertRaises(ValueError):apply(ref,roles,changed,model)
        model['source_composer_sha256']='different revision'
        with self.assertRaises(ValueError):apply(ref,roles,composer,model)
        ref['tracks'][0]['measures'][0]['voices'].append(copy.deepcopy(ref['tracks'][0]['measures'][0]['voices'][0]))
        with self.assertRaises(ValueError):locked_context(ref,roles)

if __name__=='__main__':unittest.main()
