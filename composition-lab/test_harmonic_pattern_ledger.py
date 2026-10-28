from copy import deepcopy
import unittest
from test_inner_voicing import fixture
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower
from harmonic_evidence import source_patterns
from harmonic_pattern_ledger import build,validate
from check_harmonic_pattern_ledger import check
from pathlib import Path
import tempfile


class LedgerTests(unittest.TestCase):
    def fixture(self):
        docs,_,_=fixture()
        for p in docs.values():
            for m in p.get('measures',[]):
                for v in m.get('voices',[]):
                    for b in v.get('beats',[]):b.pop('chord',None)
        c=source_patterns(strip_lower(analyze(extract_documents(docs),declared_chords=True)))
        return c,c['harmonic_evidence']

    def test_existing_guarded_relation_works_without_source_labels(self):
        c,view=self.fixture();ledger=build(c,view)
        self.assertFalse(ledger['policy_activated']);self.assertGreater(ledger['counts']['changed_layouts'],0)
        self.assertGreater(ledger['counts']['WHOLE_GEOMETRY_PREFLIGHT_ONLY'],0)
        for row in ledger['groups']:
            keys=[tuple(x['pitches'])for x in row['layouts']];self.assertEqual(len(keys),len(set(keys)))
        self.assertEqual(validate(c,view,ledger),ledger)
        self.assertEqual(check(c,view,ledger)['status'],'PASS_INDEPENDENT_PATTERN_LEDGER')
        broken=deepcopy(ledger);row=next(g for g in broken['groups']if g['layouts']);row['layouts'].append(deepcopy(row['layouts'][0]))
        self.assertEqual(check(c,view,broken)['status'],'FAIL')

    def test_unavailable_assumption_prevents_universal_claim(self):
        c,view=self.fixture();ledger=build(c,view)
        row=next(g for g in ledger['groups']if g['layouts']);target=next(g for g in view['groups']if g['group_ref']==row['group_ref'])
        # Ledger must count every supplied interpretation, even one with no eligible unit.
        target['hypotheses'].append(dict(id='unsupported-fixture-assumption'))
        newer=build(c,view);changed=next(g for g in newer['groups']if g['group_ref']==row['group_ref'])
        self.assertTrue(all(x['support_class']=='SOME_ENUMERATED_TARGET_ASSUMPTIONS'for x in changed['layouts']))
        with self.assertRaises(ValueError):validate(c,view,ledger)

    def test_pattern_count_is_invariant_to_note_serialization(self):
        c,view=self.fixture();before=build(c,view);changed=deepcopy(c);changed_view=changed['harmonic_evidence']
        # Reorder some occurrences, so an otherwise identical source pattern
        # still exists in the original order elsewhere in the same part.
        chosen={u['group_ref']for u in changed['units'][::2]}
        for u in changed['units']:
            if u['group_ref']in chosen:
                for key in ('member_refs','strings','roles','pitches'):u[key].reverse()
        for g in changed_view['groups']:
            if g['group_ref']in chosen:g['member_refs'].reverse()
        after=build(changed,changed_view)
        self.assertEqual(after['counts']['unique_normalized_patterns'],before['counts']['unique_normalized_patterns'])
        self.assertEqual(check(changed,changed_view,after)['status'],'PASS_INDEPENDENT_PATTERN_LEDGER')

    def test_actual_source_denied_common_relation_worker(self):
        from run_harmonic_evidence_qa import bundle
        from qa_isolation_harness import execute
        docs,_,_=fixture();upper=strip_lower(analyze(extract_documents(docs),declared_chords=True));c=source_patterns(upper)
        expected=dict(evidence=c['harmonic_evidence'],catalog=dict(units=c['units'],geometries=c['geometries'],component_scope_refusals=c['component_scope_refusals']),ledger=build(c,c['harmonic_evidence']))
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as tmp:
            result=execute(code,upper,dict(variation=0),expected,Path(tmp)/'relations',timeout=60)
            self.assertEqual(result['status'],'PASS',result)


if __name__=='__main__':unittest.main()
