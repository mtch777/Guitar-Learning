from copy import deepcopy
import math
import unittest
from diagnose_ordered_tonal_help_hurt import compare_piece, emission_terms, explain, transition_terms


def fixture():
    row=dict(id=7,start_q='1/3',end_q='2/3',duration_q='1/3',mask=1,previous_mask=2,sequence=0,target=dict(state=0),quarantine_reasons=[],active_note_refs=['source:1'])
    piece=dict(work='work',piece='piece',rows=[row])
    def prediction(target):
        probs=[(1-target)/23]*24;probs[0]=target
        return dict(observation_ref=7,start_q='1/3',end_q='2/3',posterior=probs,marginal_map_state=max(range(24),key=lambda i:probs[i]))
    return piece,prediction(.2),prediction(.4)


class SavedDiagnosticTests(unittest.TestCase):
    def test_exhaustive_difference_duration_and_reverse_help_hurt(self):
        p,a,b=fixture();row=compare_piece(p,[a],[b])[0]
        self.assertEqual(row['classification'],'help')
        self.assertAlmostEqual(row['ordered_minus_marginal_nll'],-math.log(2))
        self.assertAlmostEqual(row['duration_weighted_difference'],-math.log(2)/3)
        self.assertEqual(row['current_pcs'],[0]);self.assertEqual(row['previous_pcs'],[1])
        self.assertEqual(compare_piece(p,[b],[a])[0]['classification'],'hurt')
        self.assertEqual(compare_piece(p,[a],[a])[0]['classification'],'tie')

    def test_missing_duplicate_clock_and_typed_target_fail(self):
        p,a,b=fixture()
        for left in ([],[a,a]):
            with self.assertRaises(ValueError):compare_piece(p,left,[b])
        wrong=deepcopy(b);wrong['start_q']='0'
        with self.assertRaises(ValueError):compare_piece(p,[a],[wrong])
        p['rows'][0]['target']['state']=True
        with self.assertRaises(ValueError):compare_piece(p,[a],[b])

    def test_nonfinite_invalid_distribution_rejected(self):
        p,a,b=fixture()
        for value in (float('nan'),float('inf'),-1):
            wrong=deepcopy(b);wrong['posterior'][0]=value
            with self.assertRaises(ValueError):compare_piece(p,[a],[wrong])

    def test_fixed_count_arithmetic_and_odds_identity(self):
        p,a,b=fixture();source=p['rows'][0]
        model=dict(kind='ordered',alpha=2,tau=1,marginal=[{'1':3},{}],mode_totals=[4,4],contexts=[{'2':{'1':2}},{}],context_totals=[{'2':3},{}],key_transitions=[{'0:0':5},{}])
        terms=emission_terms(model,source,0);base=(3+1/4096)/5
        self.assertAlmostEqual(terms['probability'],(2+2*base)/5)
        self.assertAlmostEqual(transition_terms(model,0,0)['probability'],(5+1/24)/6)
        cell=compare_piece(p,[a],[b])[0]
        result=explain(cell,source,{'marginal':{7:a},'ordered':{7:b}},dict(marginal=dict(model,kind='marginal'),ordered=model),0)
        for detail in result['fixed_model_evidence'].values():
            self.assertAlmostEqual(detail['posterior_log_odds'],detail['emission_log_odds']+detail['normalized_past_future_message_log_odds'])
        changed=deepcopy(source);changed['target']={'state':13}
        self.assertEqual(emission_terms(model,source,0),emission_terms(model,changed,0))


if __name__=='__main__':unittest.main()
