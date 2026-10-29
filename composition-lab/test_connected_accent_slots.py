"""Sole optional ownership through the production connected inverse."""
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize,validate
from test_dynamic_context import documents


class ConnectedAccentSlotsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        doc=documents();beats=doc['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['notes']=[dict(fret=0,accentuated=0,string=0)]
        beats[1]['notes']=[dict(accentuated=1,fret=1,string=0)]
        beats[2]['notes']=[dict(fret=2,string=0,accentuated=2)]
        beats[3]['notes']=[dict(fret=3,string=0)]
        cls.before=extract_documents(doc);cls.upper=analyze(cls.before,note_accent_slots=True)

    def test_complete_zero_keeps_exact_fact_and_child_order(self):
        self.assertEqual(realize(strip_lower(self.upper)),self.before)
        self.assertEqual(validate(self.upper),self.before)
        self.assertEqual(self.upper['schema'],'connected-source-musical-relations/2')
        legacy=analyze(self.before)
        self.assertEqual(legacy['schema'],'connected-source-musical-relations/1')
        self.assertIsInstance(legacy['coverage'],list)

    def test_presence_change_uses_same_inverse_without_rewriting_coverage(self):
        upper=strip_lower(self.upper);group=next(g for g in upper['owned_parameters']['optional_note_accents']['groups']if g['state']=={'kind':'absent'})
        note_ref=group['note_structure']['id'];ledger=deepcopy(upper['coverage'])
        group['state']=dict(kind='explicit',value=1,child_index=len(group['note_structure']['children']))
        after=realize(upper);self.assertEqual(upper['coverage'],ledger)
        before_index={r['id']:r for r in self.before['facts']};after_index={r['id']:r for r in after['facts']}
        self.assertEqual(set(after_index)-set(before_index),{note_ref+'/accentuated'})
        self.assertEqual(after_index[note_ref+'/accentuated']['value'],1)
        for ref,row in before_index.items():
            expected=deepcopy(row)
            if ref==note_ref:expected['children'].append(ref+'/accentuated')
            self.assertEqual(after_index[ref],expected)
        group['state']={'kind':'absent'};self.assertEqual(realize(upper),self.before)

    def test_actual_source_denied_zero_and_parameter_change(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        upper=strip_lower(self.upper)
        with tempfile.TemporaryDirectory()as temp:
            for stage in ('zero','new_presence'):
                if stage=='new_presence':
                    g=next(g for g in upper['owned_parameters']['optional_note_accents']['groups']if g['state']['kind']=='absent')
                    g['state']=dict(kind='explicit',value=1,child_index=len(g['note_structure']['children']))
                expected=realize(upper)
                result=execute(code,upper,{'variation':0},expected,Path(temp)/stage,timeout=30)
                self.assertEqual(result['status'],'PASS',result)

    def test_forged_or_duplicated_coverage_and_structure_are_rejected(self):
        for kind in ('missing_rule','extra_rule','fixed_duplicate','reused_container','stale_accent_group','detached_child','wrong_parent_array'):
            upper=strip_lower(self.upper);model=upper['owned_parameters']['optional_note_accents'];g=model['groups'][0]
            if kind=='missing_rule':upper['coverage']['rules'].pop()
            elif kind=='extra_rule':upper['coverage']['rules'].append(dict(relation='invented'))
            elif kind=='fixed_duplicate':upper['coverage']['fixed'].append(dict(fact_ref=g['note_structure']['id'],owner='optional_note_accent'))
            elif kind=='reused_container':upper['source_structure']['facts'].append(deepcopy(g['note_structure']))
            elif kind=='stale_accent_group':
                legacy=analyze(self.before);old=next(t for t in legacy['owned_parameters']['technique_declarations']['groups']if t['field']=='accentuated')
                upper['owned_parameters']['technique_declarations']['groups'].append(old)
            elif kind=='detached_child':g['note_structure']['children'].clear()
            else:
                parent=next(r for r in upper['source_structure']['facts']if r['id']==g['note_structure']['parent']);parent['type']='object'
            with self.subTest(kind=kind):
                with self.assertRaises((ValueError,KeyError)):realize(upper)

    def test_unknown_accent_keeps_legacy_owner_and_no_optional_permission(self):
        for value in (3,None,False,1.0,'1'):
            doc=documents();doc['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['accentuated']=value
            before=extract_documents(doc);upper=analyze(before,note_accent_slots=True)
            note_ref='track-0.json#/measures/0/voices/0/beats/0/notes/0'
            self.assertFalse(any(g['note_structure']['id']==note_ref for g in upper['owned_parameters']['optional_note_accents']['groups']))
            self.assertTrue(any(g['source_fact_ref']==note_ref+'/accentuated'for g in upper['owned_parameters']['technique_declarations']['groups']))
            self.assertEqual(realize(strip_lower(upper)),before)


if __name__=='__main__':unittest.main()
