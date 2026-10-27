"""Independent candidate-after source-lock and lane-context checks."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from test_voicing_context_relations import documents
from check_voicing_context import check


def fixture(docs=None):
    docs=documents()if docs is None else docs
    after=deepcopy(docs)
    after['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][1]['fret']=21
    refs=['event:39:0:1:0:3:'+str(i)for i in range(3)]
    return docs,after,refs,['event:39:0:3:0:3:0']


def joint_fixture():
    docs=documents()
    docs['track-0.json']['measures']=[deepcopy(bar)for _ in range(2)for bar in docs['track-0.json']['measures']]
    for mi,bar in enumerate(docs['track-0.json']['measures']):
        for bi,beat in enumerate(bar['voices'][0]['beats']):
            at=mi*4+bi
            beat['notes']=[dict(string=2,fret=9)]if at!=19 else []
            if at in(0,1,5,9,16,17,21,25):beat['notes'].append(dict(string=0,fret=12))
            if at in(3,19):
                beat['notes']=[dict(string=3,fret=10),dict(string=2,fret=9)if at==3 else dict(string=0,fret=12),dict(string=1,fret=8)]
    after=deepcopy(docs)
    after['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][1]=dict(string=0,fret=12)
    return docs,after,['event:39:0:1:0:3:'+str(i)for i in range(3)],['event:39:0:5:0:3:0']


class IndependentContextTests(unittest.TestCase):
    def runcheck(self,docs,after,refs,donors):return check(extract_documents(docs),extract_documents(after),refs,donors)

    def test_positive_and_original_choice_zero_identity(self):
        docs,after,refs,donors=fixture();report=self.runcheck(docs,after,refs,donors)
        self.assertEqual(report['status'],'PASS_INDEPENDENT_VOICING_CONTEXT',report)
        self.assertEqual(report['witness_count'],5)
        # Coincident observed choice is valid, never forced different.
        zero=self.runcheck(docs,docs,refs,[refs[0]])
        self.assertEqual(zero['status'],'FAIL_INDEPENDENT_VOICING_CONTEXT') # target cannot be donor
        original=deepcopy(docs);original['track-0.json']['measures'][2]['voices'][0]['beats'][3]['notes'][1]['fret']=9
        zero=self.runcheck(original,original,refs,donors)
        self.assertEqual(zero['status'],'PASS_INDEPENDENT_VOICING_CONTEXT',zero)
        self.assertEqual(zero['changed_refs'],[])

    def test_source_nonpitch_collision_and_wrong_donor_cannot_pass(self):
        docs,after,refs,donors=fixture()
        for mode in ('string','pc','metadata','donor'):
            value=deepcopy(after);chosen=donors
            if mode=='string':value['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][1]['string']=3
            elif mode=='pc':value['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][1]['fret']=20
            elif mode=='metadata':value['metadata.json']['artist']='Changed'
            else:chosen=[refs[0]]
            self.assertEqual(self.runcheck(docs,value,refs,chosen)['status'],'FAIL_INDEPENDENT_VOICING_CONTEXT',mode)

    def test_missing_string_does_not_invent_known_other_instrument_pitch(self):
        docs=documents();docs['metadata.json']['tracks'].append(dict(instrumentId=0))
        part=deepcopy(docs['track-0.json']);part.update(partId=1,instrumentId=0,tuning=[0])
        for bar in part['measures']:bar['voices'][0]['beats']=[dict(duration=[1,1],notes=[dict(fret=60)])]
        docs['track-1.json']=part
        docs,after,refs,donors=fixture(docs)
        result=self.runcheck(docs,after,refs,donors)
        self.assertEqual(result['status'],'FAIL_INDEPENDENT_VOICING_CONTEXT',result)
        self.assertIn('UNKNOWN_VERTICAL_PITCH_OR_EXECUTION',result['issues'])

    def test_unknown_lane_long_overlap_quarantines_adjacency(self):
        docs=documents();beat=docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]
        beat['notes'].append(dict(fret=1))
        # Place the unknown-lane occurrence before the affected window and hold
        # its nominal duration into it. Conflicting source time also refuses.
        beat['duration']=[1,1]
        docs,after,refs,donors=fixture(docs)
        self.assertEqual(self.runcheck(docs,after,refs,donors)['status'],'FAIL_INDEPENDENT_VOICING_CONTEXT')

    def test_joint_rewiring_positive_and_explicit_permission(self):
        docs,after,refs,donors=joint_fixture();a=extract_documents(docs);b=extract_documents(after)
        self.assertEqual(check(a,b,refs,donors)['status'],'FAIL_INDEPENDENT_VOICING_CONTEXT')
        result=check(a,b,refs,donors,allow_string_changes=True)
        self.assertEqual(result['status'],'PASS_INDEPENDENT_VOICING_CONTEXT',result)
        self.assertGreater(result['witness_count'],5)
        for bad in(1,None,'yes'):
            self.assertEqual(check(a,b,refs,donors,allow_string_changes=bad)['status'],'FAIL_INDEPENDENT_VOICING_CONTEXT')

    def test_joint_old_reconnection_new_lane_occupancy_and_pins(self):
        for mode in('old_connection','new_connection','occupied','pin'):
            docs,after,refs,donors=joint_fixture()
            if mode=='old_connection':
                for source in(docs,after):source['track-0.json']['measures'][5]['voices'][0]['beats'][0]['notes'][0]['fret']=10
            elif mode=='new_connection':
                for source in(docs,after):source['track-0.json']['measures'][4]['voices'][0]['beats'][1]['notes'][-1]['fret']=13
            elif mode=='occupied':
                for source in(docs,after):source['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'].append(dict(string=0,fret=9))
            else:
                for source in(docs,after):source['track-0.json']['measures'][0]['voices'][0]['beats'][2]['notes'][0]['hp']=True
            result=check(extract_documents(docs),extract_documents(after),refs,donors,allow_string_changes=True)
            self.assertEqual(result['status'],'FAIL_INDEPENDENT_VOICING_CONTEXT',(mode,result))

    def test_empty_old_lane_requires_supported_boundary_contract(self):
        docs,after,refs,donors=joint_fixture()
        for mi,bar in enumerate(docs['track-0.json']['measures']):
            for bi,beat in enumerate(bar['voices'][0]['beats']):
                if(mi,bi)!=(0,3):beat['notes']=[n for n in beat['notes']if n.get('string')!=2]
        after=deepcopy(docs);after['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][1]=dict(string=0,fret=12)
        result=check(extract_documents(docs),extract_documents(after),refs,donors,allow_string_changes=True)
        self.assertIn('EMPTY_OLD_LANE_BOUNDARY_UNSUPPORTED',result['issues'])


if __name__=='__main__':unittest.main()
