"""Typed reduction preserves actual contacts, original ties and guard meaning."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import backing_execution_constraints as execution
import connected_tier2 as connected
import derived_sustain_projection as sustain
import entry_contact_continuity as contact
import material_entry_carry as carry
import material_entry_rest as entry
import material_execution_locks as locks
from source_fact_tier1 import extract_documents,project_documents
from test_material_entry_carry import fixture,planned
from test_written_tie_pitch_ownership import ref,note
from test_material_slot_clock import beat


def run_fixture(*,ring=False,chord=False,existing_tie=False):
    docs,lower,top=fixture(chord=chord,existing_tie=existing_tie)
    guard=None;pairs=[];groups=[]
    if ring:
        source=docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]
        for member in source['notes']:member.pop('hp',None)
        source['letRing']=True
        lower=extract_documents(docs);top=connected.strip_lower(connected.analyze(lower))
        data=execution._snapshot(execution.encoded(lower));refs=execution.ordered(data['nodes'])
        guard=locks.upgrade_clock_choices(locks.upgrade_successor_choices(
            locks.capture(lower,data['records'],refs),lower,data['records'],refs),lower,data['records'],refs)
        pairs=contact.required_pairs(guard,lower,data['records'],refs,selected_next_refs=[ref(0,bar=2)])
        groups=contact.required_groups(guard,lower,data['records'],refs,selected_next_refs=[ref(0,bar=2)])
    proposal,records,_=planned(top)
    definition=carry.plan(top,proposal,records,required_pairs=pairs,coherent_group_refs=groups)
    out,report=entry.project(top,[proposal],execution_records=records,carry_plan=definition,
        required_pairs=pairs,coherent_group_refs=groups)
    return lower,connected.realize(out),report,guard


def mapped_records(records,mapping):
    result=deepcopy(records)
    for row in result:
        for key in ('member_refs','tied_member_refs'):row[key]=[mapping.get(r,r)for r in row[key]]
        for key in ('origin_ref','destination_ref','candidate_destination_ref'):
            row[key]=mapping.get(row[key],row[key])
        row['id']=execution.identity(row)
    return result


class DerivedSustainProjectionTests(unittest.TestCase):
    def test_only_generated_tails_reduce_and_actual_input_remains_unchanged(self):
        for existing_tie in(False,True):
            original,actual,report,_=run_fixture(existing_tie=existing_tie)
            before=deepcopy((actual,report));raw=execution._snapshot(execution.encoded(actual))
            reduced=sustain.validate_projection(actual,report['carries'])
            self.assertEqual((actual,report),before)
            tail=report['carries'][0];previous=tail['predecessor_ref'];generated=tail['occurrence_ref']
            self.assertEqual(set(reduced['nodes']),set(raw['nodes'])-{generated})
            self.assertEqual(reduced['nodes'][previous]['duration'],raw['nodes'][previous]['duration']+F(tail['duration_q']))
            for r in set(reduced['nodes'])-{previous}:self.assertEqual(reduced['nodes'][r],raw['nodes'][r])
            if existing_tie:self.assertTrue(reduced['nodes'][ref(3)]['tie_destination'])
            maps={old:new[0]for old,new in report['maps']['events'].items()}
            self.assertEqual(reduced['records'],mapped_records(execution._snapshot(execution.encoded(original))['records'],maps))

    def test_saved_v3_guard_retains_same_commitments_after_coherent_group_carry(self):
        for chord in(False,True):
            original,actual,report,guard=run_fixture(ring=True,chord=chord)
            original_data=execution._snapshot(execution.encoded(original));raw=execution._snapshot(execution.encoded(actual))
            forward={old:new[0]for old,new in report['maps']['events'].items()}
            backward={new:old for old,new in forward.items()if new in raw['nodes']}
            records=mapped_records(original_data['records'],forward)
            refs=execution.ordered(raw['nodes']);before=deepcopy(guard)
            with self.assertRaises(ValueError):locks.validate(guard,actual,records,refs,identity_map=backward)
            locks.validate(json.loads(json.dumps(guard)),actual,records,refs,identity_map=backward,
                derived_sustains=json.loads(json.dumps(report['carries'])))
            self.assertEqual(guard,before)

    def test_pitch_tie_attack_metadata_clock_and_fake_original_node_refuse(self):
        _,actual,report,_=run_fixture()
        for action in('pitch','tie','accent','velocity','letRing','clock','original_identity'):
            changed_docs=project_documents(actual);rows=deepcopy(report['carries'])
            carrier=changed_docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]
            if action=='pitch':carrier['notes'][0]['fret']+=1
            elif action=='tie':carrier['notes'][0]['tie']=False
            elif action=='accent':carrier['notes'][0]['accent']=True
            elif action=='velocity':carrier['velocity']='ff'
            elif action=='letRing':carrier['letRing']=True
            elif action=='clock':rows[0]['duration_q']='1/2'
            else:rows[0]['occurrence_ref']=rows[0]['predecessor_ref']
            changed=extract_documents(changed_docs);before=deepcopy((changed,rows))
            with self.subTest(action=action),self.assertRaises(ValueError):sustain.validate_projection(changed,rows)
            self.assertEqual((changed,rows),before)

    def test_new_other_voice_contact_is_never_erased_by_reduction(self):
        _,actual,report,_=run_fixture()
        docs=project_documents(actual)
        docs['track-0.json']['measures'][1]['voices'].append(dict(beats=[
            beat(dict(rest=True),duration=(1,8),typ=8,rest=True),
            beat(note(fret=12),duration=(7,8),typ=2,dots=2)]))
        with self.assertRaisesRegex(ValueError,'Another current contact'):
            sustain.validate_projection(extract_documents(docs),report['carries'])

    def test_missing_or_duplicate_group_authority_refuses(self):
        _,actual,report,_=run_fixture(ring=True,chord=True)
        for rows in(report['carries'][:1],report['carries']+[report['carries'][0]]):
            with self.assertRaises(ValueError):sustain.validate_projection(actual,rows)

    def test_saved_later_owner_pitch_change_must_propagate_to_its_tail(self):
        _,actual,report,_=run_fixture(ring=True)
        docs=project_documents(actual)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['fret']+=1
        with self.assertRaisesRegex(ValueError,'equal-pitch'):sustain.validate_projection(extract_documents(docs),report['carries'])
        docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0]['fret']+=1
        sustain.validate_projection(extract_documents(docs),json.loads(json.dumps(report['carries'])))

    def test_no_source_access_and_empty_projection_preserves_original_snapshot(self):
        _,actual,report,_=run_fixture()
        expected=execution._snapshot(execution.encoded(actual))
        self.assertEqual(sustain.validate_projection(actual,[]),expected)
        execution._snapshot.cache_clear()
        with patch('builtins.open',side_effect=AssertionError('No source access')),\
             patch.object(Path,'read_text',side_effect=AssertionError('No source access')),\
             patch.object(Path,'read_bytes',side_effect=AssertionError('No source access')):
            sustain.validate_projection(actual,report['carries'])


if __name__=='__main__':unittest.main()
