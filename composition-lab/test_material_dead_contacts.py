"""String-only dead contacts preserve missing frets, pitches and live ties."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import connected_tier2 as connected
import support_material_uses as uses
from source_fact_tier1 import extract_documents, project_documents
from test_written_tie_pitch_ownership import documents, beat, note, ref

reload=lambda model:json.loads(json.dumps(model))
SCOPE=dict(parts=[0],first_bar=1,last_bar=1)
USE='material-use:0'


def build(*,mixed=False,zero_fret=False,tied=False):
    dead=dict(string=0,dead=True)
    if zero_fret:dead['fret']=0
    rows=[]
    for index in range(4):
        current=deepcopy(dead)
        if tied and index in (1,2):current['tie']=True
        members=[current]+([note(1,3)]if mixed else[])
        rows.append(beat(*members))
    docs=documents([rows]);lower=extract_documents(docs)
    t2=connected.strip_lower(connected.analyze(lower))
    if tied:
        from written_tie_pitch_ownership import lift
        t2['musical_relationships']=lift(t2['musical_relationships'],tier1=lower)
    model=uses.from_tier2(t2,[SCOPE])
    return docs,lower,model


class MaterialDeadContactTests(unittest.TestCase):
    def test_absent_and_explicit_zero_frets_remain_exact(self):
        for zero in (False,True):
            with self.subTest(zero=zero):
                docs,lower,before=build(zero_fret=zero,mixed=True)
                frozen=deepcopy(before)
                after=uses.degree_choices_candidate(before,{},contact_strings={USE:{ref(0):2}})
                expected=deepcopy(docs)
                expected['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['string']=2
                self.assertEqual(uses.reconstruct(reload(after),{'variation':0}),extract_documents(expected))
                self.assertEqual(uses.reconstruct(before,{'variation':0}),lower)
                self.assertEqual(before,frozen)
                for field in ('materials','slots','lower_tier'):self.assertEqual(after[field],before[field])
                core=uses.expand(after)['musical_relationships']
                self.assertIsNone(core['coattacks'][0]['members'][0]['voicing_interval'])

    def test_mixed_coattack_collision_and_invalid_string_refuse_atomically(self):
        _,_,before=build(mixed=True);frozen=deepcopy(before)
        for value in (1,3,-1,True):
            with self.subTest(string=value),self.assertRaises(ValueError):
                uses.degree_choices_candidate(before,{},contact_strings={USE:{ref(0):value}})
            self.assertEqual(before,frozen)

    def test_saved_successive_contact_changes_do_not_invent_pitch_or_fret(self):
        docs,_,before=build()
        first=uses.degree_choices_candidate(before,{},contact_strings={USE:{ref(0):1}})
        zero=uses.degree_choices_candidate(reload(first),{})
        self.assertEqual(first,zero)
        second=uses.degree_choices_candidate(reload(first),{},contact_strings={USE:{ref(0):2}})
        expected=deepcopy(docs)
        expected['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['string']=2
        self.assertEqual(uses.reconstruct(second,{'variation':0}),extract_documents(expected))
        self.assertEqual(second['lower_tier'],before['lower_tier'])

    def test_dead_sustain_contact_propagates_and_remains_live_after_reload(self):
        docs,_,before=build(tied=True,zero_fret=True);frozen=deepcopy(before)
        first=uses.degree_choices_candidate(before,{},contact_strings={USE:{ref(0):1}})
        expected=deepcopy(docs)
        for i in (0,1,2):expected['track-0.json']['measures'][0]['voices'][0]['beats'][i]['notes'][0]['string']=1
        self.assertEqual(uses.reconstruct(first,{'variation':0}),extract_documents(expected))
        second=uses.degree_choices_candidate(reload(first),{},contact_strings={USE:{ref(0):2}})
        for i in (0,1,2):expected['track-0.json']['measures'][0]['voices'][0]['beats'][i]['notes'][0]['string']=2
        self.assertEqual(uses.reconstruct(second,{'variation':0}),extract_documents(expected))
        self.assertEqual(second['lower_tier']['musical_relationships']['relationships'],
                         before['lower_tier']['musical_relationships']['relationships'])
        with self.assertRaisesRegex(ValueError,'attack head'):
            uses.degree_choices_candidate(before,{},contact_strings={USE:{ref(1):1}})
        self.assertEqual(before,frozen)

    def test_unresolved_dead_tie_is_not_silently_rebound(self):
        _,_,before=build(tied=True,zero_fret=False);frozen=deepcopy(before)
        with self.assertRaisesRegex(ValueError,'UNRESOLVED_AFFECTED_WRITTEN_TIE'):
            uses.degree_choices_candidate(before,{},contact_strings={USE:{ref(0):1}})
        self.assertEqual(before,frozen)

    def test_actual_denied_inverse_matches_complete_independent_score(self):
        from run_support_use_qa import bundle
        from qa_isolation_harness import execute
        docs,_,before=build(mixed=True,zero_fret=True)
        after=uses.degree_choices_candidate(before,{},contact_strings={USE:{ref(0):2}})
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['string']=2
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory()as directory:
            receipt=execute(code,reload(after),{'variation':0},extract_documents(docs),
                Path(directory)/'denied',timeout=90,purpose='exact_zero')
        self.assertEqual(receipt['status'],'PASS',receipt)
        self.assertFalse(receipt['parent_expected_staged'])

    def test_current_score_reuse_still_enforces_the_saved_hold_policy(self):
        import stable_pitch_policy as policy
        docs,lower,_=build(mixed=True)
        t2=connected.strip_lower(connected.analyze(lower))
        t2=policy.attach(t2,held_refs=[ref(0,1)])
        upper=uses.from_tier2(t2,[SCOPE])
        # A string-only dead contact does not change the other held pitch.
        moved=uses.degree_choices_candidate(upper,{},contact_strings={USE:{ref(0):2}})
        self.assertEqual(moved['lower_tier'][policy.SLOT],upper['lower_tier'][policy.SLOT])
        paths=list(range(len(upper['materials'][0]['pitch_paths'])))
        key=dict(id='authored-C-major',tonic_pc=0,intervals=[0,2,4,5,7,9,11])
        owned=uses.lift_degree_paths(moved,USE,path_refs=paths,
            interpretations={p:[key]for p in paths},evidence_ref='authored-degree-scope')
        group=owned['materials'][0]['lower_tier']['coattacks'][0]['id']
        frozen=deepcopy(owned)
        # A degree interpretation is not silently substituted for the user's
        # separate unresolved hold-context policy. The same check must refuse.
        with self.assertRaisesRegex(ValueError,'NOT_KEY_VERIFIED'):
            uses.degree_choices_candidate(owned,{USE:dict(displacements={group:1},octaves={})})
        self.assertEqual(owned,frozen)


if __name__=='__main__':unittest.main()
