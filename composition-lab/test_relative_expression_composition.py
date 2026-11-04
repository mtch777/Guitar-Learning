"""Generated dynamic choices keep source evidence and material dependencies."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import connected_tier2 as connected
import local_accents
import local_palm_mutes
import observed_dynamics
import observed_expression
import support_material_uses as uses
from source_fact_tier1 import extract_documents, project_documents
import test_material_expression_composition as fixture


def reload(value):
    return json.loads(json.dumps(value))


class RelativeExpressionCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs=fixture.authored_documents(tied=True)
        cls.t2=connected.strip_lower(connected.analyze(extract_documents(cls.docs),
            note_accent_slots=True,palm_mute_slots=True,dynamic_evidence=True,
            expression_evidence=True,backing_bindings=[fixture.direct.FOREIGN]))
        cls.model=uses.from_tier2(cls.t2,[fixture.SPEC])

    def test_generated_level_packs_without_replacing_source_or_foreign_relationships(self):
        original=deepcopy(self.model)
        current=uses.expand(self.model)
        changed=deepcopy(current)
        changed['owned_parameters']['observed_dynamics']=observed_dynamics.choose_relative(
            current['owned_parameters']['observed_dynamics'],{fixture.DYNAMIC:'mf'})
        changed=local_accents.apply(changed,fixture.ACCENT,{'kind':'absent'})
        changed=local_palm_mutes.apply(changed,
            ['track-2.json#/measures/0/voices/0/beats/0'],[{'kind':'explicit','value':False}])
        result=uses.pack_expression(self.model,changed)
        self.assertEqual(self.model,original)
        self.assertEqual(uses.expand(reload(result)),changed)
        for key in ('materials','uses','slots'):
            self.assertEqual(result[key],self.model[key])
        old=current['owned_parameters'];new=changed['owned_parameters']
        self.assertEqual(observed_dynamics.evidence(old['observed_dynamics']),
                         observed_dynamics.evidence(new['observed_dynamics']))
        self.assertEqual(new['observed_expression'],old['observed_expression'])
        self.assertEqual(changed['musical_relationships'],current['musical_relationships'])
        expected=deepcopy(self.docs)
        beats=expected['track-2.json']['measures'][0]['voices'][0]['beats']
        beats[0].update(velocity='mf',palmMute=False)
        del beats[1]['notes'][0]['accentuated']
        self.assertEqual(project_documents(uses.reconstruct(reload(result),{'variation':0})),expected)
        later=deepcopy(changed)
        later['owned_parameters']['observed_dynamics']=observed_dynamics.choose_relative(
            new['observed_dynamics'],{fixture.DYNAMIC:'ff'})
        saved=uses.pack_expression(reload(result),later)
        expected['track-2.json']['measures'][0]['voices'][0]['beats'][0]['velocity']='ff'
        self.assertEqual(project_documents(uses.reconstruct(saved,{'variation':0})),expected)

    def test_relative_level_survives_subdivision_and_denied_inverse(self):
        first=next(g['id']for g in self.model['materials'][0]['lower_tier']['coattacks']if g['part_id']==2)
        split,_=uses.subdivision_candidate(self.model,{fixture.USE:[first]})
        current=uses.expand(split);changed=deepcopy(current)
        changed['owned_parameters']['observed_dynamics']=observed_dynamics.choose_relative(
            current['owned_parameters']['observed_dynamics'],{fixture.DYNAMIC:'mf'})
        saved=uses.pack_expression(split,changed)
        self.assertEqual(uses.expand(reload(saved)),changed)
        from test_material_subdivision_uses import expected_split
        expected=expected_split(self.docs,{2:[0]})
        for beat in expected['track-2.json']['measures'][0]['voices'][0]['beats'][:2]:
            beat['velocity']='mf'
        expected=extract_documents(expected)
        self.assertEqual(uses.reconstruct(reload(saved),{'variation':0}),expected)
        from run_support_use_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory()as directory:
            receipt=execute(code,reload(saved),{'variation':0},expected,
                            Path(directory)/'proof',timeout=90,purpose='exact_zero')
        self.assertEqual(receipt['status'],'PASS',receipt)
        self.assertFalse(receipt['parent_expected_staged'])

    def test_packing_cannot_alter_original_evidence_or_unrelated_owner(self):
        before=deepcopy(self.model);current=uses.expand(self.model)
        changed=deepcopy(current)
        changed['owned_parameters']['observed_dynamics']=observed_dynamics.choose_relative(
            current['owned_parameters']['observed_dynamics'],{fixture.DYNAMIC:'mf'})
        changed['source_origin']['facts_sha256']='0'*64
        with self.assertRaises(ValueError):
            uses.pack_expression(self.model,changed)
        self.assertEqual(self.model,before)


if __name__=='__main__':
    unittest.main()
