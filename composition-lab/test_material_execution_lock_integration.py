"""Unknown gestures stay owned and locked; independent material edits remain live."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest

import backing_execution_constraints as execution
import connected_tier2 as connected
import musical_support_material as material
import support_material_uses as uses
from source_fact_tier1 import extract_documents,project_documents
from test_material_execution_locks import source,ref
from test_execution_dependencies import n,documents


SPEC=dict(parts=[0],first_bar=1,last_bar=1)


def saved(value):return json.loads(json.dumps(value))


def build(docs):
    lower=extract_documents(docs)
    top=connected.strip_lower(connected.analyze(lower))
    return lower,top,uses.from_tier2(top,[SPEC])


def final_note_change(model,steps):
    result=deepcopy(model)
    path=result['materials'][0]['pitch_paths'][0]
    path['steps'][-1]=str(F(path['steps'][-1])+steps)
    return result


class MaterialExecutionLockIntegrationTests(unittest.TestCase):
    def test_whole_material_with_unknown_gesture_is_exact_after_save(self):
        for kind in ('exit','ring','hp','shift'):
            with self.subTest(kind=kind):
                docs=source(kind);lower,top,model=build(docs);before=deepcopy(model)
                self.assertEqual(uses.expand(saved(model)),top)
                self.assertEqual(uses.reconstruct(saved(model),{'variation':0}),lower)
                guard=model['materials'][0]['unresolved_execution_locks']
                self.assertEqual(len(guard['locks']),1)
                for forbidden in ('"pitch"','"fret"','"notes"','"lower_tier"','"onset_q"'):
                    self.assertNotIn(forbidden,json.dumps(guard))
                self.assertEqual(model,before)

    def test_saved_successive_independent_pitch_edits_keep_original_locks_and_evidence(self):
        for kind in ('exit','ring'):
            with self.subTest(kind=kind):
                docs=source(kind);_,top,model=build(docs);before=deepcopy(model)
                changed=final_note_change(model,2)
                expected=deepcopy(docs)
                expected['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['fret']=9
                self.assertEqual(project_documents(uses.reconstruct(saved(changed),{'variation':0})),expected)
                again=final_note_change(saved(changed),1)
                expected['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['fret']=10
                self.assertEqual(project_documents(uses.reconstruct(saved(again),{'variation':0})),expected)
                self.assertEqual(again['materials'][0]['unresolved_execution_locks'],
                                 model['materials'][0]['unresolved_execution_locks'])
                self.assertEqual(again['lower_tier']['source_origin'],top['source_origin'])
                self.assertEqual(again['materials'][0]['provenance'],model['materials'][0]['provenance'])
                self.assertEqual(model,before)

    def test_missing_lock_record_or_guard_cannot_bypass_existing_edit_admission(self):
        for kind in ('exit','ring'):
            _,_,model=build(source(kind))
            for missing in ('guard','lock','record'):
                with self.subTest(kind=kind,missing=missing):
                    bad=deepcopy(model);definition=bad['materials'][0]
                    if missing=='guard':del definition['unresolved_execution_locks']
                    elif missing=='lock':definition['unresolved_execution_locks']['locks']=[]
                    else:definition['observed_execution']=[]
                    before=deepcopy(bad)
                    with self.assertRaises(ValueError):uses.reconstruct(saved(bad),{'variation':0})
                    self.assertEqual(bad,before)

    def test_selected_context_pitch_change_refuses_without_mutating_model(self):
        for kind in ('exit','ring'):
            with self.subTest(kind=kind):
                _,_,model=build(source(kind));bad=deepcopy(model)
                bad['materials'][0]['pitch_paths'][0]['start']='43'
                before=deepcopy(bad)
                with self.assertRaisesRegex(ValueError,'Protected unresolved execution context changed'):
                    uses.reconstruct(bad,{'variation':0})
                self.assertEqual(bad,before)

    def test_new_same_string_contact_refuses_even_when_original_records_are_identical(self):
        for kind in ('exit','ring'):
            with self.subTest(kind=kind):
                docs=source(kind);_,_,model=build(docs);definition=model['materials'][0]
                changed=deepcopy(docs)
                changed['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes']=[n(3)]
                current=extract_documents(changed);top=connected.strip_lower(connected.analyze(current))
                fragment=material._cut(top,SPEC)
                records=execution._snapshot(execution.encoded(current))['records']
                self.assertEqual(records,definition['observed_execution'])
                execution.build(current,[ref(1)])  # Original admission alone misses this insertion.
                before=deepcopy((fragment,definition))
                with self.assertRaisesRegex(ValueError,'Protected unresolved execution context changed'):
                    material.validate_fragment_execution(fragment,records,current,
                        execution_locks=definition['unresolved_execution_locks'],origin_q='0')
                self.assertEqual((fragment,definition),before)

    def test_context_contact_and_clock_changes_refuse_at_the_shared_validator(self):
        for change in ('contact','duration'):
            with self.subTest(change=change):
                docs=source();_,_,model=build(docs);definition=model['materials'][0]
                beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
                if change=='contact':beats[2]['notes'][0]['string']=4
                else:beats[0]['duration']=[1,8];beats[1]['duration']=[3,8]
                current=extract_documents(docs);top=connected.strip_lower(connected.analyze(current))
                with self.assertRaises(ValueError):
                    material.validate_fragment_execution(material._cut(top,SPEC),
                        definition['observed_execution'],current,
                        execution_locks=definition['unresolved_execution_locks'])

    def test_relative_original_clock_is_used_for_later_bar_material(self):
        docs=source('ring')
        docs['track-0.json']['measures'].insert(0,dict(signature=[4,4],voices=[dict(beats=[
            dict(duration=[1,1],notes=[dict(rest=True)])])]))
        lower=extract_documents(docs);top=connected.strip_lower(connected.analyze(lower))
        model=uses.from_tier2(top,[dict(parts=[0],first_bar=2,last_bar=2)])
        self.assertEqual(model['materials'][0]['source_start_q'],'4')
        self.assertEqual(uses.reconstruct(saved(model),{'variation':0}),lower)
        changed=final_note_change(model,1)
        docs['track-0.json']['measures'][1]['voices'][0]['beats'][3]['notes'][0]['fret']=8
        self.assertEqual(project_documents(uses.reconstruct(saved(changed),{'variation':0})),docs)

    def test_plain_material_has_no_new_guard_and_crossing_known_gesture_still_refuses(self):
        _,_,model=build(documents([n(2),n(4),n(5),n(7)]))
        self.assertNotIn('unresolved_execution_locks',model['materials'][0])
        docs=documents([n(2),n(4),n(5),n(7,hp=True)])
        docs['track-0.json']['measures'].append(documents([n(9),n(8),n(7),n(6)])['track-0.json']['measures'][0])
        lower=extract_documents(docs);top=connected.strip_lower(connected.analyze(lower));before=deepcopy(top)
        with self.assertRaisesRegex(ValueError,'crosses material boundary'):
            material.fit(top,lower=lower,**SPEC)
        self.assertEqual(top,before)

    def test_actual_saved_inverse_with_guard_runs_without_source_or_lower_payload(self):
        from qa_isolation_harness import execute
        from run_support_use_qa import bundle
        docs=source('ring');_,_,model=build(docs)
        changed=final_note_change(saved(model),2)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['fret']=9
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory()as folder:
            receipt=execute(code,saved(changed),{'variation':0},extract_documents(docs),
                Path(folder)/'proof',timeout=60,purpose='exact_zero')
            self.assertEqual(receipt['status'],'PASS',receipt)
            self.assertFalse(receipt['parent_expected_staged'])


if __name__=='__main__':unittest.main()
