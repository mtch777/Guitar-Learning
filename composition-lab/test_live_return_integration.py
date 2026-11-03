"""Successive musical edits must preserve the live return dependency."""
from copy import deepcopy
import json
import unittest

import material_rhythm_control as rhythm
import section_arrangements as sections
import thematic_return as theme
from test_live_melodic_return import build_live, SOURCE, RETURN, RHYTHM_RETURN, pitches


def saved(value):
    return json.loads(json.dumps(value))


class LiveReturnIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.live = build_live()

    def test_source_edit_then_rhythm_edit_retains_link_and_immutable_evidence(self):
        linked = theme.approach_candidate(self.live, 'opposite')
        changed = theme.change_approach_source(saved(linked), 'flip')
        original_evidence = deepcopy(changed['lower_tier']['lower_tier']['observations'])
        after = rhythm.candidate_composed(saved(changed), RHYTHM_RETURN, '1/2')
        reloaded = saved(after)
        self.assertEqual(reloaded['approach_relationship'], changed['approach_relationship'])
        self.assertEqual(reloaded['relationship'], changed['relationship'])
        self.assertEqual(reloaded['lower_tier']['choices'], changed['lower_tier']['choices'])
        self.assertEqual(reloaded['lower_tier']['lower_tier']['observations'], original_evidence)
        self.assertNotIn('approach_mode', next(u for u in reloaded['lower_tier']['lower_tier']['uses'] if u['id'] == RETURN))
        self.assertEqual(pitches(reloaded, 2), [67, 65, 64])
        self.assertEqual(pitches(reloaded, 6), [60, 62, 64])
        # Another source edit after rhythm/save still propagates.
        later = theme.change_approach_source(reloaded, 'original')
        self.assertEqual(pitches(later, 6), [67, 65, 64])
        current = sections.expand(theme.expand(later))
        self.assertEqual(next(u for u in current['uses'] if u['id'] == RHYTHM_RETURN)['rhythm_offset_q'], '1/2')
        self.assertEqual(rhythm.candidate_composed(saved(after), RHYTHM_RETURN, '0'), changed)

    def test_independent_return_stays_independent_through_same_edit_sequence(self):
        changed = theme.change_approach_source(saved(self.live), 'flip')
        after = rhythm.candidate_composed(saved(changed), RHYTHM_RETURN, '1/2')
        self.assertEqual(pitches(saved(after), 6), [60, 62, 64])
        self.assertEqual(after['approach_relationship'], self.live['approach_relationship'])
        lower, report = rhythm.intervene(rhythm.expand_uses(saved(after)), RHYTHM_RETURN,
            dict(release=0, intention='earlier', seed=0))
        locked = rhythm.embed_uses(after, lower, RHYTHM_RETURN)
        self.assertEqual(locked, after)
        self.assertFalse(report['changed'])


if __name__ == '__main__':
    unittest.main()
