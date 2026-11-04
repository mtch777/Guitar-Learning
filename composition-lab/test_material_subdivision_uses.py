"""Reattack controls preserve current pitch parents and existing owners."""
from copy import deepcopy
import json
import unittest
from pathlib import Path
import tempfile

import support_material_uses as uses
import test_material_degree_uses as degree_fixture
import test_material_expression_composition as fixture
from source_fact_tier1 import project_documents


def saved(value):return json.loads(json.dumps(value))


def expected_split(docs, selections, factor=2):
    result=deepcopy(docs)
    for part, ordinals in selections.items():
        beats=result[f'track-{part}.json']['measures'][0]['voices'][0]['beats']
        changed=[]
        for i,beat in enumerate(beats):
            count=factor if i in ordinals else 1
            for child in range(count):
                row=deepcopy(beat)
                if count>1:
                    row['type']*=count;row['duration'][1]*=count
                    if 'beamStart'in row:row['beamStart']=row['beamStart'] and child==0
                    if 'beamStop'in row:row['beamStop']=row['beamStop'] and child==count-1
                changed.append(row)
        result[f'track-{part}.json']['measures'][0]['voices'][0]['beats']=changed
    return result


class SubdivisionUseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs,cls.lower,cls.t2=fixture.build()
        cls.model=uses.from_tier2(cls.t2,[fixture.SPEC])
        cls.groups=cls.model['materials'][0]['lower_tier']['coattacks']
        cls.first=next(g['id'] for g in cls.groups if g['part_id']==2)

    def test_split_first_moves_addresses_not_identity_and_keeps_complete_chords(self):
        before=deepcopy(self.model)
        changed,report=uses.subdivision_candidate(self.model,{fixture.USE:[self.first]})
        t2,t1,ledger=uses.realize_pair(saved(changed))
        self.assertEqual(project_documents(t1),expected_split(self.docs,{2:[0]}))
        self.assertEqual(self.model,before)
        self.assertEqual(changed['materials'],self.model['materials'])
        self.assertEqual(changed['lower_tier'],self.model['lower_tier'])
        self.assertEqual(report['added_attacks'],1)
        old=uses.realize_pair(self.model)[2]
        old_second=next(r for r in old if r['current_address'].endswith(':2:1:0:1:0'))
        new_second=next(r for r in ledger if r['identity']==old_second['identity'])
        self.assertTrue(new_second['current_address'].endswith(':2:1:0:2:0'))
        self.assertEqual(t2['source_origin'],self.t2['source_origin'])
        self.assertEqual(t2['musical_relationships']['relationships'],self.t2['musical_relationships']['relationships'])

    def test_zero_keeps_current_split_then_second_split_halves_current_children(self):
        first,_=uses.subdivision_candidate(self.model,{fixture.USE:[self.first]})
        zero,report=uses.subdivision_candidate(saved(first),{fixture.USE:[self.first]},percent=0)
        self.assertEqual(first,zero);self.assertFalse(report['changed'])
        second,report=uses.subdivision_candidate(saved(first),{fixture.USE:[self.first]})
        self.assertEqual(report['current_attacks'],2);self.assertEqual(report['changed_current_attacks'],2)
        self.assertEqual(project_documents(uses.reconstruct(second,{'variation':0})),expected_split(self.docs,{2:[0]},4))
        first_ids={r['identity'] for r in uses.realize_pair(first)[2]}
        second_ids={r['identity'] for r in uses.realize_pair(second)[2]}
        self.assertTrue(first_ids<=second_ids)

    def test_split_then_degree_edit_inherits_current_parent_without_path_advance(self):
        docs,_,_,_,model=degree_fixture.build()
        groups=model['materials'][0]['lower_tier']['coattacks']
        ref=next(g['id'] for g in groups if g['part_id']==2)
        split,_=uses.subdivision_candidate(model,{fixture.USE:[ref]})
        changed=uses.degree_path_candidate(saved(split),fixture.USE,displacements={ref:1},octaves={})
        baseline=uses.degree_path_candidate(model,fixture.USE,displacements={ref:1},octaves={})
        expected=expected_split(project_documents(uses.reconstruct(baseline,{'variation':0})),{2:[0]})
        self.assertEqual(project_documents(uses.reconstruct(changed,{'variation':0})),expected)
        alternative,_=uses.subdivision_candidate(baseline,{fixture.USE:[ref]})
        self.assertEqual(changed,alternative)

    def test_original_dynamic_evidence_is_immutable_and_later_choice_reaches_children(self):
        model=deepcopy(self.model)
        changed,_=uses.subdivision_candidate(model,{fixture.USE:[self.first]})
        before=deepcopy(model['lower_tier']['owned_parameters']['observed_dynamics'])
        import observed_dynamics as dynamics
        changed['lower_tier']['owned_parameters']['observed_dynamics']=dynamics.choose(
            changed['lower_tier']['owned_parameters']['observed_dynamics'],fixture.DYNAMIC,'pp')
        t2,t1,_=uses.realize_pair(saved(changed))
        current=t2['owned_parameters']['observed_dynamics']
        self.assertEqual(dynamics.evidence(current),dynamics.evidence(before))
        actual=project_documents(t1)['track-2.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual([b['velocity'] for b in actual[:2]],['pp','pp'])

    def test_half_scope_counts_current_attacks_and_refuses_indivisible_target(self):
        refs=[g['id'] for g in self.groups]
        changed,report=uses.subdivision_candidate(self.model,{fixture.USE:refs},percent=50)
        self.assertEqual(report['changed_current_attacks'],4)
        self.assertEqual(len(uses.realize_pair(changed)[2])-len(uses.realize_pair(self.model)[2]),8)
        doubled,_=uses.subdivision_candidate(self.model,{fixture.USE:[self.first]})
        before=deepcopy(doubled)
        with self.assertRaisesRegex(ValueError,'indivisible'):
            uses.subdivision_candidate(doubled,{fixture.USE:[self.first]},percent=50)
        self.assertEqual(doubled,before)

    def test_plain_owner_beams_text_and_unsplit_execution_projection(self):
        import connected_tier2 as connected
        from source_fact_tier1 import extract_documents
        docs=fixture.authored_documents()
        beat=docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]
        beat.update(beamStart=True,beamStop=True,text=dict(text='one indication',width=1))
        t2=connected.strip_lower(connected.analyze(extract_documents(docs)))
        model=uses.from_tier2(t2,[fixture.SPEC]);before=deepcopy(model)
        ref=next(g['id'] for g in model['materials'][0]['lower_tier']['coattacks'] if g['part_id']==2)
        changed,_=uses.subdivision_candidate(model,{fixture.USE:[ref]})
        actual=project_documents(uses.reconstruct(changed,{'variation':0}))
        expected=expected_split(docs,{2:[0]});del expected['track-2.json']['measures'][0]['voices'][0]['beats'][1]['text']
        self.assertEqual(actual,expected);self.assertEqual(model,before)

    def test_existing_foreign_backing_dependency_still_propagates(self):
        import backing_pitch_ownership as backing
        import melodic_movement_ownership as movement
        import test_musical_cell_development as cell
        changed,_=uses.subdivision_candidate(self.model,{fixture.USE:[self.first]})
        changed=saved(changed);links=deepcopy(changed['lower_tier']['musical_relationships']['relationships'])
        index=backing._index(movement._body(changed['lower_tier']['musical_relationships']))
        index[cell.FOREIGN_BACKING][0]['bass_register_anchor']='41'
        actual=project_documents(uses.reconstruct(changed,{'variation':0}))
        expected=expected_split(self.docs,{2:[0]})
        for part,pitch in ((2,66),(3,41)):
            track=expected[f'track-{part}.json'];note=track['measures'][8]['voices'][0]['beats'][0]['notes'][0]
            note['fret']=pitch-track['tuning'][note['string']]
        self.assertEqual(actual,expected)
        self.assertEqual(changed['lower_tier']['musical_relationships']['relationships'],links)

    def test_rhythm_and_subdivision_commute_with_saved_current_owners(self):
        import material_rhythm_control as rhythm
        model=rhythm.lift(self.model,fixture.USE)
        a,_=uses.subdivision_candidate(rhythm.candidate(model,fixture.USE,'1/2'),{fixture.USE:[self.first]})
        b,_=uses.subdivision_candidate(model,{fixture.USE:[self.first]})
        b=rhythm.candidate(saved(b),fixture.USE,'1/2')
        self.assertEqual(a,b)
        expected=expected_split(fixture.expected_later(self.docs),{2:[0]})
        self.assertEqual(project_documents(uses.reconstruct(b,{'variation':0})),expected)

    def test_actual_source_denied_saved_inverse(self):
        from qa_isolation_harness import execute
        from run_support_use_qa import bundle
        from source_fact_tier1 import extract_documents
        changed,_=uses.subdivision_candidate(self.model,{fixture.USE:[self.first]})
        code,hashes=bundle(Path(__file__).resolve().parent)
        self.assertIn('material_subdivision_projection',hashes)
        with tempfile.TemporaryDirectory() as directory:
            receipt=execute(code,saved(changed),{'variation':0},extract_documents(expected_split(self.docs,{2:[0]})),
                            Path(directory)/'proof',timeout=60,purpose='exact_zero')
            self.assertEqual(receipt['status'],'PASS',receipt)
            self.assertFalse(receipt['parent_expected_staged'])

    def test_shifted_unsplit_backing_reference_keeps_its_live_meaning(self):
        import connected_tier2 as connected
        import backing_pitch_ownership as backing
        import musical_support_material as material
        import melodic_movement_ownership as movement
        from material_subdivision import plan
        from material_subdivision_projection import project
        from source_fact_tier1 import extract_documents
        docs=deepcopy(self.docs)
        for part in (2,3):
            for beat in docs[f'track-{part}.json']['measures'][0]['voices'][0]['beats']:
                beat['notes']=beat['notes'][:1]
        t1=extract_documents(docs)
        plain=connected.strip_lower(connected.analyze(t1))
        owner=uses.from_tier2(plain,[fixture.SPEC])
        piece,records,_=uses.place(owner['materials'][0],owner['slots'][0],owner['uses'][0],parent=owner['lower_tier'])
        group=next(g for g in piece['coattacks'] if g['part_id']==2)
        proposal=plan(piece,{group['id']:2},observed_execution=records)
        # The second, UNSPLIT chord depends on the other guitar's second chord.
        # Inserting before it moves its export ordinal but must keep that edge.
        target=next(g['members'][0]['id'] for g in piece['coattacks'] if g['part_id']==2 and g['members'][0]['beat']==1)
        reference=next(g['members'][0]['id'] for g in piece['coattacks'] if g['part_id']==3 and g['members'][0]['beat']==1)
        bound=connected.strip_lower(connected.analyze(t1,backing_bindings=[dict(occurrence_ref=target,backing_ref=reference)]))
        changed=project(bound,[proposal])
        link=changed['musical_relationships']['relationships'][0]
        self.assertEqual(link['occurrence_ref'],target.rsplit(':',2)[0]+':2:0')
        self.assertEqual(link['backing_ref'],reference)
        self.assertEqual(project_documents(connected.realize(changed)),expected_split(docs,{2:[0]}))
        changed=saved(changed)
        index=backing._index(movement._body(changed['musical_relationships']))
        original_pitch=index[reference][0]['bass_register_anchor']
        index[reference][0]['bass_register_anchor']=str(int(original_pitch)+1)
        actual=project_documents(connected.realize(changed))
        before=expected_split(docs,{2:[0]})
        for part,beat in ((2,2),(3,1)):
            for note in before[f'track-{part}.json']['measures'][0]['voices'][0]['beats'][beat]['notes']:
                note['fret']+=1
        self.assertEqual(actual,before)

    def test_active_tie_target_refuses_without_changing_saved_input(self):
        import connected_tier2 as connected
        from source_fact_tier1 import extract_documents
        docs=fixture.authored_documents(tied=True)
        t2=connected.strip_lower(connected.analyze(extract_documents(docs)))
        model=uses.from_tier2(t2,[dict(parts=[2,3],first_bar=1,last_bar=2)])
        group=next(g for g in model['materials'][0]['lower_tier']['coattacks']
                   if g['part_id']==2 and g['bar']==2 and g['members'][0]['beat']==0)
        frozen=deepcopy(model)
        zero,_=uses.subdivision_candidate(model,{fixture.USE:[group['id']]},percent=0)
        self.assertEqual(zero,model)
        with self.assertRaisesRegex(ValueError,'SUBDIVISION_BLOCKED'):
            uses.subdivision_candidate(model,{fixture.USE:[group['id']]})
        self.assertEqual(model,frozen)

    def test_outgoing_tie_belongs_to_last_child_with_same_final_hold(self):
        import connected_tier2 as connected
        import backing_written_tie_constraints as ties
        from source_fact_tier1 import extract_documents
        docs=fixture.authored_documents(tied=True)
        t2=connected.strip_lower(connected.analyze(extract_documents(docs)))
        model=uses.from_tier2(t2,[dict(parts=[2,3],first_bar=1,last_bar=2)])
        group=next(g for g in model['materials'][0]['lower_tier']['coattacks']
                   if g['part_id']==2 and g['bar']==1 and g['members'][0]['beat']==3)
        changed,_=uses.subdivision_candidate(model,{fixture.USE:[group['id']]})
        current,t1,ledger=uses.realize_pair(saved(changed))
        expected=expected_split(docs,{2:[3]})
        self.assertEqual(project_documents(t1),expected)
        originals=[m['id'] for m in group['members']]
        children=[row['current_address'] for row in ledger if row['source_occurrence']in originals]
        edges=ties.from_tier1(current['musical_relationships'],t1,children)['relations']
        self.assertEqual(len(edges),2)
        self.assertTrue(all(ties.address(e['origin_ref'])[4]==4 for e in edges))
        self.assertTrue(all(ties.address(e['destination_ref'])[2:5]==(2,0,0) for e in edges))


if __name__=='__main__':unittest.main()
