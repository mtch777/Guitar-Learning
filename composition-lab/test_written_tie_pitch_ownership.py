"""Authored sustained-note ownership; these fixtures are not musical evidence."""
from copy import deepcopy
import json
from unittest.mock import patch
import unittest

import backing_pitch_ownership as backing
import connected_tier2 as connected
import musical_tier2 as music
import written_tie_pitch_ownership as owner
from source_fact_tier1 import extract_documents, project_documents


def note(string=0, fret=5, **fields):
    return dict(string=string, fret=fret, **fields)


def beat(*notes, duration=(1, 4)):
    return dict(duration=list(duration), notes=list(notes))


def documents(bars):
    return {'metadata.json': dict(songId=77, revisionId=1, artist='Fixture', title='Sustains',
                                  tracks=[dict(name='Guitar', instrumentId=27)]),
            'track-0.json': dict(songId=77, revisionId=1, partId=0, instrumentId=27,
                                 tuning=[40, 47, 55], frets=24,
                                 measures=[dict(signature=[4, 4], voices=[dict(beats=b)]) for b in bars])}


def fixture(bars=None):
    if bars is None:
        bars = [[beat(note()), beat(note(tie=True)), beat(note(tie=True)), beat(note(fret=7))]]
    lower = extract_documents(documents(bars))
    connected_model = connected.strip_lower(connected.analyze(lower))
    core = connected_model['musical_relationships']
    return lower, connected_model, owner.lift(core, tier1=lower)


def ref(beat_number, member=0, bar=1):
    return f'event:77:0:{bar}:0:{beat_number}:{member}'


def pitches(wrapper):
    return {r: music.member_pitch(*pair) for r, pair in backing._index(owner.expand(wrapper)).items()}


def current_tier1(top, wrapper):
    current = deepcopy(top); current['musical_relationships'] = owner.expand(wrapper)
    result = connected.realize(current)
    owner.validate_contacts(wrapper, result)
    return result


class WrittenTiePitchOwnerTests(unittest.TestCase):
    def test_zero_is_exact_and_tail_parameters_are_absent(self):
        lower, top, wrapped = fixture(); before = deepcopy(wrapped)
        self.assertEqual(owner.expand(wrapped), top['musical_relationships'])
        self.assertEqual(current_tier1(top, wrapped), lower)
        for r in (ref(1), ref(2)):
            group, member = backing._index(wrapped['core'])[r]
            self.assertNotIn('voicing_interval', member)
            self.assertNotIn('bass_register_anchor', group)
            self.assertEqual(owner.attack_head(wrapped, r), ref(0))
        self.assertTrue(all(set(g) == {'member_refs', 'basis_ref'} for g in wrapped['groups']))
        self.assertEqual(wrapped, before)

    def test_head_change_propagates_chain_and_saved_subsequent_edit(self):
        _, top, original = fixture(); changed = deepcopy(original)
        backing._index(changed['core'])[ref(0)][0]['bass_register_anchor'] = '47'
        self.assertEqual(pitches(changed), {ref(0): '47', ref(1): '47', ref(2): '47', ref(3): '47'})
        owner.assert_preserved(original, changed, mutable_heads=[ref(0)])
        saved = json.loads(json.dumps(changed)); current_tier1(top, saved)
        backing._index(saved['core'])[ref(0)][0]['bass_register_anchor'] = '48'
        owner.assert_preserved(changed, saved, mutable_heads=[ref(0)])
        self.assertEqual([pitches(saved)[ref(i)] for i in range(4)], ['48', '48', '48', '47'])
        current_tier1(top, saved)

    def test_lowest_tail_does_not_move_fresh_upper_attack_even_when_crossing(self):
        bars = [[beat(note()), beat(note(tie=True), note(1, 3)),
                 beat(note(tie=True), note(1, 5)), beat(note(fret=7))]]
        lower, top, original = fixture(bars); changed = deepcopy(original)
        group, tail = backing._index(changed['core'])[ref(1)]
        self.assertEqual(group['bass_register_anchor'], '50')
        self.assertEqual(group['members'][1]['voicing_interval'], '0')
        backing._index(changed['core'])[ref(0)][0]['bass_register_anchor'] = '53'
        actual = pitches(changed)
        self.assertEqual([actual[ref(i)] for i in range(3)], ['53', '53', '53'])
        self.assertEqual([actual[ref(1, 1)], actual[ref(2, 1)]], ['50', '52'])
        owner.assert_preserved(original, changed, mutable_heads=[ref(0)])
        current_tier1(top, changed)
        self.assertEqual(current_tier1(top, original), lower)

    def test_upper_tail_and_independent_lower_pitch(self):
        bars = [[beat(note(1, 3)), beat(note(1, 3, tie=True), note()),
                 beat(note(1, 3, tie=True), note(fret=7)), beat(note(1, 4))]]
        _, top, original = fixture(bars); changed = deepcopy(original)
        backing._index(changed['core'])[ref(0)][0]['bass_register_anchor'] = '48'
        actual = pitches(changed)
        self.assertEqual((actual[ref(1)], actual[ref(1, 1)], actual[ref(2, 1)]), ('48', '45', '47'))
        owner.assert_preserved(original, changed, mutable_heads=[ref(0)])
        current_tier1(top, changed)

    def test_multiple_tied_members_leave_no_free_tail_anchor(self):
        bars = [[beat(note(), note(1, 3)), beat(note(tie=True), note(1, 3, tie=True)),
                 beat(note(fret=7)), beat(note(fret=9))]]
        _, top, original = fixture(bars); changed = deepcopy(original)
        head_group, _ = backing._index(changed['core'])[ref(0)]
        head_group['bass_register_anchor'] = '47'
        head_group['members'][1]['voicing_interval'] = '3'
        tail_group, _ = backing._index(changed['core'])[ref(1)]
        self.assertNotIn('bass_register_anchor', tail_group)
        self.assertEqual((pitches(changed)[ref(1)], pitches(changed)[ref(1, 1)]), ('47', '50'))
        owner.assert_preserved(original, changed, mutable_heads=[ref(0)])
        current_tier1(top, changed)

    def test_untied_unknown_member_is_preserved_not_given_a_pitch(self):
        bars = [[beat(note()), beat(note(tie=True), note(1, 3, dead=True)),
                 beat(note()), beat(note())]]
        _, top, original = fixture(bars); changed = deepcopy(original)
        backing._index(changed['core'])[ref(0)][0]['bass_register_anchor'] = '47'
        self.assertIsNone(pitches(changed)[ref(1, 1)])
        current_tier1(top, changed)

    def test_different_written_durations_and_cross_bar_continuity(self):
        bars = [[beat(note(), duration=(1, 1))],
                [beat(note(tie=True), duration=(1, 2)), beat(note(tie=True)), beat(note(fret=9))]]
        lower, top, original = fixture(bars)
        self.assertEqual(current_tier1(top, original), lower)
        self.assertEqual(owner.attack_head(original, ref(1, bar=2)), ref(0))
        changed = deepcopy(original)
        backing._index(changed['core'])[ref(0)][0]['bass_register_anchor'] = '46'
        current_tier1(top, changed)
        bad = deepcopy(changed)
        backing._index(bad['core'])[ref(0, bar=2)][0]['onset_q'] = '5'
        with self.assertRaisesRegex(ValueError, 'CLOCK_CONFLICT'):
            owner.expand(bad)

    def test_direct_tail_pitch_or_parameter_tampering_refuses_atomically(self):
        _, _, original = fixture()
        for field in ('voicing_interval', 'bass_register_anchor'):
            bad = deepcopy(original); group, member = backing._index(bad['core'])[ref(1)]
            (member if field == 'voicing_interval' else group)[field] = '1'
            snapshot = deepcopy(bad)
            with self.assertRaises(ValueError): owner.expand(bad)
            self.assertEqual(bad, snapshot)
        with self.assertRaisesRegex(ValueError, 'continuation edit'):
            owner.assert_preserved(original, original, mutable_heads=[ref(1)])

    def test_relationship_loss_and_redirection_are_detected(self):
        _, _, original = fixture()
        for mutate in (lambda w: w['relationships'].pop(),
                       lambda w: w['relationships'][0].update(origin_ref=ref(3)),
                       lambda w: w['groups'][0].update(basis_ref=ref(3)),
                       lambda w: w['core'].update(input={})):
            bad = deepcopy(original); mutate(bad)
            with self.assertRaises(ValueError): owner.expand(bad)

    def test_same_string_contact_is_mandatory_after_complete_inverse(self):
        lower, top, wrapped = fixture()
        docs = project_documents(lower)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0].update(string=1, fret=-2)
        bad = extract_documents(docs)
        with self.assertRaisesRegex(ValueError, 'CONTACT_CONFLICT'):
            owner.validate_contacts(wrapped, bad)
        docs = project_documents(current_tier1(top, wrapped))
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['tie'] = False
        with self.assertRaisesRegex(ValueError, 'CONTACT_CONFLICT'):
            owner.validate_contacts(wrapped, extract_documents(docs))

    def test_dead_tie_is_a_continuity_obligation_without_invented_pitch(self):
        bars = [[beat(note(dead=True)), beat(note(dead=True, tie=True)), beat(note()), beat(note())]]
        lower, top, wrapped = fixture(bars)
        self.assertEqual(wrapped['relationships'][0]['kind'], 'written_dead_tie')
        self.assertIsNone(pitches(wrapped)[ref(1)])
        self.assertEqual(owner.attack_head(wrapped, ref(1)), ref(0))
        self.assertEqual(current_tier1(top, wrapped), lower)

    def test_unresolved_source_kept_exact_without_freezing_unrelated_notes(self):
        bars = [[beat(note()), beat(note(fret=6, tie=True)), beat(note(fret=7)), beat(note(fret=9))]]
        lower, top, original = fixture(bars)
        self.assertEqual(original['relationships'], [])
        self.assertEqual(original['unresolved'][0]['reason'], 'different_written_position')
        self.assertEqual(current_tier1(top, original), lower)
        changed = deepcopy(original)
        backing._index(changed['core'])[ref(3)][0]['bass_register_anchor'] = '50'
        owner.assert_preserved(original, changed, mutable_heads=[ref(3)])
        current_tier1(top, changed)
        bad = deepcopy(original)
        backing._index(bad['core'])[ref(1)][0]['bass_register_anchor'] = '47'
        with self.assertRaisesRegex(ValueError, 'UNRESOLVED_AFFECTED'):
            owner.assert_preserved(original, bad, mutable_heads=[ref(1)])

    def test_unknown_tie_does_not_freeze_another_string_in_preceding_chord(self):
        bars = [[beat(note(), note(1, 3)), beat(note(fret=6, tie=True)),
                 beat(note(fret=7)), beat(note(fret=9))]]
        _, top, original = fixture(bars); changed = deepcopy(original)
        backing._index(changed['core'])[ref(0, 1)][1]['voicing_interval'] = '6'
        owner.assert_preserved(original, changed, mutable_heads=[ref(0, 1)])
        current_tier1(top, changed)

    def test_saved_material_inverse_rejects_unknown_pitch_edit_with_unchanged_reason(self):
        import support_material_uses as uses
        bars = [[beat(note()), beat(note(fret=6, tie=True)), beat(note(fret=7)), beat(note(fret=9))]]
        lower, top, wrapped = fixture(bars)
        top['musical_relationships'] = wrapped
        material = uses.from_tier2(top, [dict(parts=[0], first_bar=1, last_bar=1)])
        self.assertEqual(uses.reconstruct(json.loads(json.dumps(material)), {'variation': 0}), lower)
        bad = deepcopy(material); path = bad['materials'][0]['pitch_paths'][0]
        path['steps'][0] = str(music.fraction(path['steps'][0])+1)
        path['steps'][1] = str(music.fraction(path['steps'][1])-1)
        frozen = deepcopy(bad)
        with self.assertRaisesRegex(ValueError, 'UNRESOLVED_AFFECTED_WRITTEN_TIE'):
            uses.reconstruct(json.loads(json.dumps(bad)), {'variation': 0})
        self.assertEqual(bad, frozen)
        self.assertEqual(bad['lower_tier']['musical_relationships'], material['lower_tier']['musical_relationships'])
        # Another independent attack remains editable through that same saved
        # material inverse; uncertainty does not lock the complete source.
        good = deepcopy(material); path = good['materials'][0]['pitch_paths'][0]
        path['steps'][-1] = str(music.fraction(path['steps'][-1])+1)
        current = project_documents(uses.reconstruct(json.loads(json.dumps(good)), {'variation': 0}))
        beats = current['track-0.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual([b['notes'][0]['fret'] for b in beats], [5, 6, 7, 10])
        self.assertEqual(good['lower_tier']['musical_relationships']['unresolved'], wrapped['unresolved'])

    def test_unknown_fingerprint_is_required_and_contains_no_stored_note_values(self):
        _, _, wrapped = fixture([[beat(note()), beat(note(fret=6, tie=True)), beat(note()), beat(note())]])
        row = wrapped['unresolved'][0]
        self.assertEqual(set(row), {'destination_ref', 'reason', 'neighborhood_refs', 'context_fingerprint'})
        self.assertEqual(len(row['context_fingerprint']), 64)
        for value in (None, '', 'x'*64):
            bad = deepcopy(wrapped); bad['unresolved'][0]['context_fingerprint'] = value
            with self.assertRaises(ValueError): owner.expand(bad)

    def test_new_untied_basis_identity_stays_fixed_across_pitch_reordering(self):
        bars = [[beat(note()), beat(note(tie=True), note(1, 3), note(2, 0)),
                 beat(note(fret=7)), beat(note(fret=9))]]
        _, top, original = fixture(bars); changed = deepcopy(original)
        group, _ = backing._index(changed['core'])[ref(1)]
        group['bass_register_anchor'] = '57'
        group['members'][2]['voicing_interval'] = '-2'
        self.assertEqual(changed['groups'][0]['basis_ref'], ref(1, 1))
        self.assertEqual(pitches(changed)[ref(1, 2)], '55')
        self.assertEqual(pitches(changed)[ref(1, 1)], '57')
        owner.assert_preserved(original, changed, mutable_heads=[ref(1, 1)])
        current_tier1(top, changed)

    def test_inverse_has_no_source_or_file_access(self):
        _, top, wrapped = fixture(); saved = json.loads(json.dumps(wrapped))
        with patch('builtins.open', side_effect=AssertionError('No files')):
            self.assertEqual(owner.expand(saved), top['musical_relationships'])


if __name__ == '__main__':
    unittest.main()
