"""Authored execution-context boundaries, not claims about musical quality."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import backing_execution_constraints as execution
import material_execution_locks as locks
from source_fact_tier1 import extract_documents
from test_execution_dependencies import documents,n


def saved(value):return json.loads(json.dumps(value))
def ref(beat,bar=1,voice=0):return f'event:86:0:{bar}:{voice}:{beat}:0'
def state(docs):
    lower=extract_documents(docs)
    data=execution._snapshot(execution.encoded(lower))
    return lower,data['records'],execution.ordered(data['nodes'])
def source(kind='exit'):
    if kind=='exit':return documents([n(2,slide='downwards'),None,n(4),n(7)])
    if kind=='ring':return documents([n(2),None,n(4),n(7)],{0:dict(letRing=True)})
    if kind=='hp':return documents([n(2,hp=True),n(2),n(4),n(7)])
    if kind=='shift':return documents([n(2,slide='shift'),None,n(4),n(7)])
    raise AssertionError(kind)


class MaterialExecutionLockTests(unittest.TestCase):
    def test_capture_and_saved_validation_keep_unknowns_without_note_payload(self):
        for kind in ('exit','ring','hp','shift'):
            with self.subTest(kind=kind):
                lower,records,refs=state(source(kind));before=deepcopy((lower,records))
                guard=locks.capture(lower,records,refs)
                protected=locks.validate(saved(guard),lower,records,refs)
                self.assertIn(ref(0),protected)
                self.assertEqual((lower,records),before)
                text=json.dumps(guard)
                for forbidden in ('"pitch"','"fret"','"notes"','"source_t1"','"lower_tier"','"onset_q"'):
                    self.assertNotIn(forbidden,text)

    def test_new_same_string_contact_between_members_refuses_despite_identical_records(self):
        for kind in ('exit','ring'):
            with self.subTest(kind=kind):
                docs=source(kind);lower,records,refs=state(docs)
                guard=locks.capture(lower,records,refs);before=deepcopy(guard)
                changed=deepcopy(docs)
                changed['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes']=[n(3)]
                current,new_records,new_refs=state(changed)
                self.assertEqual(records,new_records)
                # This is the old guard's precise blind spot.
                execution.build(current,[ref(1)])
                with self.assertRaisesRegex(ValueError,'context changed'):
                    locks.validate(guard,current,new_records,new_refs)
                self.assertEqual(guard,before)

    def test_more_distant_note_and_other_string_edit_remain_independent(self):
        for kind in ('exit','ring','hp','shift'):
            with self.subTest(kind=kind):
                docs=source(kind);lower,records,refs=state(docs);guard=locks.capture(lower,records,refs)
                changed=deepcopy(docs)
                changed['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes']=[n(9)]
                current,new_records,new_refs=state(changed)
                locks.validate(saved(guard),current,new_records,new_refs)
        docs=source();lower,records,refs=state(docs);guard=locks.capture(lower,records,refs)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes']=[dict(string=4,fret=3)]
        current,records,refs=state(docs)
        locks.validate(guard,current,records,refs)

    def test_next_contact_boundary_includes_all_voices(self):
        docs=source();lower,records,refs=state(docs);guard=locks.capture(lower,records,refs)
        docs['track-0.json']['measures'][0]['voices'].append(dict(beats=[
            dict(duration=[1,4],notes=[dict(rest=True)]),
            dict(duration=[1,4],notes=[n(3)]),
            dict(duration=[1,2],notes=[dict(rest=True)])]))
        current,new_records,new_refs=state(docs)
        self.assertEqual(records,new_records)
        with self.assertRaisesRegex(ValueError,'context changed'):
            locks.validate(guard,current,new_records,new_refs)

    def test_protected_pitch_contact_duration_grace_and_tie_changes_refuse(self):
        for change in ('pitch','string','duration','grace','tie','delete'):
            with self.subTest(change=change):
                docs=source();lower,records,refs=state(docs);guard=locks.capture(lower,records,refs)
                beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
                if change=='pitch':beats[0]['notes'][0]['fret']=3
                elif change=='string':beats[0]['notes'][0]['string']=4
                elif change=='duration':beats[0]['duration']=[1,8];beats[1]['duration']=[3,8]
                elif change=='grace':beats[0]['graceNote']=True
                elif change=='tie':beats[2]['notes'][0]['tie']=True
                else:beats[2]['notes']=[dict(rest=True)]
                current,records,refs=state(docs)
                with self.assertRaises(ValueError):locks.validate(guard,current,records,refs)

    def test_no_next_contact_protects_written_part_end_without_inventing_endpoint(self):
        docs=documents([n(2),None,n(4,slide='downwards'),None])
        lower,records,refs=state(docs);guard=locks.capture(lower,records,refs)
        boundary=guard['locks'][0]['context_boundaries'][0]
        self.assertEqual(boundary['boundary'],'part_end')
        self.assertEqual(boundary['next_contact_ids'],[])
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes']=[n(6)]
        current,new_records,new_refs=state(docs)
        self.assertEqual(records,new_records)
        with self.assertRaisesRegex(ValueError,'context changed'):
            locks.validate(guard,current,new_records,new_refs)

    def test_relative_clock_and_identity_maps_support_translation_without_rehashing(self):
        for kind in ('exit','ring'):
            with self.subTest(kind=kind):
                docs=source(kind);lower,records,refs=state(docs);guard=locks.capture(lower,records,refs)
                unchanged=deepcopy(guard)
                docs['track-0.json']['measures'].insert(0,dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=[dict(rest=True)])])]))
                current,records,refs=state(docs)
                identities={r:r.replace(':0:2:',':0:1:')for r in refs}
                facts={r['source_fact_ref']:r['source_fact_ref'].replace('/measures/1/','/measures/0/')
                       for r in records if r['source_fact_ref']is not None}
                locks.validate(saved(guard),current,records,refs,identity_map=identities,fact_identity_map=facts,origin_q='4')
                with self.assertRaises(ValueError):
                    locks.validate(guard,current,records,refs,identity_map=identities,fact_identity_map=facts)
                self.assertEqual(guard,unchanged)

    def test_record_removal_missing_nullable_field_and_lock_removal_refuse(self):
        lower,records,refs=state(source());guard=locks.capture(lower,records,refs)
        with self.assertRaises(ValueError):locks.validate(guard,lower,[],refs)
        missing=deepcopy(records);del missing[0]['source_fact_ref']
        with self.assertRaises(ValueError):locks.validate(guard,lower,missing,refs)
        missing_guard=deepcopy(guard);missing_guard['locks']=[]
        with self.assertRaises(ValueError):locks.validate(missing_guard,lower,records,refs)
        payload=deepcopy(guard);payload['locks'][0]['notes']=[60]
        with self.assertRaises(ValueError):locks.validate(payload,lower,records,refs)

    def test_noninjective_identity_map_refuses(self):
        lower,records,refs=state(source())
        with self.assertRaisesRegex(ValueError,'Noninjective'):
            locks.capture(lower,records,refs,identity_map={refs[1]:refs[0]})

    def test_current_owner_input_is_enough_without_files_or_source_cache(self):
        lower,records,refs=state(documents([n(2),None,n(4,slide='downwards'),None]))
        # Warm pure parser imports, then forbid file reads and discard the
        # snapshot cache. No hidden original score supplies the proof.
        guard=locks.capture(lower,records,refs)
        execution._snapshot.cache_clear()
        with patch('builtins.open',side_effect=AssertionError('Unexpected file access')), \
             patch.object(Path,'read_text',side_effect=AssertionError('Unexpected source lookup')), \
             patch.object(Path,'read_bytes',side_effect=AssertionError('Unexpected source lookup')):
            self.assertEqual(locks.capture(lower,records,refs),guard)
            locks.validate(saved(guard),lower,records,refs)

    def test_new_declared_member_refuses_but_expression_without_execution_change_passes(self):
        docs=source('ring');lower,records,refs=state(docs);guard=locks.capture(lower,records,refs)
        original=deepcopy(docs)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['velocity']='pp'
        locks.validate(guard,*state(docs))
        docs=original
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'].append(dict(string=4,fret=3))
        with self.assertRaises(ValueError):locks.validate(guard,*state(docs))

    def test_malformed_lock_does_not_disable_protection(self):
        lower,records,refs=state(source());guard=locks.capture(lower,records,refs)
        for kind in ('digest','boundary','anchors'):
            with self.subTest(kind=kind):
                changed=deepcopy(guard)
                if kind=='digest':changed['locks'][0]['record_identity']=[]
                elif kind=='boundary':changed['locks'][0]['context_boundaries']=[None]
                else:changed['locks'][0]['context_boundaries']=[]
                with self.assertRaises(ValueError):locks.validate(changed,lower,records,refs)


if __name__=='__main__':unittest.main()
