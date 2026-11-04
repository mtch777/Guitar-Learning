"""Joint pitch/curve updates retain live owners and use the complete inverse."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import connected_tier2 as connected
import material_degree_paths as degrees
import material_slot_clock_control as clock
import support_material_uses as uses
import test_material_bend_excursions as fixture
from source_fact_tier1 import extract_documents, project_documents

USE='material-use:0'
SPEC=dict(parts=[2],first_bar=1,last_bar=1)
reload=lambda value:json.loads(json.dumps(value))


def build(*, plateau=False, bound=True):
    _,_,t2,lower,docs=fixture.authored(plateau=plateau,with_context=True)
    upper=uses.from_tier2(t2,[SPEC])
    if bound:upper=uses.bind_written_ties(upper)
    paths=list(range(len(upper['materials'][0]['pitch_paths'])))
    upper=uses.lift_degree_paths(upper,USE,path_refs=paths,
        interpretations={p:[fixture.KEY]for p in paths},evidence_ref='authored-C-major')
    group=upper['materials'][0]['lower_tier']['coattacks'][0]
    ref,other=[m['id']for m in group['members']]
    return docs,lower,upper,group['id'],ref,other


def change(upper,group,ref,other,*,extent='2',step=-1):
    # Preserve the companion's degree while changing the bend's start.
    return uses.degree_choices_candidate(upper,
        {USE:dict(displacements={group:step},octaves={},member_steps={other:-step})},
        bend_excursions={USE:{ref:extent}})


def expected(docs):
    out=deepcopy(docs)
    note=out['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]
    note['fret']-=2
    note['bend']['tone']=100
    for point in note['bend']['points']:
        if point['tone']:point['tone']=100
    return extract_documents(out)


class MaterialBendUsesTests(unittest.TestCase):
    def test_joint_start_and_excursion_match_independent_complete_score(self):
        docs,lower,upper,group,ref,other=build(plateau=True)
        frozen=deepcopy(upper)
        after=change(upper,group,ref,other)
        self.assertEqual(uses.reconstruct(reload(after),{'variation':0}),expected(docs))
        self.assertEqual(uses.reconstruct(upper,{'variation':0}),lower)
        self.assertEqual(upper,frozen)
        for field in ('materials','slots','lower_tier'):
            self.assertEqual(after[field],upper[field])

    def test_invalid_fixed_start_and_invalid_late_choice_refuse_atomically(self):
        _,_,upper,group,ref,other=build()
        frozen=deepcopy(upper)
        with self.assertRaisesRegex(ValueError,'bend target'):
            uses.degree_choices_candidate(upper,{},bend_excursions={USE:{ref:'2'}})
        with self.assertRaises(ValueError):
            uses.degree_choices_candidate(upper,{},bend_excursions={USE:{ref:'2',other:'2'}})
        self.assertEqual(upper,frozen)

    def test_plateau_is_checked_even_when_final_arrival_is_in_key(self):
        docs,_,_,_,_,_=build()
        curve=docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['bend']
        curve['points']=[dict(position=0,tone=0),dict(position=10,tone=50),
                        dict(position=30,tone=50),dict(position=60,tone=0)]
        lower=extract_documents(docs)
        t2=connected.strip_lower(connected.analyze(lower))
        upper=uses.bind_written_ties(uses.from_tier2(t2,[SPEC]))
        paths=list(range(len(upper['materials'][0]['pitch_paths'])))
        upper=uses.lift_degree_paths(upper,USE,path_refs=paths,
            interpretations={p:[fixture.KEY]for p in paths},evidence_ref='authored-C-major')
        ref=upper['materials'][0]['lower_tier']['coattacks'][0]['members'][0]['id']
        # E -> F# plateau -> E: arrival alone would incorrectly admit this.
        with self.assertRaisesRegex(ValueError,'bend target'):
            uses.degree_choices_candidate(upper,{},bend_excursions={USE:{ref:'2'}})

    def test_saved_zero_then_successive_joint_edit_does_not_compound_curve(self):
        _,_,upper,group,ref,other=build()
        first=change(upper,group,ref,other)
        zero=uses.degree_choices_candidate(reload(first),{})
        self.assertEqual(zero,first)
        # C -> E uses extent4; it is not extent2 multiplied by4.
        second=change(reload(first),group,ref,other,extent='4',step=-2)
        raw=project_documents(uses.reconstruct(second,{'variation':0}))
        note=raw['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]
        self.assertEqual(note['fret'],0)
        self.assertEqual(note['bend']['tone'],200)
        self.assertEqual(second['materials'],upper['materials'])
        self.assertEqual(second['lower_tier'],upper['lower_tier'])

    def test_saved_bend_survives_joint_entry_clock_without_readdressing_selection(self):
        _,_,upper,group,ref,other=build()
        first=change(upper,group,ref,other)
        lane='track-2.json#/measures/0/voices/0/beats'
        later,_=clock.apply_entry_choices(reload(first),[dict(use_id=USE,scope=SPEC,
            lane_shares={lane:{lane+'/'+str(i):v for i,v in enumerate(('1/7','2/7','2/7','2/7'))}},
            entry_shares={lane:'1/8'})])
        actual=project_documents(uses.reconstruct(reload(later),{'variation':0}))
        beats=actual['track-2.json']['measures'][0]['voices'][0]['beats']
        self.assertTrue(beats[0]['rest'])
        self.assertEqual(beats[1]['notes'][0]['bend']['tone'],100)
        self.assertEqual(later['uses'][0]['bend_excursions'],{ref:'2'})
        self.assertEqual(later['lower_tier'],upper['lower_tier'])

    def test_complete_parent_tie_membership_is_required(self):
        _,_,unbound,group,ref,other=build(bound=False)
        with self.assertRaisesRegex(ValueError,'written-tie ownership'):
            change(unbound,group,ref,other)

    def test_actual_denied_source_worker_uses_same_complete_inverse(self):
        from run_support_use_qa import bundle
        from qa_isolation_harness import execute
        docs,_,upper,group,ref,other=build(plateau=True)
        after=change(upper,group,ref,other)
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory() as directory:
            result=execute(code,reload(after),{'variation':0},expected(docs),
                Path(directory)/'denied',timeout=90,purpose='exact_zero')
        self.assertEqual(result['status'],'PASS',result)
        self.assertFalse(result['parent_expected_staged'])


if __name__=='__main__':unittest.main()
