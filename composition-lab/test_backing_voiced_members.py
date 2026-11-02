"""Independent upper-member ownership tests; authored data, no fit claim.

The lower anchor and other member intervals remain authoritative. Actual source
facts and later backing propagation must agree, not merely standalone validity.
"""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest

import backing_pitch_ownership as owner
from connected_tier2 import analyze, strip_lower, realize
from source_fact_tier1 import extract_documents, project_documents
from test_execution_dependencies import documents, n

UPPER = 'event:86:0:1:0:0:0'
MIDDLE = 'event:86:0:1:0:0:1'
LOWER = 'event:86:0:1:0:0:2'
BACKING = 'event:86:1:1:0:0:0'
OTHER_BACKING = 'event:86:1:1:0:1:0'
EXTRA = 'event:86:2:1:0:0:0'


def fixture(*, unknown_slide=False, unknown_target=False):
    docs = documents([n(0), n(2), n(4), n(5)])
    for i, beat in enumerate(docs['track-0.json']['measures'][0]['voices'][0]['beats']):
        beat['notes'] = [dict(string=1, fret=3+i), dict(string=2, fret=2), dict(string=4, fret=5)]
    if unknown_slide:
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['slide'] = 'downwards'
    if unknown_target:
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['dead'] = True
    source = deepcopy(docs['track-0.json'])
    source['partId'] = 1
    for i, beat in enumerate(source['measures'][0]['voices'][0]['beats']):
        beat['notes'] = [dict(string=1, fret=3+i), dict(string=4, fret=5)]
    extra = deepcopy(source)
    extra['partId'] = 2
    for beat in extra['measures'][0]['voices'][0]['beats']:
        beat['notes'] = [dict(string=0, fret=3)]
    docs['track-1.json'], docs['track-2.json'] = source, extra
    docs['metadata.json']['tracks'] += [dict(name='Explicit backing', instrumentId=25),
                                      dict(name='Unrelated existing owner', instrumentId=25)]
    lower = extract_documents(docs)
    return docs, lower, strip_lower(analyze(lower))


def binding(target=UPPER, backing=BACKING):
    return dict(occurrence_ref=target, backing_ref=backing)


def owned(upper, lower, links=None):
    result = deepcopy(upper)
    result['musical_relationships'] = owner.lift(upper['musical_relationships'],
        [binding()] if links is None else links, tier1=lower,
        member_scope=True, preserve_execution=True)
    return result


def rows(model):
    return {row['occurrence_ref']: row for row in model['relationships']}


def move_backing(upper, delta=1):
    result = deepcopy(upper)
    group, _ = owner._index(owner._body(result['musical_relationships']['core']))[BACKING]
    group['bass_register_anchor'] = str(F(group['bass_register_anchor']) + delta)
    return result


class BackingVoicedMemberTests(unittest.TestCase):
    def test_exact_zero_sole_member_authority_complete_coattack_retained(self):
        docs, lower, upper = fixture()
        snapshot = deepcopy(upper)
        result = owned(upper, lower)
        model = result['musical_relationships']
        self.assertEqual(model['schema'], 'backing-relative-pitches/4')
        group, selected = owner._index(owner._body(model['core']))[UPPER]
        original_group, _ = owner._index(upper['musical_relationships'])[UPPER]
        self.assertEqual(group['bass_register_anchor'], original_group['bass_register_anchor'])
        self.assertNotIn('voicing_interval', selected)
        expected = deepcopy(original_group)
        expected.pop('interpretation', None)  # Recomputed view, not an owner.
        del next(m for m in expected['members'] if m['id'] == UPPER)['voicing_interval']
        self.assertEqual(group, expected)
        self.assertEqual(rows(model)[UPPER]['interval_semitones'], '0')
        self.assertEqual(realize(result), lower)
        self.assertEqual(project_documents(realize(result)), docs)
        self.assertEqual(upper, snapshot)

    def test_saved_backing_move_propagates_upper_only_and_preserves_lower_and_middle(self):
        docs, lower, upper = fixture()
        result = json.loads(json.dumps(owned(upper, lower)))
        snapshot = deepcopy(result)
        moved = move_backing(result)
        expected = deepcopy(docs)
        for note in expected['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes']:
            note['fret'] += 1
        expected['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret'] += 1
        self.assertEqual(project_documents(realize(moved)), expected)
        self.assertEqual(rows(moved['musical_relationships']), rows(result['musical_relationships']))
        self.assertEqual(result, snapshot)

    def test_append_second_upper_member_preserves_first_link_and_every_other_authority(self):
        _, lower, upper = fixture()
        first = owned(upper, lower)
        snapshot = deepcopy(first)
        old = deepcopy(rows(first['musical_relationships'])[UPPER])
        second = deepcopy(first)
        second['musical_relationships'] = owner.extend_bindings(first['musical_relationships'],
            [binding(MIDDLE)], tier1=lower, member_scope=True, preserve_execution=True)
        self.assertEqual(rows(second['musical_relationships'])[UPPER], old)
        owner.assert_preserved(first['musical_relationships'], second['musical_relationships'])
        self.assertEqual(realize(second), lower)
        self.assertEqual(first, snapshot)
        duplicate = owner.extend_bindings(second['musical_relationships'], [binding(MIDDLE)],
            tier1=lower, member_scope=True, preserve_execution=True)
        self.assertEqual(duplicate, second['musical_relationships'])

    def test_adding_to_existing_v3_does_not_erase_unrelated_singleton_dependency(self):
        docs, lower, upper = fixture()
        old = owner.lift(upper['musical_relationships'], [binding(EXTRA)],
                         tier1=lower, preserve_execution=True)
        old_snapshot = deepcopy(old)
        extended = owner.extend_bindings(old, [binding()], tier1=lower,
                                         member_scope=True, preserve_execution=True)
        owner.assert_preserved(old, extended)
        self.assertEqual(rows(extended)[EXTRA], rows(old)[EXTRA])
        self.assertEqual(extended['schema'], 'backing-relative-pitches/4')
        upper['musical_relationships'] = extended
        moved = move_backing(json.loads(json.dumps(upper)))
        expected = deepcopy(docs)
        for note in expected['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes']:
            note['fret'] += 1
        expected['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret'] += 1
        expected['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret'] += 1
        self.assertEqual(project_documents(realize(moved)), expected)
        self.assertEqual(old, old_snapshot)

    def test_lower_unknown_same_part_and_dependency_cycles_refuse_atomically(self):
        _, lower, upper = fixture()
        for links in ([binding(LOWER)], [binding(backing=MIDDLE)],
                      [binding(), binding(BACKING, UPPER)]):
            with self.subTest(links=links):
                snapshot = deepcopy(upper)
                with self.assertRaises(ValueError):
                    owned(upper, lower, links)
                self.assertEqual(upper, snapshot)
        _, lower, unknown = fixture(unknown_target=True)
        snapshot = deepcopy(unknown)
        with self.assertRaises(ValueError):
            owned(unknown, lower)
        self.assertEqual(unknown, snapshot)

    def test_conflicting_rebind_and_chain_extension_refuse_without_mutation(self):
        _, lower, upper = fixture()
        model = owned(upper, lower)['musical_relationships']
        for links in ([binding(backing=OTHER_BACKING)], [binding(BACKING, UPPER)]):
            snapshot = deepcopy(model)
            with self.assertRaises(ValueError):
                owner.extend_bindings(model, links, tier1=lower,
                                      member_scope=True, preserve_execution=True)
            self.assertEqual(model, snapshot)

    def test_equal_or_crossing_retained_lower_and_duplicate_interval_fail_shared_inverse(self):
        _, lower, upper = fixture()
        valid = owned(upper, lower)
        for interval in ('-12', '-13'):
            corrupt = deepcopy(valid)
            corrupt['musical_relationships']['relationships'][0]['interval_semitones'] = interval
            snapshot = deepcopy(corrupt)
            with self.assertRaises(ValueError):
                realize(corrupt)
            self.assertEqual(corrupt, snapshot)
        corrupt = deepcopy(valid)
        _, member = owner._index(owner._body(corrupt['musical_relationships']['core']))[UPPER]
        member['voicing_interval'] = '12'
        with self.assertRaises(ValueError):
            realize(corrupt)

    def test_unknown_outgoing_execution_and_nonexplicit_scope_refuse(self):
        _, lower, upper = fixture(unknown_slide=True)
        snapshot = deepcopy(upper)
        with self.assertRaises(ValueError):
            owned(upper, lower)
        self.assertEqual(upper, snapshot)
        _, lower, upper = fixture()
        for extra in ({}, dict(member_scope=True, preserve_execution=False),
                      dict(member_scope=1, preserve_execution=True)):
            with self.subTest(extra=extra):
                snapshot = deepcopy(upper)
                with self.assertRaises(ValueError):
                    owner.lift(upper['musical_relationships'], [binding()], tier1=lower, **extra)
                self.assertEqual(upper, snapshot)

    def test_actual_source_denied_inverse_zero_parameter_change_and_crossing_refusal(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        docs, lower, upper = fixture()
        valid = owned(upper, lower)
        snapshot = deepcopy(valid)
        code, _ = bundle(Path(__file__).parent)
        moved = deepcopy(valid)
        moved['musical_relationships']['relationships'][0]['interval_semitones'] = '1'
        expected = deepcopy(docs)
        expected['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret'] += 1
        crossing = deepcopy(valid)
        crossing['musical_relationships']['relationships'][0]['interval_semitones'] = '-12'
        with tempfile.TemporaryDirectory() as folder:
            for name, model, wanted in (('zero', valid, lower),
                                        ('parameter', moved, extract_documents(expected))):
                receipt = execute(code, model, dict(variation=0), wanted,
                                  Path(folder) / name, timeout=30)
                self.assertEqual(receipt['status'], 'PASS', receipt)
            denied = Path(folder) / 'crossing'
            receipt = execute(code, crossing, dict(variation=0), lower, denied, timeout=30)
            self.assertEqual(receipt['status'], 'FAIL', receipt)
            self.assertFalse((denied / 'worker/output.json').exists())
        self.assertEqual(valid, snapshot)


if __name__ == '__main__':
    unittest.main()
