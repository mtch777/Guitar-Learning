"""Synthetic clock/ownership tests, not source-derived musical evidence."""
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize,validate
from test_connected_tier2 import documents as source_fixture
from step_tempo_relations import lift,expand,set_bpm,speed_relation,seconds_for_span,written_pass_seconds_at


def documents():
    docs=source_fixture();part=docs['track-0.json']
    part['measures'].append(deepcopy(part['measures'][0]))
    part['automations']={'tempo':[dict(measure=0,position=0,bpm=120,type=4),dict(measure=1,position=0,bpm=90,type=4)]}
    docs['track-1.json']=deepcopy(part);docs['track-1.json']['partId']=1
    docs['metadata.json']['tracks'].append(deepcopy(docs['metadata.json']['tracks'][0]))
    return docs


class GlobalStepTempoTests(unittest.TestCase):
    def test_same_equation_exact_aliases_and_no_raw_bpm_copy(self):
        lower=extract_documents(documents());upper=strip_lower(analyze(lower,step_tempos=True))
        model=upper['owned_parameters']['global_step_tempos']
        self.assertEqual([g['quarter_seconds']for g in model['groups']],['1/2','2/3'])
        self.assertEqual([len(g['bpm_refs'])for g in model['groups']],[2,2])
        refs=set(expand(model))
        self.assertFalse(refs & {r['fact_ref']for r in upper['owned_parameters']['source_choices']})
        self.assertEqual(realize(upper),lower);validate(upper)
        edited=deepcopy(upper)
        edited['owned_parameters']['global_step_tempos']=set_bpm(model,'global-tempo:4',100)
        expected=documents()
        for key in('track-0.json','track-1.json'):expected[key]['automations']['tempo'][1]['bpm']=100
        self.assertEqual(project_documents(realize(edited)),expected);validate(edited)
        self.assertEqual(realize(upper),lower)

    def test_exact_span_and_inverse_speed_arithmetic(self):
        self.assertEqual(speed_relation(bpm=153),'20/51')
        self.assertEqual(speed_relation(quarter_seconds='20/51'),'153')
        self.assertEqual(seconds_for_span('7/3',quarter_seconds='20/51'),'140/153')
        for bad in (True,120.0,0,-1):
            with self.assertRaises(ValueError):speed_relation(bpm=bad)
        with self.assertRaises(ValueError):speed_relation(bpm=120,quarter_seconds='1/2')

    def test_written_seconds_follow_shared_speed_and_keep_quarter_positions(self):
        model=lift(extract_documents(documents()))
        self.assertEqual(written_pass_seconds_at(model,4),'2')
        self.assertEqual(written_pass_seconds_at(model,8),'14/3')
        changed=set_bpm(model,'global-tempo:0',100)
        self.assertEqual(written_pass_seconds_at(changed,4),'12/5')
        self.assertEqual(written_pass_seconds_at(changed,8),'76/15')
        self.assertEqual([(g['onset_q'],g['end_q'])for g in model['groups']],[(g['onset_q'],g['end_q'])for g in changed['groups']])
        partial=deepcopy(model);partial['groups'].pop(0)
        with self.assertRaisesRegex(ValueError,'Incomplete'):written_pass_seconds_at(partial,5)
        with self.assertRaises(ValueError):written_pass_seconds_at(model,9)

    def test_missing_duplicate_stale_and_copied_alias_owners_fail(self):
        lower=extract_documents(documents());upper=strip_lower(analyze(lower,step_tempos=True))
        def remove_group(x):x['owned_parameters']['global_step_tempos']['groups'].pop()
        def remove_alias(x):x['owned_parameters']['global_step_tempos']['groups'][0]['bpm_refs'].pop()
        def duplicate(x):x['owned_parameters']['global_step_tempos']['groups'].append(deepcopy(x['owned_parameters']['global_step_tempos']['groups'][0]))
        def stale(x):x['owned_parameters']['global_step_tempos']['groups'][0]['id']='global-tempo:1'
        def hidden(x):x['owned_parameters']['global_step_tempos']['groups'][0]['original_bpm']=120
        for mutate in(remove_group,remove_alias,duplicate,stale,hidden):
            broken=deepcopy(upper);mutate(broken)
            with self.assertRaises((ValueError,KeyError)):realize(broken)

    def test_source_conflicts_and_unknown_execution_are_never_repaired(self):
        for update in(lambda d:d['track-1.json']['automations']['tempo'][0].update(bpm=121),
                      lambda d:d['track-0.json']['automations']['tempo'][0].update(linear=True),
                      lambda d:d['track-0.json']['automations']['tempo'][0].update(type=8)):
            docs=documents();update(docs);lower=extract_documents(docs)
            upper=strip_lower(analyze(lower,step_tempos=True))
            self.assertNotIn('global-tempo:0',[g['id']for g in upper['owned_parameters']['global_step_tempos']['groups']])
            self.assertEqual(realize(upper),lower)

    def test_optional_articulation_and_written_time_owners_still_compose(self):
        lower=extract_documents(documents())
        upper=analyze(lower,step_tempos=True,palm_mute_slots=True,note_accent_slots=True,rhythm_groups=True,rhythm_group_profile='written_time')
        self.assertEqual(realize(strip_lower(upper)),lower);validate(upper)

    def test_inverse_cannot_read_source_files(self):
        lower=extract_documents(documents());upper=strip_lower(analyze(lower,step_tempos=True))
        with patch('builtins.open',side_effect=AssertionError('Unexpected source access')),patch.object(Path,'open',side_effect=AssertionError('Unexpected source access')):
            self.assertEqual(realize(upper),lower)

    def test_actual_stripped_worker_recovers_all_source_aliases(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower=extract_documents(documents());upper=strip_lower(analyze(lower,step_tempos=True))
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as temp:
            result=execute(code,upper,{'variation':0},lower,Path(temp)/'zero',timeout=30)
        self.assertEqual(result['status'],'PASS',result)


if __name__=='__main__':unittest.main()
