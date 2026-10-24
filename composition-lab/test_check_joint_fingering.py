"""Independent joint-choice denominator and raw-output corruption checks."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize
from voicing_register import inventory,intervene,empirical_options
from check_voicing_policy import check as policy_check
from check_joint_fingering import check
from test_joint_fingering import documents


POLICY='joint_source_fingering'


def reported(catalog):
    rows=[]
    for target in catalog['units']:
        if target['refusal_reasons']:continue
        r=empirical_options(catalog,target['id'],POLICY)
        rows.append(dict(target_ref=target['id'],status=r['status'],levels=r['levels'],rejected=r['rejected'],options=r['options']))
    return rows


class IndependentJointFingeringTests(unittest.TestCase):
    def fixture(self,docs=None,**settings):
        docs=documents()if docs is None else docs;lower=extract_documents(docs);upper=strip_lower(analyze(lower));catalog=inventory(lower,POLICY)
        controls=dict(voicing=0,register=0,physical=100,target_ref=catalog['units'][0]['id'],seed=9427,context_policy=POLICY);controls.update(settings)
        edited,decision=intervene(upper,controls);return docs,lower,catalog,controls,decision,realize(edited)

    def test_complete_source_choices_and_physical_only_output_pass(self):
        docs,lower,catalog,c,d,after=self.fixture()
        self.assertEqual(policy_check(docs,catalog,reported(catalog),policy=POLICY)['status'],'PASS_INDEPENDENT_POLICY')
        r=check(lower,after,c,d);self.assertEqual(r['status'],'PASS_LOCKED_DIMENSIONS',r)
        self.assertEqual(len(r['changed_source_paths']),6);self.assertEqual(r['source_joint_witnesses'],1)

    def test_zero_and_separate_release_locks_and_joint_choices(self):
        for settings in (dict(physical=0),dict(physical=0,voicing=100,register=100),dict(physical=100,voicing=100,register=100),dict(physical=50,voicing=50,register=50)):
            _,lower,_,c,d,after=self.fixture(**settings)
            self.assertEqual(check(lower,after,c,d)['status'],'PASS_LOCKED_DIMENSIONS')

    def test_whole_source_timing_metadata_and_nonselected_notes_lock(self):
        _,lower,_,c,d,after=self.fixture()
        for kind in ('metadata','duration','unselected'):
            docs=project_documents(after)
            if kind=='metadata':docs['metadata.json']['title']='Forbidden'
            elif kind=='duration':docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['duration']=[1,2]
            else:docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0]['fret']+=1
            self.assertEqual(check(lower,extract_documents(docs),c,d)['status'],'FAIL_LOCKED_DIMENSIONS',kind)

    def test_wrong_pitch_string_type_or_missing_provenance_fails(self):
        _,lower,_,c,d,after=self.fixture()
        for kind in ('fret','string','boolean_string'):
            docs=project_documents(after);n=docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]
            if kind=='fret':n['fret']+=1
            elif kind=='string':n['string']=0
            else:n['string']=False
            self.assertEqual(check(lower,extract_documents(docs),c,d)['status'],'FAIL_LOCKED_DIMENSIONS',kind)
        for kind in ('donor','seed','release','member_refs'):
            bad=deepcopy(d)
            if kind=='donor':bad['chosen']['donor_refs']=[]
            elif kind=='seed':bad['chosen']['realization']['anchor']='99'
            elif kind=='release':bad['released']['physical']=False
            else:bad['member_refs']=list(reversed(bad['member_refs']))
            self.assertEqual(check(lower,after,c,bad)['status'],'FAIL_LOCKED_DIMENSIONS',kind)

    def test_duplicate_pitch_correspondence_is_not_just_unordered_geometry(self):
        docs=documents();tuning=docs['track-0.json']['tuning']
        for i,strings in enumerate(([0,1,2],[1,2,3])):
            docs['track-0.json']['measures'][i]['voices'][0]['beats'][0]['notes']=[dict(string=s,fret=p-tuning[s])for p,s in zip((64,64,67),strings)]
        _,lower,_,c,d,after=self.fixture(docs)
        self.assertEqual(check(lower,after,c,d)['status'],'PASS_LOCKED_DIMENSIONS')
        changed=project_documents(after);notes=changed['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes']
        notes[0],notes[1]=notes[1],notes[0]
        # Same pitch multiset and joint physical shape; declared member mapping differs.
        self.assertEqual(check(lower,extract_documents(changed),c,d)['status'],'FAIL_LOCKED_DIMENSIONS')

    def test_reported_change_and_release_flags_are_strict_booleans(self):
        _,lower,_,c,d,after=self.fixture(physical=0)
        self.assertFalse(d['changed'])
        for value in (True,0,None):
            corrupted=deepcopy(d);corrupted['changed']=value
            self.assertEqual(check(lower,after,c,corrupted)['status'],'FAIL_LOCKED_DIMENSIONS')
        _,lower,_,c,d,after=self.fixture()
        for mutation in ('changed','release','denominator'):
            corrupted=deepcopy(d)
            if mutation=='changed':corrupted['changed']=1
            elif mutation=='release':corrupted['released']['physical']=1
            else:corrupted['eligible_donor_units']=True
            self.assertEqual(check(lower,after,c,corrupted)['status'],'FAIL_LOCKED_DIMENSIONS')

    def test_independent_occupied_strings_donor_omission_and_bounds(self):
        docs=documents()
        for m in docs['track-0.json']['measures']:m['voices'].append(dict(beats=[dict(duration=[1,4],notes=[]),dict(duration=[3,4],notes=[dict(string=3,fret=20)])]))
        lower=extract_documents(docs);catalog=inventory(lower,POLICY);rows=reported(catalog)
        self.assertEqual(policy_check(docs,catalog,rows,policy=POLICY)['status'],'PASS_INDEPENDENT_POLICY')
        corrupted=deepcopy(catalog);corrupted['units'][0]['occupied_strings']=[]
        self.assertEqual(policy_check(docs,corrupted,rows,policy=POLICY)['status'],'FAIL_INDEPENDENT_POLICY')
        docs,lower,catalog,c,d,after=self.fixture();rows=reported(catalog)
        corrupted=deepcopy(rows);corrupted[0]['options'][0]['donor_refs']=[]
        self.assertEqual(policy_check(docs,catalog,corrupted,policy=POLICY)['status'],'FAIL_INDEPENDENT_POLICY')
        corrupted=deepcopy(catalog);corrupted['units'][0]['declared_frets']=True
        self.assertEqual(policy_check(docs,corrupted,rows,policy=POLICY)['status'],'FAIL_INDEPENDENT_POLICY')
        docs=documents();docs['track-0.json']['frets']=15;catalog=inventory(extract_documents(docs),POLICY)
        self.assertEqual(policy_check(docs,catalog,reported(catalog),policy=POLICY)['status'],'PASS_INDEPENDENT_POLICY')
        self.assertTrue(any(x['reason']=='INVALID_OBSERVED_FRET'for x in reported(catalog)[0]['rejected']))


if __name__=='__main__':unittest.main()
