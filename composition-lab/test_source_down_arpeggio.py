"""Integer roll-direction declarations: exact ownership, unknown numeric units."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from test_source_arpeggio_ownership import documents
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,reconstruct
from check_technique_connections import check


def source(value):
    docs=documents();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['downArpeggio']=value
    return docs


class DownArpeggioSourceTests(unittest.TestCase):
    def test_exact_integer_presence_without_rolled_timing_invention(self):
        for value in (0,1,57,-1):
            docs=source(value);lower=extract_documents(docs);upper=analyze(lower)
            self.assertFalse(upper['unsupported'])
            self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)
            groups=[g for g in upper['owned_parameters']['technique_declarations']['groups']if g['field']=='downArpeggio']
            self.assertEqual(len(groups),1);self.assertEqual(groups[0]['scope'],'beat')
            self.assertTrue(all(p['unit']=='1'for p in groups[0]['parameters']))
            self.assertEqual(check(docs,upper)['status'],'PASS_SOURCE_BACKED_RELATIONSHIPS')
            self.assertEqual({g['onset_q']for g in upper['musical_relationships']['coattacks']},{'0'})
            self.assertEqual([m['duration_q']for g in upper['musical_relationships']['coattacks']for m in g['members']],['4']*3)

    def test_absence_and_unknown_types(self):
        upper=analyze(extract_documents(documents()))
        self.assertFalse(any(g['field']=='downArpeggio'for g in upper['owned_parameters']['technique_declarations']['groups']))
        for value in (True,False,None,1.0,'down',{},[],dict(notes=[60])):
            upper=analyze(extract_documents(source(value)))
            self.assertTrue(upper['unsupported'],value)
            with self.assertRaises(ValueError):reconstruct(strip_lower(upper),dict(variation=0))

    def test_independent_source_inventory_omission_duplicate_and_tamper(self):
        docs=source(57);upper=analyze(extract_documents(docs))
        for mode in ('omit','duplicate','tamper'):
            changed=deepcopy(upper);groups=changed['owned_parameters']['technique_declarations']['groups'];i=next(i for i,g in enumerate(groups)if g['field']=='downArpeggio')
            if mode=='omit':groups.pop(i)
            elif mode=='duplicate':groups.append(deepcopy(groups[i]))
            else:groups[i]['parameters'][0]['parameter']['normalized']='58'
            self.assertEqual(check(docs,changed)['status'],'FAIL',mode)

    def test_actual_isolated_complete_inverse(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower=extract_documents(source(57));upper=strip_lower(analyze(lower));code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as temp:
            result=execute(code,upper,dict(variation=0),lower,Path(temp)/'worker',timeout=30)
        self.assertEqual(result['status'],'PASS',result)

    def test_literal_dependency_signature_zero_and_unknown_execution(self):
        from execution_dependencies import build
        from check_execution_dependencies import check as check_graph
        from check_voicing_policy import _source_units
        for value in (0,1,-1,57):
            docs=source(value);lower=extract_documents(docs);graph=build(lower)
            self.assertEqual(check_graph(lower,graph)['status'],'PASS_INDEPENDENT_EXECUTION_DEPENDENCIES')
            declaration=next(d for d in graph['signature']['declarations']if d['source_fact_ref'].endswith('/downArpeggio'))
            self.assertEqual(declaration['value'],value)
            edges=[e for e in graph['edges']if e['kind']=='downArpeggio']
            self.assertEqual(len(edges),0 if value==0 else 1)
            units=_source_units(docs,'joint_source_fingering')[0]
            self.assertEqual('BEAT_DEPENDENCY:downArpeggio'in units[0]['refusal_reasons'],value!=0)
            if value!=0:
                self.assertEqual(edges[0]['status'],'declaration_only_unknown_roll_execution')
                self.assertIsNone(edges[0]['semantics']['performed_note_offsets'])
                self.assertEqual(set(edges[0]['member_refs']),set(graph['pinned_members']))
                bad=deepcopy(graph);bad['edges'][0]['semantics']['performed_note_offsets']=['0','1','2']
                self.assertEqual(check_graph(lower,bad)['status'],'FAIL_INDEPENDENT_EXECUTION_DEPENDENCIES')


if __name__=='__main__':unittest.main()
