"""Saved original expression evidence survives edits and material reattacks."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import connected_tier2 as connected
import local_accents as accents
import observed_expression as evidence
import support_material_uses as uses
import test_material_expression_composition as fixture
from source_fact_tier1 import extract_documents, project_documents
from source_observation_evidence import require


def reload(value):
    return json.loads(json.dumps(value))


class ExpressionCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs=fixture.authored_documents()
        cls.lower=extract_documents(cls.docs)
        cls.t2=connected.strip_lower(connected.analyze(cls.lower,
            note_accent_slots=True,palm_mute_slots=True,dynamic_evidence=True,
            expression_evidence=True,backing_bindings=[fixture.direct.FOREIGN]))
        cls.model=uses.from_tier2(cls.t2,[fixture.SPEC])
        cls.first=next(g['id'] for g in cls.model['materials'][0]['lower_tier']['coattacks'] if g['part_id']==2)

    def test_saved_original_owner_allows_chaining_but_never_becomes_score_authority(self):
        self.assertEqual(connected.realize(self.t2),self.lower)
        changed=fixture.expression(self.t2)
        original=self.t2['owned_parameters']['observed_expression']
        for policy,control in ((evidence.ACCENT,'accents'),(evidence.MUTE,'palm_mute'),(evidence.TEMPO,'tempo')):
            require(reload(changed),{'context_policy':policy,control:100})
        self.assertEqual(changed['owned_parameters']['observed_expression'],original)
        legacy=deepcopy(changed);del legacy['owned_parameters']['observed_expression']
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CHAINED_EVIDENCE'):
            require(legacy,{'context_policy':evidence.ACCENT,'accents':100})

    def test_shared_child_expression_survives_save_then_further_subdivision(self):
        split,_=uses.subdivision_candidate(self.model,{fixture.USE:[self.first]})
        current,lower,_=uses.realize_pair(split)
        before=deepcopy(split)
        changed=current
        for beat in (0,1):
            changed=accents.apply(changed,f'track-2.json#/measures/0/voices/0/beats/{beat}/notes/0',dict(kind='explicit',value=1))
        packed=uses.pack_expression(split,changed)
        self.assertEqual(split,before)
        self.assertEqual(uses.expand(reload(packed)),changed)
        self.assertEqual(packed['materials'],split['materials'])
        self.assertEqual(packed['uses'],split['uses'])
        original=self.model['lower_tier']['owned_parameters']['observed_expression']
        self.assertEqual(packed['lower_tier']['owned_parameters']['observed_expression'],original)
        later,_=uses.subdivision_candidate(reload(packed),{fixture.USE:[self.first]})
        out=project_documents(uses.reconstruct(later,{'variation':0}))
        for beat in out['track-2.json']['measures'][0]['voices'][0]['beats'][:4]:
            self.assertEqual(beat['notes'][0]['accentuated'],1)
        projected=uses.expand(later)['owned_parameters']['observed_expression']
        self.assertEqual(evidence.evidence(projected),evidence.evidence(original))
        evidence.validate(projected,self.t2['source_origin'])

    def test_differing_child_choices_refuse_without_changing_complete_input(self):
        split,_=uses.subdivision_candidate(self.model,{fixture.USE:[self.first]})
        before=deepcopy(split);current=uses.expand(split)
        changed=accents.apply(current,'track-2.json#/measures/0/voices/0/beats/0/notes/0',dict(kind='explicit',value=1))
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_CHILD_EXPRESSION_OWNER_REQUIRED'):
            uses.pack_expression(split,changed)
        self.assertEqual(split,before)
        self.assertEqual(uses.expand(split),current)

    def test_actual_denied_source_inverse_includes_original_evidence_and_children(self):
        from run_support_use_qa import bundle
        from qa_isolation_harness import execute
        from test_material_subdivision_uses import expected_split
        changed,_=uses.subdivision_candidate(self.model,{fixture.USE:[self.first]})
        code,hashes=bundle(Path(__file__).resolve().parent)
        self.assertIn('observed_expression',hashes)
        with tempfile.TemporaryDirectory() as directory:
            receipt=execute(code,reload(changed),{'variation':0},
                extract_documents(expected_split(self.docs,{2:[0]})),
                Path(directory)/'proof',timeout=60,purpose='exact_zero')
            self.assertEqual(receipt['status'],'PASS',receipt)
            self.assertFalse(receipt['parent_expected_staged'])


if __name__=='__main__':unittest.main()
