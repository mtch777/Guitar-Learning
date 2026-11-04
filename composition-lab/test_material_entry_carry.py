"""Authored continuous-gesture entry; no listening or fresh-source claim."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

import backing_execution_constraints as execution
import backing_pitch_ownership as backing
import connected_tier2 as connected
import material_entry_carry as carry
import material_entry_rest as entry
import observed_dynamics
import observed_expression
import written_tie_pitch_ownership as ties
from source_fact_tier1 import extract_documents, project_documents
from test_written_tie_pitch_ownership import documents, note, ref
from test_material_slot_clock import beat

LANE = 'track-0.json#/measures/1/voices/0/beats'


def fixture(kind='hp', chord=False, existing_tie=False):
    bars = [[beat(note(fret=5+i)) for i in range(4)],
            [beat(note(fret=i)) for i in range(4)]]
    origin = bars[0][3]
    origin['notes'][0][kind] = True if kind == 'hp' else 'legato'
    origin['palmMute'] = True
    bars[0][0]['velocity'] = 'mf'; bars[1][0]['velocity'] = 'f'
    if chord:
        origin['notes'].append(note(1, 8, **{kind: True if kind == 'hp' else 'legato'}))
        bars[1][0]['notes'].append(note(1, 3))
    if existing_tie:
        bars[0][2]['notes'][0].update(fret=8, **{kind: True if kind == 'hp' else 'legato'})
        origin['notes'][0].pop(kind); origin['notes'][0]['tie'] = True
    docs = documents(bars); lower = extract_documents(docs)
    top = connected.strip_lower(connected.analyze(lower, dynamic_evidence=True,
        expression_evidence=True, note_accent_slots=True, palm_mute_slots=True))
    if existing_tie:top['musical_relationships'] = ties.lift(top['musical_relationships'], tier1=lower)
    return docs, lower, top


def planned(top, fraction='1/4'):
    fragment = entry._current_fragment(top)
    shares = entry.current_lane_shares(fragment, [LANE])[LANE]
    proposal = entry.plan(fragment, {LANE:dict(entry_share=fraction, content_shares=shares)})
    records = execution._snapshot(execution.encoded(connected.realize(top)))['records']
    continuity = carry.plan(top, proposal, records)
    return proposal, records, continuity


class EntryCarryTests(unittest.TestCase):
    def test_hopo_and_legato_keep_one_attack_and_existing_gesture_origin(self):
        for kind in ('hp', 'slide'):
            docs, lower, top = fixture(kind)
            before = deepcopy(top)
            proposal, records, continuity = planned(top)
            out, report = entry.project(top, [proposal], execution_records=records, carry_plan=continuity)
            actual = connected.realize(out); final = project_documents(actual)
            rows = final['track-0.json']['measures'][1]['voices'][0]['beats']
            self.assertEqual(rows[0], dict(duration=[1,4],type=4,notes=[dict(string=0,fret=8,tie=True)],palmMute=True))
            self.assertEqual(rows[1]['notes'], docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'])
            self.assertEqual(report['added_attacks'], 0)
            self.assertEqual(len(report['carries']), 1)
            rebuilt = execution._snapshot(execution.encoded(actual))['records']
            gesture = [r for r in rebuilt if r['kind'] == ('hopo' if kind == 'hp' else 'slide')]
            self.assertEqual([(r['origin_ref'],r['destination_ref']) for r in gesture], [(ref(3),ref(1,bar=2))])
            self.assertEqual(out['source_origin'], top['source_origin'])
            self.assertEqual(observed_dynamics.evidence(out['owned_parameters']['observed_dynamics']),
                             observed_dynamics.evidence(top['owned_parameters']['observed_dynamics']))
            self.assertEqual(observed_expression.evidence(out['owned_parameters']['observed_expression']),
                             observed_expression.evidence(top['owned_parameters']['observed_expression']))
            self.assertEqual(top, before)

    def test_saved_tail_has_no_pitch_parameter_and_later_head_change_propagates(self):
        _, _, top = fixture()
        proposal, records, continuity = planned(top)
        out, _ = entry.project(top, [proposal], execution_records=records, carry_plan=continuity)
        saved = json.loads(json.dumps(out))
        group, member = backing._index(saved['musical_relationships']['core'])[ref(0,bar=2)]
        self.assertNotIn('bass_register_anchor', group); self.assertNotIn('voicing_interval', member)
        head_group, _ = backing._index(saved['musical_relationships']['core'])[ref(3)]
        head_group['bass_register_anchor'] = '49'
        with patch('builtins.open', side_effect=AssertionError('No source files')):
            final = project_documents(connected.realize(saved))
        self.assertEqual(final['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['fret'], 9)
        self.assertEqual(final['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0]['fret'], 9)

    def test_existing_tied_chain_extends_its_last_tail_without_rebinding_origin(self):
        _, _, top = fixture(existing_tie=True)
        proposal, records, continuity = planned(top)
        out, _ = entry.project(top, [proposal], execution_records=records, carry_plan=continuity)
        actual = connected.realize(out)
        self.assertEqual(ties.attack_head(out['musical_relationships'],ref(0,bar=2)),ref(2))
        self.assertIn(top['musical_relationships']['relationships'][0],out['musical_relationships']['relationships'])
        hp = [r for r in execution._snapshot(execution.encoded(actual))['records'] if r['kind']=='hopo']
        self.assertEqual([(r['origin_ref'],r['destination_ref']) for r in hp],[(ref(2),ref(1,bar=2))])

    def test_complete_different_string_carried_chord_remains_fully_dependent(self):
        _, _, top = fixture(chord=True)
        proposal, records, continuity = planned(top)
        out, report = entry.project(top,[proposal],execution_records=records,carry_plan=continuity)
        notes = project_documents(connected.realize(out))['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes']
        self.assertEqual(notes,[dict(string=0,fret=8,tie=True),dict(string=1,fret=8,tie=True)])
        self.assertEqual(len(report['carries']),2)
        self.assertEqual(len(out['musical_relationships']['groups'][0]['member_refs']),2)

    def test_mixed_chord_carries_only_the_member_with_a_continuous_obligation(self):
        docs, _, _ = fixture(chord=True)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][1].pop('hp')
        lower = extract_documents(docs)
        top = connected.strip_lower(connected.analyze(lower, dynamic_evidence=True,
            expression_evidence=True, note_accent_slots=True, palm_mute_slots=True))
        proposal, records, continuity = planned(top)
        out, report = entry.project(top,[proposal],execution_records=records,carry_plan=continuity)
        current = project_documents(connected.realize(out))['track-0.json']['measures'][1]['voices'][0]['beats']
        self.assertEqual(current[0]['notes'],[dict(string=0,fret=8,tie=True)])
        self.assertEqual(current[1]['notes'],docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'])
        self.assertEqual(len(report['carries']),1)

    def test_zero_has_no_new_owner_or_generated_occurrence(self):
        _, lower, top = fixture()
        proposal, records, continuity = planned(top,'0')
        out, report = entry.project(top,[proposal],execution_records=records,carry_plan=continuity)
        self.assertEqual(out,top); self.assertEqual(connected.realize(out),lower)
        self.assertFalse(report['changed']); self.assertEqual(continuity['carries'],[])

    def test_missing_or_tampered_plan_is_atomic_and_never_a_gesture_bypass(self):
        _, _, top = fixture(); before=deepcopy(top)
        proposal, records, continuity = planned(top)
        with self.assertRaisesRegex(ValueError,'SEPARATES_CONTINUOUS'):
            entry.project(top,[proposal],execution_records=records)
        bad=deepcopy(continuity);bad['carries'][0]['members'][0]['predecessor_ref']=ref(2)
        with self.assertRaisesRegex(ValueError,'Carry plan differs'):
            entry.project(top,[proposal],execution_records=records,carry_plan=bad)
        self.assertEqual(top,before)

    def test_competing_voice_on_same_physical_string_refuses(self):
        docs,_,_=fixture()
        docs['track-0.json']['measures'][1]['voices'].append(dict(beats=[
            beat(dict(rest=True),duration=(1,8),typ=8,rest=True),
            beat(note(fret=12),duration=(7,8),typ=2,dots=2)]))
        lower=extract_documents(docs);top=connected.strip_lower(connected.analyze(lower))
        before=deepcopy(top)
        with self.assertRaisesRegex(ValueError,'COMPETING_STRING'):planned(top)
        self.assertEqual(top,before)

    def test_required_letring_contact_preserves_written_hold_without_claiming_its_release(self):
        docs, _, _ = fixture(chord=True)
        origin = docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]
        for member in origin['notes']:member.pop('hp')
        origin['letRing'] = True
        lower = extract_documents(docs)
        top = connected.strip_lower(connected.analyze(lower, dynamic_evidence=True,expression_evidence=True))
        proposal, records, _ = planned(top)
        pairs = [dict(previous_ref=ref(3),next_ref=ref(0,bar=2))]
        continuity = carry.plan(top,proposal,records,required_pairs=pairs)
        out, report = entry.project(top,[proposal],execution_records=records,carry_plan=continuity,required_pairs=pairs)
        current = connected.realize(out)
        beat = project_documents(current)['track-0.json']['measures'][1]['voices'][0]['beats'][0]
        self.assertEqual(beat['notes'],[dict(string=0,fret=8,tie=True)])
        self.assertNotIn('letRing',beat)
        retained = [r for r in execution._snapshot(execution.encoded(current))['records'] if r['kind']=='letRing']
        self.assertEqual(retained,records)
        self.assertEqual(retained[0]['status'],'declaration_only_unknown_end')
        self.assertEqual(report['carries'][0]['relationship_kinds'],['guarded_written_contact'])
        bad=[dict(previous_ref=ref(2),next_ref=ref(0,bar=2))]
        with self.assertRaisesRegex(ValueError,'EXISTING_LETRING'):
            carry.plan(top,proposal,records,required_pairs=bad)

    def test_hopo_and_guarded_contact_share_one_carrier_without_duplicate_owner(self):
        docs,_,_=fixture();docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]['letRing']=True
        lower=extract_documents(docs);top=connected.strip_lower(connected.analyze(lower))
        proposal,records,_=planned(top);pairs=[dict(previous_ref=ref(3),next_ref=ref(0,bar=2))]
        continuity=carry.plan(top,proposal,records,required_pairs=pairs)
        out,report=entry.project(top,[proposal],execution_records=records,carry_plan=continuity,required_pairs=pairs)
        connected.realize(out)
        self.assertEqual(len(report['carries']),1)
        self.assertEqual(len(report['carries'][0]['support_record_ids']),2)
        self.assertEqual(len(out['musical_relationships']['relationships']),1)

    def test_guarded_coending_group_keeps_companions_without_inventing_their_gesture_target(self):
        docs,_,_=fixture(chord=True)
        origin=docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]
        for member in origin['notes']:member.pop('hp')
        origin['letRing']=True
        # Only one member has a following note at this entrance. The other
        # continues because the existing protected chord ends together.
        docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'].pop()
        lower=extract_documents(docs);top=connected.strip_lower(connected.analyze(lower))
        proposal,records,_=planned(top)
        pairs=[dict(previous_ref=ref(3),next_ref=ref(0,bar=2))]
        groups=[dict(member_refs=[ref(3),ref(3,1)],next_ref=ref(0,bar=2))]
        continuity=carry.plan(top,proposal,records,required_pairs=pairs,coherent_group_refs=groups)
        out,report=entry.project(top,[proposal],execution_records=records,carry_plan=continuity,
                                required_pairs=pairs,coherent_group_refs=groups)
        actual=connected.realize(out)
        current=project_documents(actual)['track-0.json']['measures'][1]['voices'][0]['beats']
        self.assertEqual(current[0]['notes'],[dict(string=0,fret=8,tie=True),dict(string=1,fret=8,tie=True)])
        self.assertEqual(len(current[1]['notes']),1)
        self.assertEqual(report['carries'][1]['relationship_kinds'],['guarded_coending_member'])
        self.assertEqual(execution._snapshot(execution.encoded(actual))['records'],records)
        with self.assertRaisesRegex(ValueError,'COMPLETE_EXISTING_COENDING_GROUP'):
            carry.plan(top,proposal,records,required_pairs=pairs,coherent_group_refs=[dict(member_refs=[ref(3)],next_ref=ref(0,bar=2))])

    def test_guarded_companion_new_contact_refuses_the_whole_group(self):
        docs,_,_=fixture(chord=True)
        origin=docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]
        for member in origin['notes']:member.pop('hp')
        origin['letRing']=True
        docs['track-0.json']['measures'][1]['voices'].append(dict(beats=[
            beat(dict(rest=True),duration=(1,8),typ=8,rest=True),
            beat(note(1,12),duration=(7,8),typ=2,dots=2)]))
        lower=extract_documents(docs);top=connected.strip_lower(connected.analyze(lower));before=deepcopy(top)
        proposal,records,_=planned(top)
        pairs=[dict(previous_ref=ref(3),next_ref=ref(0,bar=2))]
        groups=[dict(member_refs=[ref(3),ref(3,1)],next_ref=ref(0,bar=2))]
        with self.assertRaisesRegex(ValueError,'COMPETING_STRING'):
            carry.plan(top,proposal,records,required_pairs=pairs,coherent_group_refs=groups)
        self.assertEqual(top,before)


if __name__=='__main__':unittest.main()
