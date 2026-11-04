"""Silent source bars stay exact while adjacent current attacks can subdivide."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import connected_tier2 as connected
import musical_support_material as material
import support_material_uses as uses
import test_material_expression_composition as fixture
from source_fact_tier1 import extract_documents, project_documents

SPEC=dict(parts=[2],first_bar=1,last_bar=3)
USE='material-use:0'

def saved(value):return json.loads(json.dumps(value))

def documents():
    docs=fixture.authored_documents()
    measures=docs['track-2.json']['measures']
    measures[1]=dict(signature=[4,4],rest=True,
        marker=dict(text='silent source bar'),
        voices=[dict(rest=True,beats=[dict(type=1,duration=[1,1],rest=True,notes=[dict(rest=True)])])])
    measures[2]=deepcopy(measures[0])
    return docs

def analyze(docs):
    lower=extract_documents(docs)
    return lower,connected.strip_lower(connected.analyze(lower,
        note_accent_slots=True,palm_mute_slots=True,dynamic_evidence=True,
        backing_bindings=[fixture.direct.FOREIGN]))

def expected(docs,factors):
    result=deepcopy(docs)
    for bar,factor in factors.items():
        voice=result['track-2.json']['measures'][bar-1]['voices'][0]
        first=voice['beats'][0]
        children=[deepcopy(first)for _ in range(factor)]
        for child in children:
            child['type']*=factor;child['duration'][1]*=factor
        voice['beats']=children+voice['beats'][1:]
    return result


class MaterialSilentSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs=documents();cls.lower,cls.t2=analyze(cls.docs)
        cls.model=uses.from_tier2(cls.t2,[SPEC])
        groups=cls.model['materials'][0]['lower_tier']['coattacks']
        cls.refs={bar:next(g['id']for g in groups if g['bar']==bar)for bar in (1,3)}

    def test_saved_zero_retains_silent_flags_placeholders_clock_and_every_fact(self):
        self.assertEqual(uses.expand(saved(self.model)),self.t2)
        self.assertEqual(uses.reconstruct(saved(self.model),{'variation':0}),self.lower)
        definition=self.model['materials'][0]
        slot=next(r for r in definition['slots']if '/measures/1/'in r['beat_ref'])
        self.assertLess(slot['from_pulse'],slot['to_pulse'])
        self.assertFalse(any(g['bar']==2 for g in definition['lower_tier']['coattacks']))
        self.assertEqual(project_documents(self.lower),self.docs)
        self.assertEqual(self.model['lower_tier']['source_origin'],self.t2['source_origin'])

    def test_silent_slots_can_be_owned_without_inventing_a_pitched_attack(self):
        docs=documents()
        docs['track-2.json']['measures'][2]=deepcopy(docs['track-2.json']['measures'][1])
        lower,t2=analyze(docs)
        model=uses.from_tier2(t2,[dict(parts=[2],first_bar=2,last_bar=3)])
        definition=model['materials'][0]
        self.assertEqual(definition['lower_tier']['coattacks'],[])
        self.assertEqual(definition['pitch_paths'],[])
        self.assertEqual(uses.reconstruct(saved(model),{'variation':0}),lower)
        before=deepcopy(model)
        with self.assertRaises(ValueError):uses.subdivision_candidate(model,{USE:[]})
        self.assertEqual(model,before)

    def test_one_clock_slot_remains_explicit_existing_group_boundary(self):
        # The shared group-clock relation needs at least two slots. This repair
        # admits silence within groups; it does not change that other contract.
        before=deepcopy(self.t2)
        with self.assertRaisesRegex(ValueError,'at least two attacks'):
            uses.from_tier2(self.t2,[dict(parts=[2],first_bar=2,last_bar=2)])
        self.assertEqual(self.t2,before)

    def test_independent_attacks_before_and_after_silence_change_without_moving_it(self):
        before=deepcopy(self.model)
        changed,report=uses.subdivision_candidate(self.model,{USE:list(self.refs.values())},percent=100)
        current_t2,current,ledger=uses.realize_pair(saved(changed))
        self.assertEqual(project_documents(current),expected(self.docs,{1:2,3:2}))
        self.assertEqual(report['changed_current_attacks'],2)
        self.assertEqual(report['changed_note_durations'],4)
        self.assertEqual(report['original_onsets_moved'],0)
        self.assertEqual(current_t2['source_origin'],self.t2['source_origin'])
        self.assertEqual(self.model,before)
        self.assertEqual(changed['materials'],before['materials'])
        self.assertEqual(changed['lower_tier'],before['lower_tier'])
        # Later edits address the same saved parent beyond the silent bar.
        again,second=uses.subdivision_candidate(saved(changed),{USE:[self.refs[3]]})
        self.assertEqual(second['current_attacks'],2)
        self.assertEqual(second['changed_current_attacks'],2)
        self.assertEqual(project_documents(uses.reconstruct(saved(again),{'variation':0})),expected(self.docs,{1:2,3:4}))
        old_ids={r['identity']for r in ledger}
        new_ids={r['identity']for r in uses.realize_pair(again)[2]}
        self.assertTrue(old_ids<=new_ids)

    def test_actual_denied_inverse_preserves_silent_bar_after_change(self):
        from qa_isolation_harness import execute
        from run_support_use_qa import bundle
        changed,_=uses.subdivision_candidate(self.model,{USE:list(self.refs.values())})
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory()as folder:
            receipt=execute(code,saved(changed),{'variation':0},extract_documents(expected(self.docs,{1:2,3:2})),
                Path(folder)/'proof',timeout=60,purpose='exact_zero')
            self.assertEqual(receipt['status'],'PASS',receipt)
            self.assertFalse(receipt['parent_expected_staged'])

    def test_rest_declarations_do_not_hide_pitched_or_dead_attacks(self):
        for note in (dict(string=0,fret=0),dict(rest=True,string=0,fret=0),dict(dead=True,string=0)):
            with self.subTest(note=note):
                docs=documents()
                docs['track-2.json']['measures'][1]['voices'][0]['beats'][0]['notes']=[note]
                lower,t2=analyze(docs);before=deepcopy(t2)
                with self.assertRaisesRegex(ValueError,'Declared silent measure'):
                    material.fit(t2,**SPEC,lower=lower)
                self.assertEqual(t2,before)

    def test_invalid_silent_structure_or_clock_is_refused_not_reinterpreted(self):
        for name in ('empty_voice','empty_beats','short_span','two_rest_beats','untyped_rest_flag'):
            with self.subTest(case=name):
                docs=documents();measure=docs['track-2.json']['measures'][1]
                if name=='empty_voice':measure['voices']=[]
                elif name=='empty_beats':measure['voices'][0]['beats']=[]
                elif name=='short_span':measure['voices'][0]['beats'][0]['duration']=[1,2]
                elif name=='two_rest_beats':measure['voices'][0]['beats']*=2
                else:measure['rest']=1
                lower,t2=analyze(docs);before=deepcopy(t2)
                with self.assertRaises(ValueError):material.fit(t2,**SPEC,lower=lower)
                self.assertEqual(t2,before)


if __name__=='__main__':unittest.main()
