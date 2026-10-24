"""Relationship locks protect tie semantics, not just literal tie flags."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents,project_documents
from source_tie_tier1 import extract_documents as context_documents
from connected_tier2 import analyze,strip_lower,reconstruct
from voicing_register import inventory,intervene,empirical_options,tie_relationships
from check_voicing_policy import check
from test_voicing_policy import evidence


def documents(keep_origin=False,unresolved=False):
    part=dict(partId=0,songId=84,revisionId=1,instrumentId=25,tuning=[64,59,55,50,45,40],frets=24,measures=[])
    for i in range(3):
        frets=[0,2,2]if i==0 else([0,14,14]if keep_origin else[12,14,14])
        continuation=12 if unresolved or(i>0 and not keep_origin)else 0
        part['measures'].append(dict(signature=[4,4],voices=[dict(beats=[
            dict(duration=[1,2],notes=[dict(string=s,fret=f)for s,f in zip((5,4,3),frets)]),
            dict(duration=[1,2],notes=[dict(string=5,fret=continuation,tie=True)])])]))
    return {'metadata.json':dict(songId=84,revisionId=1,artist='Fixture',title='Outgoing continuity',tracks=[dict(name='Guitar',instrumentId=25)]),'track-0.json':part}


class VoicingTieLockTests(unittest.TestCase):
    def fixture(self,**kwargs):
        docs=documents(**kwargs);lower=extract_documents(docs);catalog=inventory(lower);return docs,lower,catalog,catalog['units'][0]['id']

    def test_outgoing_tie_at_exact_halfopen_end_is_pinned_and_refused(self):
        docs,lower,catalog,target=self.fixture();unit=catalog['units'][0]
        self.assertFalse(unit['refusal_reasons'])
        self.assertEqual(unit['locked_tie_members'],['event:84:0:1:0:0:0'])
        self.assertEqual(len(catalog['written_tie_relationships']['links']),3)
        choices=empirical_options(catalog,target,'source_witnessed_fixed_strings')
        self.assertEqual(choices['status'],'NO_ELIGIBLE_ALTERNATIVE')
        self.assertTrue(choices['rejected'])
        self.assertTrue(all(r['reason']=='LOCKED_WRITTEN_TIE_ENDPOINT'for r in choices['rejected']))
        report=check(docs,catalog,evidence(catalog));self.assertEqual(report['status'],'PASS_INDEPENDENT_POLICY',report)
        upper=strip_lower(analyze(lower));changed,decision=intervene(upper,dict(voicing=100,register=100,target_ref=target,seed=9427,context_policy='source_witnessed_fixed_strings'))
        self.assertFalse(decision['changed']);self.assertEqual(reconstruct(changed,dict(variation=0)),lower)

    def test_other_members_can_change_when_incident_endpoint_pitch_stays_fixed(self):
        docs,lower,catalog,target=self.fixture(keep_origin=True)
        self.assertEqual(check(docs,catalog,evidence(catalog))['status'],'PASS_INDEPENDENT_POLICY')
        upper=strip_lower(analyze(lower));changed,decision=intervene(upper,dict(voicing=100,register=100,target_ref=target,seed=9427,context_policy='source_witnessed_fixed_strings'))
        self.assertTrue(decision['changed']);after=project_documents(reconstruct(changed,dict(variation=0)))
        self.assertEqual(after['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret'],0)
        self.assertEqual(after['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][1]['fret'],14)
        self.assertEqual(tie_relationships(context_documents(after)),catalog['written_tie_relationships'])

    def test_independent_oracle_rejects_pin_graph_and_filter_corruption(self):
        docs,lower,catalog,target=self.fixture();rows=evidence(catalog)
        changed=deepcopy(catalog);changed['units'][0]['locked_tie_members']=[]
        self.assertEqual(check(docs,changed,rows)['status'],'FAIL_INDEPENDENT_POLICY')
        changed=deepcopy(catalog);changed['written_tie_relationships']['links'].pop()
        self.assertIn('WRITTEN_TIE_RELATIONSHIPS_MISMATCH',check(docs,changed,rows)['issues'])
        changed=deepcopy(rows);changed[0]['rejected'].pop()
        self.assertEqual(check(docs,catalog,changed)['status'],'FAIL_INDEPENDENT_POLICY')
        changed=deepcopy(rows);changed[0]['rejected'][0]['reason']='NO_JOINT_FIXED_STRING_WITNESS'
        self.assertEqual(check(docs,catalog,changed)['status'],'FAIL_INDEPENDENT_POLICY')

    def test_final_guard_preserves_unresolved_reasons_not_just_resolved_links(self):
        docs,lower,catalog,target=self.fixture(unresolved=True)
        self.assertEqual(catalog['written_tie_relationships']['unresolved'],[dict(destination='event:84:0:1:0:1:0',reason='different_written_position')])
        self.assertEqual(check(docs,catalog,evidence(catalog))['status'],'PASS_INDEPENDENT_POLICY')
        upper=strip_lower(analyze(lower))
        for policy in ('exact_context','source_witnessed_fixed_strings'):
            with self.assertRaisesRegex(ValueError,'Locked written tie relationship changed'):
                intervene(upper,dict(voicing=100,register=100,target_ref=target,seed=9427,context_policy=policy))


if __name__=='__main__':unittest.main()
