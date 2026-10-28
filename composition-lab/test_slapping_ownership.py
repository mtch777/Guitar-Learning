"""Observed beat declaration: preserve it, pin execution, do not invent audio."""
from pathlib import Path
import tempfile
import unittest
from test_execution_dependencies import documents,n
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize
from execution_dependencies import build
from check_execution_dependencies import expected
from voicing_register import effect_reasons


class SlappingTests(unittest.TestCase):
    def test_literal_presence_and_execution_scope(self):
        for present,value in ((False,None),(True,False),(True,True)):
            docs=documents([n(0),n(2),n(4),n(5)])
            beat=docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]
            beat['notes'].append(dict(string=4,fret=2))
            if present:beat['slapping']=value
            lower=extract_documents(docs);upper=strip_lower(analyze(lower));self.assertEqual(project_documents(realize(upper)),docs)
            owned=[x for x in upper['owned_parameters']['source_choices'] if x['fact_ref'].endswith('/slapping')]
            self.assertEqual(len(owned),int(present))
            if owned:self.assertEqual(owned[0]['owner'],'source_beat_execution_declaration')
            graph=build(lower);self.assertEqual(graph,expected(lower))
            self.assertEqual(graph['pinned_members'],['event:86:0:1:0:0:0','event:86:0:1:0:0:1'] if value is True else [])
            self.assertEqual('BEAT_DEPENDENCY:slapping'in effect_reasons(beat,beat['notes'][0]),value is True)
            if value is True:self.assertIsNone(graph['edges'][0]['semantics']['performed_attack'])

    def test_unknown_types_refused(self):
        for value in (None,0,1,1.0,'true',[],{}):
            docs=documents([n(0),n(2),n(4),n(5)],{0:dict(slapping=value)})
            upper=strip_lower(analyze(extract_documents(docs)))
            self.assertTrue(upper['unsupported'])
            with self.assertRaises(ValueError):realize(upper)

    def test_actual_isolated_reconstruction(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower=extract_documents(documents([n(0),n(2),n(4),n(5)],{0:dict(slapping=True)}))
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as tmp:
            result=execute(code,strip_lower(analyze(lower)),dict(variation=0),lower,Path(tmp)/'zero',timeout=30)
            self.assertEqual(result['status'],'PASS',result)


if __name__=='__main__':unittest.main()
