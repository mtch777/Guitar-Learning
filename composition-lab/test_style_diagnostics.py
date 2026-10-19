import unittest
from style_diagnostics import rank_rate_report,audit_split,support,stratified_accounting


def event(song='s',family='f',partition='development',labels=(),known=('x',),**kwargs):
    return dict(song_id=song,family=family,partition=partition,artist='A',flagged=False,
                labels=list(labels),known=list(known),**kwargs)


class StyleDiagnosticTests(unittest.TestCase):
    def test_equal_piece_rates_not_pooled_and_signed(self):
        report=dict(pieces=[dict(file='a',known={'x':1},positive={'x':1}),
                            dict(file='b',known={'x':9},positive={'x':0})],
                    features={'x':dict(source_family_balanced_attack_rate=.7,generated_equal_piece_attack_rate=.5)})
        r=rank_rate_report(report)[0]
        self.assertAlmostEqual(r['signed_gap_pp'],-20)
        self.assertEqual((r['generated_known'],r['positive_pieces']),(10,1))
        report['features']['x']['generated_equal_piece_attack_rate']=.1
        with self.assertRaises(ValueError):rank_rate_report(report)

    def test_unknown_is_not_negative_and_positives_require_eligibility(self):
        rows=[event(labels=('x',)),event(known=())]
        self.assertEqual(support(rows,'x')['eligible'],1)
        with self.assertRaises(ValueError):support([event(labels=('x',),known=())],'x')

    def test_family_leakage_and_model_membership_fail_closed(self):
        rows=[event(),event('h','hf','held_out')]
        model=dict(training_songs=['s'],training_families=['f'],training_events=1)
        self.assertEqual(audit_split(rows,model)['heldout_songs'],1)
        rows[1]['family']='f'
        with self.assertRaises(ValueError):audit_split(rows,model)
        rows[1]['family']='hf';model['training_events']=2
        with self.assertRaises(ValueError):audit_split(rows,model)

    def test_mix_difference_without_within_stratum_change(self):
        source=[event(role='low',labels=('x',),weight=3),event(role='high',weight=1)]
        target=[event(role='low',labels=('x',),weight=1),event(role='high',weight=3)]
        r=stratified_accounting(source,target,'x',('role',))
        self.assertEqual(r['components']['within_context_component'],0)
        self.assertEqual(r['components']['context_mix_component'],-.5)
        self.assertEqual(r['components']['signed_gap'],-.5)

    def test_unshared_and_missing_roles_are_not_imputed(self):
        r=stratified_accounting([event(role='low'),event()], [event(role='high')],'x',('role',))
        self.assertIsNone(r['components']);self.assertEqual(r['source_missing_stratum'],1)
        self.assertEqual(r['source_shared_known_mass'],0)

    def test_invalid_support_rejected(self):
        bad=dict(pieces=[dict(file='a',known={'x':0},positive={'x':1})],features={'x':dict(source_family_balanced_attack_rate=0,generated_equal_piece_attack_rate=0)})
        with self.assertRaises(ValueError):rank_rate_report(bad)
        with self.assertRaises(ValueError):stratified_accounting([event(role='low',weight=0)],[],'x',('role',))

    def test_nonfinite_or_nonnumeric_supplied_rates_cannot_pass_reconciliation(self):
        for field in ('source_family_balanced_attack_rate','generated_equal_piece_attack_rate'):
            for value in (float('nan'),float('inf'),-1,2,True,'0.5'):
                report=dict(pieces=[dict(file='a',known={'x':1},positive={'x':1})],
                            features={'x':dict(source_family_balanced_attack_rate=1,generated_equal_piece_attack_rate=1)})
                report['features']['x'][field]=value
                with self.subTest(field=field,value=value):
                    with self.assertRaises(ValueError):rank_rate_report(report)


if __name__=='__main__':unittest.main()
