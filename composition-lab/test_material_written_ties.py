"""Sustains cross material boundaries without duplicating pitch authority."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import connected_tier2 as connected
import musical_support_material as material
import support_material_uses as uses
import written_tie_pitch_ownership as ties
from source_fact_tier1 import extract_documents,project_documents
from test_written_tie_pitch_ownership import documents,beat,note


def fixture():
    docs=documents([
        [beat(note(fret=7)),beat(note(fret=9)),beat(note(fret=7)),beat(note(fret=5))],
        [beat(note(fret=5,tie=True),note(1,3)),beat(note(fret=5,tie=True),note(1,5)),
         beat(note(fret=7)),beat(note(fret=9))]])
    lower=extract_documents(docs)
    t2=connected.strip_lower(connected.analyze(lower))
    old=uses.from_tier2(t2,[dict(parts=[0],first_bar=1,last_bar=1)])
    wrapped=uses.bind_written_ties(old)
    result=uses.extend_materials(wrapped,[dict(parts=[0],first_bar=2,last_bar=2)])
    return docs,lower,old,result


def change_head(model,amount):
    out=deepcopy(model)
    definition=out['materials'][0]
    # The declared attack is the final attack of the first material. Its path
    # is the only pitch owner; tails in the other material have no free pitch.
    definition['pitch_paths'][0]['steps'][-1]=str(int(definition['pitch_paths'][0]['steps'][-1])+amount)
    return out


class MaterialWrittenTieTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.docs,cls.lower,cls.old,cls.model=fixture()

    def test_old_definitions_and_all_zero_facts_survive(self):
        self.assertEqual(self.model['materials'][0],self.old['materials'][0])
        self.assertEqual(uses.reconstruct(self.model,{'variation':0}),self.lower)
        shared=uses.expand(self.model)['musical_relationships']
        self.assertEqual(len(shared['relationships']),2)
        tail=next(g for g in material._arrays(uses.expand(self.model))['coattacks'] if g['bar']==2)
        self.assertNotIn('voicing_interval',tail['members'][0])
        self.assertEqual(tail['bass_register_anchor'],'50')

    def test_cross_material_edit_and_reload_preserve_fresh_upper_notes(self):
        before=deepcopy(self.model)
        changed=change_head(self.model,8)
        expected=deepcopy(self.docs)
        expected['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['fret']=13
        for b in (0,1):expected['track-0.json']['measures'][1]['voices'][0]['beats'][b]['notes'][0]['fret']=13
        actual=uses.reconstruct(json.loads(json.dumps(changed)),{'variation':0})
        self.assertEqual(project_documents(actual),expected)
        second=change_head(json.loads(json.dumps(changed)),-2)
        actual=project_documents(uses.reconstruct(second,{'variation':0}))
        self.assertEqual(actual['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0]['fret'],11)
        self.assertEqual(actual['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][1]['fret'],3)
        self.assertEqual(self.model,before)

    def test_tail_parameter_and_changed_contact_refuse(self):
        bad=deepcopy(self.model)
        definition=bad['materials'][1]
        binding=definition['bindings'][0]
        definition['voicings'][binding['voicing_ref']][0]='0'
        with self.assertRaisesRegex(ValueError,'duplicate interval authority'):uses.expand(bad)
        bad=deepcopy(self.model)
        ref='track-0.json#/measures/1/voices/0/beats/0/notes/0/string'
        choice=next(c for c in bad['materials'][1]['lower_tier']['source_choices'] if c['fact_ref']==ref)
        choice['parameter']['normalized']='1'
        with self.assertRaises(ValueError):uses.expand(bad)
        self.assertEqual(uses.reconstruct(self.model,{'variation':0}),self.lower)

    def test_binding_keeps_saved_rhythm_and_optional_membership_owners(self):
        import material_rhythm_control as rhythm
        docs=deepcopy(self.docs)
        for bar in docs['track-0.json']['measures']:
            for row in bar['voices'][0]['beats']:row['type']=4
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['palmMute']=True
        t2=connected.strip_lower(connected.analyze(extract_documents(docs),palm_mute_slots=True))
        model=uses.from_tier2(t2,[dict(parts=[0],first_bar=1,last_bar=1)])
        model=rhythm.candidate(rhythm.lift(model,'material-use:0'),'material-use:0','1/2')
        expected=uses.reconstruct(model,{'variation':0})
        saved_parameters=deepcopy(model['lower_tier']['owned_parameters'])
        bound=uses.bind_written_ties(model)
        self.assertEqual(bound['materials'],model['materials'])
        self.assertEqual(bound['lower_tier']['owned_parameters'],saved_parameters)
        self.assertEqual(uses.reconstruct(bound,{'variation':0}),expected)

    def test_actual_denied_source_inverse_after_saved_cross_material_edit(self):
        from run_support_use_qa import bundle
        from qa_isolation_harness import execute
        changed=change_head(self.model,2)
        expected=deepcopy(self.docs)
        expected['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['fret']=7
        for b in (0,1):expected['track-0.json']['measures'][1]['voices'][0]['beats'][b]['notes'][0]['fret']=7
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory()as folder:
            receipt=execute(code,json.loads(json.dumps(changed)),{'variation':0},extract_documents(expected),
                            Path(folder)/'proof',timeout=60,purpose='exact_zero')
        self.assertEqual(receipt['status'],'PASS',receipt)
        self.assertFalse(receipt['parent_expected_staged'])


if __name__=='__main__':unittest.main()
