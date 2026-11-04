"""Written contact topology permits timing choices without guessing ring ends."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import backing_execution_constraints as execution
import material_execution_locks as locks
from test_execution_dependencies import documents,n
from test_material_execution_locks import source,state,ref
from test_material_successor_choices import upgraded


def saved(value):return json.loads(json.dumps(value))


def adjacent(kind='ring'):
    docs=documents([n(2),n(5)],{0:dict(letRing=True)}if kind=='ring'else{})
    beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
    beats[0]['duration']=[1,4];beats[1]['duration']=[3,4]
    if kind=='exit':beats[0]['notes'][0]['slide']='downwards'
    return docs


def clock_guard(docs):
    lower,records,refs,legacy,v2=upgraded(docs)
    return legacy,v2,locks.upgrade_clock_choices(v2,lower,records,refs)


class MaterialExecutionClockTests(unittest.TestCase):
    def test_explicit_upgrade_preserves_all_original_fields_without_note_payload(self):
        for kind in ('ring','exit'):
            docs=adjacent(kind);lower,records,refs=state(docs)
            legacy,v2,v3=clock_guard(docs);before=deepcopy((lower,records,legacy,v2))
            self.assertEqual(v3['schema'],locks.CLOCK_SCHEMA)
            self.assertEqual(locks._legacy_guard(v3),legacy)
            self.assertEqual(locks._successor_guard(v3),v2)
            self.assertEqual(v3['successor_guard_sha256'],locks._hash(v2))
            scope=locks.choice_scope(saved(v3),lower,records,refs)
            self.assertEqual(scope['clock_flexible_refs'],scope['covered_refs'])
            self.assertEqual(scope['strict_refs'],[])
            self.assertEqual((lower,records,legacy,v2),before)
            for forbidden in ('"notes"','"pitch"','"fret"','"onset_q"','"duration_q"','"performed_end_q"'):
                self.assertNotIn(forbidden,json.dumps(v3))

    def test_shared_boundary_one_plus_three_to_two_plus_two_then_saved_successive_edit(self):
        for kind in ('ring','exit'):
            docs=adjacent(kind);legacy,v2,v3=clock_guard(docs)
            before=deepcopy(v3);original_records=state(docs)[1]
            for first,second in (([1,2],[1,2]),([3,8],[5,8])):
                changed=deepcopy(docs);beats=changed['track-0.json']['measures'][0]['voices'][0]['beats']
                beats[0]['duration']=first;beats[1]['duration']=second
                beats[0]['notes'][0]['fret']=3;beats[1]['notes'][0]['fret']=6
                lower,records,refs=state(changed)
                self.assertEqual(records,original_records)
                locks.validate(saved(v3),lower,records,refs)
                for old in (legacy,v2):
                    with self.assertRaisesRegex(ValueError,'context changed'):
                        locks.validate(old,lower,records,refs)
            self.assertEqual(v3,before)

    def test_stale_v2_and_second_upgrade_refuse_without_recapturing(self):
        docs=adjacent();_,v2,v3=clock_guard(docs)
        changed=deepcopy(docs);beats=changed['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['duration']=[1,2];beats[1]['duration']=[1,2]
        with self.assertRaisesRegex(ValueError,'context changed'):
            locks.upgrade_clock_choices(v2,*state(changed))
        with self.assertRaisesRegex(ValueError,'existing v2'):
            locks.upgrade_clock_choices(v3,*state(docs))

    def test_commitment_projection_and_payload_tampering_refuse(self):
        docs=adjacent();_,_,guard=clock_guard(docs)
        for field in ('fingerprint','successor_fingerprint','clock_fingerprint','legacy_guard_sha256',
                      'successor_guard_sha256','missing','payload'):
            changed=deepcopy(guard)
            if field.endswith('sha256'):changed[field]='0'*64
            elif field=='missing':changed['locks'][0].pop('clock_fingerprint')
            elif field=='payload':changed['locks'][0]['notes']=[60]
            else:changed['locks'][0][field]='0'*64
            with self.subTest(field=field),self.assertRaises(ValueError):
                locks.validate(changed,*state(docs))

    def test_changed_next_contact_and_new_intervening_contacts_refuse(self):
        docs=source('ring');_,_,guard=clock_guard(docs)
        for action in ('insert','other_voice','replace_next','next_string','dead','grace','tie'):
            changed=deepcopy(docs);voices=changed['track-0.json']['measures'][0]['voices'];beats=voices[0]['beats']
            if action=='insert':beats[1]['notes']=[n(4)]
            elif action=='other_voice':voices.append(dict(beats=[dict(duration=[1,4],notes=[]),
                dict(duration=[3,4],notes=[n(3)])]))
            elif action=='replace_next':beats[2]['notes']=[]
            elif action=='next_string':beats[2]['notes'][0]['string']=4
            elif action=='dead':beats[2]['notes'][0]['dead']=True
            elif action=='grace':beats[2]['graceNote']=True
            elif action=='tie':beats[2]['notes'][0]['tie']=True
            before=deepcopy(guard)
            with self.subTest(action=action),self.assertRaises(ValueError):locks.validate(guard,*state(changed))
            self.assertEqual(guard,before)

    def test_current_neighborhood_detects_existing_contact_moved_into_window(self):
        docs=source('ring')
        voices=docs['track-0.json']['measures'][0]['voices']
        voices.append(dict(beats=[dict(duration=[3,4],notes=[]),dict(duration=[1,4],notes=[n(8)])]))
        _,_,guard=clock_guard(docs)
        changed=deepcopy(docs);beats=changed['track-0.json']['measures'][0]['voices'][1]['beats']
        beats[0]['duration']=[3,8];beats[1]['duration']=[5,8]
        with self.assertRaisesRegex(ValueError,'context changed'):locks.validate(guard,*state(changed))

    def test_contiguous_to_gap_or_overlap_refuses_even_with_same_contact_ids(self):
        docs=adjacent();voices=docs['track-0.json']['measures'][0]['voices']
        # The next contact belongs to another voice; its onset stays independent
        # from the origin's duration, so changing one can open a gap or overlap.
        voices[0]['beats'][1]['notes']=[]
        voices.append(dict(beats=[dict(duration=[1,4],notes=[]),dict(duration=[3,4],notes=[n(5)])]))
        _,_,guard=clock_guard(docs)
        for duration,remainder in (([1,8],[7,8]),([3,8],[5,8])):
            changed=deepcopy(docs);beats=changed['track-0.json']['measures'][0]['voices'][0]['beats']
            beats[0]['duration']=duration;beats[1]['duration']=remainder
            with self.assertRaisesRegex(ValueError,'context changed'):locks.validate(guard,*state(changed))

    def test_overlap_to_gap_with_same_non_equal_endpoints_refuses(self):
        docs=adjacent();voices=docs['track-0.json']['measures'][0]['voices']
        voices[0]['beats'][0]['duration']=[3,8];voices[0]['beats'][1]['duration']=[5,8]
        voices[0]['beats'][1]['notes']=[]
        voices.append(dict(beats=[dict(duration=[1,4],notes=[]),dict(duration=[3,4],notes=[n(5)])]))
        _,_,guard=clock_guard(docs)
        changed=deepcopy(docs);beats=changed['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['duration']=[1,8];beats[1]['duration']=[7,8]
        with self.assertRaisesRegex(ValueError,'context changed'):locks.validate(guard,*state(changed))

    def test_incoming_tie_outside_window_remains_a_dependency(self):
        docs=documents([None,None,None,n(2)])
        docs['track-0.json']['measures'].append(dict(signature=[4,4],voices=[dict(beats=[
            dict(duration=[1,4],letRing=True,notes=[n(2,tie=True)]),
            dict(duration=[3,4],notes=[n(5)])])]))
        _,_,guard=clock_guard(docs)
        scope=locks.choice_scope(guard,*state(docs))
        self.assertIn(ref(3),scope['covered_refs'])
        changed=deepcopy(docs);beats=changed['track-0.json']['measures'][1]['voices'][0]['beats']
        beats[0]['duration']=[1,2];beats[1]['duration']=[1,2]
        locks.validate(saved(guard),*state(changed))
        changed['track-0.json']['measures'][0]['voices'][0]['beats'][3]['duration']=[1,8]
        with self.assertRaisesRegex(ValueError,'incoming written tie'):locks.validate(guard,*state(changed))

    def test_hopo_shift_legato_keep_strict_clock_and_pitch(self):
        for kind in ('hp','shift','legato'):
            notes=[n(2),n(4),n(7,hp=True),n(7)]if kind=='hp'else[n(2),n(4),n(7,slide=kind),None]
            docs=documents(notes,{0:dict(letRing=True)});_,_,guard=clock_guard(docs)
            scope=locks.choice_scope(guard,*state(docs))
            self.assertIn(ref(2),scope['strict_refs'])
            self.assertNotIn(ref(2),scope['clock_flexible_refs'])
            changed=deepcopy(docs);beats=changed['track-0.json']['measures'][0]['voices'][0]['beats']
            beats[2]['duration']=[1,8];beats[3]['duration']=[3,8]
            with self.subTest(kind=kind),self.assertRaises(ValueError):locks.validate(guard,*state(changed))

    def test_added_contact_during_incoming_tie_predecessor_hold_refuses(self):
        docs=documents([None,None,None,n(2)])
        docs['track-0.json']['measures'].append(dict(signature=[4,4],voices=[dict(beats=[
            dict(duration=[1,4],letRing=True,notes=[n(2,tie=True)]),
            dict(duration=[3,4],notes=[n(5)])])]))
        _,_,guard=clock_guard(docs)
        # The added contact ends exactly where the main letRing window starts;
        # checking only that window misses interruption of its incoming hold.
        docs['track-0.json']['measures'][0]['voices'].append(dict(beats=[
            dict(duration=[7,8],notes=[]),dict(duration=[1,8],notes=[n(8)])]))
        with self.assertRaisesRegex(ValueError,'context changed'):locks.validate(guard,*state(docs))

    def test_no_source_reads_or_cached_original_needed_after_reload(self):
        docs=adjacent();_,_,guard=clock_guard(docs)
        beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['duration']=[1,2];beats[1]['duration']=[1,2]
        lower,records,refs=state(docs);guard=saved(guard)
        execution._snapshot.cache_clear()
        with patch('builtins.open',side_effect=AssertionError('Source access')),\
             patch.object(Path,'read_text',side_effect=AssertionError('Source access')),\
             patch.object(Path,'read_bytes',side_effect=AssertionError('Source access')):
            locks.validate(guard,lower,records,refs)

    def test_leading_rest_keeps_original_occurrence_and_fact_identities(self):
        docs=adjacent();_,_,guard=clock_guard(docs)
        changed=deepcopy(docs);beats=changed['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[1]['duration']=[1,2]
        beats.insert(0,dict(duration=[1,4],notes=[]))
        lower,records,refs=state(changed)
        identities={ref(1):ref(0),ref(2):ref(1)}
        facts={row['source_fact_ref']:row['source_fact_ref'].replace('/beats/1/','/beats/0/')
               for row in records if row['source_fact_ref']is not None}
        locks.validate(saved(guard),lower,records,refs,identity_map=identities,fact_identity_map=facts)
        with self.assertRaises(ValueError):locks.validate(guard,lower,records,refs)

    def test_unrelated_later_or_other_string_changes_remain_free(self):
        docs=source('ring');_,_,guard=clock_guard(docs)
        beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[3]['notes'][0]['fret']=9;beats[1]['notes']=[dict(string=4,fret=3)]
        locks.validate(guard,*state(docs))


if __name__=='__main__':unittest.main()
