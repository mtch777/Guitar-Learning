"""Joint chord choices preserve held pitches and physical contacts across uses."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import connected_tier2 as connected
import material_degree_paths as degrees
import support_material_uses as uses
import written_tie_pitch_ownership as ties
from source_fact_tier1 import extract_documents,project_documents
from test_written_tie_pitch_ownership import documents,beat,note

COLLECTION=dict(id='authored-C-major',tonic_pc=0,intervals=[0,2,4,5,7,9,11])
USE='material-use:0'
HEAD='event:77:0:1:0:0:0'
UPPER='event:77:0:1:0:0:1'


def saved(value):return json.loads(json.dumps(value))


def fixture(*,own_tails=True):
    # Two independent notes, each sustained through eight written occurrences.
    # A separate later chain must remain completely unchanged.
    bars=[[beat(note(0,5,tie=i>0),note(1,5,tie=i>0))for i in range(4)],
          [beat(note(0,5,tie=True),note(1,5,tie=True))for _ in range(4)],
          [beat(note(3,0)),beat(note(3,0,tie=True)),beat(note(3,3)),beat(note(3,0))]]
    docs=documents(bars);docs['track-0.json'].update(tuning=[40,47,52,59],frets=5)
    lower=extract_documents(docs);top=connected.strip_lower(connected.analyze(lower))
    top['musical_relationships']=ties.lift(top['musical_relationships'],tier1=lower)
    specs=[dict(parts=[0],first_bar=b,last_bar=b)for b in ((1,2,3)if own_tails else(1,))]
    model=uses.from_tier2(top,specs)
    model=uses.lift_degree_paths(model,USE,path_refs=[0],interpretations={0:[COLLECTION]},
                                evidence_ref='authored-contact-counterexample')
    group=degrees.selected_refs(model['materials'][0])[0]
    return docs,lower,model,group


def expected(docs,*,lower_fret=0,upper_fret=1,lower_string=1,upper_string=2):
    out=deepcopy(docs)
    for measure in out['track-0.json']['measures'][:2]:
        for row in measure['voices'][0]['beats']:
            row['notes'][0].update(string=lower_string,fret=lower_fret)
            row['notes'][1].update(string=upper_string,fret=upper_fret)
    return out


class MaterialJointContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.docs,cls.lower,cls.model,cls.group=fixture()

    def test_complete_chord_head_change_recontacts_every_held_member_across_uses(self):
        before=deepcopy(self.model)
        changed=uses.degree_path_candidate(self.model,USE,displacements={self.group:1},octaves={},refinger=True)
        self.assertEqual(project_documents(uses.reconstruct(saved(changed),{'variation':0})),expected(self.docs))
        self.assertEqual(changed['materials'],self.model['materials'])
        self.assertEqual(changed['lower_tier'],self.model['lower_tier'])
        self.assertEqual(self.model,before)
        self.assertEqual(len(changed['uses'][0]['contact_strings']),8)
        self.assertEqual(len(changed['uses'][1]['contact_strings']),8)
        self.assertEqual(changed['materials'][1]['pitch_paths'],[])
        self.assertEqual(changed['uses'][2],self.model['uses'][2])

    def test_common_and_member_choices_commit_together_without_independent_tail_pitches(self):
        changed=uses.degree_choices_candidate(self.model,{USE:dict(displacements={self.group:1},
            octaves={},member_steps={UPPER:1})},contact_strings={USE:{HEAD:1,UPPER:2}})
        self.assertEqual(project_documents(uses.reconstruct(saved(changed),{'variation':0})),
                         expected(self.docs,upper_fret=3))
        self.assertEqual(changed['uses'][0]['degree_member_steps'],{UPPER:1})
        self.assertNotIn('degree_member_steps',changed['uses'][1])
        self.assertEqual(changed['lower_tier']['source_origin'],self.model['lower_tier']['source_origin'])

    def test_saved_second_head_edit_updates_existing_contacts_and_preserves_unrelated_chain(self):
        first=uses.degree_choices_candidate(self.model,{USE:dict(displacements={self.group:1},octaves={})},
                                            contact_strings={USE:{HEAD:1,UPPER:2}})
        second=uses.degree_choices_candidate(saved(first),{USE:dict(displacements={},octaves={})},
                                             contact_strings={USE:{HEAD:0,UPPER:1}})
        self.assertEqual(uses.reconstruct(saved(second),{'variation':0}),self.lower)
        self.assertEqual(second['materials'],self.model['materials'])
        self.assertEqual(second['uses'][2],self.model['uses'][2])
        self.assertEqual(second['lower_tier'],self.model['lower_tier'])

    def test_subdivided_head_children_inherit_the_same_parent_contact_before_held_chain(self):
        split,_=uses.subdivision_candidate(self.model,{USE:[self.group]},percent=100)
        changed=uses.degree_choices_candidate(split,{USE:dict(displacements={self.group:1},octaves={})},
                                              contact_strings={USE:{HEAD:1,UPPER:2}})
        oracle=expected(self.docs)
        voice=oracle['track-0.json']['measures'][0]['voices'][0]
        child=deepcopy(voice['beats'][0]);child['duration']=[1,8]
        voice['beats']=[deepcopy(child),deepcopy(child)]+voice['beats'][1:]
        self.assertEqual(project_documents(uses.reconstruct(saved(changed),{'variation':0})),oracle)
        self.assertEqual(changed['uses'][0]['subdivision_factors'],split['uses'][0]['subdivision_factors'])
        self.assertEqual(changed['materials'],split['materials'])

    def test_tail_only_conflicting_or_unowned_contact_requests_refuse_atomically(self):
        tail='event:77:0:2:0:0:0'
        cases=[{'material-use:1':{tail:1}},
               {USE:{HEAD:1},'material-use:1':{tail:0}},
               {USE:{'missing':1}}, {USE:{HEAD:True}}, {'missing-use':{HEAD:1}}]
        for contacts in cases:
            with self.subTest(contacts=contacts):
                before=deepcopy(self.model)
                with self.assertRaises(ValueError):uses.degree_choices_candidate(self.model,{},contact_strings=contacts)
                self.assertEqual(self.model,before)
        _,_,partial,group=fixture(own_tails=False);before=deepcopy(partial)
        with self.assertRaisesRegex(ValueError,'lacks an existing material physical owner'):
            uses.degree_choices_candidate(partial,{USE:dict(displacements={group:1},octaves={})},
                                          contact_strings={USE:{HEAD:1,UPPER:2}})
        self.assertEqual(partial,before)

    def test_saved_tail_contact_tampering_cannot_weaken_the_tie_relationship(self):
        changed=uses.degree_path_candidate(self.model,USE,displacements={self.group:1},octaves={},refinger=True)
        bad=saved(changed);bad['uses'][1]['contact_strings']['event:77:0:2:0:0:0']=0
        before=deepcopy(bad)
        with self.assertRaisesRegex(ValueError,'WRITTEN_TIE_CONTACT_CONFLICT'):
            uses.reconstruct(bad,{'variation':0})
        self.assertEqual(bad,before)

    def test_legacy_contact_map_is_moved_not_layered_and_duplicate_authority_refuses(self):
        legacy=deepcopy(self.model);legacy['uses'][0]['degree_strings']={HEAD:0,UPPER:1}
        self.assertEqual(uses.reconstruct(legacy,{'variation':0}),self.lower)
        changed=uses.degree_choices_candidate(legacy,{USE:dict(displacements={self.group:1},octaves={})},
                                              contact_strings={USE:{HEAD:1,UPPER:2}})
        self.assertEqual(changed['uses'][0]['degree_strings'],{})
        self.assertEqual(project_documents(uses.reconstruct(saved(changed),{'variation':0})),expected(self.docs))
        bad=deepcopy(changed);bad['uses'][0]['degree_strings']={HEAD:1}
        with self.assertRaisesRegex(ValueError,'Two active physical contact authorities'):
            uses.reconstruct(bad,{'variation':0})

    def test_complete_coattack_collision_or_out_of_bounds_contacts_refuse(self):
        for contacts in ({HEAD:1,UPPER:1},{HEAD:3,UPPER:2},{HEAD:99}):
            with self.subTest(contacts=contacts):
                before=deepcopy(self.model)
                with self.assertRaises(ValueError):
                    uses.degree_choices_candidate(self.model,{USE:dict(displacements={self.group:1},octaves={})},
                                                  contact_strings={USE:contacts})
                self.assertEqual(self.model,before)

    def test_empty_transaction_preserves_current_state_without_migrating_unused_contacts(self):
        changed=uses.degree_path_candidate(self.model,USE,displacements={self.group:1},octaves={},refinger=True)
        self.assertEqual(uses.degree_choices_candidate(saved(changed),{}),changed)

    def test_multiple_degree_uses_commit_together_and_one_invalid_request_refuses_all(self):
        model=uses.lift_degree_paths(self.model,'material-use:2',path_refs=[0],
            interpretations={0:[COLLECTION]},evidence_ref='authored-second-chain')
        group=degrees.selected_refs(model['materials'][2])[0]
        requests={USE:dict(displacements={self.group:1},octaves={}),
                  'material-use:2':dict(displacements={group:1},octaves={})}
        changed=uses.degree_choices_candidate(model,requests,contact_strings={USE:{HEAD:1,UPPER:2}})
        oracle=expected(self.docs)
        for index in (0,1):oracle['track-0.json']['measures'][2]['voices'][0]['beats'][index]['notes'][0]['fret']=1
        self.assertEqual(project_documents(uses.reconstruct(saved(changed),{'variation':0})),oracle)
        before=deepcopy(model);requests['material-use:2']['octaves']={group:10}
        with self.assertRaises(ValueError):
            uses.degree_choices_candidate(model,requests,contact_strings={USE:{HEAD:1,UPPER:2}})
        self.assertEqual(model,before)

    def test_ordinary_material_contact_edit_preserves_unresolved_execution_locks(self):
        from test_material_execution_locks import source
        docs=source();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret']=9
        lower=extract_documents(docs);top=connected.strip_lower(connected.analyze(lower))
        model=uses.from_tier2(top,[dict(parts=[0],first_bar=1,last_bar=1)])
        old=deepcopy(model);origin='event:86:0:1:0:0:0';unrelated='event:86:0:1:0:3:0'
        # Both alternative frets are valid; the gesture context is the blocker.
        with self.assertRaisesRegex(ValueError,'Protected next contact changed lane or kind'):
            uses.degree_choices_candidate(model,{},contact_strings={USE:{origin:4}})
        self.assertEqual(model,old)
        changed=uses.degree_choices_candidate(model,{},contact_strings={USE:{unrelated:4}})
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0].update(string=4,fret=2)
        self.assertEqual(project_documents(uses.reconstruct(saved(changed),{'variation':0})),docs)
        self.assertEqual(changed['materials'],model['materials'])

    def test_saved_joint_chord_change_reconstructs_in_actual_denied_worker(self):
        from qa_isolation_harness import execute
        from run_support_use_qa import bundle
        changed=uses.degree_choices_candidate(self.model,{USE:dict(displacements={self.group:1},
            octaves={},member_steps={UPPER:1})},contact_strings={USE:{HEAD:1,UPPER:2}})
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory()as folder:
            receipt=execute(code,saved(changed),{'variation':0},extract_documents(expected(self.docs,upper_fret=3)),
                            Path(folder)/'proof',timeout=60,purpose='exact_zero')
        self.assertEqual(receipt['status'],'PASS',receipt)
        self.assertFalse(receipt['parent_expected_staged'])


if __name__=='__main__':unittest.main()
