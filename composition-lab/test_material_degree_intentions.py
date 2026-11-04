"""Authored preflight proofs; no source/song or physical-feasibility claims."""
from copy import deepcopy
import json
import unittest

from connected_tier2 import analyze, strip_lower
from source_fact_tier1 import extract_documents
import musical_support_material as material
import material_degree_paths as degree
import material_degree_intentions as intentions
from test_material_degree_paths import C, G
import test_musical_cell_development as fixture


def authored(*, separate_roles=True, one_role=False, ambiguous=False, dead=False):
    docs = fixture.authored_score()
    # Two repeated shapes cross at the ending. Equal displacement there can
    # preserve its signed interval even though both notes actually changed.
    shapes = [(60,), (60,), (60,67), (60,67), (60,67), (60,), (60,67)]
    if not separate_roles:
        shapes = [(60,), (60,67)]  # Each role occurs once: all arch factors zero.
    if one_role:
        shapes = [(60,), (60,), (60,)]
    for part in (2,3):
        track = docs[f'track-{part}.json']
        track['tuning'] = [50,45,40,35,30,25]
        beats = []
        for i, pitches in enumerate(shapes):
            duration = ([1,4] if i<2 else [1,2]) if one_role else (
                [1,2] if len(shapes)==2 else ([1,4] if i==6 else [1,8]))
            notes = [dict(string=k, fret=p-track['tuning'][k]) for k,p in enumerate(pitches)]
            if dead:
                notes.append(dict(string=2,dead=True))
            beats.append(dict(duration=duration, notes=notes, palmMute=True, velocity='f'))
        track['measures'][0]['voices'][0]['beats'] = beats
    lower = extract_documents(docs)
    original = material.fit(strip_lower(analyze(lower)), parts=[2,3], first_bar=1,
                            last_bar=1, lower=lower)
    paths = list(range(len(original['pitch_paths'])))
    owned = degree.fit(original, path_refs=paths,
        interpretations={p:deepcopy([C,G] if ambiguous else [C]) for p in paths},
        evidence_ref='authored-frozen-degree-context')
    solved = material.expand(original)
    lines = {}
    for part in (2,3):
        lines[part] = [next(m['id'] for m in reversed(g['members'])
                           if m['voicing_interval'] is not None)
                      for g in solved['coattacks'] if g['part_id']==part]
    return original, owned, lines


class DegreeIntentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.owned, cls.lines = authored()

    def plan(self, **kwargs):
        controls = dict(movement_percent=100, register_percent=100,
                        octave=1, max_degree_stride=3)
        controls.update(kwargs)
        return intentions.plans(self.original,self.owned,self.lines,**controls)

    def test_cross_role_unchanged_step_is_rejected_then_same_relation_fixes_it(self):
        result = self.plan()
        failed = next(row for row in result['rejections'] if row['strides']==[1,1])
        self.assertEqual(failed['measurements']['movement'],dict(total=12,changed=10))
        self.assertEqual(failed['measurements']['register'],dict(total=22,changed=22))
        for part in failed['measurements']['by_part']:
            self.assertFalse(part['steps'][-1]['changed'])
            self.assertEqual(part['steps'][-1]['before'],7)
        self.assertTrue(result['candidates'])
        selected = result['candidates'][0]
        self.assertEqual(selected['measurements']['movement'],dict(total=12,changed=12))
        self.assertEqual(selected['measurements']['register'],dict(total=22,changed=22))
        self.assertEqual(result['search']['trials'],9)
        self.assertEqual(len(result['candidates'])+len(result['rejections']),9)

    def test_paired_bindings_share_source_role_values_and_all_members_are_measured(self):
        result = self.plan()
        selected = result['candidates'][0]
        groups = {g['id']:g for g in self.original['lower_tier']['coattacks']}
        by_beat = {}
        for ref, value in selected['displacements'].items():
            member = groups[ref]['members'][0]
            by_beat.setdefault(member['beat'],set()).add(value)
        self.assertTrue(all(len(values)==1 for values in by_beat.values()))
        self.assertEqual(result['totals'],dict(movement=12,register=22,line_roots=14))
        self.assertEqual([p['total_register'] for p in selected['measurements']['by_part']],[11,11])

    def test_zero_is_exact_on_supplied_original_and_octave_is_independent(self):
        zero = self.plan(movement_percent=0,register_percent=0,octave=0)
        self.assertEqual(len(zero['candidates']),1)
        row = zero['candidates'][0]
        self.assertEqual(degree.expand(self.owned,row['displacements'],row['octaves']),self.original)
        register = self.plan(movement_percent=0)
        self.assertEqual(register['candidates'][0]['measurements']['movement']['changed'],0)
        self.assertEqual(register['candidates'][0]['measurements']['register']['changed'],22)
        conflict = self.plan(movement_percent=0,register_percent=0,octave=1)
        self.assertFalse(conflict['candidates'])
        self.assertEqual(conflict['rejections'][0]['failed_features'],['register'])

    def test_half_is_actual_output_target_and_first_failed_trials_are_retained(self):
        result = self.plan(movement_percent=50)
        self.assertEqual(result['targets']['movement'],6)
        for row in result['candidates']:
            self.assertEqual(row['measurements']['movement']['changed'],6)
        for row in result['rejections']:
            if row['reason']=='FINAL_OUTPUT_TARGET_NOT_MET':
                self.assertNotEqual(row['measurements']['movement']['changed'],6)
        self.assertEqual(intentions._count(3,50),2)
        self.assertEqual(sorted(row['trial_index'] for row in result['candidates']+result['rejections']),list(range(9)))
        original, owned, lines = authored(one_role=True)
        half = intentions.plans(original,owned,lines,movement_percent=50,max_degree_stride=3)
        self.assertEqual(len(half['candidates']),3)
        self.assertTrue(all(row['measurements']['movement']==dict(total=4,changed=2)
                            for row in half['candidates']))

    def test_global_transposition_with_zero_arch_factors_cannot_claim_movement(self):
        original, owned, lines = authored(separate_roles=False)
        result = intentions.plans(original,owned,lines,movement_percent=100,
                                  octave=1,max_degree_stride=3)
        self.assertFalse(result['candidates'])
        self.assertEqual(len(result['rejections']),9)
        self.assertTrue(all(row['measurements']['movement']['changed']==0 for row in result['rejections']))
        self.assertTrue(all(row['measurements']['register']['changed']==6 for row in result['rejections']))

    def test_saved_inputs_unchanged_repeated_results_identical_and_exact_inverse_retained(self):
        before = deepcopy((self.original,self.owned,self.lines))
        result = self.plan()
        loaded_original = json.loads(json.dumps(self.original))
        loaded_owned = json.loads(json.dumps(self.owned))
        loaded_lines = {int(k):v for k,v in json.loads(json.dumps(self.lines)).items()}
        again = intentions.plans(loaded_original,loaded_owned,loaded_lines,
            movement_percent=100,register_percent=100,octave=1,max_degree_stride=3)
        self.assertEqual(result,again)
        self.assertEqual((self.original,self.owned,self.lines),before)
        self.assertEqual(degree.expand(self.owned),self.original)
        rank = [(r['absolute_degree_displacement'],r['strides']) for r in result['candidates']]
        self.assertEqual(rank,sorted(rank))
        self.assertIn('not musical preference',result['ranking'])

    def test_unknown_unselected_duplicate_and_narrowed_lines_refuse(self):
        for kind in ('unknown','wrong-part','duplicate','narrowed','part-missing','backwards','string-part'):
            lines = deepcopy(self.lines)
            if kind=='unknown':lines[2][0]='event:missing'
            elif kind=='wrong-part':lines[2][0]=lines[3][0]
            elif kind=='duplicate':lines[2][1]=lines[2][0]
            elif kind=='narrowed':lines[2].pop()
            elif kind=='part-missing':lines.pop(3)
            elif kind=='backwards':lines[2].reverse()
            else:lines[str(2)]=lines.pop(2)
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                intentions.plans(self.original,self.owned,lines,movement_percent=100,max_degree_stride=3)
        changed = degree.expand(self.owned,octaves={ref:1 for ref in degree.selected_refs(self.owned)})
        with self.assertRaisesRegex(ValueError,'not a current-state updater'):
            intentions.plans(changed,self.owned,self.lines,movement_percent=100,max_degree_stride=3)

    def test_ambiguous_hypotheses_are_retained_not_picked_to_admit_a_candidate(self):
        original, owned, lines = authored(ambiguous=True)
        result = intentions.plans(original,owned,lines,movement_percent=100,max_degree_stride=3)
        self.assertTrue(any(row['reason']=='RELATIONSHIP_REALIZATION_REFUSED'
                            and 'interpretations disagree' in row['error'] for row in result['rejections']))
        self.assertEqual(result['search']['trials'],9)
        self.assertEqual(degree.expand(owned),original)

    def test_dead_members_are_retained_and_disclosed_not_treated_as_pitch_choices(self):
        original, owned, lines = authored(dead=True)
        result = intentions.plans(original,owned,lines,movement_percent=100,max_degree_stride=3)
        self.assertTrue(result['candidates'])
        candidate = result['candidates'][0]
        self.assertEqual(result['totals']['register'],22)
        self.assertEqual([len(p['retained_unpitched_refs']) for p in candidate['measurements']['by_part']],[7,7])
        current = degree.expand(owned,candidate['displacements'],candidate['octaves'])
        self.assertEqual(current['lower_tier'],original['lower_tier'])
        self.assertEqual(current['observed_execution'],original['observed_execution'])

    def test_invalid_control_types_and_bounds_refuse_before_search(self):
        for kwargs in (dict(movement_percent=True),dict(movement_percent=101),
                       dict(register_percent=-1),dict(octave=1.0),dict(max_degree_stride=0)):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.plan(**kwargs)


if __name__=='__main__':unittest.main()
