"""Corruption tests for independent voicing source-denominator verification."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from voicing_register import inventory, empirical_options
from check_voicing_policy import check


def documents():
    def measure(frets,beam=False):
        beat=dict(duration=[1,1],notes=[dict(string=s,fret=f)for s,f in zip((5,4,3),frets)])
        if beam:beat['beamStart']=True
        return dict(signature=[4,4],voices=[dict(beats=[beat])])
    return {'metadata.json':dict(songId=81,revisionId=2,artist='Fixture',title='Independent geometry',tracks=[dict(name='Guitar',instrumentId=25)]),
            'track-0.json':dict(songId=81,revisionId=2,partId=0,instrumentId=25,tuning=[64,59,55,50,45,40],frets=24,
                measures=[measure([0,2,2]),measure([12,14,14],True),measure([12,14,14])])}


def evidence(catalog):
    rows=[]
    for target in catalog['units']:
        if target['refusal_reasons']:continue
        r=empirical_options(catalog,target['id'],'source_witnessed_fixed_strings')
        rows.append(dict(target_ref=target['id'],status=r['status'],levels=r['levels'],rejected=r['rejected'],options=r['options']))
    return rows


class PolicyOracleTests(unittest.TestCase):
    def fixture(self,docs=None):
        docs=documents()if docs is None else docs
        catalog=inventory(extract_documents(docs));return docs,catalog,evidence(catalog)

    def test_positive_complete_denominator_graphic_noise_and_repeated_pcs(self):
        docs,catalog,rows=self.fixture();result=check(docs,catalog,rows)
        self.assertEqual(result['status'],'PASS_INDEPENDENT_POLICY',result)
        self.assertEqual(result['source_units'],3);self.assertEqual(result['source_occurrences'],9)
        self.assertTrue(rows[0]['options']);self.assertEqual(len(rows[0]['options'][0]['donor_refs']),2)

    def test_dropped_duplicate_unit_or_member_is_rejected(self):
        docs,catalog,rows=self.fixture()
        mutations=[]
        m=deepcopy(catalog);m['units'].pop();mutations.append(m)
        m=deepcopy(catalog);m['units'].append(m['units'][0]);mutations.append(m)
        m=deepcopy(catalog);m['units'][0]['member_refs'].pop();mutations.append(m)
        for mutated in mutations:self.assertEqual(check(docs,mutated,rows)['status'],'FAIL_INDEPENDENT_POLICY')

    def test_missing_valid_donor_and_fabricated_context_rejection_fail(self):
        docs,catalog,rows=self.fixture()
        changed=deepcopy(rows);changed[0]['options'][0]['donor_refs'].pop()
        self.assertIn('COMPLETE_POLICY_DECISIONS_MISMATCH',check(docs,catalog,changed)['issues'])
        changed=deepcopy(rows);changed[0]['options']=[];changed[0]['status']='NO_ELIGIBLE_ALTERNATIVE'
        self.assertEqual(check(docs,catalog,changed)['status'],'FAIL_INDEPENDENT_POLICY')
        changed=deepcopy(rows);changed[0]['rejected'].append(dict(donor_ref=catalog['units'][1]['id'],reason='CONTEXT_MISMATCH'))
        self.assertEqual(check(docs,catalog,changed)['status'],'FAIL_INDEPENDENT_POLICY')

    def test_cross_time_refs_cannot_pose_as_simultaneous_source_shape(self):
        docs,catalog,rows=self.fixture();changed=deepcopy(catalog)
        changed['units'][0]['member_refs'][0]=catalog['units'][1]['member_refs'][0]
        self.assertEqual(check(docs,changed,rows)['status'],'FAIL_INDEPENDENT_POLICY')
        changed=deepcopy(catalog);changed['units'][0]['source_geometry']['members'][0][2]='99'
        self.assertEqual(check(docs,changed,rows)['status'],'FAIL_INDEPENDENT_POLICY')

    def test_context_clock_realization_and_boolean_count_corruption_fail(self):
        docs,catalog,rows=self.fixture()
        for field,value in [('musical_context_key','{}'),('onset_q','1'),('refusal_reasons',['FAKE']),('realization',dict(anchor='99',intervals=['0','1','2']))]:
            changed=deepcopy(catalog);changed['units'][0][field]=value
            self.assertEqual(check(docs,changed,rows)['status'],'FAIL_INDEPENDENT_POLICY',field)
        changed=deepcopy(catalog);changed['source_occurrences']=True
        self.assertEqual(check(docs,changed,rows)['status'],'FAIL_INDEPENDENT_POLICY')

    def test_real_joint_shape_rejections_cannot_be_removed_or_relabelled(self):
        docs=documents()
        for m in docs['track-0.json']['measures'][1:]:
            m['voices'][0]['beats'][0]['notes']=[dict(string=3,fret=2),dict(string=2,fret=4),dict(string=1,fret=5)]
        docs,catalog,rows=self.fixture(docs);result=check(docs,catalog,rows)
        self.assertEqual(result['status'],'PASS_INDEPENDENT_POLICY',result)
        index=next(i for i,row in enumerate(rows)if row['rejected'])
        changed=deepcopy(rows);changed[index]['rejected'].pop()
        self.assertEqual(check(docs,catalog,changed)['status'],'FAIL_INDEPENDENT_POLICY')
        changed=deepcopy(rows);changed[index]['rejected'][0]['reason']='FAKE_CONTEXT_REJECTION'
        self.assertEqual(check(docs,catalog,changed)['status'],'FAIL_INDEPENDENT_POLICY')

    def test_no_choices_and_expression_refusals_remain_source_accounted(self):
        docs=documents();docs['track-0.json']['measures']=docs['track-0.json']['measures'][:1]
        docs,catalog,rows=self.fixture(docs);self.assertEqual(check(docs,catalog,rows)['status'],'PASS_INDEPENDENT_POLICY')
        self.assertEqual(rows[0]['status'],'NO_ELIGIBLE_ALTERNATIVE')
        docs=documents();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['bend']={}
        docs,catalog,rows=self.fixture(docs);result=check(docs,catalog,rows)
        self.assertEqual(result['status'],'PASS_INDEPENDENT_POLICY',result)
        self.assertEqual(result['source_units'],3);self.assertLess(result['eligible_units'],3)


if __name__=='__main__':unittest.main()
