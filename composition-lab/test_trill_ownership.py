from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from test_check_declared_allocation import fixture
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize
from technique_observation_relations import lift,realize as restore_observations


class TrillOwnershipTests(unittest.TestCase):
    def test_trill_fields_are_owned_once_and_exact_in_actual_worker(self):
        docs,_,_,_=fixture();note=docs['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][1];note['trill']=dict(auxiliaryFret=5,speed=65)
        lower=extract_documents(docs);full=analyze(lower,declared_chords=True);upper=strip_lower(full);self.assertFalse(upper['unsupported'])
        from check_technique_connections import check
        result=check(docs,full);self.assertFalse(result['issues'],result)
        self.assertEqual(result['counts']['trill_persisted_declarations'],1)
        bad=deepcopy(full);bad['owned_parameters']['technique_declarations']['groups']=[g for g in bad['owned_parameters']['technique_declarations']['groups'] if g['field']!='trill']
        self.assertIn('Technique declaration root inventory/uniqueness differs',check(docs,bad)['issues'])
        self.assertEqual(project_documents(realize(upper)),docs)
        observed=lift(lower);g=next(g for g in observed['groups'] if g['field']=='trill')
        self.assertEqual([p['parameter']['normalized'] for p in g['parameters']],['5','65']);self.assertTrue(all(p['unit']=='1' for p in g['parameters']))
        self.assertEqual(g['scope'],'note');self.assertNotIn('value',str(g['structure']))
        actual=restore_observations(dict(schema=observed['schema'],groups=[g],unsupported=[]))
        self.assertEqual([r for r in lower['facts'] if r['id'] in {x['id'] for x in actual}],actual)
        from voicing_context_relations import graph
        from check_voicing_context import _nodes
        ref='event:19:0:2:0:1:1'
        self.assertIn('unresolved_sounding_pitch_trill',graph(lower)['nodes'][ref]['reasons'])
        self.assertIn('unresolved_sounding_pitch_trill',_nodes(lower)[2][ref]['reasons'])
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as tmp:
            result=execute(code,upper,dict(variation=0),lower,Path(tmp)/'zero',timeout=30)
            self.assertEqual(result['status'],'PASS',result)

    def test_absent_partial_empty_and_typed_malformed_declarations(self):
        for value in ({},dict(auxiliaryFret=5),dict(speed=65)):
            docs,_,_,_=fixture();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['trill']=value
            lower=extract_documents(docs);upper=strip_lower(analyze(lower,declared_chords=True));self.assertFalse(upper['unsupported']);self.assertEqual(realize(upper),lower)
        for value in (False,None,[],5,dict(auxiliaryFret=True),dict(speed=65.0),dict(speed='65'),dict(hiddenNotes=[60])):
            docs,_,_,_=fixture();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['trill']=value
            upper=analyze(extract_documents(docs));self.assertTrue(upper['unsupported'],value)
        docs,_,_,_=fixture();self.assertFalse(any(g['field']=='trill' for g in lift(extract_documents(docs))['groups']))

    def test_trill_cannot_be_used_as_plain_inner_component_or_neighbor(self):
        from test_inner_voicing import fixture as inner_fixture,analyzed
        from inner_voicing import options
        for place in ('target','donor','neighbor','geometry'):
            docs,refs,_=inner_fixture();mi,bi,ni={'target':(1,1,1),'donor':(3,0,1),'neighbor':(1,0,1),'geometry':(4,2,1)}[place]
            docs['track-0.json']['measures'][mi]['voices'][0]['beats'][bi]['notes'][ni]['trill']=dict(auxiliaryFret=5,speed=65)
            _,upper,c=analyzed(docs);result=options(upper,refs[0],c)
            self.assertFalse(any(o['changed'] for o in result['options']),place)


if __name__=='__main__':unittest.main()
