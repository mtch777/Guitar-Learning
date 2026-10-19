import json,tempfile,unittest
from pathlib import Path
from test_learned_performance import fixture
from learned_performance import apply,FAMILIES
from gp_author import write_gp
from compose_controlled import run,amounts


class ControlledPipelineTests(unittest.TestCase):
    def test_harmony_only_needs_no_locked_role_pitch_support(self):
        from test_corpus_composer import fixture as source_fixture,model_for
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);reference,_,_=self.core(p/'base.gp')
            report,raw=source_fixture();model=model_for(report,raw)
            model['parts']={k:v for k,v in model['parts'].items() if k=='harmony'}
            (p/'composer.json').write_text(json.dumps(model))
            run(p/'base.gp',{'composer':p/'composer.json'},{'harmony':100},p/'out')
            actual=json.loads((p/'out/composition.expected.json').read_text())
            self.assertEqual(reference['tracks'][1:],actual['tracks'][1:])
            for before,after in zip(reference['tracks'][0]['measures'],actual['tracks'][0]['measures']):
                self.assertEqual([e['duration_q'] for e in before['voices'][0]],[e['duration_q'] for e in after['voices'][0]])

    def test_extra_archive_members_fail_closed(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.core(p/'base.gp')
            with zipfile.ZipFile(p/'base.gp','a') as z:z.writestr('private-extra.txt','must not disappear')
            with self.assertRaisesRegex(ValueError,'outside'):run(p/'base.gp',{}, {},p/'out')
            self.assertFalse((p/'out').exists())

    def test_palm_only_needs_only_palm_model_and_explicit_artist(self):
        from test_palm_mute_method import model
        import copy
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.core(p/'base.gp');m=model()
            other=copy.deepcopy(m['tables'])
            for t in other:t['artist']='Other'
            m['tables'].extend(other);(p/'palm.json').write_text(json.dumps(m))
            result=run(p/'base.gp',{'palm':p/'palm.json'},{'palm_mute':100},p/'out',artist='Artist')
            self.assertEqual(result['artist'],'Artist')
            self.assertEqual([s['stage'] for s in result['stages']],['palm_mute'])
            self.assertEqual(set(result['model_sha256']),{'palm'})

    def core(self,p):
        score,model,shapes=fixture();score['source_file']='development-only empirical corpus generation'
        score['tracks'][0]['name']='harmony'
        # The zero-control path still requires the declared three-role layout.
        import copy
        for role in ('melody','bass'):
            track=copy.deepcopy(score['tracks'][0]);track['index']=len(score['tracks']);track['name']=role;score['tracks'].append(track)
        write_gp(score,p);p.with_suffix('.expected.json').write_text(json.dumps(score))
        return score,model,shapes

    def test_zero_requires_no_models_and_preserves_exact_gp(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.core(p/'base.gp')
            result=run(p/'base.gp',{}, {},p/'out')
            self.assertTrue(result['all_zero_byte_identity'])
            self.assertEqual((p/'base.gp').read_bytes(),(p/'out/composition.gp').read_bytes())
            self.assertFalse(result['stages'])

    def test_rejects_unknown_controls_and_invalid_amounts(self):
        for values in ({'form':100},{'rhythm':True},{'bass':101},{'bend':-1}):
            with self.assertRaises(ValueError):amounts(values)

    def test_rejects_performed_inputs_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);_,model,shapes=self.core(p/'base.gp')
            apply(p/'base.gp',p/'performed.gp',model,shapes,'Artist',{f:100 for f in FAMILIES})
            (p/'performed.expected.json').write_bytes((p/'base.expected.json').read_bytes())
            with self.assertRaisesRegex(ValueError,'Existing performance'):run(p/'performed.gp',{}, {},p/'out')
            self.assertFalse((p/'out').exists())

    def test_rejects_gp_json_disagreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);score,_,_=self.core(p/'base.gp')
            score['tracks'][0]['measures'][0]['voices'][0][0]['notes'][0]['midi']+=1
            score['tracks'][0]['measures'][0]['voices'][0][0]['notes'][0]['fret']+=1
            (p/'base.expected.json').write_text(json.dumps(score))
            with self.assertRaisesRegex(ValueError,'disagree'):run(p/'base.gp',{}, {},p/'out')


if __name__=='__main__':unittest.main()
