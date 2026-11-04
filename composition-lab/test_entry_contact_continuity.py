"""Only existing, validated written contact equalities create carry requests."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

import backing_execution_constraints as execution
import entry_contact_continuity as contact
from test_execution_dependencies import documents,n
from test_material_execution_clock import adjacent,clock_guard,saved
from test_material_execution_locks import source,state,ref


class EntryContactContinuityTests(unittest.TestCase):
    def test_ring_and_exit_explicit_fences_produce_identity_only_pair(self):
        for kind in ('ring','exit'):
            docs=adjacent(kind);_,_,guard=clock_guard(docs);lower,records,refs=state(docs)
            before=deepcopy((guard,lower,records,refs))
            self.assertEqual(contact.required_pairs(saved(guard),lower,records,refs),
                [dict(previous_ref=ref(0),next_ref=ref(1))])
            self.assertEqual((guard,lower,records,refs),before)

    def test_selection_is_current_explicit_and_does_not_create_a_requirement(self):
        docs=adjacent();_,_,guard=clock_guard(docs);args=state(docs)
        self.assertEqual(contact.required_pairs(guard,*args,selected_next_refs=[]),[])
        self.assertEqual(contact.required_pairs(guard,*args,selected_next_refs=[ref(0)]),[])
        self.assertEqual(len(contact.required_pairs(guard,*args,selected_next_refs=[ref(1)])),1)
        for invalid in ([ref(7)],[ref(1),ref(1)],[None],'all'):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                contact.required_pairs(guard,*args,selected_next_refs=invalid)

    def test_existing_gap_and_overlap_do_not_become_continuity_claims(self):
        docs=source('ring');_,_,guard=clock_guard(docs)
        self.assertEqual(contact.required_pairs(guard,*state(docs)),[])
        docs=adjacent();voices=docs['track-0.json']['measures'][0]['voices']
        voices[0]['beats'][0]['duration']=[3,8];voices[0]['beats'][1]['duration']=[5,8]
        voices[0]['beats'][1]['notes']=[]
        voices.append(dict(beats=[dict(duration=[1,4],notes=[]),dict(duration=[3,4],notes=[n(5)])]))
        _,_,guard=clock_guard(docs)
        self.assertEqual(contact.required_pairs(guard,*state(docs)),[])

    def test_unknown_part_end_does_not_invent_a_next_contact(self):
        docs=documents([n(2),None,None,None],{0:dict(letRing=True)})
        _,_,guard=clock_guard(docs)
        self.assertEqual(contact.required_pairs(guard,*state(docs)),[])

    def test_chord_members_keep_their_own_next_string_contact(self):
        docs=adjacent();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['notes'].append(dict(string=4,fret=3))
        beats[1]['notes'].append(dict(string=4,fret=7))
        _,_,guard=clock_guard(docs)
        self.assertEqual(contact.required_pairs(guard,*state(docs)),[
            dict(previous_ref=ref(0),next_ref=ref(1)),
            dict(previous_ref='event:86:0:1:0:0:1',next_ref='event:86:0:1:0:1:1')])

    def test_requires_valid_current_v3_no_stale_rebaseline(self):
        docs=adjacent();v1,v2,v3=clock_guard(docs);args=state(docs)
        for old in (v1,v2):
            with self.assertRaisesRegex(ValueError,'v3'):contact.required_pairs(old,*args)
        changed=deepcopy(docs)
        changed['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['string']=4
        before=deepcopy(v3)
        with self.assertRaises(ValueError):contact.required_pairs(v3,*state(changed))
        self.assertEqual(v3,before)

    def test_groups_use_protected_complete_coending_members_not_chord_inference(self):
        docs=adjacent();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['notes'].append(dict(string=4,fret=3))
        _,_,guard=clock_guard(docs)
        self.assertEqual(contact.required_groups(guard,*state(docs),selected_next_refs=[ref(1)]),[
            dict(member_refs=[ref(0),'event:86:0:1:0:0:1'],next_ref=ref(1))])
        self.assertEqual(contact.required_groups(guard,*state(docs),selected_next_refs=[]),[])

    def test_current_identity_mapping_after_saved_entry_change(self):
        docs=adjacent();_,_,guard=clock_guard(docs)
        beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[1]['duration']=[1,2];beats.insert(0,dict(duration=[1,4],notes=[]))
        lower,records,refs=state(docs)
        identities={ref(1):ref(0),ref(2):ref(1)}
        facts={row['source_fact_ref']:row['source_fact_ref'].replace('/beats/1/','/beats/0/')for row in records}
        self.assertEqual(contact.required_pairs(saved(guard),lower,records,refs,
            selected_next_refs=[ref(2)],identity_map=identities,fact_identity_map=facts),
            [dict(previous_ref=ref(1),next_ref=ref(2))])

    def test_group_member_order_is_numeric_occurrence_order(self):
        docs=adjacent();track=docs['track-0.json'];track['tuning']=[64-i for i in range(11)]
        track['measures'][0]['voices'][0]['beats'][0]['notes']=[dict(string=i,fret=2)for i in range(11)]
        _,_,guard=clock_guard(docs)
        groups=contact.required_groups(guard,*state(docs),selected_next_refs=[ref(1)])
        self.assertEqual(groups[0]['member_refs'],[f'event:86:0:1:0:0:{i}'for i in range(11)])

    def test_saved_current_input_without_source_or_snapshot_cache(self):
        docs=adjacent();_,_,guard=clock_guard(docs);args=state(docs)
        execution._snapshot.cache_clear()
        with patch('builtins.open',side_effect=AssertionError('Source access')),\
             patch.object(Path,'read_text',side_effect=AssertionError('Source access')),\
             patch.object(Path,'read_bytes',side_effect=AssertionError('Source access')):
            self.assertEqual(len(contact.required_pairs(saved(guard),*args)),1)


if __name__=='__main__':unittest.main()
