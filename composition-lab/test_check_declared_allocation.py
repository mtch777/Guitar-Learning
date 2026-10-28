"""Independent raw degree-placement locks and source-motion support."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from check_declared_allocation import check


def fixture():
    a=[8,10,9,7];b=[5,5,5,7]
    beats=[dict(duration=[1,4],chord=dict(text='Am'),notes=[dict(string=s,fret=f)for s,f in enumerate(b if i==12 else a)])for i in range(20)]
    docs={'metadata.json':dict(songId=19,revisionId=1,title='Authored allocation support',artist='Fixture',tracks=[dict(instrumentId=26)]),
        'track-0.json':dict(songId=19,revisionId=1,partId=0,instrumentId=26,tuning=[64,59,55,50,45,40],frets=24,measures=[dict(signature=[4,4],voices=[dict(beats=beats[i:i+4])])for i in range(0,20,4)])}
    after=deepcopy(docs)
    for note,fret in zip(after['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'],b):note['fret']=fret
    target=[f'event:19:0:2:0:1:{i}'for i in range(4)];donor=[f'event:19:0:4:0:0:{i}'for i in range(4)]
    return docs,after,target,donor

try:
    import music21
except ImportError:music21=None

@unittest.skipUnless(music21,'Pinned native music21 evaluation dependency absent')
class IndependentAllocationTests(unittest.TestCase):
    def runcheck(self,d,a,t,s):return check(extract_documents(d),extract_documents(a),t,s)
    def test_actual_member_pcs_can_change_under_same_chord(self):
        d,a,t,s=fixture();r=self.runcheck(d,a,t,s)
        self.assertEqual(r['status'],'PASS_LOCKED_DECLARED_ALLOCATION',r)
        self.assertEqual(len(r['changed_refs']),3)
        self.assertGreater(r['witness_count'],0)
    def test_locked_fields_geometry_and_formula_corruptions(self):
        d,a,t,s=fixture()
        for mode in ('outside','string','metadata','formula','bass','donor','incomplete'):
            b=deepcopy(a);donors=s;targets=t
            beat=b['track-0.json']['measures'][1]['voices'][0]['beats'][1]
            if mode=='outside':b['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret']+=1
            elif mode=='string':beat['notes'][0]['string']=4
            elif mode=='metadata':b['metadata.json']['artist']='changed'
            elif mode=='formula':beat['notes'][0]['fret']=6
            elif mode=='bass':beat['notes'][3]['fret']=19
            elif mode=='donor':donors=t
            else:targets=t[:-1]
            self.assertEqual(self.runcheck(d,b,targets,donors)['status'],'FAIL',mode)
    def test_missing_independent_motion_witness_is_not_waived(self):
        d,a,t,s=fixture()
        # The donor remains, but destroy its A-B-A neighboring support without
        # altering the selected output or swapping the donor itself.
        for i in (11,13):
            for doc in (d,a):
                doc['track-0.json']['measures'][i//4]['voices'][0]['beats'][i%4]['notes'][0]['fret']=9
        r=self.runcheck(d,a,t,s)
        self.assertEqual(r['status'],'FAIL')
        self.assertTrue(any('NO_INDEPENDENT_SOURCE_'in x for x in r['issues']),r)
    def test_execution_and_pitch_declarations_refuse(self):
        for field,value,scope in [('brushStroke',{'direction':'down','duration':30,'shift':100},'beat'),('letRing',True,'beat'),('sustainPedal',True,'beat'),('spn',[4,0,0],'note')]:
            d,a,t,s=fixture()
            for doc in (d,a):
                beat=doc['track-0.json']['measures'][1]['voices'][0]['beats'][1]
                (beat if scope=='beat'else beat['notes'][0])[field]=value
            self.assertEqual(self.runcheck(d,a,t,s)['status'],'FAIL',field)



    def test_earlier_pedal_flag_quarantines_whole_part(self):
        d,a,t,s=fixture()
        for doc in (d,a):doc['track-0.json']['measures'][0]['voices'][0]['beats'][0]['sustainPedal']=True
        r=self.runcheck(d,a,t,s)
        self.assertEqual(r['status'],'FAIL');self.assertTrue(any('pedal'in x for x in r['issues']))
        for doc in (d,a):doc['track-0.json']['measures'][0]['voices'][0]['beats'][0]['sustainPedal']=False
        self.assertEqual(self.runcheck(d,a,t,s)['status'],'PASS_LOCKED_DECLARED_ALLOCATION')
    def test_other_part_unknown_is_retained_without_inventing_pitch(self):
        d,a,t,s=fixture()
        for doc in (d,a):
            doc['metadata.json']['tracks'].append(dict(instrumentId=0))
            piano=deepcopy(doc['track-0.json']);piano.update(partId=1,instrumentId=0,tuning=[0])
            for m in piano['measures']:m['voices'][0]['beats']=[dict(duration=[1,1],notes=[dict(fret=60)])]
            doc['track-1.json']=piano
        r=self.runcheck(d,a,t,s)
        self.assertEqual(r['status'],'PASS_LOCKED_DECLARED_ALLOCATION',r)
        self.assertTrue(r['unchanged_outside_uncertainty_refs'])
        self.assertTrue(r['nominal_contribution']['all_unchanged_context_completions_invariant'])



    def test_presentation_width_is_locked_not_a_pitch_dependency(self):
        d,a,t,s=fixture()
        for doc in (d,a):
            for m in doc['track-0.json']['measures']:
                for beat in m['voices'][0]['beats']:beat['chord']['width']=19.5
        self.assertEqual(self.runcheck(d,a,t,s)['status'],'PASS_LOCKED_DECLARED_ALLOCATION')
        a['track-0.json']['measures'][1]['voices'][0]['beats'][1]['chord']['width']=20
        self.assertEqual(self.runcheck(d,a,t,s)['status'],'FAIL')
        d,a,t,s=fixture()
        for doc in (d,a):doc['track-0.json']['measures'][1]['voices'][0]['beats'][1]['chord']['diagram']={'position':5}
        self.assertEqual(self.runcheck(d,a,t,s)['status'],'FAIL')
    def test_independent_source_proposal_denominator(self):
        from check_declared_allocation import proposal_inventory
        d,a,t,s=fixture();r=proposal_inventory(extract_documents(d))
        self.assertEqual(r['counts'],dict(all_groups=20,declared_groups=20,eligible_groups=20,proposed_links=400,changed_proposed_links=38))
        self.assertEqual(len({(x['target_ref'],x['donor_ref'])for x in r['proposed_links']}),400)
        d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['sustainPedal']=True
        r=proposal_inventory(extract_documents(d));self.assertEqual(r['counts']['eligible_groups'],0);self.assertEqual(r['proposed_links'],[])



    def test_exact_contribution_negatives_not_masked_by_full_union(self):
        from check_declared_allocation import nominal_contribution
        from fractions import Fraction as F
        def n(p,d=1):return dict(pitch=None if p is None else F(p),onset=F(0),duration=F(d),reasons=[],instrument=26)
        before={'a':n(60),'b':n(64),'outside':n(None)}
        after=deepcopy(before);after['a']['pitch']=F(64);after['b']['pitch']=F(60)
        self.assertEqual(nominal_contribution(before,after,['a','b'])['status'],'PASS_EXACT_NOMINAL_CONTRIBUTION')
        # Same aggregate classes at onset cannot cover unequal source note ends.
        before['b']['duration']=F(2);after['b']['duration']=F(2)
        self.assertIn('TARGET_WRITTEN_PC_MULTISET_CHANGED',nominal_contribution(before,after,['a','b'])['issues'])
        before={'a':n(60),'b':n(64),'outsideE':n(64),'outsideG':n(67)}
        after=deepcopy(before);after['b']['pitch']=F(67)
        self.assertIn('TARGET_WRITTEN_PC_MULTISET_CHANGED',nominal_contribution(before,after,['a','b'])['issues'])
        after=deepcopy(before);after['outsideE']['pitch']=F(76)
        self.assertTrue(any('OUTSIDE_NODE_CHANGED'in x for x in nominal_contribution(before,after,['a','b'])['issues']))
        after=deepcopy(before);after['a']['pitch']=None
        self.assertTrue(any('UNKNOWN_SELECTED_PITCH'in x for x in nominal_contribution(before,after,['a','b'])['issues']))

if __name__=='__main__':unittest.main()
