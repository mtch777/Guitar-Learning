"""Source-observed closed-shape choices through the composed family inverse."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize,reconstruct,validate
from voicing_register import inventory,intervene,select_target


def documents():
    def bar(notes):return dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=[dict(string=s,fret=f)for s,f in notes])])])
    return {'metadata.json':dict(songId=83,revisionId=1,artist='Fixture',title='Family relations',tracks=[dict(name='Guitar',instrumentId=25)]),
        'track-0.json':dict(songId=83,revisionId=1,partId=0,instrumentId=25,tuning=[64,59,55,50,45,40],frets=24,
            measures=[bar([(3,10),(2,9),(1,8)]),bar([(3,12),(0,14),(2,14)])])}


class FamilyIntegrationTests(unittest.TestCase):
    def fixture(self):
        lower=extract_documents(documents());upper=strip_lower(analyze(lower,families=True))
        cat=inventory(lower,'transposed_voicing_family');target=select_target(cat,'transposed_voicing_family')['target_ref']
        controls=dict(voicing=100,register=0,physical=100,target_ref=target,seed=9427,context_policy='transposed_voicing_family')
        return lower,upper,controls

    def test_complete_source_zero_reversal_and_composed_validation(self):
        lower,upper,c=self.fixture();self.assertEqual(reconstruct(upper,dict(variation=0)),lower)
        self.assertEqual(validate(analyze(lower,families=True)),lower)
        self.assertEqual(reconstruct(upper,dict(c,voicing=0,physical=0)),lower)

    def test_source_choice_changes_voicing_with_register_fixed(self):
        lower,upper,c=self.fixture();original=deepcopy(upper);edited,decision=intervene(upper,c)
        self.assertTrue(decision['changed']);self.assertEqual(upper,original)
        self.assertEqual(decision['original']['anchor'],decision['chosen']['realization']['anchor'])
        self.assertEqual(edited['musical_relationships']['schema'],'source-voicing-families/1')
        docs=project_documents(realize(edited));notes=docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes']
        self.assertEqual(notes,[dict(string=3,fret=10),dict(string=0,fret=12),dict(string=2,fret=12)])
        self.assertEqual(docs['track-0.json']['measures'][1],documents()['track-0.json']['measures'][1])

    def test_actual_isolated_family_zero_and_nonzero(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower,upper,c=self.fixture();code,_=bundle(Path(__file__).parent)
        for controls,expected,purpose in ((dict(variation=0),lower,'exact_zero'),(c,reconstruct(upper,c),'voicing_register_intervention')):
            with tempfile.TemporaryDirectory() as temp:
                result=execute(code,upper,controls,expected,Path(temp)/'worker',timeout=30,purpose=purpose)
            self.assertEqual(result['status'],'PASS',result)

    def test_scope_and_separate_release_conflicts(self):
        lower,upper,c=self.fixture()
        with self.assertRaises(ValueError):intervene(upper,dict(c,register=100))
        edited,decision=intervene(upper,dict(c,physical=0))
        self.assertFalse(decision['changed']);self.assertEqual(realize(edited),lower)
        edited,decision=intervene(upper,dict(c,voicing=0))
        self.assertFalse(decision['changed']);self.assertEqual(realize(edited),lower)

    def test_pitch_declaration_blocks_uncoupled_edit(self):
        docs=documents();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['spn']=[0,0,4]
        lower=extract_documents(docs);upper=strip_lower(analyze(lower,families=True))
        self.assertEqual(realize(upper),lower)
        cat=inventory(lower,'transposed_voicing_family')
        self.assertIn('SOURCE_PITCH_DECLARATION_NOT_COUPLED',cat['units'][0]['refusal_reasons'])

    def test_selected_float_fret_sign_is_dependent_on_new_value(self):
        docs=documents();bars=docs['track-0.json']['measures']
        bars[0]['voices'][0]['beats'][0]['notes']=[dict(string=0,fret=-0.0),dict(string=1,fret=9),dict(string=2,fret=16)]
        bars[1]['voices'][0]['beats'][0]['notes']=[dict(string=3,fret=10),dict(string=0,fret=12),dict(string=1,fret=8)]
        lower=extract_documents(docs);upper=strip_lower(analyze(lower,families=True))
        self.assertEqual(realize(upper),lower)
        cat=inventory(lower,'transposed_voicing_family');target=select_target(cat,'transposed_voicing_family')['target_ref']
        c=dict(voicing=100,register=0,physical=100,target_ref=target,seed=9427,context_policy='transposed_voicing_family')
        edited,decision=intervene(upper,c);self.assertTrue(decision['changed'])
        note=project_documents(realize(edited))['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]
        self.assertEqual(note,dict(string=3,fret=14.0));self.assertIs(type(note['fret']),float)

    def test_unchanged_raw_technique_checker_accepts_family_representation(self):
        from check_technique_connections import check
        from test_connected_tier2 import documents as expressive
        docs=expressive();lower=extract_documents(docs)
        original=check(docs,analyze(lower));family=analyze(lower,families=True)
        self.assertEqual(check(docs,family),original)
        family['musical_relationships']['spacings'].append(dict(id='spacing:fake',intervals=['0','4']))
        with self.assertRaises(ValueError):check(docs,family)

    def test_changed_family_has_matching_raw_source_relationships(self):
        from check_technique_connections import check
        lower,upper,c=self.fixture();edited,decision=intervene(upper,c);after=realize(edited)
        reviewed=analyze(after,families=True)
        self.assertEqual(check(project_documents(after),reviewed)['status'],'PASS_SOURCE_BACKED_RELATIONSHIPS')


if __name__=='__main__':unittest.main()
