"""Authored bend ownership/combination tests, not musical listening evidence."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from connected_tier2 import analyze, strip_lower, realize
from source_fact_tier1 import extract_documents
import bend_choice_constraints as targets
import material_bend_excursions as bends
import material_degree_paths as degree
import musical_support_material as material
import technique_observation_relations as technique
import test_musical_cell_development as fixture


KEY = dict(id='authored-C-major', tonic_pc=0, intervals=[0, 2, 4, 5, 7, 9, 11])


def authored(*, plateau=False, floating=False, with_context=False):
    docs = fixture.authored_score()
    track = docs['track-2.json'];track['tuning'] = [60, 55, 50, 45, 40, 35]
    curve = dict(tone=50, points=[dict(position=0, tone=0), dict(position=60, tone=50)])
    if plateau:curve['points'].insert(1, dict(position=15, tone=50))
    if floating:
        curve['tone'] = 50.0;curve['points'][0]['tone'] = -0.0
        for point in curve['points'][1:]:point['tone'] = float(point['tone'])
    track['measures'][0]['voices'][0]['beats'] = [
        dict(type=4, duration=[1, 4], notes=[
            dict(string=0, fret=pitch-60, bend=deepcopy(curve)),
            dict(string=1, fret=other-55)])
        for pitch, other in ((64,67), (65,69), (67,71), (69,72))]
    lower = extract_documents(docs);upper = strip_lower(analyze(lower))
    definition = material.fit(upper, parts=[2], first_bar=1, last_bar=1, lower=lower)
    refs = [group['members'][0]['id'] for group in definition['lower_tier']['coattacks']]
    return (definition, refs, upper, lower, docs) if with_context else (definition, refs)


def source_rows(definition):
    return technique.realize(dict(schema='technique-observation-relations/1',
        groups=definition['lower_tier']['technique_declarations'], unsupported=[]))


def facts(definition):
    return {row['id']:row for row in source_rows(definition)}


class MaterialBendExcursionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.refs = authored()

    def test_empty_and_source_extent_are_exact_independent_copies(self):
        original = self.original
        for choices in (None, {}):
            result = bends.resolve(original, choices)
            self.assertEqual(result, original);self.assertIsNot(result, original)
        self.assertEqual(bends.resolve(original, {self.refs[0]:'1'}, tied_refs=[]), original)
        self.assertEqual(material.expand(bends.resolve(original)), material.expand(original))

    def test_simple_rise_has_no_required_held_tail_or_earlier_reference(self):
        old = deepcopy(self.original);ref = self.refs[0]
        after = bends.resolve(old, {ref:'2'}, tied_refs=[])
        a,b = facts(old),facts(after);prefix = bends.gesture.pointer(ref)+'/bend'
        changed = {key for key in a if a[key] != b[key]}
        self.assertEqual(changed, {prefix+'/tone',prefix+'/points/1/tone'})
        self.assertEqual(b[prefix+'/tone']['value'], 100)
        self.assertEqual(old, self.original)
        self.assertEqual(after['pitch_paths'], old['pitch_paths'])
        self.assertEqual(after['voicings'], old['voicings'])
        self.assertEqual(after['provenance'], old['provenance'])

    def test_plateau_point_times_and_unselected_chord_member_survive(self):
        original,refs = authored(plateau=True);after = bends.resolve(original,{refs[0]:'2'},tied_refs=[])
        a,b=facts(original),facts(after)
        self.assertEqual({k:v for k,v in a.items() if not k.endswith('/tone')},
                         {k:v for k,v in b.items() if not k.endswith('/tone')})
        self.assertEqual(material.expand(original)['coattacks'], material.expand(after)['coattacks'])
        self.assertEqual(after['lower_tier']['physical_positions'],original['lower_tier']['physical_positions'])

    def test_float_source_types_and_negative_zero_preserved(self):
        original,refs=authored(floating=True);after=bends.resolve(original,{refs[0]:'2'},tied_refs=[])
        rows=facts(after);prefix=bends.gesture.pointer(refs[0])+'/bend'
        self.assertIs(type(rows[prefix+'/tone']['value']),float)
        self.assertEqual(rows[prefix+'/tone']['value'],100.0)
        self.assertEqual(json.dumps(rows[prefix+'/points/0/tone']['value']),'-0.0')

    def test_parent_tie_context_is_required_and_cannot_be_inferred_from_local_absence(self):
        for kwargs in ({},dict(tied_refs=None),dict(tied_refs='not-a-ref-list')):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                bends.resolve(self.original,{self.refs[0]:'2'},**kwargs)
        with self.assertRaisesRegex(ValueError,'Tied bend'):
            bends.resolve(self.original,{self.refs[0]:'2'},tied_refs=[self.refs[0]])
        with self.assertRaisesRegex(ValueError,'Unique'):
            bends.resolve(self.original,{self.refs[0]:'2'},tied_refs=[self.refs[1],self.refs[1]])

    def test_bad_late_choice_is_atomic_and_never_changes_original_evidence(self):
        original=deepcopy(self.original);refs=self.refs
        cases=[{refs[0]:'2',refs[1]:'0'},{refs[0]:'2','event:980213:2:99:0:0:0':'2'},
               {refs[0]:'2',refs[1]:'1/3'},{refs[0]:2},{refs[0]:'2.0'},{refs[0]:True}]
        for choice in cases:
            with self.subTest(choice=choice),self.assertRaises(ValueError):
                bends.resolve(original,choice,tied_refs=[])
            self.assertEqual(original,self.original)

    def test_missing_peak_unknown_curve_or_malformed_unit_refuses(self):
        for kind in ('missing_peak','negative_point','unknown_structure','unit'):
            bad=deepcopy(self.original);group=bad['lower_tier']['technique_declarations'][0]
            prefix=group['source_fact_ref'];params={p['fact_ref']:p for p in group['parameters']}
            if kind=='missing_peak':
                group['structure']=[s for s in group['structure']if s['id']!=prefix+'/tone']
                group['structure'][0]['children'].remove(prefix+'/tone')
                group['parameters']=[p for p in group['parameters']if p['fact_ref']!=prefix+'/tone']
            elif kind=='negative_point':params[prefix+'/points/0/tone']['parameter']['normalized']='-1'
            elif kind=='unknown_structure':group['structure'][0]['mystery']='not-supported'
            else:params[prefix+'/tone']['unit']='100'
            saved=deepcopy(bad)
            with self.subTest(kind=kind),self.assertRaises(ValueError):bends.resolve(bad,{self.refs[0]:'2'},tied_refs=[])
            self.assertEqual(bad,saved)

    def test_saved_choices_successive_resolve_do_not_compound_or_create_observations(self):
        original=deepcopy(self.original);ref=self.refs[0]
        saved=json.loads(json.dumps(dict(definition=original,excursions={ref:'2'})))
        with patch('builtins.open',side_effect=AssertionError('No source access')):
            first=bends.resolve(saved['definition'],saved['excursions'],tied_refs=[])
            unchanged=bends.resolve(saved['definition'],saved['excursions'],tied_refs=[])
            saved['excursions'][ref]='3'
            second=bends.resolve(saved['definition'],saved['excursions'],tied_refs=[])
        self.assertEqual(first,unchanged)
        prefix=bends.gesture.pointer(ref)+'/bend'
        self.assertEqual(facts(second)[prefix+'/tone']['value'],150)
        self.assertEqual(saved['definition'],self.original)
        self.assertEqual(second['provenance'],original['provenance'])

    def test_composed_existing_inverse_matches_independent_source_field_expectation(self):
        original,refs,upper,lower,docs=authored(plateau=True,with_context=True)
        skeleton=material._remove(upper,[original['scope']])
        expected=deepcopy(docs)
        selected=expected['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['bend']
        selected['tone']=100
        for point in selected['points']:
            if point['tone']:point['tone']=100
        saved=json.loads(json.dumps(dict(definition=original,skeleton=skeleton,choices={refs[0]:'2'})))
        with patch('builtins.open',side_effect=AssertionError('No source or cache access')):
            transient=bends.resolve(saved['definition'],saved['choices'],tied_refs=[])
            restored=material.restore_fragments(saved['skeleton'],[material.expand(transient)])
            actual=realize(restored)
        self.assertEqual(actual,extract_documents(expected))
        self.assertEqual(restored['source_origin'],upper['source_origin'])
        self.assertEqual(bends.resolve(original),original)
        self.assertEqual(realize(upper),lower)

    def test_degree_and_curve_choices_compose_before_held_target_admission(self):
        original=deepcopy(self.original);paths=list(range(len(original['pitch_paths'])))
        owned=degree.fit(original,path_refs=paths,interpretations={p:[KEY]for p in paths},evidence_ref='authored-only')
        group=owned['degree_paths']['bindings'][0]['coattack_ref'];ref=self.refs[0]
        # E->F source bend; merely expanding it to E->F# is out of key.
        # Move the existing degree-owned start down to D, then D->E is valid.
        transient=bends.resolve(owned,{ref:'2'},tied_refs=[])
        combined=degree.expand(transient,{group:-1})
        reverse_order=bends.resolve(degree.expand(owned,{group:-1}),{ref:'2'},tied_refs=[])
        self.assertEqual(combined,reverse_order)
        g=next(g for g in material.expand(combined)['coattacks']if g['id']==group)
        member=next(m for m in g['members']if m['id']==ref)
        pitch=int(g['bass_register_anchor'])+int(member['voicing_interval'])
        declaration=next(g for g in combined['lower_tier']['technique_declarations']if g['source_fact_ref']==bends.gesture.pointer(ref)+'/bend')
        constraint=dict(schema=targets.SCHEMA,occurrence_ref=ref,source_fact_ref=declaration['source_fact_ref'],hypotheses=[KEY],targets=targets._targets(declaration))
        self.assertFalse(targets.evaluate(constraint,64)['admissible'])
        self.assertEqual(pitch,62);self.assertTrue(targets.evaluate(constraint,pitch)['admissible'])
        self.assertEqual(degree.expand(owned),original)


if __name__=='__main__':unittest.main()
