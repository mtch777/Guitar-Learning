import unittest
from fractions import Fraction as F
from annotation_context_gap import decompose,run
from unittest.mock import patch


class ContextGapTests(unittest.TestCase):
    def test_equal_piece_weights_use_feature_known_denominators(self):
        yes=dict(context='a',known=['double_stop'],labels=['double_stop'])
        no=dict(context='a',known=['double_stop'],labels=[])
        unknown=dict(context='a',known=[],labels=[])
        model=dict(schema='artist-conditional-notation-v1',weighting='family',tables=[
            dict(artist='Artist',context='a',known={'double_stop':'1'},features={'double_stop':'0'})])
        with patch('annotation_context_gap.extract_score',side_effect=lambda p:p),patch(
            'annotation_context_gap.generated',side_effect=[[yes]+[unknown]*99,[no]]):
            result=run(model,['a','b'],'Artist')
        self.assertEqual(F(result['features']['double_stop']['components']['generated_rate']),F(1,2))

    def test_exact_identity_with_both_components(self):
        r=decompose({'a':(3,0),'b':(1,1)},{'a':(1,0),'b':(3,2)})['components']
        self.assertEqual(F(r['signed_gap']),F(1,4))
        self.assertEqual(F(r['context_mix_component']),F(1,2))
        self.assertEqual(F(r['within_context_component']),F(-1,4))

    def test_no_invention_for_unsupported_contexts(self):
        r=decompose({'a':(2,1),'b':(2,0)},{'a':(1,1),'c':(3,2)})
        self.assertEqual(F(r['source_shared_known_mass']),F(1,2))
        self.assertEqual(F(r['generated_shared_known_mass']),F(1,4))
        self.assertIsNone(decompose({'a':(1,1)},{'b':(1,0)})['components'])

    def test_invalid_mass_rejected(self):
        with self.assertRaises(ValueError):decompose({'a':(1,2)},{})


if __name__=='__main__':unittest.main()
