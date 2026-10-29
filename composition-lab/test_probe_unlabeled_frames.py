from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower
from unlabeled_inner_voicing import catalog
from test_check_unlabeled_inner import ambiguous_fixture
from probe_unlabeled_frames import compare,inventory,cheap_guard


class FrameOpportunityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        docs,cls.target=ambiguous_fixture()
        for n in docs['track-0.json']['measures'][6]['voices'][0]['beats'][0]['notes']:n['fret']+=2
        cls.c=catalog(strip_lower(analyze(extract_documents(docs),declared_chords=True)))

    def test_cross_root_ambiguous_source_transfer_adds_one_common_concrete_change(self):
        result=compare(self.c,self.c['harmonic_evidence'],self.c['ledger'])
        row=next(r for r in result['targets']if r['target_ref']==self.target[0])
        changed=[x for x in row['layouts']if x['changed']and x['all_assumptions']]
        self.assertTrue(changed)
        for x in changed:
            self.assertEqual(len(x['support']),2)
            self.assertEqual(x['donor_refs'],sorted(set(x['donor_refs'])))
        self.assertTrue(any(cheap_guard(self.c,x)=='PASSES_CHEAP_GUARDS_ONLY' for x in changed))
        self.assertFalse(result['policy_activated'])

    def test_absent_hypothesis_support_cannot_be_called_universal(self):
        evidence=deepcopy(self.c['harmonic_evidence'])
        group=next(g for g in evidence['groups']if g['member_refs']==self.target)
        group['hypotheses'].append(dict(id='missing-supported-interpretation'))
        row=next(r for r in inventory(self.c,evidence,framed=True)if r['target_ref']==self.target[0])
        self.assertTrue(row['layouts'])
        self.assertTrue(all(not x['all_assumptions']for x in row['layouts']))

    def test_changed_saved_baseline_is_not_silently_replaced(self):
        saved=deepcopy(self.c['ledger']);saved['groups'].pop()
        with self.assertRaisesRegex(ValueError,'baseline'):compare(self.c,self.c['harmonic_evidence'],saved)


if __name__=='__main__':unittest.main()
