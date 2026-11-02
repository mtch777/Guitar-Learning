"""Authored positive/negative contrasts, separate from real-song evidence."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents, project_documents
from connected_tier2 import analyze, strip_lower, realize
from test_melodic_contour_choices import documents as original_documents, TARGET
import melodic_figure_intervention as figure


def documents():
    docs = original_documents()
    for i, measure in enumerate(docs['track-0.json']['measures']):
        # Separate comparison figures with genuine silence so this positive
        # fixture does not also ask to change an established repeating pedal.
        if i not in (1, 4, 7):
            measure['voices'][0]['beats'] = [dict(type=1, duration=[1, 1], velocity='f', notes=[dict(rest=True)])]
            continue
        frets = [2, 9, 5] if i == 4 else [0, 4, 7]
        for beat, fret in zip(measure['voices'][0]['beats'], frets):
            beat['notes'][0]['fret'] = fret
    return docs


def model(docs=None):
    before = extract_documents(documents() if docs is None else docs)
    return before, strip_lower(analyze(before, rhythm_groups=True,
                                      rhythm_group_profile='written_time', note_accent_slots=True))


class MelodicFigureTests(unittest.TestCase):
    def test_real_source_choice_changes_endpoints_contour_and_membership(self):
        before, upper = model()
        c = figure.prepare(upper)
        result = figure.options(upper, TARGET, c)
        changed = [r for r in result['options'] if r['changed']]
        self.assertTrue(changed, result['rejected'])
        option = changed[0]
        self.assertEqual(option['pitches'], ['62', '69', '65'])
        after = realize(figure.apply(upper, result['target'], option['pitches']))
        expected = documents()
        for beat, fret in zip(expected['track-0.json']['measures'][1]['voices'][0]['beats'], [2, 9, 5]):
            beat['notes'][0]['fret'] = fret
        self.assertEqual(project_documents(after), expected)
        proof = option['relationships']
        self.assertEqual(proof['before_directions'], [1, 1])
        self.assertEqual(proof['after_directions'], [1, -1])
        self.assertTrue(all(row['lowest_pitch'] == '48' for row in proof['bass']))
        self.assertTrue(any(h['after']['status'] == 'TEMPLATE_NONMEMBER'
                            for r in proof['roles'] for h in r['hypotheses']))
        self.assertEqual(realize(upper), before)

    def test_zero_and_probabilistic_release_allow_original_coincidence(self):
        before, upper = model()
        control = dict(context_policy=figure.POLICY, melody=0, target_ref=TARGET, seed=0)
        out, decision = figure.intervene(upper, control)
        self.assertEqual(out, upper)
        self.assertEqual(realize(out), before)
        result = figure.options(upper, TARGET)
        self.assertTrue(any(not r['changed'] for r in result['options']))
        for strength in (0, 50, 100):
            draws = [figure.sample(result, dict(control, melody=strength, seed=s))[1] for s in range(512)]
            released = sum(d['released'] for d in draws)
            if strength == 0:
                self.assertEqual(released, 0)
            elif strength == 50:
                self.assertTrue(200 < released < 312)
            else:
                self.assertEqual(released, 512)
                self.assertTrue(any(d['changed'] for d in draws))
                self.assertTrue(any(not d['changed'] for d in draws))

    def test_octave_clock_technique_and_source_string_are_not_released(self):
        for field in ('octave', 'duration', 'technique', 'string'):
            docs = documents()
            beat = docs['track-0.json']['measures'][4]['voices'][0]['beats'][0]
            if field == 'octave':
                beat['notes'][0]['fret'] += 12
            elif field == 'duration':
                beat['duration'] = [1, 8]
            elif field == 'technique':
                beat['notes'][0]['bend'] = {}
            else:
                docs['track-0.json']['tuning'].append(60)
                beat['notes'][0]['string'] = 1
            _, upper = model(docs)
            result = figure.options(upper, TARGET)
            self.assertFalse(any(r['changed'] for r in result['options']), field)

    def test_unknown_or_different_accompaniment_is_not_permission(self):
        for change in ('missing', 'different'):
            docs = documents()
            if change == 'missing':
                docs.pop('track-1.json')
                docs['metadata.json']['tracks'].pop()
            else:
                for note in docs['track-1.json']['measures'][4]['voices'][0]['beats'][0]['notes']:
                    note['fret'] = 2
            _, upper = model(docs)
            result = figure.options(upper, TARGET)
            self.assertFalse(any(r['changed'] for r in result['options']), change)

    def test_bass_must_stay_fixed_and_outside_corruption_fails(self):
        before, upper = model()
        c = figure.prepare(upper)
        result = figure.options(upper, TARGET, c)
        donor = c['by_ref']['event:77:0:5:0:1:0']
        contract = result['membership_contract']
        with self.assertRaisesRegex(ValueError, 'Lowest written ensemble'):
            figure.bass_profile(c, result['target'], contract, ['47', '47', '47'])
        after = realize(figure.apply(upper, result['target'], donor['pitches']))
        next(r for r in after['facts'] if r['id'] == 'track-0.json#/measures/7/voices/0/beats/0/notes/0/fret')['value'] = 1
        with self.assertRaisesRegex(ValueError, 'outside observed figure'):
            figure.verify(before, after, result['target'], donor, contract, c)

    def test_invalid_controls_and_empty_source_pool(self):
        control = dict(context_policy=figure.POLICY, melody=50, target_ref=TARGET, seed=0)
        for value in (True, float('nan'), float('inf'), -1, 101, '50'):
            with self.assertRaises(ValueError):
                figure.validate_controls(dict(control, melody=value))
        for key, value in (('seed', False), ('target_ref', 'event:not-an-id'), ('extra', 0)):
            with self.assertRaises(ValueError):
                figure.validate_controls(dict(control, **{key: value}))
        selected, decision = figure.sample(dict(options=[]), dict(control, melody=100))
        self.assertIsNone(selected)
        self.assertFalse(decision['changed'])

    def test_existing_pedal_relationship_is_not_silently_released(self):
        docs = original_documents()
        for i, measure in enumerate(docs['track-0.json']['measures']):
            for beat, fret in zip(measure['voices'][0]['beats'], [2, 9, 5] if i == 4 else [0, 4, 7]):
                beat['notes'][0]['fret'] = fret
        _, upper = model(docs)
        result = figure.options(upper, TARGET)
        self.assertFalse(any(r['changed'] for r in result['options']))
        self.assertTrue(any(r['reason'] == 'Approved pedal relationship changed' for r in result['rejected']))

    def test_actual_isolated_percentage_policy(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before, upper = model()
        c = figure.prepare(upper)
        result = figure.options(upper, TARGET, c)
        code, _ = bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            for strength in (0, 50, 100):
                control = dict(context_policy=figure.POLICY, melody=strength, target_ref=TARGET, seed=8)
                chosen, _ = figure.sample(result, control)
                if strength:
                    self.assertIsNotNone(chosen)
                    self.assertTrue(chosen['changed'])
                expected = deepcopy(before)
                if chosen is not None:
                    donor = c['by_ref'][chosen['donor_refs'][0]]
                    original = {f['id']: f for f in before['facts']}
                    facts = {f['id']: f for f in expected['facts']}
                    for ref, dref in zip(result['target']['occurrence_refs'], donor['occurrence_refs']):
                        facts[figure.note_path(ref)+'/fret']['value'] = original[figure.note_path(dref)+'/fret']['value']
                report = execute(code, upper, control, expected, Path(folder)/str(strength),
                                 timeout=90, purpose='local_melodic_figure_intervention')
                self.assertEqual(report['status'], 'PASS', report)


if __name__ == '__main__':
    unittest.main()
