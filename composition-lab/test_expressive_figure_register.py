"""Authored integration cases for one shared octave, not artist evidence."""
from copy import deepcopy
import unittest

from connected_tier2 import analyze, strip_lower, realize, reconstruct, validate
from source_fact_tier1 import extract_documents, project_documents
import figure_register_ownership as groups
import observed_figure_register as register
from check_technique_connections import check


SONG = 765432
SEEDS = [f'event:{SONG}:0:2:0:{i}:0' for i in range(3)]
MEMBERS = [f'event:{SONG}:0:1:0:{i}:0' for i in (1, 2)] + SEEDS


def documents():
    def beat(duration, **note):
        return dict(duration=duration, notes=[note])
    def bar(beats):
        return dict(signature=[4, 4], voices=[dict(beats=beats)])
    first = bar([beat([3, 4], rest=True),
                 beat([1, 8], string=1, fret=19, leftHandVibrato='slight'),
                 beat([1, 8], string=1, fret=19, tie=True, leftHandVibrato='slight')])
    second = bar([beat([1, 8], string=1, fret=19, tie=True, slide='downwards'),
                  beat([1, 8], string=2, fret=16, bend=dict(tone=100, points=[
                      dict(position=0, tone=0), dict(position=30, tone=100), dict(position=60, tone=100)])),
                  beat([1, 4], string=1, fret=14), beat([1, 2], rest=True)])
    donors = bar([beat([1, 8], string=s, fret=f) for s, f in
                  [(0, 2), (1, 0), (1, 2), (0, 14), (0, 7), (0, 9)]] + [beat([1, 4], rest=True)])
    return {
        'metadata.json': dict(songId=SONG, revisionId=1, artist='Authored fixture', title='Held figure',
                              tracks=[dict(name='Guitar', instrumentId=27), dict(name='Bass', instrumentId=34)]),
        'track-0.json': dict(songId=SONG, revisionId=1, partId=0, instrumentId=27,
                             tuning=[64, 59, 55, 50, 45, 40], frets=24, measures=[first, second, donors]),
        'track-1.json': dict(songId=SONG, revisionId=1, partId=1, instrumentId=34,
                             tuning=[40, 35, 30, 25], frets=24,
                             measures=[bar([beat([1, 1], string=0, fret=0)]) for _ in range(3)])}


def fixture(*, extra_owner=False):
    docs = documents(); lower = extract_documents(docs)
    bindings = [dict(occurrence_ref=ref, backing_ref=f'event:{SONG}:1:{ref.split(":")[3]}:0:0:0')
                for ref in MEMBERS]
    if extra_owner:
        bindings.append(dict(occurrence_ref=f'event:{SONG}:0:3:0:0:0', backing_ref=f'event:{SONG}:1:3:0:0:0'))
    full = analyze(lower, backing_bindings=bindings, expressive_figure_seed_refs=SEEDS)
    return docs, lower, full


def controls(level=100, seed=0, physical=100):
    return dict(context_policy=register.EXPRESSIVE, register=level, seed=seed, physical=physical)


class ExpressiveFigureRegisterTests(unittest.TestCase):
    def test_unrelated_existing_owner_survives_and_still_follows_its_backing(self):
        from fractions import Fraction
        import backing_pitch_ownership as backing
        _, _, full = fixture(extra_owner=True); upper = strip_lower(full)
        extra = f'event:{SONG}:0:3:0:0:0'; anchor = f'event:{SONG}:1:3:0:0:0'
        old_link = next(row for row in upper['musical_relationships']['core']['relationships'] if row['occurrence_ref'] == extra)
        for seed in range(4):
            changed, result = register.intervene(upper, controls(seed=seed))
            if result['changed']:
                break
        self.assertTrue(result['changed'])
        self.assertIn(old_link, changed['musical_relationships']['core']['relationships'])
        original_output = project_documents(realize(changed))
        later = deepcopy(changed)
        base = backing._body(later['musical_relationships']['core']['core'])
        group = next(g for g in base['coattacks'] if any(n['id'] == anchor for n in g['members']))
        group['bass_register_anchor'] = str(Fraction(group['bass_register_anchor']) + 1)
        later_output = project_documents(realize(later))
        before_note = original_output['track-0.json']['measures'][2]['voices'][0]['beats'][0]['notes'][0]
        after_note = later_output['track-0.json']['measures'][2]['voices'][0]['beats'][0]['notes'][0]
        self.assertEqual(after_note['fret'], before_note['fret'] + 1)
        with self.assertRaises(ValueError):
            groups.assert_preserved(changed['musical_relationships'], later['musical_relationships'])

    def test_forward_owns_complete_chain_and_exact_zero_without_duplicate_pitch_values(self):
        docs, before, full = fixture(); upper = strip_lower(full)
        self.assertEqual(validate(full), before)
        self.assertEqual(project_documents(realize(upper)), docs)
        self.assertEqual(reconstruct(upper, controls(0)), before)
        wrapper = upper['musical_relationships']
        self.assertEqual(wrapper['schema'], groups.EXPRESSIVE_SCHEMA)
        self.assertEqual(wrapper['groups'][0]['occurrence_refs'], MEMBERS)
        contract = wrapper['execution_contract']
        self.assertEqual(len(contract['closure']['attack_root_refs']), 3)
        self.assertEqual(contract['source_exit_endpoint'], 'unknown')
        for row in wrapper['core']['relationships']:
            self.assertNotIn('interval_semitones', row)
            self.assertIn('figure_register_ref', row)
        self.assertEqual(check(docs, full)['issues'], [])

    def test_same_parameter_changes_five_frets_and_nothing_else_at_nonzero_levels(self):
        docs, before, full = fixture(); upper = strip_lower(full); snapshot = deepcopy(upper)
        prepared = register.prepare_original(upper, MEMBERS, expressive=True)
        options, _ = register.choices(prepared, before, MEMBERS)
        self.assertEqual({o['shift_semitones'] for o in options}, {-12, 0})
        outcomes = []
        for level in (0, 50, 100):
            for seed in range(4):
                edited, decision = register.intervene(upper, controls(level, seed))
                actual = project_documents(realize(edited)); expected = deepcopy(docs)
                shift = decision.get('choice', {}).get('shift_semitones', 0) if decision.get('choice') else 0
                for ref in MEMBERS:
                    _, _, part, bar, voice, beat, note = ref.split(':')
                    expected[f'track-{part}.json']['measures'][int(bar)-1]['voices'][int(voice)]['beats'][int(beat)]['notes'][int(note)]['fret'] += shift
                self.assertEqual(actual, expected)
                self.assertEqual(reconstruct(upper, controls(level, seed)), realize(edited))
                self.assertEqual(edited['source_origin'], upper['source_origin'])
                groups.assert_preserved(upper['musical_relationships'], edited['musical_relationships'],
                    mutable_groups=[upper['musical_relationships']['groups'][0]['id']])
                outcomes.append((level, decision['released'], shift))
        self.assertTrue(any(level == 100 and shift == -12 for level, _, shift in outcomes))
        self.assertTrue(any(level == 100 and shift == 0 for level, _, shift in outcomes))
        self.assertTrue(any(level == 50 and not released for level, released, _ in outcomes))
        self.assertEqual(upper, snapshot)

    def test_changed_evidence_cannot_become_original_and_physical_lock_refuses(self):
        _, _, full = fixture(); upper = strip_lower(full)
        changed = None
        for seed in range(4):
            candidate, decision = register.intervene(upper, controls(seed=seed))
            if decision['changed']:
                changed = candidate; changed_seed = seed; break
        self.assertIsNotNone(changed)
        snapshot = deepcopy(changed)
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_CHAINED_EVIDENCE'):
            register.intervene(changed, controls())
        self.assertEqual(register.intervene(changed, controls(0))[0], changed)
        with self.assertRaisesRegex(ValueError, 'PHYSICAL_CONTACT_LOCK'):
            register.intervene(upper, controls(seed=changed_seed, physical=0))
        self.assertEqual(changed, snapshot)

    def test_source_denied_inverse_rejects_nonuniform_geometry_and_changed_curve(self):
        _, _, full = fixture(); upper = strip_lower(full)
        bad = deepcopy(upper)
        bad['musical_relationships']['groups'][0]['offsets_semitones'][-1] = '99'
        with self.assertRaises(ValueError):
            realize(bad)
        bad = deepcopy(upper)
        p = next(p for g in bad['owned_parameters']['technique_declarations']['groups']
                 for p in g['parameters'] if p['fact_ref'].endswith('/bend/points/1/position'))
        p['parameter']['normalized'] = '1/3'
        with self.assertRaisesRegex(ValueError, 'FIGURE|figure'):
            realize(bad)
        self.assertEqual(realize(upper), realize(strip_lower(full)))

    def test_old_plain_policy_and_execution_guard_are_not_silently_relaxed(self):
        _, before, full = fixture(); upper = strip_lower(full)
        with self.assertRaises(ValueError):
            register.intervene(upper, dict(controls(), context_policy=register.STANDALONE))
        from backing_execution_constraints import build
        with self.assertRaisesRegex(ValueError, 'UNRESOLVED_AFFECTED_EXECUTION'):
            build(before, MEMBERS)
        downgraded = deepcopy(upper['musical_relationships'])
        downgraded['schema'] = groups.SCHEMA
        del downgraded['execution_contract']
        with self.assertRaisesRegex(ValueError, 'execution contract'):
            groups.assert_preserved(upper['musical_relationships'], downgraded)

    def test_actual_isolated_worker_accepts_changed_owner_and_rejects_curve_corruption(self):
        from pathlib import Path
        import tempfile
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute

        _, before, full = fixture(); upper = strip_lower(full)
        code, _ = bundle(Path(__file__).parent)
        for seed in range(4):
            edited, decision = register.intervene(upper, controls(seed=seed))
            if decision['changed']:
                break
        self.assertTrue(decision['changed'])
        bad = deepcopy(upper)
        parameter = next(p for g in bad['owned_parameters']['technique_declarations']['groups']
                         for p in g['parameters'] if p['fact_ref'].endswith('/bend/points/1/position'))
        parameter['parameter']['normalized'] = '1/3'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, model, request, expected, accepted in (
                ('zero', upper, controls(0), before, True),
                ('changed', upper, controls(seed=seed), realize(edited), True),
                ('bad-curve', bad, controls(0), before, False),
            ):
                receipt = execute(code, model, request, expected, root/name,
                                  timeout=40, purpose='guitar_figure_register')
                self.assertEqual(receipt['status'] == 'PASS', accepted, receipt)
                self.assertFalse(receipt['parent_expected_staged'])


if __name__ == '__main__':
    unittest.main()
