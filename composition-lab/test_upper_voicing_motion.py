"""Shared upper-voice motion on existing dyads, not lookup/prediction evidence.

Original source observations remain distinct from current editable references.
These authored fixtures test the actual owners/inverse, without mocked music.
"""
from copy import deepcopy
import json
import unittest

import backing_pitch_ownership as backing
import upper_voicing_motion as motion
from connected_tier2 import analyze, strip_lower, realize
from source_fact_tier1 import extract_documents, project_documents
from test_execution_dependencies import documents, n

SOURCE = [f'event:86:0:1:0:{i}:0' for i in range(3)]
TARGET = [f'event:86:0:2:0:{i}:0' for i in range(3)]
PEER = [f'event:86:1:2:0:{i}:0' for i in range(3)]


def fixture(*, coupled=True):
    docs = documents([n(0), n(2), n(4), n(5)])
    def measure(frets):
        beats = [dict(duration=[1, 4], notes=[dict(string=2, fret=f),
                                             dict(string=4, fret=5)]) for f in frets]
        beats.append(dict(duration=[1, 4], notes=[dict(rest=True)]))
        return dict(signature=[4, 4], voices=[dict(beats=beats)])
    docs['track-0.json']['measures'] = [measure((2, 3, 5)), measure((2, 2, 2))]
    peer = deepcopy(docs['track-0.json']); peer['partId'] = 1
    extra = deepcopy(peer); extra['partId'] = 2
    for bar in extra['measures']:
        for beat in bar['voices'][0]['beats'][:3]:
            beat['notes'] = [dict(string=0, fret=3)]
    docs['track-1.json'], docs['track-2.json'] = peer, extra
    docs['metadata.json']['tracks'] += [dict(name='Explicit coupled voice', instrumentId=25),
                                      dict(name='Independent voice', instrumentId=25)]
    lower = extract_documents(docs)
    upper = strip_lower(analyze(lower))
    if coupled:
        upper['musical_relationships'] = backing.lift(upper['musical_relationships'],
            [dict(occurrence_ref=p, backing_ref=t) for p, t in zip(PEER, TARGET)],
            tier1=lower, member_scope=True, preserve_execution=True)
    before_ownership = deepcopy(upper)
    bindings = [dict(source_ref=s, target_ref=t) for s, t in zip(SOURCE, TARGET)]
    upper['musical_relationships'] = motion.lift(upper['musical_relationships'], lower,
        bindings, source_origin=upper['source_origin'])
    return docs, lower, upper, before_ownership, bindings


def request(level=100, intent='follow_reference_upper_motion', seed=0):
    return dict(context_policy='source_upper_voicing_motion', voicing=level,
                intent=intent, seed=seed)


def stored_body(upper):
    core = upper['musical_relationships']['core']
    if core.get('schema') in backing.SCHEMAS:
        core = core['core']
    return backing._body(core)


def expected_follow(docs):
    expected = deepcopy(docs)
    for part in (0, 1):
        for beat, fret in zip(expected[f'track-{part}.json']['measures'][1]['voices'][0]['beats'], (2, 3, 5)):
            beat['notes'][0]['fret'] = fret
    return expected


class UpperVoicingMotionTests(unittest.TestCase):
    def test_same_equation_identifies_common_base_and_binary_motion(self):
        source = ['7', '8', '10']
        for target, wanted in ((['7', '7', '7'], 0), (['9', '10', '12'], 1)):
            solved = motion.relation(source_intervals=source, target_intervals=target)
            self.assertEqual(solved['base_interval'], target[0])
            self.assertEqual(solved['motion'], wanted)
            inverse = motion.relation(source_intervals=source,
                                      base_interval=solved['base_interval'], motion=wanted)
            self.assertEqual(inverse['target_intervals'], target)
        for source, target in ((['7', '7'], ['7', '7']),
                               (['7', '8', '10'], ['7', '9', '10'])):
            with self.assertRaises(ValueError):
                motion.relation(source_intervals=source, target_intervals=target)
        for invalid in (True, 1.0, -1, 2, None):
            with self.assertRaises(ValueError):
                motion.relation(source_intervals=['7', '8'], base_interval='7', motion=invalid)

    def test_forward_exact_baseline_and_sole_controlled_member_authority(self):
        _, lower, upper, original, _ = fixture()
        model = upper['musical_relationships']
        self.assertEqual(model['schema'], 'source-upper-voicing-motion/1')
        self.assertEqual(model['parameters'], dict(base_interval='7', motion=0))
        index = backing._index(stored_body(upper))
        for ref in TARGET:
            group, member = index[ref]
            self.assertNotIn('voicing_interval', member)
            self.assertEqual(group['bass_register_anchor'], '50')
            self.assertEqual(next(m for m in group['members'] if m['id'] != ref)['voicing_interval'], '0')
        self.assertEqual(model['core']['schema'], backing.MEMBER_SCHEMA)
        self.assertEqual(model['core']['relationships'], original['musical_relationships']['relationships'])
        self.assertEqual(realize(upper), lower)
        snapshot = deepcopy(upper)
        zero, _ = motion.intervene(upper, request(0))
        self.assertEqual(zero, upper)
        self.assertEqual(upper, snapshot)

    def test_follow_realizes_reference_motion_and_only_two_upper_voices_change(self):
        docs, _, upper, _, _ = fixture()
        snapshot = deepcopy(upper)
        final, decision = motion.intervene(upper, request())
        self.assertEqual(project_documents(realize(final)), expected_follow(docs))
        self.assertTrue(decision['changed'])
        self.assertEqual(final['musical_relationships']['parameters'], dict(base_interval='7', motion=1))
        self.assertEqual(final['musical_relationships']['core'], upper['musical_relationships']['core'])
        self.assertEqual(final['musical_relationships']['observations'], upper['musical_relationships']['observations'])
        self.assertEqual(final['owned_parameters'], upper['owned_parameters'])
        self.assertEqual(upper, snapshot)

    def test_shared_base_moves_all_upper_targets_and_peer_but_not_lowers_or_reference(self):
        docs, _, upper, _, _ = fixture()
        changed = deepcopy(upper)
        changed['musical_relationships']['parameters']['base_interval'] = '8'
        expected = deepcopy(docs)
        for part in (0, 1):
            for beat in expected[f'track-{part}.json']['measures'][1]['voices'][0]['beats'][:3]:
                beat['notes'][0]['fret'] += 1
        self.assertEqual(project_documents(realize(changed)), expected)

    def test_current_reference_interval_propagates_only_with_motion_without_rewriting_observations(self):
        docs, _, upper, _, _ = fixture()
        for intent, follows in (('repeat_upper_interval', False),
                                ('follow_reference_upper_motion', True)):
            with self.subTest(intent=intent):
                initial, _ = motion.intervene(upper, request(intent=intent))
                saved = json.loads(json.dumps(initial))
                observed = deepcopy(saved['musical_relationships']['observations'])
                _, member = backing._index(stored_body(saved))[SOURCE[1]]
                member['voicing_interval'] = '9'  # Current8→9; original observation stays8.
                expected = expected_follow(docs) if follows else deepcopy(docs)
                expected['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['fret'] += 1
                if follows:
                    for part in (0, 1):
                        expected[f'track-{part}.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0]['fret'] += 1
                self.assertEqual(project_documents(realize(saved)), expected)
                self.assertEqual(saved['musical_relationships']['observations'], observed)

    def test_json_saved_switch_repeat_and_current_zero_keep_original_observations(self):
        _, lower, upper, _, _ = fixture()
        followed, _ = motion.intervene(upper, request())
        saved = json.loads(json.dumps(followed))
        observations = deepcopy(saved['musical_relationships']['observations'])
        snapshot = deepcopy(saved)
        current_zero, _ = motion.intervene(saved, request(0))
        self.assertEqual(current_zero, saved)
        again, decision = motion.intervene(saved, request())
        self.assertFalse(decision['changed'])
        self.assertEqual(realize(again), realize(saved))
        repeated, _ = motion.intervene(saved, request(intent='repeat_upper_interval'))
        self.assertEqual(realize(repeated), lower)
        self.assertEqual(repeated['musical_relationships']['observations'], observations)
        self.assertEqual(saved, snapshot)

    def test_seeded_half_has_both_release_outcomes_and_no_partial_mutation(self):
        _, lower, upper, _, _ = fixture()
        snapshot = deepcopy(upper)
        decisions = []
        for seed in range(12):
            final, decision = motion.intervene(upper, request(50, seed=seed))
            decisions.append(decision['released'])
            self.assertEqual(realize(final) != lower, decision['released'])
        self.assertEqual(set(decisions), {False, True})
        self.assertEqual(upper, snapshot)

    def test_duplicate_scalar_invalid_motion_and_conflicting_binding_refuse(self):
        _, lower, upper, original, bindings = fixture()
        for parameters in (dict(base_interval='7', motion=True),
                           dict(base_interval='7', motion=2), dict(base_interval='-1', motion=0)):
            corrupt = deepcopy(upper)
            corrupt['musical_relationships']['parameters'] = parameters
            with self.assertRaises(ValueError):
                realize(corrupt)
        corrupt = deepcopy(upper)
        backing._index(stored_body(corrupt))[TARGET[0]][1]['voicing_interval'] = '7'
        with self.assertRaises(ValueError):
            realize(corrupt)
        bad = deepcopy(bindings); bad[1]['target_ref'] = bad[0]['target_ref']
        snapshot = deepcopy(original)
        with self.assertRaises(ValueError):
            motion.lift(original['musical_relationships'], lower, bad, source_origin=original['source_origin'])
        self.assertEqual(original, snapshot)

    def test_unrelated_existing_voice_still_moves_after_save_without_ownership_loss(self):
        _, _, upper, _, _ = fixture()
        followed, _ = motion.intervene(upper, request())
        saved = json.loads(json.dumps(followed))
        original = deepcopy(saved)
        group = backing._index(stored_body(saved))['event:86:2:1:0:0:0'][0]
        group['bass_register_anchor'] = '68'
        before, after = project_documents(realize(original)), project_documents(realize(saved))
        before['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret'] += 1
        self.assertEqual(after, before)

    def test_controls_refuse_atomically_without_source_or_model_changes(self):
        _, _, upper, _, _ = fixture()
        for bad in (dict(request(), voicing=True), dict(request(), voicing=float('nan')),
                    dict(request(), voicing=-1), dict(request(), seed=True),
                    dict(request(), intent='guess_artist_choice'),
                    dict(request(), target_intervals=['7', '8', '10'])):
            with self.subTest(control=bad):
                snapshot = deepcopy(upper)
                with self.assertRaises(ValueError):
                    motion.intervene(upper, bad)
                self.assertEqual(upper, snapshot)

    def test_original_evidence_intake_refuses_changed_core_bound_to_untouched_tier1(self):
        _, lower, _, original, bindings = fixture()
        shared = deepcopy(original['musical_relationships'])
        body = backing._body(shared['core'])
        backing._index(body)[SOURCE[1]][1]['voicing_interval'] = '9'
        snapshot = deepcopy(shared)
        # The historical digest is genuine, but this supplied current core is
        # no longer its score. Forward intake must not call9 an original vote.
        with self.assertRaises(ValueError):
            motion.lift(shared, lower, bindings, source_origin=original['source_origin'])
        self.assertEqual(shared, snapshot)

    def test_original_upper_observation_domain_is_positive_integral_not_just_canonical_rational(self):
        _, _, upper, _, _ = fixture()
        for values in (['-7', '-8', '-10'], ['7', '15/2', '10']):
            with self.subTest(values=values):
                corrupt = deepcopy(upper)
                corrupt['musical_relationships']['observations']['source_intervals'] = values
                snapshot = deepcopy(corrupt)
                with self.assertRaises(ValueError):
                    realize(corrupt)
                self.assertEqual(corrupt, snapshot)


if __name__ == '__main__':
    unittest.main()
