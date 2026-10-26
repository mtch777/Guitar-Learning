"""Actual family edits checked independently of producer choices and equations."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,realize
from voicing_register import inventory,intervene
from check_joint_fingering import check
from test_joint_fingering import documents


def family_documents():
    docs=documents();part=docs['track-0.json'];tuning=part['tuning']
    for bar,pitches in zip(part['measures'],([64,67,71],[66,81,73],[68,71,75])):
        bar['voices'][0]['beats'][0]['notes']=[dict(string=s,fret=p-tuning[s])for p,s in zip(pitches,[1,2,3])]
    return docs


class FamilyChangedOutputTests(unittest.TestCase):
    def fixture(self):
        lower=extract_documents(family_documents());upper=strip_lower(analyze(lower,families=True))
        catalog=inventory(lower,'transposed_voicing_family')
        controls=dict(voicing=100,register=0,physical=100,target_ref=catalog['units'][0]['id'],seed=9427,context_policy='transposed_voicing_family')
        return lower,upper,controls

    def test_actual_family_change_same_inverse_and_independent_witness(self):
        before,upper,controls=self.fixture();edited,decision=intervene(upper,controls);after=realize(edited)
        report=check(before,after,controls,decision)
        self.assertEqual(report['status'],'PASS_LOCKED_DIMENSIONS',report)
        self.assertTrue(decision['changed'])
        self.assertEqual(len(report['changed_source_paths']),1)

    def test_zero_and_separate_locks_all_fixed_seeds(self):
        before,upper,controls=self.fixture()
        for voicing,physical in ((0,0),(0,100),(100,0),(50,50),(100,100)):
            for seed in range(9427,9447):
                c=dict(controls,voicing=voicing,physical=physical,seed=seed)
                edited,decision=intervene(upper,c)
                report=check(before,realize(edited),c,decision)
                self.assertEqual(report['status'],'PASS_LOCKED_DIMENSIONS',report)

    def test_corrupt_actual_locks_seed_witness_and_controls(self):
        before,upper,controls=self.fixture();edited,decision=intervene(upper,controls);after=realize(edited)
        for mode in ('unselected','string','pitch','decision','weight','seed','register','bool'):
            actual=deepcopy(after);d=deepcopy(decision);c=deepcopy(controls)
            if mode=='unselected':next(r for r in actual['facts']if r['id'].endswith('/artist'))['value']='Changed'
            elif mode=='string':next(r for r in actual['facts']if r['id'].endswith('/measures/0/voices/0/beats/0/notes/0/string'))['value']=0
            elif mode=='pitch':next(r for r in actual['facts']if r['id'].endswith('/measures/0/voices/0/beats/0/notes/0/fret'))['value']+=1
            elif mode=='decision':d['chosen']['donor_refs']=[]
            elif mode=='weight':d['eligible_donor_units']=999
            elif mode=='seed':d['released']['register']=True
            elif mode=='register':c['register']=100
            elif mode=='bool':d['changed']=1
            with self.subTest(mode=mode):self.assertEqual(check(before,actual,c,d)['status'],'FAIL_LOCKED_DIMENSIONS')


if __name__=='__main__':unittest.main()
