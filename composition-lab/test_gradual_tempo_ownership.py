"""Literal tempo-ramp ownership, without inventing a playback interpretation."""
from pathlib import Path
import tempfile
import unittest
from test_connected_tier2 import documents
from source_fact_tier1 import extract_documents, project_documents
from connected_tier2 import analyze, strip_lower, realize


class GradualTempoOwnershipTests(unittest.TestCase):
    def test_absent_false_true_are_distinct_and_owned_once(self):
        for present, value in ((False, None), (True, False), (True, True)):
            docs = documents()
            docs['track-0.json']['automations'] = {}
            if present:
                docs['track-0.json']['automations']['gradualTempo'] = value
            lower = extract_documents(docs)
            upper = strip_lower(analyze(lower))
            self.assertFalse(upper['unsupported'])
            self.assertEqual(project_documents(realize(upper)), docs)
            owners = [r for r in upper['owned_parameters']['source_choices']
                      if r['fact_ref'] == 'track-0.json#/automations/gradualTempo']
            self.assertEqual(len(owners), int(present))
            if present:
                self.assertEqual(owners[0]['owner'], 'source_clock_or_control')
                self.assertEqual(owners[0]['parameter'], {'symbol': value})

    def test_actual_source_free_worker_and_nominal_geometry_unchanged(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        from voicing_context_relations import graph
        docs = documents()
        original = extract_documents(docs)
        docs['track-0.json']['automations'] = {'gradualTempo': True}
        lower = extract_documents(docs)
        self.assertEqual(graph(original), graph(lower))
        upper = strip_lower(analyze(lower))
        code, _ = bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(code, upper, {'variation': 0}, lower,
                             Path(tmp)/'zero', timeout=30)
            self.assertEqual(result['status'], 'PASS', result)

    def test_unknown_types_are_rejected_not_coerced(self):
        for value in (None, 0, 1, 1.0, 'true', [], {}, {'linear': True}):
            docs = documents()
            docs['track-0.json']['automations'] = {'gradualTempo': value}
            upper = strip_lower(analyze(extract_documents(docs)))
            self.assertTrue(upper['unsupported'], value)
            with self.assertRaises(ValueError):
                realize(upper)


if __name__ == '__main__':
    unittest.main()
