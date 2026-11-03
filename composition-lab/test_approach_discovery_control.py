"""No caller-selected bars/notes: discovery feeds the existing reversible edit."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

import connected_tier2 as connected
import support_material_uses as uses
from approach_discovery_control import prepare_first
from source_fact_tier1 import extract_documents, project_documents


def authored():
    # A C-major backing chord and a separate C-D-E guitar line. Independent
    # written score construction; no key or target-note inputs to discovery.
    docs = {'metadata.json': dict(songId=990001, revisionId=1, artist='Authored fixture',
        title='Automatic approach', tracks=[dict(name='Line', instrumentId=27),
                                          dict(name='Backing', instrumentId=34)])}
    def bar(beats):
        return dict(signature=[4, 4], voices=[dict(beats=beats)])
    docs['track-0.json'] = dict(songId=990001, revisionId=1, partId=0,
        instrumentId=27, tuning=[60], frets=24, measures=[bar([
            dict(duration=d, notes=[dict(string=0, fret=f)])
            for d, f in [([1, 4], 0), ([1, 4], 2), ([1, 2], 4)]])])
    docs['track-1.json'] = dict(songId=990001, revisionId=1, partId=1,
        instrumentId=34, tuning=[48, 47, 43], frets=24, measures=[bar([
            dict(duration=[1, 1], notes=[dict(string=s, fret=f)
                for s, f in [(0, 0), (1, 5), (2, 12)]])])])
    lower = extract_documents(docs)
    return docs, lower, connected.strip_lower(connected.analyze(lower))


class DiscoveryControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.lower, cls.t2 = authored()
        cls.result = prepare_first(cls.t2)

    def test_discovers_and_binds_without_part_bar_or_note_arguments(self):
        result = self.result
        self.assertEqual(result['status'], 'PREPARED')
        self.assertEqual(result['selection'], 'first_applicable_chronological_not_preferred')
        self.assertEqual(result['selected']['original_pitches'], ['60', '62', '64'])
        self.assertEqual(result['selected']['proposed_pitches'], ['67', '65', '64'])
        self.assertEqual(uses.expand(result['original']), self.t2)
        self.assertEqual(uses.reconstruct(result['original'], {'variation': 0}), self.lower)

    def test_changed_score_uses_same_relationship_and_only_expected_frets_change(self):
        changed = self.result['changed']
        expected = deepcopy(self.docs)
        for beat, fret in zip(expected['track-0.json']['measures'][0]['voices'][0]['beats'], [7, 5, 4]):
            beat['notes'][0]['fret'] = fret
        self.assertEqual(project_documents(uses.reconstruct(json.loads(json.dumps(changed)), {'variation': 0})), expected)
        restored = uses.approach_candidate(changed, self.result['use_id'], 'original')
        self.assertEqual(uses.expand(restored), self.t2)

    def test_existing_material_is_refined_without_creating_an_overlapping_use(self):
        before = uses.from_tier2(self.t2, [dict(parts=[0], first_bar=1, last_bar=1)])
        saved = deepcopy(before)
        result = prepare_first(before)
        self.assertEqual(result['status'], 'PREPARED')
        self.assertEqual(len(result['original']['uses']), 1)
        self.assertEqual(before, saved)

    def test_nonfit_is_retained_and_input_unchanged(self):
        docs = deepcopy(self.docs)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['fret'] = 14
        t2 = connected.strip_lower(connected.analyze(extract_documents(docs)))
        saved = deepcopy(t2)
        result = prepare_first(t2)
        self.assertEqual(result['status'], 'NO_APPLICABLE_APPROACH')
        self.assertEqual(t2, saved)
        self.assertNotIn('original', result)

    def test_unknown_tier_is_refused(self):
        with self.assertRaises(ValueError):
            prepare_first(dict(tier=9))

    def test_declared_scope_keeps_other_discoveries_without_editing_them(self):
        docs = deepcopy(self.docs)
        for name in ('track-0.json', 'track-1.json'):
            measure = docs[name]['measures'][0]
            rest = dict(signature=[4, 4], voices=[dict(beats=[
                dict(duration=[1, 1], rest=True, notes=[])])])
            docs[name]['measures'] = [deepcopy(measure), rest, deepcopy(measure)]
        t2 = connected.strip_lower(connected.analyze(extract_documents(docs)))
        saved = deepcopy(t2)
        result = prepare_first(t2, scope=dict(first_bar=3, last_bar=3))
        self.assertEqual(result['status'], 'PREPARED')
        self.assertEqual(result['selected']['bars'], [3, 3])
        self.assertTrue(any(r['bars'] == [1, 1] for r in result['discovery']['runs']))
        self.assertTrue(any(a['status'] == 'OUTSIDE_DECLARED_SCOPE' for a in result['attempts']))
        realized = project_documents(uses.reconstruct(result['changed'], {'variation': 0}))
        self.assertEqual(realized['track-0.json']['measures'][:2], docs['track-0.json']['measures'][:2])
        self.assertEqual(realized['track-1.json'], docs['track-1.json'])
        self.assertEqual(t2, saved)

    def test_empty_scope_does_not_fall_back_to_an_earlier_fit(self):
        result = prepare_first(self.t2, scope=dict(first_bar=2, last_bar=2))
        self.assertEqual(result['status'], 'NO_APPLICABLE_APPROACH')
        self.assertTrue(result['discovery']['runs'])
        self.assertNotIn('changed', result)

    def test_cross_boundary_run_is_not_shortened_to_pass(self):
        docs = deepcopy(self.docs)
        measures = docs['track-0.json']['measures']
        first = measures[0]['voices'][0]['beats']
        last = deepcopy(first[-1]); last['duration'] = [1, 1]
        measures.append(dict(signature=[4, 4], voices=[dict(beats=[last])]))
        first[:] = first[:2]
        for beat in first:
            beat['duration'] = [1, 2]
        docs['track-1.json']['measures'].append(deepcopy(docs['track-1.json']['measures'][0]))
        t2 = connected.strip_lower(connected.analyze(extract_documents(docs)))
        result = prepare_first(t2, scope=dict(first_bar=2, last_bar=2))
        crossing = [r for r in result['discovery']['runs'] if r['bars'] == [1, 2]]
        self.assertTrue(crossing)
        self.assertEqual(result['status'], 'NO_APPLICABLE_APPROACH')
        self.assertNotIn('changed', result)

    def test_invalid_scope_refuses_before_discovery(self):
        for scope in ({'first_bar': 0, 'last_bar': 1}, {'first_bar': 2, 'last_bar': 1},
                      {'first_bar': True, 'last_bar': 2}, {'first_bar': 1},
                      {'first_bar': 1, 'last_bar': 2, 'pitch': 64}):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                prepare_first(self.t2, scope=scope)

    def test_binding_refusal_does_not_narrow_the_remaining_search(self):
        docs = deepcopy(self.docs)
        for name in ('track-0.json', 'track-1.json'):
            measure = docs[name]['measures'][0]
            rest = dict(signature=[4, 4], voices=[dict(beats=[
                dict(duration=[1, 1], rest=True, notes=[])])])
            docs[name]['measures'] = [deepcopy(measure), rest, deepcopy(measure)]
        t2 = connected.strip_lower(connected.analyze(extract_documents(docs)))
        before = deepcopy(t2)
        actual_lift = uses.lift_approach
        for declared_scope in (None, dict(first_bar=1, last_bar=3)):
            calls = []
            def refuse_first(*args, **kwargs):
                calls.append(args[1])
                if len(calls) == 1:
                    raise ValueError('Injected mechanical refusal after a valid relationship fit')
                return actual_lift(*args, **kwargs)
            with self.subTest(scope=declared_scope), patch.object(uses, 'lift_approach', side_effect=refuse_first):
                result = prepare_first(t2, scope=declared_scope)
            self.assertEqual(result['status'], 'PREPARED')
            self.assertEqual(result['selected']['bars'], [3, 3])
            self.assertEqual(len(calls), 2)
            self.assertEqual(result['attempts'][0]['status'], 'BINDING_OR_EXECUTION_REFUSED')
            self.assertEqual(t2, before)


if __name__ == '__main__':
    unittest.main()
