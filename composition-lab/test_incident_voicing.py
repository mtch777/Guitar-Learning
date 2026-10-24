"""Incident execution locks versus explicit uncertain cross-part context."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from test_voicing_policy import documents
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,reconstruct
from voicing_register import inventory,select_target,intervene
from check_voicing_policy import check


def with_accompaniment(note):
    docs=documents();part=deepcopy(docs['track-0.json']);part['partId']=1
    for measure in part['measures']:measure['voices'][0]['beats']=[dict(duration=[1,1],notes=[deepcopy(note)])]
    docs['track-1.json']=part;docs['metadata.json']['tracks'].append(dict(name='Other guitar',instrumentId=25))
    return docs


class IncidentVoicingTests(unittest.TestCase):
    policy='incident_dependencies'

    def test_unrelated_other_part_expression_is_explicit_uncertainty(self):
        docs=with_accompaniment(dict(string=0,fret=0,vibrato=True));lower=extract_documents(docs)
        old=inventory(lower,'source_witnessed_fixed_strings');new=inventory(lower,self.policy)
        self.assertFalse(any(not r['refusal_reasons'] for r in old['units']))
        selection=select_target(new,self.policy);self.assertIsNotNone(selection['target_ref'])
        target=next(r for r in new['units'] if r['id']==selection['target_ref'])
        self.assertTrue(target['context_uncertainty']);self.assertFalse(target['locked_execution_members'])
        self.assertIn('sounding pitch/end unknown',target['context_uncertainty'][0]['claim'])
        self.assertEqual(check(docs,new,policy=self.policy)['status'],'PASS_INDEPENDENT_POLICY')

    def test_actual_shared_inverse_worker_preserves_expressive_other_part(self):
        docs=with_accompaniment(dict(string=0,fret=0,vibrato=True));lower=extract_documents(docs);catalog=inventory(lower,self.policy)
        target=select_target(catalog,self.policy)['target_ref'];controls=dict(voicing=100,register=100,target_ref=target,seed=9427,context_policy=self.policy)
        upper=strip_lower(analyze(lower));edited,decision=intervene(upper,controls)
        self.assertTrue(decision['changed']);expected=reconstruct(edited,dict(variation=0))
        self.assertEqual(project_documents(expected)['track-1.json'],docs['track-1.json'])
        self.assertEqual(reconstruct(upper,dict(controls,voicing=0,register=0)),lower)
        from run_voicing_register_qa import locked_diff
        self.assertEqual(locked_diff(lower,expected,decision['member_refs'])['status'],'PASS_LOCKED_DIMENSIONS')
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as temp:
            result=execute(code,upper,controls,expected,Path(temp)/'worker',timeout=30,purpose='voicing_register_intervention')
        self.assertEqual(result['status'],'PASS',result)

    def test_unknown_other_part_pitch_stays_unknown(self):
        docs=with_accompaniment(dict(string=0,fret=0,dead=True));catalog=inventory(extract_documents(docs),self.policy)
        selection=select_target(catalog,self.policy);self.assertIsNotNone(selection['target_ref'])
        target=next(r for r in catalog['units'] if r['id']==selection['target_ref'])
        self.assertEqual(target['context_uncertainty'][0]['written_pitch_status'],'unknown_or_noninteger')
        self.assertEqual(check(docs,catalog,policy=self.policy)['status'],'PASS_INDEPENDENT_POLICY')

    def test_uncertainty_evidence_has_canonical_order_across_staggered_parts(self):
        docs=with_accompaniment(dict(string=0,fret=0,vibrato=True));other=deepcopy(docs['track-1.json']);other['partId']=2
        docs['track-2.json']=other;docs['metadata.json']['tracks'].append(dict(name='Other part',instrumentId=25))
        for measure in docs['track-1.json']['measures']:
            measure['voices'][0]['beats']=[dict(duration=[1,2],rest=True,notes=[]),dict(duration=[1,2],notes=[dict(string=0,fret=0,vibrato=True)])]
        catalog=inventory(extract_documents(docs),self.policy)
        self.assertEqual(check(docs,catalog,policy=self.policy)['status'],'PASS_INDEPENDENT_POLICY')
        target=next(r for r in catalog['units'] if r['part_id']==0)
        refs=[r['occurrence_ref'] for r in target['context_uncertainty']]
        self.assertEqual(refs,sorted(refs))

    def test_fractional_other_part_pitch_is_not_a_twelve_class_category(self):
        docs=with_accompaniment(dict(string=0,fret=0.5));catalog=inventory(extract_documents(docs),self.policy)
        target=next(r for r in catalog['units'] if r['part_id']==0)
        self.assertEqual(target['context_uncertainty'][0]['written_pitch_status'],'unknown_or_noninteger')
        context=json.loads(target['dependency_context_key'])
        self.assertIsNone(context['overlaps'][0][-1])
        self.assertEqual(check(docs,catalog,policy=self.policy)['status'],'PASS_INDEPENDENT_POLICY')

    def test_same_part_uncertain_overlap_still_refuses(self):
        docs=documents()
        for measure in docs['track-0.json']['measures']:
            measure['voices'].append(dict(beats=[dict(duration=[1,4],rest=True,notes=[]),dict(duration=[3,4],notes=[dict(string=0,fret=0,vibrato=True)])]))
        catalog=inventory(extract_documents(docs),self.policy)
        target=catalog['units'][0]
        self.assertIn('UNRESOLVED_OVERLAP_EXECUTION',target['refusal_reasons'])
        self.assertEqual(check(docs,catalog,policy=self.policy)['status'],'PASS_INDEPENDENT_POLICY')

    def test_independent_oracle_rejects_erased_graph_or_uncertainty(self):
        docs=with_accompaniment(dict(string=0,fret=0,vibrato=True));catalog=inventory(extract_documents(docs),self.policy)
        corrupted=deepcopy(catalog);corrupted['execution_dependencies']['signature']={}
        self.assertNotEqual(check(docs,corrupted,policy=self.policy)['status'],'PASS_INDEPENDENT_POLICY')
        corrupted=deepcopy(catalog);next(r for r in corrupted['units'] if not r['refusal_reasons'])['context_uncertainty']=[]
        self.assertNotEqual(check(docs,corrupted,policy=self.policy)['status'],'PASS_INDEPENDENT_POLICY')

    def test_dependency_view_is_stored_recomputed_and_never_an_inverse_cache(self):
        from connected_tier2 import validate
        from execution_dependencies import build
        lower=extract_documents(with_accompaniment(dict(string=0,fret=0,vibrato=True)))
        upper=analyze(lower)
        self.assertEqual(upper['derived_views']['execution_dependencies'],build(lower))
        self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)
        upper['derived_views']['execution_dependencies']['signature']={}
        with self.assertRaisesRegex(ValueError,'Stale or altered'):validate(upper)


if __name__=='__main__':unittest.main()
