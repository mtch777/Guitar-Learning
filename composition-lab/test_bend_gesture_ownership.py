"""Authored bend-frame counterexamples; no private artifacts or artist evidence."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest

import backing_pitch_ownership as backing
import bend_gesture_ownership as gesture
from connected_tier2 import analyze, strip_lower, realize, reconstruct, validate
from source_fact_tier1 import extract_documents, project_documents


SONG = 980001
REFERENCE = [f'event:{SONG}:0:1:0:{i}:0' for i in (0, 1)]
TARGET = [f'event:{SONG}:0:2:0:{i}:0' for i in (0, 1)]
DEPENDENT = f'event:{SONG}:0:3:0:0:0'
BACKING = f'event:{SONG}:1:3:0:0:0'


def curve(tone, held=False):
    positions = (0, 30, 60) if held else (0, 15, 60)
    values = (tone, tone, tone) if held else (0, tone, tone)
    return dict(tone=tone, points=[dict(position=p, tone=v) for p, v in zip(positions, values)])


def documents(explicit_hold=True):
    def beat(duration, **note):
        return dict(duration=duration, notes=[note])
    def bar(beats):
        return dict(signature=[4, 4], voices=[dict(beats=beats)])
    reference = bar([
        beat([3, 8], string=0, fret=7, bend=curve(50), leftHandVibrato='slight'),
        beat([1, 8], string=0, fret=7, tie=True, bend=curve(50, True), leftHandVibrato='slight'),
        beat([1, 2], rest=True)])
    held = dict(string=0, fret=9, tie=True, leftHandVibrato='slight')
    if explicit_hold:
        held['bend'] = curve(100, True)
    target = bar([
        beat([3, 8], string=0, fret=9, bend=curve(100), leftHandVibrato='slight'),
        beat([1, 8], **held), beat([1, 2], rest=True)])
    return {
        'metadata.json': dict(songId=SONG, revisionId=1, artist='Authored fixture', title='Fixed bend frames',
            tracks=[dict(name='Authored guitar', instrumentId=27), dict(name='Authored bass', instrumentId=34)]),
        'track-0.json': dict(songId=SONG, revisionId=1, partId=0, instrumentId=27,
            tuning=[60, 55, 50, 45, 40, 35], frets=24, measures=[reference, target,
                bar([beat([1, 4], string=0, fret=12), beat([3, 4], rest=True)])]),
        'track-1.json': dict(songId=SONG, revisionId=1, partId=1, instrumentId=34,
            tuning=[48, 43, 38, 33], frets=24,
            measures=[bar([beat([1, 1], string=0, fret=0)]) for _ in range(3)])}


def note(docs, part, bar_index, beat_index):
    return docs[f'track-{part}.json']['measures'][bar_index]['voices'][0]['beats'][beat_index]['notes'][0]


def expected_target(docs, *, fret, tone):
    """Literal independent raw expectation, not the owner under test."""
    result = deepcopy(docs)
    for i in (0, 1):
        n = note(result, 0, 1, i)
        n['fret'] = fret
        if i == 0 or 'bend' in n:
            n['bend'] = curve(tone, i == 1)
    return result


def base_upper(docs, *, unrelated=False):
    lower = extract_documents(docs)
    kwargs = dict(backing_bindings=[dict(occurrence_ref=DEPENDENT, backing_ref=BACKING)]) if unrelated else {}
    return lower, strip_lower(analyze(lower, **kwargs))


def fixture(*, explicit_hold=True, unrelated=False):
    docs = documents(explicit_hold)
    lower, upper = base_upper(docs, unrelated=unrelated)
    return docs, lower, gesture.lift(upper, reference_ref=REFERENCE[0], target_ref=TARGET[0])


def controls(level=100, intent='keep_start', seed=0):
    return dict(context_policy=gesture.POLICY, bend=level, intent=intent, seed=seed)


def changed_reference_extent(upper, multiplier):
    result = deepcopy(upper)
    prefixes = {gesture.pointer(ref) + '/bend' for ref in REFERENCE}
    for group in result['owned_parameters']['technique_declarations']['groups']:
        if group['source_fact_ref'] in prefixes:
            for p in group['parameters']:
                if p['fact_ref'].endswith('/tone'):
                    p['parameter']['normalized'] = str(F(p['parameter']['normalized']) * multiplier)
    return result


class BendGestureOwnershipTests(unittest.TestCase):
    def assert_only_current_parameters_changed(self, before, after):
        restored = deepcopy(after)
        restored['owned_parameters'][gesture.SLOT]['parameters'] = deepcopy(before['owned_parameters'][gesture.SLOT]['parameters'])
        self.assertEqual(restored, before)

    def test_forward_zero_exact_and_single_authority_for_base_and_amplitude(self):
        for explicit_hold in (False, True):
            with self.subTest(explicit_hold=explicit_hold):
                docs = documents(explicit_hold); lower, upper = base_upper(docs)
                snapshot = deepcopy(upper)
                owned = gesture.lift(upper, reference_ref=REFERENCE[0], target_ref=TARGET[0])
                self.assertEqual(upper, snapshot)
                self.assertEqual(realize(owned), lower)
                self.assertEqual(validate(owned), lower)
                self.assertEqual(project_documents(realize(owned)), docs)
                owner = owned['owned_parameters'][gesture.SLOT]
                self.assertEqual(owner['reference_refs'], REFERENCE)
                self.assertEqual(owner['target_refs'], TARGET)
                self.assertEqual(owner['observations']['reference_excursion'], '1')
                self.assertEqual(owner['parameters'], dict(frame='start', frame_pitch='69', excursion='2'))
                groups = backing._index(gesture._body(owned['musical_relationships']))
                for ref in TARGET:
                    self.assertNotIn('bass_register_anchor', groups[ref][0])
                amplitude_refs = {r['fact_ref'] for r in owner['curve_amplitudes']}
                remaining = {p['fact_ref'] for g in owned['owned_parameters']['technique_declarations']['groups'] for p in g['parameters']}
                self.assertFalse(amplitude_refs & remaining)
                self.assertEqual(len(amplitude_refs), 8 if explicit_hold else 4)
                for intent in ('keep_start', 'keep_arrival'):
                    zero, decision = gesture.intervene(owned, controls(0, intent))
                    self.assertEqual(zero, owned)
                    self.assertFalse(decision['released'])
                    self.assertEqual(reconstruct(owned, controls(0, intent)), lower)

    def test_both_frames_change_the_full_tie_and_nothing_else(self):
        for explicit_hold in (False, True):
            docs, _, upper = fixture(explicit_hold=explicit_hold)
            snapshot = deepcopy(upper)
            for intent, fret, frame, pitch in (('keep_start', 9, 'start', '69'), ('keep_arrival', 10, 'arrival', '71')):
                with self.subTest(explicit_hold=explicit_hold, intent=intent):
                    edited, decision = gesture.intervene(upper, controls(intent=intent))
                    self.assertTrue(decision['released'])
                    self.assertTrue(decision['changed'])
                    self.assertEqual(project_documents(realize(edited)), expected_target(docs, fret=fret, tone=50))
                    self.assertEqual(edited['owned_parameters'][gesture.SLOT]['parameters'],
                                     dict(frame=frame, frame_pitch=pitch, excursion='reference_excursion'))
                    self.assert_only_current_parameters_changed(upper, edited)
                    self.assertEqual(upper, snapshot)

    def test_half_release_is_deterministic_and_zero_after_save_preserves_current(self):
        docs, _, upper = fixture()
        for seed, released in ((0, False), (1, True)):
            edited, decision = gesture.intervene(upper, controls(50, 'keep_arrival', seed))
            again, repeated = gesture.intervene(upper, controls(50, 'keep_arrival', seed))
            self.assertEqual((edited, decision), (again, repeated))
            self.assertEqual(decision['released'], released)
            self.assertEqual(project_documents(realize(edited)), expected_target(docs, fret=10, tone=50) if released else docs)
            saved = json.loads(json.dumps(edited))
            zero, report = gesture.intervene(saved, controls(0, 'keep_start'))
            self.assertEqual(zero, saved)
            self.assertFalse(report['released'])

    def test_live_reference_change_after_serialization_preserves_original_evidence(self):
        docs, _, upper = fixture()
        observations = deepcopy(upper['owned_parameters'][gesture.SLOT]['observations'])
        for intent, fret in (('keep_start', 9), ('keep_arrival', 8)):
            with self.subTest(intent=intent):
                edited, _ = gesture.intervene(upper, controls(intent=intent))
                saved = json.loads(json.dumps(edited))
                later = changed_reference_extent(saved, 3)
                expected = expected_target(docs, fret=fret, tone=150)
                for i in (0, 1):
                    note(expected, 0, 0, i)['bend'] = curve(150, i == 1)
                self.assertEqual(project_documents(realize(later)), expected)
                self.assertEqual(later['owned_parameters'][gesture.SLOT]['observations'], observations)
                self.assertEqual(later['source_origin'], upper['source_origin'])
                zero, _ = gesture.intervene(later, controls(0, intent))
                self.assertEqual(zero, later)

    def test_malformed_original_excursion_is_rejected_without_mutation(self):
        _,_,upper=fixture()
        for value in ('0','-1'):
            bad=deepcopy(upper)
            bad['owned_parameters'][gesture.SLOT]['observations']['reference_excursion']=value
            before=deepcopy(bad)
            with self.assertRaisesRegex(ValueError,'Historical reference excursion'):
                gesture.intervene(bad,controls())
            self.assertEqual(bad,before)

    def test_current_frame_switch_and_hundred_percent_coincidence_are_allowed(self):
        docs, _, upper = fixture()
        start, _ = gesture.intervene(upper, controls(intent='keep_start'))
        arrival, report = gesture.intervene(start, controls(intent='keep_arrival'))
        self.assertTrue(report['released'])
        self.assertFalse(report['changed'])
        self.assertEqual(arrival['owned_parameters'][gesture.SLOT]['parameters']['frame_pitch'], '70')
        self.assertEqual(project_documents(realize(arrival)), expected_target(docs, fret=9, tone=50))
        repeated, report = gesture.intervene(arrival, controls(intent='keep_arrival'))
        self.assertTrue(report['released'])
        self.assertFalse(report['changed'])
        self.assertEqual(repeated, arrival)

    def test_unrelated_dependency_survives_and_still_propagates(self):
        docs, _, upper = fixture(unrelated=True)
        original_core = deepcopy(upper['musical_relationships'])
        original_link = next(r for r in original_core['relationships'] if r['occurrence_ref'] == DEPENDENT)
        edited, _ = gesture.intervene(upper, controls(intent='keep_arrival'))
        self.assertEqual(edited['musical_relationships'], original_core)
        self.assertIn(original_link, edited['musical_relationships']['relationships'])
        later = json.loads(json.dumps(edited))
        group, _ = backing._index(gesture._body(later['musical_relationships']))[BACKING]
        group['bass_register_anchor'] = str(F(group['bass_register_anchor']) + 1)
        expected = expected_target(docs, fret=10, tone=50)
        note(expected, 1, 2, 0)['fret'] = 1
        note(expected, 0, 2, 0)['fret'] = 13
        self.assertEqual(project_documents(realize(later)), expected)
        self.assertIn(original_link, later['musical_relationships']['relationships'])

    def test_dependent_outside_released_scope_refuses_without_dropping_link(self):
        docs=documents();lower=extract_documents(docs)
        dependent=f'event:{SONG}:1:2:0:0:0'
        upper=strip_lower(analyze(lower,backing_bindings=[dict(occurrence_ref=dependent,backing_ref=TARGET[0])]))
        owned=gesture.lift(upper,reference_ref=REFERENCE[0],target_ref=TARGET[0])
        snapshot=deepcopy(owned)
        self.assertEqual(gesture.intervene(owned,controls(0))[0],owned)
        started,_=gesture.intervene(owned,controls(intent='keep_start'))
        self.assertEqual(project_documents(realize(started)),expected_target(docs,fret=9,tone=50))
        with self.assertRaisesRegex(ValueError,'BEND_SCOPE_CONFLICT'):
            gesture.intervene(owned,controls(intent='keep_arrival'))
        self.assertEqual(owned,snapshot)
        self.assertEqual(started['musical_relationships'],owned['musical_relationships'])

    def test_duplicate_or_missing_pitch_curve_and_closure_owners_refuse(self):
        _, _, upper = fixture()
        expanded = gesture.expand(upper)
        corruptions = []
        duplicate_pitch = deepcopy(upper)
        backing._index(gesture._body(duplicate_pitch['musical_relationships']))[TARGET[0]][0]['bass_register_anchor'] = '69'
        corruptions.append(duplicate_pitch)
        duplicate_curve = deepcopy(upper)
        row = duplicate_curve['owned_parameters'][gesture.SLOT]['curve_amplitudes'][0]
        original_group = next(g for g in expanded['owned_parameters']['technique_declarations']['groups'] if g['id'] == row['group_ref'])
        group = next(g for g in duplicate_curve['owned_parameters']['technique_declarations']['groups'] if g['id'] == row['group_ref'])
        group['parameters'].append(deepcopy(next(p for p in original_group['parameters'] if p['fact_ref'] == row['fact_ref'])))
        corruptions.append(duplicate_curve)
        missing_curve = deepcopy(upper); missing_curve['owned_parameters'][gesture.SLOT]['curve_amplitudes'].pop()
        corruptions.append(missing_curve)
        missing_member = deepcopy(upper); missing_member['owned_parameters'][gesture.SLOT]['target_refs'].pop()
        corruptions.append(missing_member)
        cycle = deepcopy(upper); cycle['owned_parameters'][gesture.SLOT]['reference_refs'] = list(TARGET)
        corruptions.append(cycle)
        for i, bad in enumerate(corruptions):
            with self.subTest(corruption=i):
                snapshot = deepcopy(bad)
                with self.assertRaises(ValueError):
                    gesture.intervene(bad, controls(0))
                self.assertEqual(bad, snapshot)
        snapshot = deepcopy(upper)
        with self.assertRaises(ValueError):
            gesture.lift(upper, reference_ref=REFERENCE[0], target_ref=TARGET[0])
        self.assertEqual(upper, snapshot)

    def test_unsupported_curves_chords_dead_and_tie_topologies_refuse_atomically(self):
        cases = {}
        for key in ('nonboolean_tie', 'release', 'reference_release', 'retrigger', 'different_pitch', 'dead', 'chord', 'gap', 'third_tie'):
            cases[key] = documents()
        note(cases['nonboolean_tie'], 0, 1, 1)['tie'] = 'yes'
        note(cases['release'], 0, 1, 1)['bend'] = dict(tone=100, points=[dict(position=0, tone=100), dict(position=60, tone=0)])
        note(cases['reference_release'], 0, 0, 0)['bend'] = dict(tone=50, points=[dict(position=0, tone=0), dict(position=30, tone=50), dict(position=60, tone=0)])
        note(cases['retrigger'], 0, 1, 1).pop('tie')
        note(cases['different_pitch'], 0, 1, 1)['fret'] = 10
        note(cases['dead'], 0, 1, 0)['dead'] = True
        cases['chord']['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'].append(dict(string=1, fret=7))
        beats = cases['gap']['track-0.json']['measures'][1]['voices'][0]['beats']
        beats.insert(1, dict(duration=[1, 8], notes=[dict(rest=True)])); beats[-1]['duration'] = [3, 8]
        beats = cases['third_tie']['track-0.json']['measures'][1]['voices'][0]['beats']
        beats.insert(2, dict(duration=[1, 8], notes=[dict(string=0, fret=9, tie=True, bend=curve(100, True))]))
        beats[-1]['duration'] = [3, 8]
        for key, docs in cases.items():
            with self.subTest(case=key):
                lower, upper = base_upper(docs)
                snapshot = deepcopy(upper)
                if key == 'nonboolean_tie':
                    self.assertTrue(upper['unsupported'])
                    with self.assertRaises(ValueError):
                        realize(upper)
                else:
                    self.assertEqual(project_documents(realize(upper)), docs)
                with self.assertRaises(ValueError):
                    gesture.lift(upper, reference_ref=REFERENCE[0], target_ref=TARGET[0])
                self.assertEqual(upper, snapshot)

    def test_typed_controls_and_invalid_contact_refuse_atomically(self):
        _, _, upper = fixture()
        malformed = [dict(controls(), bend=v) for v in (None, True, 50.0, float('nan'), -1, 101)]
        malformed += [dict(controls(), seed=v) for v in (None, True, 0.0)]
        malformed += [dict(controls(), intent='automatic'), dict(controls(), result_pitch=70)]
        snapshot = deepcopy(upper)
        for request in malformed:
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    gesture.intervene(upper, request)
                self.assertEqual(upper, snapshot)
        invalid = deepcopy(upper)
        invalid['owned_parameters'][gesture.SLOT]['parameters']['frame_pitch'] = '59'
        snapshot = deepcopy(invalid)
        with self.assertRaises(ValueError):
            gesture.intervene(invalid, controls(0))
        self.assertEqual(invalid, snapshot)

    def test_reference_must_precede_target_and_source_origin_cannot_be_replaced(self):
        _, upper = base_upper(documents())
        snapshot = deepcopy(upper)
        with self.assertRaises(ValueError):
            gesture.lift(upper, reference_ref=TARGET[0], target_ref=REFERENCE[0])
        self.assertEqual(upper, snapshot)
        _, _, owned = fixture()
        bad = deepcopy(owned)
        bad['owned_parameters'][gesture.SLOT]['observations']['origin']['facts_sha256'] = '0' * 64
        snapshot = deepcopy(bad)
        with self.assertRaises(ValueError):
            gesture.intervene(bad, controls(0))
        self.assertEqual(bad, snapshot)

    def test_actual_isolated_zero_changed_and_corrupted_input(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        docs, lower, upper = fixture()
        code, _ = bundle(Path(__file__).parent)
        expected = extract_documents(expected_target(docs, fret=10, tone=50))
        bad = deepcopy(upper)
        backing._index(gesture._body(bad['musical_relationships']))[TARGET[0]][0]['bass_register_anchor'] = '69'
        with tempfile.TemporaryDirectory() as temporary:
            for name, packet, request, output, accepted in (
                ('zero', upper, controls(0), lower, True),
                ('arrival', upper, controls(100, 'keep_arrival'), expected, True),
                ('duplicate-base', bad, controls(0), lower, False),
            ):
                receipt = execute(code, packet, request, output, Path(temporary)/name,
                                  timeout=45, purpose='bend_gesture')
                audit_path = Path(temporary)/name/'worker/audit.json'
                audit = json.loads(audit_path.read_text()) if audit_path.exists() else None
                self.assertEqual(receipt['status'] == 'PASS', accepted, (receipt, audit))
                self.assertFalse(receipt['parent_expected_staged'])


if __name__ == '__main__':
    unittest.main()
