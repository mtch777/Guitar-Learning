"""Declared continuity differs from repetition; harmonic labels need not differ."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from test_reversible_ties import capture,beat,measure
from source_tie_tier1 import extract
from musical_tier2 import analyze,harmonic_span_evidence,tied_harmonic_context,harmonic_membership_evidence,strip_lower,reconstruct,same


class TiedHarmonicContextTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def case(self,tied=True,dead=False,orphan=False):
        capture(self.path,[measure([beat(fret=20,dead=dead,**({'tie':True} if orphan else {})),beat(fret=20,dead=dead,**({'tie':True} if tied else {}))])])
        meta=json.loads((self.path/'metadata.json').read_text());meta['tracks'].append(dict(partId=1));(self.path/'metadata.json').write_text(json.dumps(meta))
        context=dict(songId=77,revisionId=3,partId=1,instrumentId=25,tuning=[43,47,50],measures=[measure([dict(duration=[1,4],notes=[dict(string=i,fret=5) for i in range(3)]),dict(duration=[1,4],notes=[dict(string=i,fret=0) for i in range(3)])])])
        (self.path/'track-1.json').write_text(json.dumps(context));lower=extract(self.path);upper=analyze(lower);evidence=harmonic_span_evidence(upper,'0','2')
        self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)
        return lower,upper,evidence

    def test_continuation_changes_membership_with_original_occurrences(self):
        lower,upper,evidence=self.case();origin='event:77:0:1:0:0:0'
        result=tied_harmonic_context(upper,evidence,origin,['1/2','3/2'])
        self.assertTrue(same(result,tied_harmonic_context(strip_lower(upper),evidence,origin,['1/2','3/2'])))
        self.assertEqual(result['status'],'CONDITIONAL_CONTINUITY_CONTEXT')
        self.assertEqual([r['occurrence_ref'] for r in result['resolved_original_queries']],[origin,'event:77:0:1:0:1:0'])
        self.assertEqual({tuple(r['memberships']) for r in result['membership']['feasible_membership_vectors']},{('chord_member','nonmember')})
        self.assertEqual(len(lower['events']),8)
        reversed_query=tied_harmonic_context(upper,evidence,origin,['3/2','1/2'])
        self.assertEqual(reversed_query['requested_clocks_q'],['3/2','1/2'])
        self.assertEqual(reversed_query['membership']['feasible_membership_vectors'][0]['memberships'],['nonmember','chord_member'])

    def test_untied_repetition_keeps_same_harmony_without_invented_continuity(self):
        _,upper,evidence=self.case(tied=False)
        result=tied_harmonic_context(upper,evidence,'event:77:0:1:0:0:0',['1/2','3/2'])
        self.assertEqual(result['status'],'NO_DECLARED_CHAIN')
        individual=harmonic_membership_evidence(upper,evidence,[dict(occurrence_ref='event:77:0:1:0:0:0',at_q='1/2'),dict(occurrence_ref='event:77:0:1:0:1:0',at_q='3/2')])
        self.assertEqual(individual['feasible_membership_vectors'][0]['memberships'],['chord_member','nonmember'])

    def test_entire_chain_dead_or_orphan_or_timing_uncertain_is_quarantined(self):
        for options,reason in ((dict(dead=True),'unpitched_dead_notation'),(dict(orphan=True),'unresolved_incoming_continuity')):
            _,upper,evidence=self.case(**options);result=tied_harmonic_context(upper,evidence,'event:77:0:1:0:0:0',['1/2','3/2'])
            self.assertEqual(result['status'],'QUARANTINED_CHAIN');self.assertIn(reason,result['quarantine_reasons']);self.assertIsNone(result['membership'])
        lower,_,_=self.case();lower['source_coverage']['timing_warnings']=[dict(part_id=0,bar=1,voice=0,reason='voice_overflows_bar',duration_q='5',span_q='4')]
        upper=analyze(lower);evidence=harmonic_span_evidence(upper,'0','2');result=tied_harmonic_context(upper,evidence,'event:77:0:1:0:0:0',['1/2'])
        self.assertIn('source_timing_uncertain',result['quarantine_reasons'])

    def test_boundary_scope_staleness_and_later_origin_refused(self):
        _,upper,evidence=self.case();origin='event:77:0:1:0:0:0'
        for clocks in (['2'],['-1'],[]):
            with self.assertRaises(ValueError):tied_harmonic_context(upper,evidence,origin,clocks)
        for bad in (harmonic_span_evidence(upper,'0','1'),harmonic_span_evidence(upper,'0','2',part_id=1)):
            with self.assertRaises(ValueError):tied_harmonic_context(upper,bad,origin,['1/2'])
        stale=deepcopy(evidence);stale['optimal_score']=999
        with self.assertRaises(ValueError):tied_harmonic_context(upper,stale,origin,['1/2'])
        broken=strip_lower(upper);broken['coattacks'][0]['members'][0]['voicing_interval']='1'
        with self.assertRaises(ValueError):tied_harmonic_context(broken,evidence,origin,['1/2'])
        with self.assertRaises(ValueError):tied_harmonic_context(upper,evidence,'event:77:0:1:0:1:0',['3/2'])

    def test_resource_limit_is_retained_not_replaced(self):
        _,upper,_=self.case();evidence=harmonic_span_evidence(upper,'0','2',max_edges=1)
        result=tied_harmonic_context(upper,evidence,'event:77:0:1:0:0:0',['1/2','3/2'])
        self.assertEqual(result['status'],'HARMONIC_ANALYSIS_NOT_RUN');self.assertEqual(result['harmonic_status'],'NOT_RUN_RESOURCE_LIMIT')

    def test_orphan_only_declaration_is_not_reported_as_absent_continuity(self):
        _,upper,evidence=self.case(tied=False,orphan=True)
        result=tied_harmonic_context(upper,evidence,'event:77:0:1:0:0:0',['1/2'])
        self.assertEqual(result['status'],'UNRESOLVED_DECLARATION_WITHOUT_RESOLVED_CHAIN')
        self.assertEqual(result['unresolved_declaration']['reason'],'no_predecessor')
        self.assertIsNone(result['membership'])

    def test_independent_harmonic_oracle_checks_joint_witnesses(self):
        from check_harmonic_span_source import check
        lower,upper,evidence=self.case();context=tied_harmonic_context(upper,evidence,'event:77:0:1:0:0:0',['1/2','3/2'])
        owned={r['id']:r for r in lower['events']};raw=[tuple(r[k] for k in ('part_id','bar','pitch','onset_q','duration_q')) for r in lower['events']]
        membership=context['membership'];self.assertEqual(check(raw,evidence,membership,owned)['status'],'PASS')
        wrong=deepcopy(membership);wrong['feasible_membership_vectors'][0]['memberships'][0]='nonmember'
        self.assertEqual(check(raw,evidence,wrong,owned)['status'],'FAIL')
        empty=deepcopy(membership);empty['feasible_membership_vectors']=[]
        self.assertEqual(check(raw,evidence,empty,owned)['status'],'FAIL')
        label=deepcopy(membership);label['feasible_membership_vectors'][0]['one_valid_path_and_label_witness'][0]['label']['root_pc']=1
        self.assertEqual(check(raw,evidence,label,owned)['status'],'FAIL')

    def test_source_context_checker_requires_every_part_and_unresolved_declaration(self):
        from run_tied_harmonic_context_qa import study,source_queries
        _,upper,_=self.case(orphan=True)
        result=study(strip_lower(upper),50000)
        self.assertEqual(source_queries(self.path,upper,result)['status'],'PASS')
        duplicate=deepcopy(result);duplicate['parts'][1]=deepcopy(duplicate['parts'][0])
        self.assertEqual(source_queries(self.path,upper,duplicate)['status'],'FAIL')
        omitted=deepcopy(result);omitted['parts'].pop()
        self.assertEqual(source_queries(self.path,upper,omitted)['status'],'FAIL')
        missing=deepcopy(result);missing['parts'][0]['unresolved_declarations']=[]
        self.assertEqual(source_queries(self.path,upper,missing)['status'],'FAIL')


if __name__=='__main__':unittest.main()
