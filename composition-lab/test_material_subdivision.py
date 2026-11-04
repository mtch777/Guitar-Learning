"""Authored subdivision equations and lineage; no production/audio QA claim."""
from copy import deepcopy
from fractions import Fraction as F
import json
import unittest

import material_subdivision as subdivision
import musical_support_material as material
from source_observation_evidence import digest
from test_material_expression_composition import authored_documents
from test_material_rhythm_displacement import build


def fragment(docs=None):
    documents, lower, _, definition = build(authored_documents() if docs is None else docs)
    return material.expand(definition), definition['observed_execution']


class SubdivisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment, cls.execution = fragment()
        cls.first = cls.fragment['coattacks'][0]
        cls.ref = cls.first['id']

    def test_rational_equation_is_bidirectional_and_exact(self):
        result = subdivision.relation(start_q='7/3', span_q='5/7', factor=4)
        self.assertEqual(result['children'][1], dict(onset_q='211/84', duration_q='5/28'))
        self.assertEqual(subdivision.relation(children=result['children'], factor=4), result)
        self.assertEqual(sum(F(c['duration_q']) for c in result['children']), F(5,7))
        for bad in (0, 3, True, 1.0):
            with self.subTest(factor=bad), self.assertRaises(ValueError):
                subdivision.relation(start_q='0', span_q='1', factor=bad)
        broken = deepcopy(result['children']); broken[1]['onset_q'] = '3'
        with self.assertRaises(ValueError):subdivision.relation(children=broken, factor=4)

    def test_factor_one_is_identity_including_saved_current_values(self):
        frozen = digest(self.fragment)
        result = subdivision.plan(self.fragment, {self.ref:1}, observed_execution=self.execution)
        mapping = subdivision.plan_maps([json.loads(json.dumps(result))])
        self.assertTrue(all(before == after[0] and len(after)==1 for before,after in mapping['beats'].items()))
        self.assertTrue(all(before == after[0] and len(after)==1 for before,after in mapping['events'].items()))
        self.assertEqual(result['changed_beat_units'], 0)
        self.assertEqual(digest(self.fragment), frozen)

    def test_complete_chord_children_use_same_current_parent(self):
        before = digest(self.fragment)
        result = subdivision.plan(self.fragment, {self.ref:2}, observed_execution=self.execution)
        children = [r for r in result['coattack_map'] if r['parent_coattack_ref']==self.ref]
        self.assertEqual(len(children), 2)
        self.assertTrue(all(r['member_parent_refs']==[m['id'] for m in self.first['members']] for r in children))
        self.assertTrue(all(r['inherit_pitch_contact_from']==self.ref for r in children))
        for member in self.first['members']:
            rows = [r for r in result['event_map'] if r['parent_occurrence']==member['id']]
            self.assertEqual([r['relative_parent_offset'] for r in rows], ['0','1/2'])
            self.assertTrue(all(r['inherit_pitch_contact_from']==member['id'] for r in rows))
            self.assertEqual(rows[0]['identity'], member['id'])
        self.assertNotIn('pitches', json.dumps(result))
        self.assertEqual(digest(self.fragment), before)

    def test_second_coattack_shifts_address_but_does_not_supply_child_pitch(self):
        result = subdivision.plan(self.fragment, {self.ref:2})
        mapping = subdivision.plan_maps([result])
        first_member = self.first['members'][0]['id']
        later = next(g for g in self.fragment['coattacks'] if g['part_id']==2 and g['members'][0]['beat']==1)
        later_member = later['members'][0]['id']
        self.assertEqual(mapping['events'][first_member], [first_member, first_member.rsplit(':',2)[0]+':1:0'])
        self.assertEqual(mapping['events'][later_member], [later_member.rsplit(':',2)[0]+':2:0'])
        self.assertTrue(all(r['inherit_pitch_contact_from']==first_member for r in result['event_map'] if r['parent_occurrence']==first_member))
        self.assertEqual(mapping['spans'][first_member], [dict(onset_q='0',duration_q='1/2'),dict(onset_q='1/2',duration_q='1/2')])
        self.assertEqual(mapping['spans'][later_member], [dict(onset_q='1',duration_q='1')])

    def test_later_subdivision_retains_existing_child_logical_identity(self):
        twice = subdivision.plan(self.fragment, {self.ref:2})
        four = subdivision.plan(self.fragment, {self.ref:4})
        old = {r['identity']:r for r in twice['event_map'] if r['parent_coattack_ref']==self.ref}
        new = {r['identity']:r for r in four['event_map'] if r['parent_coattack_ref']==self.ref}
        self.assertTrue(old.keys() < new.keys())
        for identity,row in old.items():
            self.assertEqual(new[identity]['relative_parent_offset'], row['relative_parent_offset'])
            self.assertEqual(new[identity]['inherit_pitch_contact_from'], row['inherit_pitch_contact_from'])

    def test_dynamics_accents_mute_inherit_and_beam_edges_stay_outer(self):
        docs = authored_documents()
        beat = docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]
        beat.update(beamStart=True,beamStop=True)
        beat['notes'][0]['accentuated'] = 1
        source, execution = fragment(docs)
        first = source['coattacks'][0]
        result = subdivision.plan(source,{first['id']:2},observed_execution=execution)
        row = next(r for r in result['beat_map'] if r['parent_coattack_ref']==first['id'])
        for child in row['children']:
            self.assertIn('velocity',child['copy_beat_fields']);self.assertIn('palmMute',child['copy_beat_fields'])
        self.assertIn('beamStart',row['children'][0]['copy_beat_fields'])
        self.assertNotIn('beamStop',row['children'][0]['copy_beat_fields'])
        self.assertNotIn('beamStart',row['children'][1]['copy_beat_fields'])
        self.assertIn('beamStop',row['children'][1]['copy_beat_fields'])
        self.assertTrue(all('accentuated' in r['inherited_note_fields'] for r in result['event_map']
                            if r['parent_occurrence']==first['members'][0]['id']))

    def test_dead_member_without_pitch_is_retained_as_same_parent(self):
        docs = authored_documents()
        docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'].append(dict(dead=True,string=2))
        source, execution = fragment(docs); first=source['coattacks'][0]
        result=subdivision.plan(source,{first['id']:2},observed_execution=execution)
        dead=first['members'][-1]['id']
        rows=[r for r in result['event_map']if r['parent_occurrence']==dead]
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r['inherit_pitch_contact_from']==dead and 'dead'in r['inherited_note_fields'] for r in rows))

    def test_rest_is_counted_and_refused_without_partial_plan(self):
        docs=authored_documents()
        docs['track-2.json']['measures'][0]['voices'][0]['beats'][1]['notes']=[dict(rest=True)]
        source,execution=fragment(docs); frozen=digest(source)
        inventory=subdivision.inventory(source,execution)
        self.assertEqual(len(inventory),8)
        rest=next(r for r in inventory if r['part_id']==2 and r['beat']==1)
        self.assertIn('REST_OR_UNBOUND_BEAT',rest['blocked_reasons'])
        with self.assertRaises(ValueError)as caught:
            subdivision.plan(source,{source['coattacks'][0]['id']:2,rest['beat_ref']:2})
        self.assertEqual(len(caught.exception.blocked_units),1)
        self.assertEqual(len(caught.exception.inventory),8)
        self.assertEqual(digest(source),frozen)
        self.assertEqual(subdivision.plan(source,{rest['beat_ref']:1})['changed_beat_units'],0)

    def test_external_execution_edge_refuses_both_endpoints_atomically(self):
        member=self.first['members'][0]['id']; other=self.fragment['coattacks'][-1]['members'][0]['id']
        original=digest(self.fragment)
        records=[dict(origin_ref=other,destination_ref=member,member_refs=[other,member])]
        with self.assertRaisesRegex(ValueError,'EXISTING_EXECUTION_DEPENDENCY'):
            subdivision.plan(self.fragment,{self.ref:2},observed_execution=records)
        self.assertEqual(digest(self.fragment),original)
        self.assertEqual(subdivision.plan(self.fragment,{self.ref:1},observed_execution=records)['changed_beat_units'],0)

    def test_active_tie_slide_and_grace_fields_refuse_without_mutation(self):
        # Inject typed declarations into the already valid fragment: the helper
        # must inspect execution independently of the caller's detector receipt.
        from technique_observation_relations import scalar_relation
        for field in ('tie','slide','graceNote'):
            with self.subTest(field=field):
                source=deepcopy(self.fragment)
                beat=f'track-2.json#/measures/0/voices/0/beats/0'
                owner=beat if field=='graceNote'else beat+'/notes/0'
                row=next(r for r in source['source_structure']if r['id']==owner)
                ref=owner+'/'+field;row['children'].append(ref)
                source['source_structure'].append(dict(id=ref,document='track-2.json',pointer=ref.split('#')[1],parent=owner,slot=field,type='boolean'))
                source['source_choices'].append(dict(fact_ref=ref,parameter=scalar_relation('boolean',source=True)))
                old=digest(source)
                with self.assertRaisesRegex(ValueError,'UNSUPPORTED_EXECUTION:'+field):subdivision.plan(source,{self.ref:2})
                self.assertEqual(digest(source),old)
                subdivision.plan(source,{self.ref:1})

    def test_unknown_requests_and_noninjective_or_overlapping_maps_refuse(self):
        with self.assertRaisesRegex(ValueError,'Unknown'):subdivision.plan(self.fragment,{'missing':2})
        unit=subdivision.inventory(self.fragment)[0]
        with self.assertRaisesRegex(ValueError,'twice'):subdivision.plan(self.fragment,{unit['beat_ref']:2,unit['coattack_ref']:2})
        result=subdivision.plan(self.fragment,{self.ref:2})
        with self.assertRaises(ValueError):subdivision.plan_maps([result,result])
        broken=deepcopy(result);broken['event_map'][1]['current_address']=broken['event_map'][0]['current_address']
        with self.assertRaisesRegex(ValueError,'Noninjective'):subdivision.plan_maps([broken])

    def test_notation_limit_is_reported_without_arbitrary_factor_cap(self):
        result=subdivision.plan(self.fragment,{self.ref:32})
        row=next(r for r in result['beat_map']if r['parent_coattack_ref']==self.ref)
        self.assertEqual(len(row['children']),32)
        self.assertTrue(all(c['notation']==dict(type=128,dots=0)for c in row['children']))
        with self.assertRaisesRegex(ValueError,'UNREPRESENTABLE_CHILD_NOTATION'):
            subdivision.plan(self.fragment,{self.ref:64})


if __name__=='__main__':unittest.main()
