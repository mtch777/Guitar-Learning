"""Synthetic ownership checks, not source musical evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
import backing_pitch_ownership as owner
import group_rhythm_relations as rhythm
import musical_tier2 as music
from connected_tier2 import analyze, strip_lower, realize
from source_fact_tier1 import extract_documents
from test_backing_motion_intervention import documents, TARGET


def setup(owned_time=False):
    docs = documents()
    if owned_time:
        for measure in docs['track-0.json']['measures']:
            beats = measure['voices'][0]['beats']
            beats[0]['beamStart'] = True
            beats[2]['beamStop'] = True
            for beat, kind in zip(beats, (16, 16, 8)):
                beat['type'] = kind
    lower = extract_documents(docs)
    top = strip_lower(analyze(lower, rhythm_groups=owned_time,
                            rhythm_group_profile='written_time' if owned_time else 'plain_repeat'))
    bindings = [dict(occurrence_ref=ref, backing_ref=f'event:987:1:2:0:{i}:0')
                for i, ref in enumerate(TARGET)]
    return lower, top, bindings


def fixture_lift(shared, bindings):
    # Authored fixture has no tie declarations; production callers supply T1.
    return owner.lift(shared, bindings, tier1=extract_documents(documents()))


class BackingOwnerTests(unittest.TestCase):
    def test_plain_zero_has_one_owner_and_reconstructs_complete_source(self):
        lower, top, bindings = setup(); shared = top['musical_relationships']; original = deepcopy(shared)
        wrapped = fixture_lift(shared, bindings)
        self.assertEqual(shared, original)
        self.assertEqual(set(wrapped), {'schema', 'core', 'relationships', 'written_tie_constraints'})
        self.assertEqual(set(wrapped['core']), owner.BASE_FIELDS)
        for group in wrapped['core']['coattacks']:
            self.assertNotIn('interpretation', group)
            if group['members'][0]['id'] in TARGET:
                self.assertNotIn('bass_register_anchor', group)
        expanded = owner.expand(wrapped)
        self.assertEqual(expanded, shared)
        self.assertEqual(music.reconstruct(expanded, {'variation': 0}), music.reconstruct(shared, {'variation': 0}))
        top['musical_relationships'] = expanded
        self.assertEqual(realize(top), lower)

    def test_owned_rhythm_zero_is_exact_without_duplicate_clocks(self):
        lower, top, bindings = setup(True); shared = top['musical_relationships']
        self.assertEqual(len(shared['groups']), 2)
        wrapped = fixture_lift(shared, bindings)
        target = owner._index(wrapped['core']['pitch_relationships'])[TARGET[1]]
        self.assertNotIn('onset_q', target[0]); self.assertNotIn('duration_q', target[1])
        self.assertEqual(owner.expand(wrapped), shared)
        top['musical_relationships'] = owner.expand(wrapped)
        self.assertEqual(realize(top), lower)

    def test_interval_edit_uses_existing_equation_and_only_selected_pitch_changes(self):
        _, top, bindings = setup(); shared = top['musical_relationships']
        wrapped = fixture_lift(shared, bindings); saved = deepcopy(wrapped)
        wrapped['relationships'][1]['interval_semitones'] = str(music.fraction(wrapped['relationships'][1]['interval_semitones']) + 2)
        before = music.realize(shared); after = music.realize(owner.expand(wrapped))
        expected = deepcopy(before)
        event = next(e for e in expected['events'] if e['id'] == TARGET[1])
        event['pitch'] = str(music.fraction(event['pitch']) + 2)
        self.assertEqual(after, expected)
        wrapped['relationships'][1] = saved['relationships'][1]
        self.assertEqual(owner.expand(wrapped), shared)

    def test_backing_pitch_edit_flows_through_same_relationship(self):
        _, top, bindings = setup(); wrapped = fixture_lift(top['musical_relationships'], bindings)
        group, note = owner._index(wrapped['core'])[bindings[1]['backing_ref']]
        group['bass_register_anchor'] = str(music.fraction(group['bass_register_anchor']) + 2)
        actual = owner._index(owner.expand(wrapped))[TARGET[1]]
        self.assertEqual(music.member_pitch(*actual), '35')

    def test_binding_order_canonical_and_independent_of_selected_pitch(self):
        _, top, bindings = setup(); shared = top['musical_relationships']
        a = fixture_lift(shared, bindings); b = fixture_lift(shared, list(reversed(bindings)))
        self.assertEqual(a, b)
        changed = deepcopy(shared)
        owner._index(changed)[TARGET[1]][0]['bass_register_anchor'] = '34'
        rhythm.refresh(changed)
        c = fixture_lift(changed, bindings)
        self.assertEqual([(r['occurrence_ref'], r['backing_ref']) for r in a['relationships']],
                         [(r['occurrence_ref'], r['backing_ref']) for r in c['relationships']])

    def test_binding_failures_leave_original_unchanged(self):
        _, top, bindings = setup(); shared = top['musical_relationships']; snapshot = deepcopy(shared)
        invalid = [[], bindings + [bindings[0]],
                   [dict(bindings[0], backing_ref=TARGET[0])],
                   [dict(bindings[0], backing_ref=TARGET[1])],
                   [dict(bindings[0], backing_ref='event:987:7:2:0:0:0')],
                   [dict(bindings[0], backing_ref='event:999:1:2:0:0:0')],
                   [dict(bindings[0], pitch='35')],
                   [dict(bindings[0], occurrence_ref='event:987:0:22:0:0:0')]]
        for case in invalid:
            with self.subTest(case=case), self.assertRaises(ValueError): fixture_lift(shared, case)
            self.assertEqual(shared, snapshot)

    def test_targets_cannot_be_anchors_even_without_cycle(self):
        _, top, _ = setup(); shared = top['musical_relationships']
        bindings = [dict(occurrence_ref=TARGET[0], backing_ref='event:987:1:2:0:0:0'),
                    dict(occurrence_ref='event:987:1:2:0:0:0', backing_ref='event:987:1:1:0:0:0')]
        with self.assertRaisesRegex(ValueError, 'independent backing anchor'): fixture_lift(shared, bindings)

    def test_prior_expired_and_future_notes_refuse(self):
        _, top, bindings = setup(); shared = top['musical_relationships']
        for ref in ('event:987:1:1:0:0:0', 'event:987:1:2:0:1:0'):
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, 'not active'):
                fixture_lift(shared, [dict(bindings[0], backing_ref=ref)])
        with self.assertRaisesRegex(ValueError, 'not active'):
            fixture_lift(shared, [dict(bindings[1], backing_ref=bindings[0]['backing_ref'])])

    def test_pruned_ownership_or_cache_corruptions_refuse_atomically(self):
        _, top, bindings = setup(); original = fixture_lift(top['musical_relationships'], bindings)
        cases = []
        def add(fn):
            row = deepcopy(original); fn(row); cases.append(row)
        add(lambda w: w['core'].update(input={}))
        add(lambda w: w['core'].update(nominal_written_spans=[]))
        add(lambda w: w['core'].update(written_ties={}))
        add(lambda w: w['core'].update(original_target_pitch='35'))
        add(lambda w: owner._index(w['core'])[TARGET[0]][0].update(bass_register_anchor='35'))
        add(lambda w: owner._index(w['core'])[bindings[0]['backing_ref']][0].pop('bass_register_anchor'))
        add(lambda w: owner._index(w['core'])[bindings[0]['backing_ref']][0].update(interpretation={}))
        add(lambda w: w['relationships'].pop())
        add(lambda w: w['relationships'].append(deepcopy(w['relationships'][0])))
        add(lambda w: w['relationships'].reverse())
        add(lambda w: w['relationships'][0].update(backing_ref=TARGET[1]))
        add(lambda w: w['relationships'][0].update(interval_semitones='2/2'))
        add(lambda w: w['relationships'][0].update(interval_semitones=1))
        add(lambda w: w.update(original_pitch='35'))
        for case in cases:
            before = deepcopy(case)
            with self.subTest(case=case), self.assertRaises(ValueError): owner.expand(case)
            self.assertEqual(case, before)

    def test_unknown_pitch_refuses_without_guess(self):
        _, top, bindings = setup(); shared = deepcopy(top['musical_relationships'])
        group, member = owner._index(shared)[bindings[0]['backing_ref']]
        for note in group['members']: note['voicing_interval'] = None
        group['bass_register_anchor'] = None
        rhythm.refresh(shared); music.validate(shared)
        with self.assertRaisesRegex(ValueError, 'known independent owner'): fixture_lift(shared, bindings)

    def test_owned_time_change_cannot_silently_keep_inactive_anchor(self):
        _, top, bindings = setup(True); wrapped = fixture_lift(top['musical_relationships'], bindings)
        group = next(g for g in wrapped['core']['groups'] if g['bar'] == 2)
        group['shares'] = ['1/2', '1/4', '1/4']
        with self.assertRaisesRegex(ValueError, 'not active'): owner.expand(wrapped)

    def test_unsupported_wrapper_refuses(self):
        _, top, bindings = setup(True); shared = top['musical_relationships']
        for schema in ('source-group-rhythm/1', 'source-voicing-families/1', 'invented/1'):
            value = deepcopy(shared); value['schema'] = schema
            with self.assertRaises(ValueError): fixture_lift(value, bindings)

    def test_unknown_clock_is_not_repaired_from_available_numbers(self):
        _, top, bindings = setup(); shared = top['musical_relationships']
        shared['source_quality']['layout_warnings'] = [dict(bar=2, reason='conflicting_track_meter')]
        for group in shared['coattacks']:
            group['timing_uncertain'] = group['bar'] == 2
        rhythm.refresh(shared); music.validate(shared)
        with self.assertRaisesRegex(ValueError, 'Unknown written clock'): fixture_lift(shared, bindings)

    def test_missing_target_clock_is_not_inferred(self):
        _, top, bindings = setup(); wrapped = fixture_lift(top['musical_relationships'], bindings)
        owner._index(wrapped['core'])[TARGET[0]][0].pop('onset_q')
        with self.assertRaisesRegex(ValueError, 'Missing owned written clock'): owner.expand(wrapped)

    def test_polyphonic_focal_cannot_hide_multiple_pitch_owners(self):
        _, top, _ = setup()
        with self.assertRaisesRegex(ValueError, 'Exactly one owned focal pitch'):
            fixture_lift(top['musical_relationships'], [dict(occurrence_ref='event:987:1:2:0:0:0', backing_ref=TARGET[0])])

    def test_foreign_song_anchor_refuses_even_when_it_exists(self):
        _, top, bindings = setup(); shared = top['musical_relationships']
        replacements = {}
        for group in shared['coattacks']:
            if group['part_id'] != 1: continue
            for member in group['members']:
                old = member['id']; member['id'] = old.replace('event:987:', 'event:988:')
                replacements[old] = member['id']
        shared['realization_order'] = [replacements.get(ref, ref) for ref in shared['realization_order']]
        rhythm.refresh(shared); music.validate(shared)
        with self.assertRaisesRegex(ValueError, 'same source song'):
            fixture_lift(shared, [dict(bindings[0], backing_ref=replacements[bindings[0]['backing_ref']])])


if __name__ == '__main__':
    unittest.main()
