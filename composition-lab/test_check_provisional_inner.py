"""Only geometry evidence is replaced; all musical/source guards stay hard."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from test_check_inner_voicing import fixture
from check_inner_voicing import check,_note
from fretting_contacts import analyze

try:
    import music21
except ImportError:music21=None

def coverage(after,refs):
    rows=[]
    for ref in refs:
        _,_,note=_note(after,ref);rows.append(dict(string=note['string'],fret=note['fret']))
    return analyze(rows)

@unittest.skipUnless(music21,'Pinned native music21 oracle unavailable')
class ProvisionalInnerOracleTests(unittest.TestCase):
    def test_default_exact_and_new_explicit_contact_route(self):
        before,after,target,donor,geometry=fixture();b=extract_documents(before);a=extract_documents(after)
        old=check(b,a,target,donor,geometry)
        self.assertEqual(old['status'],'PASS_LOCKED_INNER_VOICING',old)
        self.assertNotIn('human_playability',old)
        self.assertEqual(check(b,a,target,donor,[])['status'],'FAIL')
        r=check(b,a,target,donor,[],contact_coverage=coverage(after,target))
        self.assertEqual(r['status'],'PASS_PROVISIONAL_INNER_CONTACTS',r)
        self.assertEqual(r['human_playability'],'UNVERIFIED');self.assertEqual(len(r['changed_refs']),2)
        self.assertEqual(old['protected_outer_refs'],r['protected_outer_refs'])
        self.assertEqual(old['nominal_contribution'],r['nominal_contribution'])

    def test_rejects_forged_partial_or_mixed_physical_evidence(self):
        before,after,target,donor,geometry=fixture();b=extract_documents(before);a=extract_documents(after);good=coverage(after,target)
        self.assertEqual(check(b,a,target,donor,geometry,contact_coverage=good)['status'],'FAIL')
        for change in [lambda c:c['covers'].pop(),lambda c:c.update(human_playability='VERIFIED'),
            lambda c:c.update(max_digits=3),lambda c:c['required'][0].update(fret=0),
            lambda c:c.update(status='SEARCH_LIMIT',covers=[],minimum_contacts=None,examined=100000)]:
            bad=deepcopy(good);change(bad)
            self.assertEqual(check(b,a,target,donor,[],contact_coverage=bad)['status'],'FAIL')

    def test_nonphysical_locks_are_not_waived(self):
        for mode in ('outside','outer','string','component','diagram','finger','pedal','brush','held','bound'):
            before,after,target,donor,_=fixture()
            if mode in ('diagram','finger','pedal','brush','held','bound'):
                for docs in (before,after):
                    part=docs['track-0.json'];beat=part['measures'][1]['voices'][0]['beats'][1]
                    if mode=='diagram':beat['chord']['fingers']=[1,2,3]
                    elif mode=='finger':beat['notes'][1]['leftFinger']=2
                    elif mode=='pedal':part['measures'][0]['voices'][0]['beats'][0]['sustainPedal']=True
                    elif mode=='brush':beat['brushStroke']=dict(direction='down',duration=30,shift=100)
                    elif mode=='held':part['measures'][1]['voices'].append(dict(beats=[dict(duration=[1,1],notes=[dict(string=5,fret=3)])]))
                    else:part['frets']=4
            elif mode=='outside':after['metadata.json']['title']='forged'
            elif mode=='outer':after['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0]['fret']+=12
            elif mode=='string':after['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][1]['string']=4
            else:after['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][1]['fret']=6
            report=check(extract_documents(before),extract_documents(after),target,donor,[],contact_coverage=coverage(after,target))
            self.assertEqual(report['status'],'FAIL',(mode,report))

    def test_incident_unknown_dependency_remains_hard(self):
        before,after,target,donor,_=fixture()
        for docs in (before,after):
            docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][1]['slide']=1
        report=check(extract_documents(before),extract_documents(after),target,donor,[],contact_coverage=coverage(after,target))
        self.assertEqual(report['status'],'FAIL',report)

if __name__=='__main__':unittest.main()
