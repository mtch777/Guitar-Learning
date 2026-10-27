from copy import deepcopy
import unittest
import voicing_semantics as v


H=dict(root_pc=0,kind='major',formula=[0,4,7])


def group(pitches,ids=None):
    known=[p for p in pitches if p is not None];bass=str(min(known))if known else None
    return dict(id='fixture',bass_register_anchor=bass,members=[dict(id=ident,voicing_interval=None if p is None else str(p-min(known)))for ident,p in zip(ids or [str(i)for i in range(len(pitches))],pitches)])


class SemanticTests(unittest.TestCase):
    def check(self,a,b,locks,h=H,k=None,**kw):return v.check(group(a),group(b),[h],[k or h],locks,**kw)
    def test_1_spacing_same_harmony_doubling_bass_not_same_register(self):
        self.assertEqual(self.check([48,52,55],[48,64,55],['harmonic_hypotheses','doubling','inversion','bass_pitch','member_pitch_classes'])['status'],'PASS_CONDITIONAL_SEMANTIC_LOCKS')
        self.assertIn('SPACING_CHANGED',self.check([48,52,55],[48,64,55],['spacing'])['issues'])
        self.assertTrue(any(s.startswith('MEMBER_REGISTER_CHANGED')for s in self.check([48,52,55],[48,64,55],['member_register'])['issues']))

    def test_2_doubling_is_not_harmonic_identity(self):
        self.assertEqual(self.check([48,52,55,60],[48,52,55,67],['harmonic_hypotheses','occurrence_ids','inversion','bass_pitch'])['status'],'PASS_CONDITIONAL_SEMANTIC_LOCKS')
        self.assertTrue(any(s.startswith('REALIZED_DOUBLING_CHANGED')for s in self.check([48,52,55,60],[48,52,55,67],['doubling'])['issues']))

    def test_3_inversion_does_not_change_conditional_root(self):
        self.assertEqual(self.check([48,52,55],[60,52,55],['harmonic_hypotheses','doubling','member_pitch_classes'])['status'],'PASS_CONDITIONAL_SEMANTIC_LOCKS')
        r=self.check([48,52,55],[60,52,55],['inversion','bass_pitch'])
        self.assertIn('LOWEST_WRITTEN_PITCH_CHANGED',r['issues']);self.assertTrue(any(x.startswith('CONDITIONAL_INVERSION_CHANGED')for x in r['issues']))

    def test_4_bass_register_shift_can_change_inversion(self):
        r=self.check([36,52,55],[48,52,55],['inversion','doubling','member_pitch_classes'])
        self.assertEqual(r['status'],'PASS_CONDITIONAL_SEMANTIC_LOCKS')
        self.assertTrue(any(x.startswith('CONDITIONAL_INVERSION_CHANGED')for x in self.check([48,52,55],[60,52,55],['inversion'])['issues']))

    def test_5_ambiguous_dyad_never_fills_missing_third(self):
        g=group([48,55]);hypotheses=[H,dict(root_pc=0,kind='minor',formula=[0,3,7])]
        result=v.describe(g,hypotheses)
        self.assertEqual(len(result['hypotheses']),2)
        self.assertTrue(all(len(h['members'])==2 and h['unplayed_formula_roles']for h in result['hypotheses']))
        self.assertIn('HARMONIC_HYPOTHESIS_SET_CHANGED',v.check(g,g,hypotheses,[H],['harmonic_hypotheses'])['issues'])

    def test_6_held_nonchord_member_stays_exact(self):
        h=dict(root_pc=2,kind='major',formula=[0,4,7]);view=v.describe(group([48,54,57]),[h])
        self.assertEqual(view['hypotheses'][0]['members'][0]['membership'],'nonmember_under_hypothesis')
        self.assertIn('PINNED_EXECUTION_PITCH_CHANGED',self.check([48,54,57],[50,54,57],[],h=h,pinned_occurrences=['0'])['issues'])
        self.assertTrue(any(x.startswith('INVERSION_UNESTABLISHED')for x in self.check([48,54,57],[48,54,57],['inversion'],h=h)['issues']))

    def test_7_missing_third_and_unknown_pitch_do_not_establish_major(self):
        result=v.describe(group([48,55]),[H]);h=result['hypotheses'][0]
        self.assertEqual(h['unplayed_formula_roles'],['4']);self.assertIn('not_established',h['hypothesis']['status'])
        r=v.check(group([48,None]),group([48,None]),[H],[H],['doubling','bass_pitch'])
        self.assertIn('INCOMPLETE_WRITTEN_PITCH',r['issues'])

    def test_8_execution_pitch_pin_and_member_identity(self):
        self.assertEqual(self.check([48,52,55],[48,64,55],[],pinned_occurrences=['0'])['status'],'PASS_CONDITIONAL_SEMANTIC_LOCKS')
        self.assertIn('PINNED_EXECUTION_PITCH_CHANGED',self.check([48,52,55],[48,64,55],[],pinned_occurrences=['1'])['issues'])
        self.assertIn('OCCURRENCE_IDENTITIES_CHANGED',v.check(group([48,52]),group([48,52],['x','y']),[H],[H],['occurrence_ids'])['issues'])

    def test_same_equation_exact_rational_negative_and_wrap_coordinates(self):
        for root in range(12):
            for pitch in ('-1','0','11','12','48','127','97/2'):
                c=v.pitch_coordinate(root_pc=root,pitch=pitch)['coordinates']
                self.assertEqual(v.pitch_coordinate(root_pc=root,coordinates=c)['pitch'],pitch)
        with self.assertRaises(ValueError):v.pitch_coordinate(root_pc=0,coordinates=dict(semitone_role='12',register=3))

    def test_stale_cache_and_false_theory_rejected(self):
        g=group([48,52,55]);result=v.describe(g,[H]);self.assertTrue(v.validate_view(g,[H],result))
        changed=deepcopy(result);changed['hypotheses'][0]['bass_formula_slot']=2
        with self.assertRaises(ValueError):v.validate_view(g,[H],changed)
        with self.assertRaises(ValueError):v.validate_view(group([48,64,55]),[H],result)
        with self.assertRaises(ValueError):v.describe(g,[dict(H,formula=[0,3,7])])
        with self.assertRaises(ValueError):v.check(g,g,[H],[H],['fake'])
        self.assertIn('INSUFFICIENT_HARMONIC_HYPOTHESIS',v.check(g,g,[],[],['inversion'])['issues'])

    def test_typed_theory_no_boolean_float_tuple_or_unknown_keys(self):
        for changed in (dict(H,formula=[False,4,7]),dict(H,formula=[0.0,4,7]),dict(H,formula=(0,4,7)),dict(H,root_pc=False),dict(H,arbitrary='authority')):
            with self.assertRaises(ValueError):v.describe(group([48,52,55]),[changed])
        source=deepcopy(H);view=v.describe(group([48,52,55]),[source]);view['hypotheses'][0]['hypothesis']['formula'][0]=99
        self.assertEqual(source,H)

    def test_assumption_equality_is_not_realized_harmonic_evidence(self):
        for pitches in ([],[None,None]):
            self.assertIn('INCOMPLETE_WRITTEN_PITCH',self.check(pitches,pitches,['harmonic_hypotheses'])['issues'])
        # Assumptions stayed identical, but the actual chord support disappeared.
        result=self.check([48,52,55],[49,53,56],['harmonic_hypotheses','observed_formula_support','formula_membership'])
        self.assertTrue(any(x.startswith('OBSERVED_FORMULA_SUPPORT_CHANGED')for x in result['issues']))
        self.assertTrue(any(x.startswith('FORMULA_MEMBERSHIP_CHANGED')for x in result['issues']))
        # Doubling can change without losing observed chord-tone support.
        self.assertEqual(self.check([48,52,55,60],[48,52,55,67],['harmonic_hypotheses','observed_formula_support','formula_membership'])['status'],'PASS_CONDITIONAL_SEMANTIC_LOCKS')


if __name__=='__main__':unittest.main()
