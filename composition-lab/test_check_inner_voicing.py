from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from check_inner_voicing import check,inventory
from test_check_declared_allocation import fixture as old_fixture
try:
    import music21
except ImportError:music21=None


def fixture():
    docs,_,target,donor=old_fixture();g=docs['track-0.json']['measures'][4]['voices'][0]['beats'][0];g.pop('chord')
    for n,f in zip(g['notes'],[6,3,3,5]):n['fret']=f
    after=deepcopy(docs);notes=after['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'];notes[1]['fret']=5;notes[2]['fret']=5
    geom=[f'event:19:0:5:0:0:{i}'for i in range(4)]
    return docs,after,target,donor,geom

@unittest.skipUnless(music21,'Pinned native music21 evaluation oracle absent')
class IndependentInnerTests(unittest.TestCase):
    def runcheck(self,d,a,t,s,g):return check(extract_documents(d),extract_documents(a),t,s,g)
    def test_new_doubling_from_coupled_inner_component(self):
        d,a,t,s,g=fixture();r=self.runcheck(d,a,t,s,g)
        self.assertEqual(r['status'],'PASS_LOCKED_INNER_VOICING',r)
        self.assertEqual(len(r['changed_refs']),2)
        self.assertEqual(set(r['protected_outer_refs']),{t[0],t[3]})
    def test_plain_context_novelty_is_reported_not_a_hard_melody_claim(self):
        d,a,t,s,g=fixture()
        for doc in(d,a):
            for n in doc['track-0.json']['measures'][2]['voices'][0]['beats'][3]['notes']:n['fret']+=12
        r=self.runcheck(d,a,t,s,g)
        self.assertEqual(r['status'],'PASS_LOCKED_INNER_VOICING',r)
        self.assertTrue(r['novel_plain_contexts'])

    def test_outside_outer_strings_formula_and_geometry_locks(self):
        d,a,t,s,g=fixture()
        for mode in('outer','outside','string','formula','geometry','component','partial'):
            b=deepcopy(a);donor=s;geo=g;target=t
            note=b['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes']
            if mode=='outer':note[0]['fret']+=12
            elif mode=='outside':b['metadata.json']['artist']='changed'
            elif mode=='string':note[1]['string']=4
            elif mode=='formula':note[1]['fret']=6
            elif mode=='geometry':geo=s
            elif mode=='component':donor=t
            else:target=t[:-1]
            self.assertEqual(self.runcheck(d,b,target,donor,geo)['status'],'FAIL',mode)
    def test_geometry_neighborhood_and_open_status(self):
        d,a,t,s,g=fixture()
        self.assertEqual(self.runcheck(d,a,t,s,t)['status'],'FAIL')
        # Same relative fret shape but an open source string may not slide closed.
        for doc in(d,a):
            source=doc['track-0.json']['measures'][4]['voices'][0]['beats'][0]['notes']
            for n,f in zip(source,[3,0,0,2]):n['fret']=f
        r=self.runcheck(d,a,t,s,g);self.assertEqual(r['status'],'FAIL');self.assertIn('GEOMETRY_OPEN_STATUS_CHANGED',r['issues'])
    def test_same_part_extra_held_note_and_execution_refuse(self):
        for mode in('held','brush','finger','pedal'):
            d,a,t,s,g=fixture()
            for doc in(d,a):
                part=doc['track-0.json'];beat=part['measures'][1]['voices'][0]['beats'][1]
                if mode=='held':part['measures'][1]['voices'].append(dict(beats=[dict(duration=[1,1],notes=[dict(string=5,fret=5)])]))
                elif mode=='brush':beat['brushStroke']={'direction':'down','duration':30,'shift':100}
                elif mode=='finger':beat['notes'][1]['leftFinger']=2
                else:part['measures'][0]['voices'][0]['beats'][0]['sustainPedal']=True
            self.assertEqual(self.runcheck(d,a,t,s,g)['status'],'FAIL',mode)
    def test_all_extreme_unisons_protected_and_inventory_complete(self):
        d,a,t,s,g=fixture();r=inventory(extract_documents(d))
        self.assertEqual(r['counts']['declared_groups'],19);self.assertEqual(r['counts']['raw_geometry_groups'],20)
        self.assertEqual(len({(p['target_ref'],p['donor_ref'])for p in r['component_links']}),len(r['component_links']))
        unit=next(u for u in r['units']if u['id']==t[0]);self.assertEqual(unit['outer_refs'],[t[0],t[3]])
        for doc in(d,a):doc['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][1]['fret']=13 # A4 -> C5 samehighest as string0
        r=inventory(extract_documents(d));unit=next(u for u in r['units']if u['id']==t[0]);self.assertEqual(set(unit['outer_refs']),{t[0],t[1],t[3]})
    def test_pitch_order_reversal_is_not_voice_inference(self):
        d,a,t,s,g=fixture()
        # Swapping the coupled source pitches is a crossing, even if both remain
        # strictly inside the protected envelope and full formula survives.
        for doc in(d,a):
            source=doc['track-0.json']['measures'][3]['voices'][0]['beats'][0]['notes'];source[1]['fret']=1;source[2]['fret']=9 # C4,E4
        n=a['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'];n[1]['fret']=1;n[2]['fret']=9
        r=self.runcheck(d,a,t,s,g);self.assertEqual(r['status'],'FAIL');self.assertIn('INNER_PITCH_ORDER_REVERSED',r['issues'])




class IndependentOverlapTests(unittest.TestCase):
    def test_point_on_lower_boundary_and_half_open_upper(self):
        from fractions import Fraction as F
        from check_inner_voicing import _overlap,_overlap_index,_has_outside_overlap
        rows={'a':dict(part=0,onset=F(1),duration=F(1)),'point':dict(part=0,onset=F(1),duration=F(0)),'end':dict(part=0,onset=F(2),duration=F(0)),'old':dict(part=0,onset=F(0),duration=F(1))}
        self.assertEqual(_overlap(rows,['a']),['point'])
        self.assertTrue(_has_outside_overlap(rows,['a'],_overlap_index(rows)))
        del rows['point'];self.assertFalse(_has_outside_overlap(rows,['a'],_overlap_index(rows)))
    def test_interval_index_matches_literal_rational_scan(self):
        import random
        from fractions import Fraction as F
        from check_inner_voicing import _overlap,_overlap_index,_has_outside_overlap
        rng=random.Random(33)
        rows={str(i):dict(part=i%2,onset=F(rng.randrange(24),4),duration=F(rng.randrange(5),4))for i in range(70)}
        index=_overlap_index(rows)
        for i in range(70):
            refs=[str(i)]
            self.assertEqual(_has_outside_overlap(rows,refs,index),bool(_overlap(rows,refs)))

if __name__=='__main__':unittest.main()
