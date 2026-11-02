"""Authored mathematical and ownership contrasts; not musical-fit evidence."""
from copy import deepcopy
import unittest

import backing_motion_relations as motion
import backing_pitch_ownership as owner
import explicit_backing_stream as stream
import group_rhythm_relations as rhythm
import musical_tier2 as music
from connected_tier2 import analyze, strip_lower, realize
from source_fact_tier1 import extract_documents
from test_backing_motion_intervention import documents, SOURCE, TARGET

ANCHOR = 'event:987:1:1:0:0:0'
BACKING = [f'event:987:1:2:0:{i}:0' for i in range(3)]


def fixture(edit=None, owned_time=False):
    docs = documents()
    measure = docs['track-1.json']['measures'][0]
    measure['voices'][0]['beats'][0]['notes'] = [measure['voices'][0]['beats'][0]['notes'][1]]
    for beat in docs['track-1.json']['measures'][1]['voices'][0]['beats'][:3]:
        beat['notes'] = [beat['notes'][0]]
    if owned_time:
        for m in docs['track-0.json']['measures']:
            for beat, kind in zip(m['voices'][0]['beats'], (16, 16, 8)):
                beat['type'] = kind
            m['voices'][0]['beats'][0]['beamStart'] = True
            m['voices'][0]['beats'][2]['beamStop'] = True
    if edit:
        edit(docs)
    before = extract_documents(docs)
    upper = strip_lower(analyze(before, rhythm_groups=owned_time,
                               rhythm_group_profile='written_time' if owned_time else 'plain_repeat'))
    return before, upper


def correspondence(shared, i, source_anchor=ANCHOR, target_anchor=None):
    target_anchor = BACKING[i] if target_anchor is None else target_anchor
    index = owner._index(owner._normal(shared))
    def side(ref):
        return [dict(ref=ref, pitch=music.member_pitch(*index[ref]))]
    def context(focal, anchor):
        return dict(time_q=index[focal][0]['onset_q'], context_refs=[anchor], qualifications=[])
    match = stream.stream_relation(side(source_anchor), side(target_anchor), backing_part=1, backing_voice=0,
                                   source_context=context(SOURCE[i], source_anchor),
                                   target_context=context(TARGET[i], target_anchor))
    return dict(source_ref=SOURCE[i], target_ref=TARGET[i], match=match)


def correspondences(shared):
    return [correspondence(shared, i) for i in range(3)]


class ExplicitBackingStreamTests(unittest.TestCase):
    def test_same_scalar_relation_forward_and_reverse_nonconstant(self):
        _, top = fixture(); shared = top['musical_relationships']; rows = correspondences(shared)
        self.assertEqual([r['match']['selected_delta'] for r in rows], [0, -2, 0])
        original = [35, 33, 35]
        changed = [motion.solve_pitch(source_pitch=p, delta=r['match']['selected_delta'])['target_pitch']
                   for p, r in zip(original, rows)]
        self.assertEqual(changed, [35, 31, 35])
        self.assertEqual([motion.solve_pitch(target_pitch=p, delta=r['match']['selected_delta'])['source_pitch']
                          for p, r in zip(changed, rows)], original)
        self.assertTrue(all(r['match']['schema'] == stream.SCHEMA and r['match']['kind'] == stream.KIND for r in rows))

    def test_old_two_pitch_policy_still_refuses_same_singletons(self):
        a = [dict(ref=ANCHOR, pitch=54)]; b = [dict(ref=BACKING[1], pitch=52)]
        old = motion.maximum_translations(a, b)
        self.assertEqual(old['status'], 'INSUFFICIENT_DISTINCT_PITCH_MATCHES')
        self.assertIsNone(old['selected_delta'])

    def test_strict_occurrence_address_voice_and_pitch_contract(self):
        good = dict(source=[dict(ref=ANCHOR, pitch=54)], target=[dict(ref=BACKING[1], pitch=52)],
                    backing_part=1, backing_voice=0,
                    source_context=dict(time_q='0', context_refs=[ANCHOR], qualifications=[]),
                    target_context=dict(time_q='17/4', context_refs=[BACKING[1]], qualifications=[]))
        bad_cases = []
        for value in (None, True, 54.0, float('nan'), float('inf'), '54.0', '1/2', '1/0'):
            bad_cases.append(dict(good, source=[dict(ref=ANCHOR, pitch=value)]))
        for refs in ([], [dict(ref=ANCHOR, pitch=54)] * 2,
                     [dict(ref=ANCHOR, pitch=54), dict(ref='event:987:1:1:0:0:1', pitch=54)]):
            bad_cases.append(dict(good, source=refs))
        for ref in ('event:0987:1:1:0:0:0', 'invented', 'event:987:2:1:0:0:0',
                    'event:987:1:1:1:0:0', 'event:988:1:1:0:0:0'):
            bad_cases.append(dict(good, source=[dict(ref=ref, pitch=54)]))
        for part, voice in ((True, 0), (1, True), (-1, 0), (1, -1), (1.0, 0)):
            bad_cases.append(dict(good, backing_part=part, backing_voice=voice))
        bad_cases.extend([dict(good, source_context=None),
                          dict(good, source_context=dict(time_q='0', context_refs=[ANCHOR, BACKING[0]], qualifications=[])),
                          dict(good, source=[dict(ref=ANCHOR, pitch=54, focal_target_pitch=60)])])
        for args in bad_cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                stream.stream_relation(**args)

    def test_context_qualifications_are_carried_not_mutated_or_claimed_verified(self):
        sc = dict(time_q='0', context_refs=[ANCHOR], qualifications=['written_tie'])
        tc = dict(time_q='17/4', context_refs=[BACKING[1]], qualifications=['sounding_endpoint_unknown'])
        saved = deepcopy((sc, tc))
        result = stream.stream_relation([dict(ref=ANCHOR, pitch=54)], [dict(ref=BACKING[1], pitch=52)],
                                        backing_part=1, backing_voice=0, source_context=sc, target_context=tc)
        self.assertEqual((sc, tc), saved)
        self.assertEqual(result['source_context']['metadata_status'], 'SUPPLIED_NOT_INDEPENDENTLY_VERIFIED')
        result['target_context']['qualifications'].clear()
        self.assertEqual(tc['qualifications'], ['sounding_endpoint_unknown'])

    def test_both_sides_owned_and_held_anchor_reused_without_backup(self):
        before, top = fixture(); shared = top['musical_relationships']; snapshot = deepcopy(shared)
        links = stream.canonical_bindings(shared, correspondences(shared))
        self.assertEqual(len(links), 6)
        self.assertEqual(sum(r['backing_ref'] == ANCHOR for r in links), 3)
        wrapped = owner.lift(shared, links, tier1=before)
        self.assertEqual(owner.expand(wrapped), shared)
        self.assertEqual(shared, snapshot)
        top['musical_relationships'] = wrapped
        self.assertEqual(realize(top), before)
        body = owner._body(wrapped['core']); index = owner._index(body)
        for ref in SOURCE + TARGET:
            self.assertNotIn('bass_register_anchor', index[ref][0])
        self.assertNotIn('input', wrapped)
        self.assertNotIn('source_documents', wrapped)

    def test_structural_time_owner_uses_same_bindings_and_inverse(self):
        before, top = fixture(owned_time=True); shared = top['musical_relationships']
        self.assertEqual(shared['schema'], 'source-group-rhythm/2')
        self.assertTrue(shared['groups'])
        wrapped = owner.lift(shared, stream.canonical_bindings(shared, correspondences(shared)), tier1=before)
        self.assertEqual(owner.expand(wrapped), shared)
        top['musical_relationships'] = wrapped
        self.assertEqual(realize(top), before)

    def test_anchor_identity_independent_of_source_and_target_focal_pitches(self):
        _, top = fixture(); shared = top['musical_relationships']; rows = correspondences(shared)
        expected = stream.canonical_bindings(shared, rows)
        for ref, pitch in ((SOURCE[1], '74'), (TARGET[1], '7')):
            changed = deepcopy(shared); owner._index(changed)[ref][0]['bass_register_anchor'] = pitch
            rhythm.refresh(changed)
            self.assertEqual(stream.canonical_bindings(changed, rows), expected)

    def test_transposition_preserves_deltas_and_reference_binding(self):
        _, top = fixture(); shared = top['musical_relationships']; rows = correspondences(shared)
        shifted = music.transpose(shared, 12); changed_rows = correspondences(shifted)
        self.assertEqual([r['match']['selected_delta'] for r in rows],
                         [r['match']['selected_delta'] for r in changed_rows])
        self.assertEqual(stream.canonical_bindings(shared, rows), stream.canonical_bindings(shifted, changed_rows))
        with self.assertRaisesRegex(ValueError, 'current owned evidence'):
            stream.canonical_bindings(shifted, rows)

    def test_future_expired_or_missing_anchor_refuses(self):
        _, top = fixture(); shared = top['musical_relationships']
        for i, ref in ((0, BACKING[1]), (1, BACKING[0]), (0, ANCHOR)):
            with self.subTest(i=i, ref=ref), self.assertRaisesRegex(ValueError, 'not active'):
                stream.canonical_bindings(shared, [correspondence(shared, i, target_anchor=ref)])
        row = correspondence(shared, 0)
        row['match']['target_refs'] = ['event:987:1:99:0:0:0']
        with self.assertRaises(ValueError):
            stream.canonical_bindings(shared, [row])

    def test_unison_duplicates_and_different_pitch_overlap_refuse(self):
        for unknown, change in ((False, 0), (False, 1), (True, 0)):
            def edit(docs):
                notes = docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes']
                other = deepcopy(notes[0]); other['fret'] += change
                if unknown: other['dead'] = True
                notes.append(other)
            _, top = fixture(edit); shared = top['musical_relationships']; rows = correspondences(shared)
            with self.subTest(unknown=unknown, change=change), self.assertRaisesRegex(ValueError, 'complete active occurrence'):
                stream.canonical_bindings(shared, rows)

    def test_other_voice_is_an_explicitly_different_stream(self):
        def edit(docs):
            for measure in docs['track-1.json']['measures']:
                measure['voices'].append(dict(beats=[dict(duration=[1, 1], notes=[dict(string=5, fret=7)])]))
        _, top = fixture(edit); shared = top['musical_relationships']; rows = correspondences(shared)
        self.assertEqual(len(stream.canonical_bindings(shared, rows)), 6)
        rows[0]['match']['backing_voice'] = 1
        with self.assertRaisesRegex(ValueError, 'declared stream'):
            stream.canonical_bindings(shared, rows)

    def test_unknown_clock_is_not_rescued_by_nominal_numbers(self):
        _, top = fixture(); shared = top['musical_relationships']; rows = correspondences(shared)
        shared['source_quality']['layout_warnings'] = [dict(bar=1, reason='conflicting_track_meter')]
        for group in shared['coattacks']:
            group['timing_uncertain'] = group['bar'] == 1
        rhythm.refresh(shared)
        with self.assertRaisesRegex(ValueError, 'Unknown written clock'):
            stream.canonical_bindings(shared, rows)
        shared = deepcopy(top['musical_relationships']); owner._index(shared)[SOURCE[0]][0].pop('onset_q')
        with self.assertRaises(ValueError):
            stream.canonical_bindings(shared, rows)

    def test_stale_context_and_typed_claims_refuse_without_mutation(self):
        _, top = fixture(); shared = top['musical_relationships']; original = deepcopy(shared)
        mutations = [lambda r: r['match'].update(selected_delta=False),
                     lambda r: r['match'].update(source_pitch=54.0),
                     lambda r: r['match'].update(target_pitch=999),
                     lambda r: r['match']['source_context'].update(time_q='1/2'),
                     lambda r: r['match']['source_context'].update(context_refs=[]),
                     lambda r: r['match'].update(schema=motion.SCHEMA),
                     lambda r: r['match'].update(kind='sonority'),
                     lambda r: r.update(target_ref=SOURCE[0])]
        for mutate in mutations:
            rows = correspondences(shared); mutate(rows[0]); saved = deepcopy(rows)
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                stream.canonical_bindings(shared, rows)
            self.assertEqual(rows, saved); self.assertEqual(shared, original)

    def test_self_part_cycles_and_duplicate_owner_requests_refuse(self):
        _, top = fixture(); shared = top['musical_relationships']; rows = correspondences(shared)
        for focal in (ANCHOR, BACKING[0]):
            altered = deepcopy(rows); altered[0]['source_ref'] = focal
            with self.subTest(focal=focal), self.assertRaises(ValueError):
                stream.canonical_bindings(shared, altered)
        with self.assertRaisesRegex(ValueError, 'Duplicate target'):
            stream.canonical_bindings(shared, rows + [rows[0]])
        self.assertEqual(stream.canonical_bindings(shared, rows), stream.canonical_bindings(shared, list(reversed(rows))))


if __name__ == '__main__':
    unittest.main()
