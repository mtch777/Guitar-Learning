from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from check_context_membership import expected,assess,check

REF='event:92:0:1:0:0:0'
def documents(backgrounds=None):
    backgrounds=backgrounds or [([1,1],[48,52,55])]
    beats=[];tuning=[]
    for duration,values in backgrounds:
        offset=len(tuning);tuning+=values;beats.append(dict(duration=duration,notes=[dict(string=offset+i,fret=0)for i in range(len(values))]))
    parts=[dict(songId=92,revisionId=1,partId=0,instrumentId=25,tuning=[60],measures=[dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=[dict(string=0,fret=2)])])])]),
           dict(songId=92,revisionId=1,partId=1,instrumentId=25,tuning=tuning,measures=[dict(signature=[4,4],voices=[dict(beats=beats)])])]
    return {'metadata.json':dict(songId=92,revisionId=1,title='Membership contrast',artist='Authored',tracks=[dict(instrumentId=25),dict(instrumentId=25)]),**{f'track-{i}.json':p for i,p in enumerate(parts)}}
def facts(docs):return extract_documents(docs)
def request(refs=None,scope='ensemble_minus_edited'):return dict(edited_refs=sorted(refs or [REF]),scope=scope)
def changed(docs,fret):
    d=deepcopy(docs);d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret']=fret;return facts(d)

class IndependentMembershipTests(unittest.TestCase):
 def test_supported_and_contradicted_actual_raw_pitch_changes(self):
    d=documents();before=facts(d);packet=expected(before,request())['packet'];self.assertIsNotNone(packet)
    self.assertEqual(assess(before,packet)['status'],'SUPPORTED')
    self.assertEqual(assess(changed(d,14),packet)['status'],'SUPPORTED')
    self.assertEqual(assess(changed(d,0),packet)['status'],'CONTRADICTED')
    self.assertEqual(check(before,changed(d,0),packet,dict(status='CONTRADICTED'))['issues'],[])
 def test_held_note_mixed_temporal_results_are_ambiguous(self):
    d=documents([([1,2],[48,52,55]),([1,2],[55,59,62])]);before=facts(d);packet=expected(before,request())['packet']
    self.assertEqual(len(packet['contexts']),2)
    self.assertEqual([c['memberships'][0]['values']for c in packet['contexts']],[[False],[True]])
    self.assertEqual(assess(changed(d,7),packet)['status'],'AMBIGUOUS')
 def test_root_ambiguity_does_not_create_membership_ambiguity(self):
    before=facts(documents([([1,1],[48,52,55,57])]))
    packet=expected(before,request())['packet'];self.assertEqual(len(packet['contexts'][0]['hypotheses']),2)
    self.assertEqual(packet['contexts'][0]['memberships'][0]['values'],[False,False])
 def test_entire_edit_set_excluded(self):
    d=documents();notes=d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'];notes.append(dict(string=1,fret=4));d['track-0.json']['tuning'].append(60)
    refs=[REF,'event:92:0:1:0:0:1'];packet=expected(facts(d),request(refs))['packet']
    self.assertFalse(set(refs)&set(packet['contexts'][0]['support_refs']))
    self.assertEqual(len(packet['contexts'][0]['memberships']),2)
 def test_missing_is_not_nonmember_and_scope_is_explicit(self):
    d=documents();before=facts(d);packet=expected(before,request())['packet']
    d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['dead']=True
    self.assertEqual(assess(facts(d),packet)['status'],'MISSING')
    self.assertEqual(expected(before,request(scope='focal_part_minus_edited'))['status'],'MISSING')
 def test_unqualified_support_and_incomplete_coverage(self):
    d=documents();d['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['dead']=True
    self.assertEqual(expected(facts(d),request())['status'],'MISSING')
    d=documents();d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['duration']=[5,4]
    self.assertEqual(expected(facts(d),request())['status'],'MISSING')
 def test_context_change_and_complete_packet_corruption(self):
    d=documents();before=facts(d);packet=expected(before,request())['packet'];d['track-1.json']['tuning']=[48,51,55]
    self.assertEqual(assess(facts(d),packet)['status'],'MISSING')
    for mutate in [lambda p:p['contexts'].clear(),lambda p:p['contexts'][0]['support_refs'].pop(),lambda p:p['contexts'][0]['memberships'][0]['values'].__setitem__(0,0),lambda p:p['contexts'][0]['memberships'][0]['values'].__setitem__(0,True),lambda p:p['contexts'][0]['hypotheses'][0].__setitem__('root_pc',True)]:
        bad=deepcopy(packet);mutate(bad);self.assertEqual(check(before,before,bad)['status'],'FAIL')
 def test_strict_request_and_half_open_support_boundary(self):
    before=facts(documents([([1,2],[48,52,55]),([1,2],[55,59,62])]))
    packet=expected(before,request())['packet'];a,b=packet['contexts'];self.assertEqual(a['end_q'],b['start_q'])
    self.assertFalse(set(a['included_refs'])&set(b['included_refs']))
    self.assertEqual(expected(before,dict(edited_refs=['missing'],scope='ensemble_minus_edited'))['status'],'MISSING')
    for bad in [dict(edited_refs=[REF,REF],scope='ensemble_minus_edited'),dict(edited_refs=[REF],scope=True)]:
        with self.assertRaises(ValueError):expected(before,bad)
 def test_redistributed_boolean_vector_cannot_change_row_denominators(self):
    d=documents([([1,1],[48,52,55,57])]);d['track-0.json']['tuning'].append(60)
    d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'].append(dict(string=1,fret=4))
    before=facts(d);packet=expected(before,request([REF,'event:92:0:1:0:0:1']))['packet']
    rows=packet['contexts'][0]['memberships'];rows[0]['values'].append(rows[1]['values'].pop(0))
    self.assertEqual(check(before,before,packet)['status'],'FAIL')
if __name__=='__main__':unittest.main()
