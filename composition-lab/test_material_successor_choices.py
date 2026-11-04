"""Declaration-only written successor choices; no ringing-end inference."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import backing_execution_constraints as execution
import connected_tier2 as connected
import material_execution_locks as locks
import musical_support_material as material
from source_fact_tier1 import extract_documents
from test_execution_dependencies import documents, n
from test_material_execution_locks import source, state, ref


def saved(value):
    return json.loads(json.dumps(value))


def upgraded(docs):
    lower, records, refs = state(docs)
    legacy = locks.capture(lower, records, refs)
    current = locks.upgrade_successor_choices(legacy, lower, records, refs)
    return lower, records, refs, legacy, current


class MaterialSuccessorChoiceTests(unittest.TestCase):
    def test_upgrade_is_explicit_keeps_legacy_evidence_and_exact_current_context(self):
        for kind in ('ring', 'exit'):
            with self.subTest(kind=kind):
                lower, records, refs, legacy, current = upgraded(source(kind))
                before = deepcopy(legacy)
                self.assertEqual(current['schema'], locks.SUCCESSOR_SCHEMA)
                self.assertEqual(current['legacy_guard_sha256'], locks._hash(legacy))
                self.assertEqual(locks._legacy_guard(current), legacy)
                self.assertEqual(locks.validate(current, lower, records, refs),
                                 locks.validate(legacy, lower, records, refs))
                scope = locks.choice_scope(current, lower, records, refs)
                self.assertEqual(scope['covered_refs'], scope['pitch_flexible_refs'])
                self.assertEqual(scope['strict_refs'], [])
                self.assertEqual(locks.pitch_flexible_refs(legacy, lower, records, refs), [])
                self.assertEqual(legacy, before)
                text = json.dumps(current)
                for field in ('"pitch"', '"fret"', '"notes"', '"duration_q"', '"performed_end_q"'):
                    self.assertNotIn(field, text)

    def test_fret_changes_preserve_unknown_meaning_through_saved_successive_edits(self):
        for kind in ('ring', 'exit'):
            docs = source(kind)
            lower, records, refs, legacy, current = upgraded(docs)
            before = deepcopy(current)
            for value in (3, 5):
                changed = deepcopy(docs)
                beats = changed['track-0.json']['measures'][0]['voices'][0]['beats']
                beats[0]['notes'][0]['fret'] = value
                beats[2]['notes'][0]['fret'] = value+3
                after, new_records, new_refs = state(changed)
                self.assertEqual(records, new_records)
                self.assertEqual(locks.validate(saved(current), after, new_records, new_refs),
                                 locks.validate(current, lower, records, refs))
                with self.assertRaisesRegex(ValueError, 'context changed'):
                    locks.validate(legacy, after, new_records, new_refs)
            self.assertEqual(current, before)

    def test_constructor_cannot_rebaseline_an_edited_or_forged_legacy_guard(self):
        docs = source('ring'); lower, records, refs, legacy, current = upgraded(docs)
        changed = deepcopy(docs)
        changed['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret'] = 3
        with self.assertRaisesRegex(ValueError, 'context changed'):
            locks.upgrade_successor_choices(legacy, *state(changed))
        forged = deepcopy(legacy); forged['locks'][0]['fingerprint'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'context changed'):
            locks.upgrade_successor_choices(forged, lower, records, refs)
        with self.assertRaisesRegex(ValueError, 'original v1'):
            locks.upgrade_successor_choices(current, lower, records, refs)

    def test_string_successor_membership_clock_and_unknown_pitch_status_stay_locked(self):
        for kind in ('ring', 'exit'):
            docs = source(kind); _, _, _, _, guard = upgraded(docs)
            for change in ('origin_string', 'next_string', 'insert', 'duration', 'dead', 'grace', 'tie', 'declaration'):
                changed = deepcopy(docs)
                beats = changed['track-0.json']['measures'][0]['voices'][0]['beats']
                if change == 'origin_string': beats[0]['notes'][0]['string'] -= 1
                elif change == 'next_string': beats[2]['notes'][0]['string'] -= 1
                elif change == 'insert': beats[1]['notes'] = [n(3)]
                elif change == 'duration': beats[0]['duration'] = [1,8]; beats[1]['duration'] = [3,8]
                elif change == 'dead': beats[0]['notes'][0]['dead'] = True
                elif change == 'grace': beats[0]['graceNote'] = True
                elif change == 'tie': beats[0]['notes'][0]['tie'] = True
                elif kind == 'ring': beats[0]['letRing'] = False
                else: beats[0]['notes'][0]['slide'] = 'upwards'
                before = deepcopy(guard)
                with self.subTest(kind=kind, change=change), self.assertRaises(ValueError):
                    locks.validate(guard, *state(changed))
                self.assertEqual(guard, before)

    def test_new_same_string_contact_in_another_voice_remains_a_refusal(self):
        docs = source('ring'); _, _, _, _, guard = upgraded(docs)
        docs['track-0.json']['measures'][0]['voices'].append(dict(beats=[
            dict(duration=[1,4], notes=[dict(rest=True)]),
            dict(duration=[1,4], notes=[n(3)]),
            dict(duration=[1,2], notes=[dict(rest=True)])]))
        with self.assertRaisesRegex(ValueError, 'context changed'):
            locks.validate(guard, *state(docs))

    def test_unrelated_string_and_later_numeric_edit_remain_independent(self):
        docs = source('ring'); _, _, _, _, guard = upgraded(docs)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'] = [dict(string=4, fret=3)]
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['fret'] = 9
        locks.validate(guard, *state(docs))

    def test_other_unresolved_gestures_keep_numeric_fingerprints_in_mixed_guard(self):
        for kind in ('hp', 'shift', 'legato'):
            notes = [n(2), n(4), n(7, hp=True), n(7)] if kind == 'hp' else [n(2), n(4), n(7, slide=kind), None]
            docs = documents(notes, {0:dict(letRing=True)})
            lower, records, refs, _, guard = upgraded(docs)
            scope = locks.choice_scope(guard, lower, records, refs)
            self.assertIn(ref(2), scope['strict_refs'])
            self.assertNotIn(ref(2), scope['pitch_flexible_refs'])
            changed = deepcopy(docs)
            beats = changed['track-0.json']['measures'][0]['voices'][0]['beats']
            beats[2]['notes'][0]['fret'] = 8
            if kind == 'hp': beats[3]['notes'][0]['fret'] = 8
            after, new_records, new_refs = state(changed)
            self.assertEqual(records, new_records)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'context changed'):
                locks.validate(guard, after, new_records, new_refs)

    def test_overlapping_strict_policy_wins_over_numeric_permission(self):
        docs = documents([n(2, hp=True), n(2), n(4), n(7)], {0:dict(letRing=True)})
        lower, records, refs, _, guard = upgraded(docs)
        scope = locks.choice_scope(guard, lower, records, refs)
        self.assertIn(ref(0), scope['covered_refs'])
        self.assertIn(ref(0), scope['strict_refs'])
        self.assertNotIn(ref(0), scope['pitch_flexible_refs'])
        self.assertNotIn(ref(1), scope['pitch_flexible_refs'])

    def test_known_hopo_and_slide_relationships_still_use_existing_material_validator(self):
        for kind in ('hp', 'shift', 'legato'):
            marking = dict(hp=True) if kind == 'hp' else dict(slide=kind)
            docs = documents([n(2), n(4), n(7, **marking), n(9)], {0:dict(letRing=True)})
            lower = extract_documents(docs)
            top = connected.strip_lower(connected.analyze(lower))
            plain = material.fit(top, parts=[0], first_bar=1, last_bar=1, lower=lower)
            guard = locks.upgrade_successor_choices(plain['unresolved_execution_locks'], lower,
                plain['observed_execution'], plain['lower_tier']['realization_order'])
            changed = deepcopy(docs)
            changed['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['fret'] = 6
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'MATERIAL_EXECUTION_CHANGED'):
                material.validate_execution(plain, extract_documents(changed), execution_locks=guard)

    def test_legacy_commitment_and_active_projection_tampering_refuse(self):
        lower, records, refs, _, current = upgraded(source('ring'))
        for field in ('fingerprint', 'successor_fingerprint', 'legacy_guard_sha256', 'missing', 'payload'):
            changed = deepcopy(current)
            if field == 'legacy_guard_sha256': changed[field] = '0'*64
            elif field == 'missing': changed['locks'][0].pop('successor_fingerprint')
            elif field == 'payload': changed['locks'][0]['notes'] = [60]
            else: changed['locks'][0][field] = '0'*64
            with self.subTest(field=field), self.assertRaises(ValueError):
                locks.validate(changed, lower, records, refs)

    def test_no_source_or_files_are_needed_after_saved_upgrade(self):
        docs = source('ring'); _, _, _, _, guard = upgraded(docs)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret'] = 3
        lower, records, refs = state(docs); guard = saved(guard)
        execution._snapshot.cache_clear()
        with patch('builtins.open', side_effect=AssertionError('Source file access')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('Source file access')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('Source file access')):
            locks.validate(guard, lower, records, refs)

    def test_guard_without_eligible_policy_cannot_claim_numeric_release(self):
        lower, records, refs = state(source('hp'))
        guard = locks.capture(lower, records, refs)
        with self.assertRaisesRegex(ValueError, 'No eligible'):
            locks.upgrade_successor_choices(guard, lower, records, refs)


if __name__ == '__main__':
    unittest.main()
