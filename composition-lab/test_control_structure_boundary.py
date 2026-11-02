"""Ordinary score structures checked before extending the treatment control."""
from copy import deepcopy
import json
import unittest

import coattack_treatment_ownership as treatment
from connected_tier2 import analyze, strip_lower, realize
from source_fact_tier1 import extract_documents, project_documents
from test_coattack_treatment_ownership import documents, bindings, controls


class StructureBoundaryTests(unittest.TestCase):
    def test_rest_between_complete_coattacks_survives_saved_successive_edits(self):
        docs = documents()
        for bar in docs['track-0.json']['measures']:
            beats = bar['voices'][0]['beats']
            beats.insert(1, dict(duration=[1, 16], notes=[dict(rest=True)]))
            beats[-1]['duration'] = [11, 16]
        before = extract_documents(docs)
        upper = strip_lower(analyze(before))
        links = bindings()
        for i, row in enumerate(links):
            beat = i + (i > 0)
            row['reference_anchor_ref'] = f'event:995:0:1:0:{beat}:2'
            row['target_anchor_ref'] = f'event:995:0:2:0:{beat}:2'
        upper['musical_relationships'] = treatment.lift(
            upper['musical_relationships'], before, links, source_origin=upper['source_origin'])
        self.assertEqual(realize(upper), before)
        repeated, _ = treatment.intervene(upper, controls())
        followed, _ = treatment.intervene(json.loads(json.dumps(repeated)),
                                          controls(intent=treatment.INTENTS[1]))
        expected = deepcopy(docs)
        for i, beat in enumerate((0, 2, 3, 4)):
            # The fixture's independently specified backing shift is -2 after
            # its first attack. Rest and dead member have no pitch obligation.
            target = expected['track-0.json']['measures'][1]['voices'][0]['beats'][beat]
            target['notes'][0]['fret'] = 13 if i == 0 else 11
            target['notes'][2]['fret'] = 11 if i == 0 else 9
        self.assertEqual(project_documents(realize(followed)), expected)
        self.assertEqual(treatment.intervene(followed, controls(0))[0], followed)

    def test_selected_linked_markings_are_retained_then_refused_atomically(self):
        for field, value in (('slide', 'shift'), ('hp', True), ('tie', True)):
            with self.subTest(field=field):
                docs = documents()
                docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0][field] = value
                before = extract_documents(docs)
                upper = strip_lower(analyze(before))
                self.assertEqual(project_documents(realize(upper)), docs)
                snapshot = deepcopy(upper)
                with self.assertRaises(ValueError):
                    treatment.lift(upper['musical_relationships'], before, bindings(),
                                   source_origin=upper['source_origin'])
                self.assertEqual(upper, snapshot)


if __name__ == '__main__':
    unittest.main()
