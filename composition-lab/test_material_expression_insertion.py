"""Saved expression insertion preserves ordered, material-derived membership."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import connected_tier2 as connected
import local_accents as accents
import local_palm_mutes as mutes
import material_rhythm_control as rhythm
import support_material_uses as uses
import test_material_expression_composition as fixture
from source_fact_tier1 import extract_documents, project_documents

BEAT='track-2.json#/measures/0/voices/0/beats/0'
def reload(value): return json.loads(json.dumps(value))

def build(*, text=False):
    docs=fixture.authored_documents()
    beat=docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]
    del beat['palmMute']
    if text: beat['text']=dict(text='one indication',width=1)
    t2=connected.strip_lower(connected.analyze(extract_documents(docs),
        note_accent_slots=True,palm_mute_slots=True,dynamic_evidence=True,
        expression_evidence=True))
    model=uses.from_tier2(t2,[fixture.SPEC])
    model=rhythm.candidate(rhythm.lift(model,fixture.USE),fixture.USE,'1/2')
    return docs,model

def group(model,ref=BEAT):
    return next(g for g in model['owned_parameters']['optional_beat_palm_mutes']['groups']
                if g['beat_structure']['id']==ref)

class MaterialInsertionTests(unittest.TestCase):
    def test_new_mute_after_derived_dot_survives_exact_save_and_inverse(self):
        docs,model=build(); before=deepcopy(model)
        current=uses.expand(model)
        self.assertNotIn(BEAT+'/dots',group(model['lower_tier'])['beat_structure']['children'])
        self.assertIn(BEAT+'/dots',group(current)['beat_structure']['children'])
        changed=mutes.apply(current,[BEAT],[dict(kind='explicit',value=True)])
        packed=uses.pack_expression(model,changed)
        self.assertEqual(model,before)
        self.assertEqual(packed['materials'],model['materials'])
        self.assertEqual(packed['uses'],model['uses'])
        self.assertEqual(packed['lower_tier']['owned_parameters']['observed_expression'],
                         model['lower_tier']['owned_parameters']['observed_expression'])
        expected=fixture.expected_later(docs)
        expected['track-2.json']['measures'][0]['voices'][0]['beats'][0]['palmMute']=True
        saved=reload(packed)
        with patch('builtins.open',side_effect=AssertionError('Hidden source read')),patch.object(Path,'open',side_effect=AssertionError('Hidden source read')):
            self.assertEqual(uses.expand(saved),changed)
            self.assertEqual(uses.reconstruct(saved,{'variation':0}),extract_documents(expected))
        later=mutes.apply(uses.expand(saved),[BEAT],[dict(kind='explicit',value=False)])
        updated=uses.pack_expression(saved,later)
        self.assertEqual(uses.expand(reload(updated)),later)
        self.assertEqual(uses.pack_expression(updated,uses.expand(updated)),updated)

    def test_split_children_append_coherently_then_subdivide_again(self):
        _,model=build()
        first=next(g['id'] for g in model['materials'][0]['lower_tier']['coattacks'] if g['part_id']==2)
        split,_=uses.subdivision_candidate(model,{fixture.USE:[first]})
        refs=[BEAT,BEAT.rsplit('/',1)[0]+'/1']
        current=uses.expand(split)
        changed=mutes.apply(current,refs,[dict(kind='explicit',value=True)]*2)
        packed=uses.pack_expression(split,changed)
        self.assertEqual(uses.expand(reload(packed)),changed)
        later,_=uses.subdivision_candidate(reload(packed),{fixture.USE:[first]})
        actual=project_documents(uses.reconstruct(later,{'variation':0}))
        for beat in actual['track-2.json']['measures'][0]['voices'][0]['beats'][:4]:
            self.assertIs(beat['palmMute'],True)
            self.assertEqual(list(beat)[-2:],['dots','palmMute'])

    def test_accent_insertion_and_existing_mute_position_remain_independent(self):
        _,model=build(); current=uses.expand(model)
        changed=accents.apply(current,BEAT+'/notes/0',dict(kind='explicit',value=1))
        packed=uses.pack_expression(model,changed)
        self.assertEqual(uses.expand(reload(packed)),changed)
        self.assertEqual(group(packed['lower_tier']),group(model['lower_tier']))
        original=deepcopy(model); corrupted=deepcopy(changed)
        corrupted['source_origin']['facts_sha256']='0'*64
        with self.assertRaises(ValueError):uses.pack_expression(model,corrupted)
        self.assertEqual(model,original)

    def test_child_text_removal_translates_insertion_by_sibling_identity(self):
        _,model=build(text=True)
        first=next(g['id'] for g in model['materials'][0]['lower_tier']['coattacks'] if g['part_id']==2)
        split,_=uses.subdivision_candidate(model,{fixture.USE:[first]})
        refs=[BEAT,BEAT.rsplit('/',1)[0]+'/1']
        current=uses.expand(split)
        changed=mutes.apply(current,refs,[dict(kind='explicit',value=True)]*2)
        self.assertNotEqual(group(changed,refs[0])['state']['child_index'],
                            group(changed,refs[1])['state']['child_index'])
        packed=uses.pack_expression(split,changed)
        self.assertEqual(uses.expand(reload(packed)),changed)
        later,_=uses.subdivision_candidate(reload(packed),{fixture.USE:[first]})
        beats=project_documents(uses.reconstruct(later,{'variation':0}))['track-2.json']['measures'][0]['voices'][0]['beats']
        self.assertIn('text',beats[0])
        self.assertTrue(all('text' not in beat for beat in beats[1:4]))
        self.assertTrue(all(list(beat)[-1]=='palmMute' for beat in beats[:4]))

    def test_different_split_values_remain_atomic_refusal(self):
        _,model=build()
        first=next(g['id'] for g in model['materials'][0]['lower_tier']['coattacks'] if g['part_id']==2)
        split,_=uses.subdivision_candidate(model,{fixture.USE:[first]})
        frozen=deepcopy(split);current=uses.expand(split)
        changed=mutes.apply(current,[BEAT],[dict(kind='explicit',value=True)])
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_CHILD_EXPRESSION_OWNER_REQUIRED'):
            uses.pack_expression(split,changed)
        self.assertEqual(split,frozen)

    def test_source_explicit_flag_after_text_keeps_original_order_on_first_child(self):
        from test_material_subdivision_uses import expected_split
        docs=fixture.authored_documents()
        beat=docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]
        value=beat.pop('palmMute');beat['text']=dict(text='one indication',width=1)
        beat['palmMute']=value
        t2=connected.strip_lower(connected.analyze(extract_documents(docs),
            note_accent_slots=True,palm_mute_slots=True,dynamic_evidence=True))
        model=uses.from_tier2(t2,[fixture.SPEC])
        first=next(g['id'] for g in model['materials'][0]['lower_tier']['coattacks'] if g['part_id']==2)
        split,_=uses.subdivision_candidate(model,{fixture.USE:[first]})
        expected=expected_split(docs,{2:[0]})
        del expected['track-2.json']['measures'][0]['voices'][0]['beats'][1]['text']
        self.assertEqual(uses.reconstruct(reload(split),{'variation':0}),extract_documents(expected))
        self.assertNotIn('expression_insertions',split)

    def test_absent_removes_live_placement_and_malformed_placement_refuses(self):
        _,model=build();current=uses.expand(model)
        changed=mutes.apply(current,[BEAT],[dict(kind='explicit',value=True)])
        packed=uses.pack_expression(model,changed)
        self.assertEqual(packed['expression_insertions'],{'palm-mute-slot:'+BEAT:'append'})
        absent=mutes.apply(uses.expand(packed),[BEAT],[dict(kind='absent')])
        erased=uses.pack_expression(packed,absent)
        self.assertNotIn('expression_insertions',erased)
        self.assertEqual(erased,model)
        for placements in ({'missing':'append'},{'palm-mute-slot:'+BEAT:'prepend'},
                           {'palm-mute-slot:'+BEAT:{'value':True}}):
            bad=deepcopy(packed);bad['expression_insertions']=placements;frozen=deepcopy(bad)
            with self.assertRaises(ValueError):uses.expand(bad)
            self.assertEqual(bad,frozen)

if __name__=='__main__': unittest.main()
