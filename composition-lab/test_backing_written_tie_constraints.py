"""Authored boundary cases for one saved predicate; no artist-data fixture."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import backing_motion_intervention as motion
import backing_pitch_ownership as owner
import backing_written_tie_constraints as ties
from connected_tier2 import analyze, strip_lower, realize, validate
from source_fact_tier1 import extract_documents
from test_backing_motion_intervention import documents, controls, SOURCE, TARGET


def fixture(reference=False, target=True, unchanged=False, rhythm=False, target_fret=None):
    docs = documents()
    for bar, enabled in ((0, reference), (1, target)):
        if not enabled:
            continue
        beats = docs['track-0.json']['measures'][bar]['voices'][0]['beats']
        if bar == 1 and target_fret is not None:
            beats[2]['notes'][0]['fret'] = target_fret
        if unchanged and bar == 1:
            # A source-identical target with backing identical at each attack.
            for a, b in zip(docs['track-0.json']['measures'][0]['voices'][0]['beats'][:3], beats[:3]):
                b['notes'] = deepcopy(a['notes'])
            docs['track-1.json']['measures'][1] = deepcopy(docs['track-1.json']['measures'][0])
        last = deepcopy(beats[2]['notes'][0]); last['tie'] = True
        beats[3:] = [dict(duration=[1,8], notes=[last]), dict(duration=[5,8], notes=[dict(rest=True)])]
    if rhythm:
        for measure in docs['track-0.json']['measures']:
            beats = measure['voices'][0]['beats']
            beats[0]['beamStart'] = True; beats[2]['beamStop'] = True
            for beat, kind in zip(beats, (16,16,8)):
                beat['type'] = kind
    lower = extract_documents(docs)
    top = strip_lower(analyze(lower, rhythm_groups=rhythm,
                             rhythm_group_profile='written_time' if rhythm else 'plain_repeat'))
    prepared = motion.prepare(top, controls())
    owned = motion.own_intervals(top, prepared)
    return lower, top, prepared, owned


class WrittenTieConstraintTests(unittest.TestCase):
    def test_same_predicate_filters_only_bad_candidate_and_keeps_zero(self):
        for rhythm in (False, True):
            lower, top, prepared, owned = fixture(rhythm=rhythm)
            self.assertEqual(prepared['options'], [])
            self.assertEqual(len(prepared['execution_rejections']), len(prepared['physical']['assignments']))
            self.assertTrue(all('WRITTEN_TIE_LOCK_CONFLICT' in r['reason'] for r in prepared['execution_rejections']))
            self.assertEqual(realize(owned), lower)
            self.assertEqual(validate(owned), lower)
            for amount in (0, 50, 100):
                changed, decision = motion.intervene(top, dict(controls(), melody=amount))
                self.assertEqual(realize(changed), lower)
                self.assertFalse(decision['changed'])

    def test_saved_relationship_has_no_original_pitch_or_contact_payload(self):
        _, _, _, owned = fixture()
        model = owned['musical_relationships']; scope = model['written_tie_constraints']
        self.assertEqual(model['schema'], owner.SCHEMA)
        self.assertEqual(len(scope['relations']), 1)
        self.assertEqual(scope['relations'][0]['origin_ref'], TARGET[-1])
        self.assertEqual(scope['relations'][0]['destination_ref'], 'event:987:0:2:0:3:0')
        self.assertEqual(set(scope['relations'][0]), ties.RELATION_FIELDS)
        self.assertEqual(len(scope['incidence']), 6)
        for entry in model['core']['coattacks']:
            if entry['members'][0]['id'] in SOURCE+TARGET:
                self.assertNotIn('bass_register_anchor', entry)

    def test_direct_pitch_and_string_edits_fail_in_shared_inverse(self):
        _, _, _, owned = fixture()
        bad = deepcopy(owned)
        link = next(r for r in bad['musical_relationships']['relationships'] if r['occurrence_ref'] == TARGET[-1])
        link['interval_semitones'] = str(int(link['interval_semitones'])+5)
        with self.assertRaisesRegex(ValueError, 'WRITTEN_TIE_LOCK_CONFLICT'):
            realize(bad)
        _, _, _, string_owned = fixture(target_fret=7)
        bad = deepcopy(string_owned)
        ref = 'track-0.json#/measures/1/voices/0/beats/2/notes/0/string'
        row = next(r for r in bad['owned_parameters']['source_choices'] if r['fact_ref'] == ref)
        row['parameter']['normalized'] = '2'
        with self.assertRaisesRegex(ValueError, 'WRITTEN_TIE_LOCK_CONFLICT'):
            realize(bad)

    def test_omitted_constraints_and_incidence_cannot_disable_the_lock(self):
        _, _, _, owned = fixture()
        for mode in ('field', 'relation', 'both'):
            bad = deepcopy(owned); model = bad['musical_relationships']
            if mode == 'field':
                del model['written_tie_constraints']
            else:
                model['written_tie_constraints']['relations'] = []
                if mode == 'both':
                    for row in model['written_tie_constraints']['incidence']:
                        row['relation_refs'] = []
            with self.assertRaises(ValueError):
                realize(bad)

    def test_reference_only_and_unchanged_target_ties_are_allowed(self):
        for kwargs in (dict(reference=True, target=False), dict(unchanged=True)):
            lower, top, prepared, owned = fixture(**kwargs)
            self.assertTrue(prepared['options'])
            self.assertEqual(prepared['execution_rejections'], [])
            changed, decision = motion.intervene(top, controls())
            after = realize(changed)
            if kwargs.get('unchanged'):
                self.assertEqual(after, lower)
            else:
                self.assertTrue(decision['changed'])
                self.assertNotEqual(after, lower)
                # Original reference tie remains in the same saved validator.
                self.assertEqual(changed['musical_relationships']['written_tie_constraints'],
                                 owned['musical_relationships']['written_tie_constraints'])

    def test_legacy_v1_remains_readable_without_claiming_new_tie_guard(self):
        lower, top, prepared, _ = fixture()
        from canonical_backing_bindings import canonical_bindings
        old = deepcopy(top)
        bindings = canonical_bindings(top['musical_relationships'], prepared['correspondences'])
        old['musical_relationships'] = owner.legacy_relift(top['musical_relationships'], bindings)
        self.assertEqual(old['musical_relationships']['schema'], owner.LEGACY_SCHEMA)
        self.assertEqual(realize(old), lower)
        self.assertEqual(validate(old), lower)

    def test_actual_source_denied_worker_refuses_direct_tie_corruption(self):
        from qa_isolation_harness import execute
        from run_connected_tier2_qa import bundle
        lower, _, _, owned = fixture()
        bad = deepcopy(owned)
        link = next(r for r in bad['musical_relationships']['relationships'] if r['occurrence_ref'] == TARGET[-1])
        link['interval_semitones'] = str(int(link['interval_semitones'])+5)
        code, _ = bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'refused'
            # Only the stripped parameter model, controls and exact code enter.
            receipt = execute(code, bad, {'variation': 0}, lower, root, timeout=40)
            self.assertEqual(receipt['status'], 'FAIL')
            audit = json.loads((root/'worker'/'audit.json').read_text())
            self.assertIn('WRITTEN_TIE_LOCK_CONFLICT', audit['error']['message'])
            self.assertFalse((root/'worker'/'output.json').exists())


if __name__ == '__main__':
    unittest.main()
