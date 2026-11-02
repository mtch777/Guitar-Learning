from copy import deepcopy
import unittest
from test_backing_pitch_ownership import setup, fixture_lift
import canonical_backing_bindings as canonical
import backing_pitch_ownership as owner
import backing_motion_intervention as motion
from test_backing_motion_intervention import controls
import group_rhythm_relations as rhythm


class BindingTests(unittest.TestCase):
    def prepared(self):
        _, top, _ = setup(True)
        return top['musical_relationships'], motion.prepare(top, controls())['correspondences']

    def test_six_owners_reproduce_every_pair_and_numeric_choice(self):
        shared, rows = self.prepared(); bindings = canonical.canonical_bindings(shared, rows)
        self.assertEqual(len(bindings), 6)
        wrapped = fixture_lift(shared, bindings)
        self.assertEqual(owner.expand(wrapped), shared)
        for row in rows:
            pairs = canonical._pairs(row['match']['maxima'])
            first = min(pairs, key=lambda p:(owner.address(p[0]),owner.address(p[1])))
            found = {r['occurrence_ref']:r['backing_ref'] for r in bindings}
            self.assertEqual((found[row['source_ref']],found[row['target_ref']]), first)

    def test_order_is_not_a_pitch_selection_heuristic(self):
        shared, rows = self.prepared(); expected = canonical.canonical_bindings(shared, rows)
        changed = deepcopy(rows)
        changed.reverse()
        for row in changed:
            row['match']['maxima'][0]['matched'].reverse()
        self.assertEqual(canonical.canonical_bindings(shared, changed), expected)

    def test_target_pitch_and_register_do_not_change_bindings(self):
        shared, rows = self.prepared(); expected = canonical.canonical_bindings(shared, rows)
        body = shared['pitch_relationships']; group,_ = owner._index(body)[rows[0]['target_ref']]
        group['bass_register_anchor'] = '47'
        self.assertEqual(canonical.canonical_bindings(shared, rows), expected)

    def test_omitted_maximal_pair_refuses(self):
        shared, rows = self.prepared(); rows[0]['match']['maxima'][0]['matched'].pop()
        with self.assertRaisesRegex(ValueError,'maximal pairs'): canonical.canonical_bindings(shared, rows)

    def test_false_matched_pitch_refuses(self):
        shared, rows = self.prepared(); rows[0]['match']['maxima'][0]['matched'][0]['target_pitch'] += 1
        with self.assertRaisesRegex(ValueError,'maximal pairs'): canonical.canonical_bindings(shared, rows)

    def test_hidden_backing_occurrence_refuses(self):
        shared, rows = self.prepared(); rows[0]['match']['source_refs'].pop()
        with self.assertRaisesRegex(ValueError,'Incomplete owned backing context'): canonical.canonical_bindings(shared, rows)

    def test_duplicate_focal_owner_refuses(self):
        shared, rows = self.prepared()
        with self.assertRaisesRegex(ValueError,'Duplicate target owner'): canonical.canonical_bindings(shared, rows+rows[:1])

    def test_ambiguous_maximum_cannot_choose_a_convenient_pair(self):
        shared, rows = self.prepared(); normal = owner._normal(shared); index = owner._index(normal)
        index['event:987:1:1:0:0:3'][1]['voicing_interval'] = '19'
        index['event:987:1:2:0:0:1'][1]['voicing_interval'] = '7'
        rhythm.refresh(normal)
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            canonical.canonical_bindings(normal, rows)


if __name__ == '__main__': unittest.main()
