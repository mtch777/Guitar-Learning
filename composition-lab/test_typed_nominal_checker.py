"""Independent typed nominal-path oracle: unpitched slots stay in sequence."""
from copy import deepcopy
from fractions import Fraction as F
import json
import unittest
from check_voicing_context import _paths,_nodes
from source_fact_tier1 import extract_documents


def nodes():
    result={}
    for i,p in enumerate((60,None,67)):
        ref=chr(97+i);dead=p is None
        result[ref]=dict(id=ref,part=0,voice=0,string=0,pitch=None if dead else F(p),onset=F(i),duration=F(1),reasons=['UNKNOWN_PITCH','unresolved_sounding_pitch_dead']if dead else[],note_declarations={'dead':True}if dead else{},beat_declarations={},instrument=26,pure_dead_nominal=dead,dead_fret_declaration=dict(present=True,type='int',value=0)if dead else None)
    return result

class TypedPathTests(unittest.TestCase):
    def test_dead_slot_and_bracketing_register_preserved(self):
        source=nodes();old=_paths(source,[]);typed=_paths(source,[],True);r=typed['triple','b']
        self.assertEqual(r['refs'],['a','b','c']);self.assertEqual(r['reasons'],[])
        signature=json.loads(r['signature']);self.assertEqual(signature[0],'typed-nominal-slots/1')
        self.assertEqual(signature[2],['PITCHED','UNPITCHED_DEAD','PITCHED']);self.assertEqual(signature[3],[[0,2,'7']])
        self.assertIn('UNKNOWN_PITCH',old['triple','b']['reasons'])
        changed=deepcopy(source);changed['c']['pitch']+=12
        self.assertNotEqual(r['signature'],_paths(changed,[],True)['triple','b']['signature'])
        shortened=deepcopy(source);del shortened['b']
        self.assertNotEqual(r['signature'],_paths(shortened,[],True)['edge','a']['signature'])
    def test_dead_fret_presence_type_value_are_not_a_pitch(self):
        source=nodes();original=_paths(source,[],True)['triple','b']['signature']
        for declaration in(dict(present=False,type='NoneType',value=None),dict(present=True,type='float',value=0.0),dict(present=True,type='int',value=12)):
            changed=deepcopy(source);changed['b']['dead_fret_declaration']=declaration
            self.assertIsNone(changed['b']['pitch'])
            self.assertNotEqual(original,_paths(changed,[],True)['triple','b']['signature'])
        self.assertEqual(_paths(source,[]),_paths(source,[],False))

    def test_unknown_and_other_execution_never_exempted(self):
        source=nodes();source['b']['pure_dead_nominal']=False
        self.assertIn('UNKNOWN_NOMINAL_SLOT',_paths(source,[],True)['triple','b']['reasons'])
        source=nodes();source['b']['reasons'].append('unresolved_sounding_pitch_slide')
        self.assertIn('unresolved_sounding_pitch_slide',_paths(source,[],True)['triple','b']['reasons'])
        source=nodes();source['b']['reasons'].append('UNCERTAIN_SOURCE_CLOCK')
        self.assertIn('UNCERTAIN_SOURCE_CLOCK',_paths(source,[],True)['triple','b']['reasons'])
        with self.assertRaises(ValueError):_paths(source,[],1)
    def test_maximal_multiple_dead_span_keeps_bracketing_and_unknown(self):
        source=nodes();end=source.pop('c');end.update(id='d',onset=F(3));source['d']=end
        source['c']=deepcopy(source['b']);source['c'].update(id='c',onset=F(2))
        result=_paths(source,[],True);span=result['unpitched_span','b']
        self.assertEqual(span['refs'],['a','b','c','d']);self.assertEqual(span['reasons'],[])
        self.assertNotIn(('unpitched_span','c'),result)
        self.assertEqual(json.loads(span['signature'])[3],[[0,3,'7']])
        changed=deepcopy(source);changed['d']['pitch']+=12
        self.assertNotEqual(span['signature'],_paths(changed,[],True)['unpitched_span','b']['signature'])
        unknown=deepcopy(source);unknown['d'].update(pitch=None,pure_dead_nominal=False,reasons=['UNKNOWN_PITCH'])
        self.assertIn('UNKNOWN_NOMINAL_SLOT',_paths(unknown,[],True)['unpitched_span','b']['reasons'])
        slide=deepcopy(source);slide['d']['reasons']=['unresolved_sounding_pitch_slide']
        self.assertIn('unresolved_sounding_pitch_slide',_paths(slide,[],True)['unpitched_span','b']['reasons'])

    def test_fully_pitched_keys_remain_identical(self):
        source=nodes();source['b'].update(pitch=F(64),reasons=[],note_declarations={},pure_dead_nominal=False)
        self.assertEqual(_paths(source,[]),_paths(source,[],True))


def fixture():
    from test_check_declared_allocation import fixture as original
    docs,after,target,donor=original()
    for d in(docs,after):
        for index in(6,13):
            beat=d['track-0.json']['measures'][index//4]['voices'][0]['beats'][index%4]
            beat.pop('chord');beat['notes']=[dict(string=s,fret=0,dead=True)for s in range(3)]
    return docs,after,target,donor

try:
    import music21
except ImportError:music21=None

@unittest.skipUnless(music21,'Pinned native oracle unavailable')
class TypedAllocationTests(unittest.TestCase):
    def test_authored_positive_requires_typed_opt_in(self):
        from check_declared_allocation import check
        d,a,t,s=fixture();before=extract_documents(d);after=extract_documents(a)
        self.assertEqual(check(before,after,t,s)['status'],'FAIL')
        r=check(before,after,t,s,typed_nominal=True)
        self.assertEqual(r['status'],'PASS_LOCKED_DECLARED_ALLOCATION',r)
        self.assertTrue(r['witness_count']);self.assertTrue(r['typed_nominal'])
        self.assertEqual(check(before,after,t,s,typed_nominal=1)['status'],'FAIL')
    def test_wrong_dead_types_or_contradictory_source_remain_unknown(self):
        from check_declared_allocation import check
        for value in(None,False,1,'true'):
            d,a,t,s=fixture()
            for doc in(d,a):
                for i in(6,13):
                    for n in doc['track-0.json']['measures'][i//4]['voices'][0]['beats'][i%4]['notes']:
                        n['dead']=value;n.pop('fret')
            r=check(extract_documents(d),extract_documents(a),t,s,typed_nominal=True)
            self.assertEqual(r['status'],'FAIL',value)
        d,a,t,s=fixture()
        for doc in(d,a):doc['track-0.json']['measures'][1]['voices'][0]['beats'][2]['notes'][0]['spn']=[4,0,0]
        r=check(extract_documents(d),extract_documents(a),t,s,typed_nominal=True)
        self.assertEqual(r['status'],'FAIL')
    def test_missing_source_bracketing_witness_is_not_skipped(self):
        from check_declared_allocation import check
        d,a,t,s=fixture()
        for doc in(d,a):
            for n in doc['track-0.json']['measures'][3]['voices'][0]['beats'][2]['notes']:n['fret']+=12
        r=check(extract_documents(d),extract_documents(a),t,s,typed_nominal=True)
        self.assertEqual(r['status'],'FAIL');self.assertTrue(any('NO_INDEPENDENT_SOURCE_'in x for x in r['issues']),r)

if __name__=='__main__':unittest.main()
