"""No caller-selected bars/notes: discovery feeds the existing reversible edit."""
from copy import deepcopy
import json
import unittest

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


if __name__ == '__main__':
    unittest.main()
