"""Common motion and chord spacing remain separate across saved material uses."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import connected_tier2 as connected
import support_material_uses as uses
import written_tie_pitch_ownership as ties
from source_fact_tier1 import extract_documents,project_documents
from test_written_tie_pitch_ownership import documents,beat,note

COLLECTION=dict(id='authored-c-major',tonic_pc=0,intervals=[0,2,4,5,7,9,11])
MEMBER='event:77:0:2:0:0:2'
HELD='event:77:0:2:0:0:0'
USE='material-use:1'


def fixture():
    docs=documents([
        [beat(note(fret=7)),beat(note(fret=8)),beat(note(fret=7)),beat(note(fret=5))],
        [beat(note(fret=5,tie=True),note(1,12),note(2,4)),
         beat(note(fret=5,tie=True),note(1,13),note(2,5)),
         beat(note(fret=7)),beat(note(fret=8))]])
    lower=extract_documents(docs)
    t2=connected.strip_lower(connected.analyze(lower))
    t2['musical_relationships']=ties.lift(t2['musical_relationships'],tier1=lower)
    model=uses.from_tier2(t2,[dict(parts=[0],first_bar=i,last_bar=i)for i in (1,2)])
    model=uses.lift_degree_paths(model,USE,path_refs=[0],interpretations={0:[COLLECTION]},evidence_ref='authored-fixture')
    group=model['materials'][1]['degree_paths']['bindings'][0]['coattack_ref']
    return docs,lower,model,group


class DegreeMemberUseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.docs,cls.lower,cls.model,cls.group=fixture()

    def test_zero_spacing_and_saved_independent_common_motion(self):
        self.assertEqual(uses.reconstruct(self.model,{'variation':0}),self.lower)
        spread=uses.degree_path_candidate(self.model,USE,displacements={},octaves={},member_steps={MEMBER:2})
        expected=deepcopy(self.docs)
        expected['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][2]['fret']=7  # B3 -> D4
        self.assertEqual(project_documents(uses.reconstruct(spread,{'variation':0})),expected)
        moved=uses.degree_path_candidate(json.loads(json.dumps(spread)),USE,
            displacements={self.group:1},octaves={})
        expected['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][1]['fret']=13 # C4
        expected['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][2]['fret']=9  # E4
        self.assertEqual(project_documents(uses.reconstruct(moved,{'variation':0})),expected)
        self.assertEqual(moved['materials'],self.model['materials'])
        self.assertEqual(moved['lower_tier'],self.model['lower_tier'])
        self.assertEqual(moved['uses'][1]['degree_member_steps'],{MEMBER:2})

    def test_tied_member_and_impossible_contacts_refuse_without_mutation(self):
        before=deepcopy(self.model)
        with self.assertRaises(ValueError):
            uses.degree_path_candidate(self.model,USE,displacements={},octaves={},member_steps={HELD:1})
        with self.assertRaises(ValueError):
            uses.degree_path_candidate(self.model,USE,displacements={},octaves={self.group:8},member_steps={MEMBER:2})
        self.assertEqual(self.model,before)

    def test_batch_owns_both_passages_without_changing_preceding_tier(self):
        t2=connected.strip_lower(connected.analyze(self.lower))
        t2['musical_relationships']=ties.lift(t2['musical_relationships'],tier1=self.lower)
        original=uses.from_tier2(t2,[dict(parts=[0],first_bar=i,last_bar=i)for i in (1,2)])
        request=dict(path_refs=[0],interpretations={0:[COLLECTION]},evidence_ref='authored-fixture')
        both=uses.lift_degree_paths_many(original,{'material-use:0':request,USE:request})
        self.assertEqual(uses.expand(both),t2)
        self.assertEqual(uses.reconstruct(both,{'variation':0}),self.lower)
        frozen=deepcopy(original)
        with self.assertRaises(ValueError):
            uses.lift_degree_paths_many(original,{'material-use:0':request,'absent-use':request})
        self.assertEqual(original,frozen)

    def test_saved_composition_reconstructs_with_source_and_lower_unavailable(self):
        from run_support_use_qa import bundle
        from qa_isolation_harness import execute
        changed=uses.degree_path_candidate(self.model,USE,displacements={self.group:1},octaves={},member_steps={MEMBER:2})
        expected=deepcopy(self.docs)
        target=expected['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes']
        target[1]['fret']=13;target[2]['fret']=9
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory()as folder:
            receipt=execute(code,json.loads(json.dumps(changed)),{'variation':0},extract_documents(expected),
                            Path(folder)/'proof',timeout=60,purpose='exact_zero')
        self.assertEqual(receipt['status'],'PASS',receipt)
        self.assertFalse(receipt['parent_expected_staged'])


if __name__=='__main__':unittest.main()
