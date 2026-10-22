"""Shared accepted tie eligibility plus exact musical-context ownership."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from test_reversible_ties import capture,beat,measure
from source_tie_tier1 import extract
from musical_tier2 import analyze,strip_lower,reconstruct,written_tie_chains,written_tie_context,written_tie_edges
from reversible_annotations import extract as old_extract
from reversible_ties import encode as old_encode
from check_reversible_source import check_tie_relations


class MusicalTieTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def run_case(self,measures):
        capture(self.folder,measures);lower=extract(self.folder);upper=analyze(lower)
        self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)
        self.assertEqual(check_tie_relations(self.folder,upper['written_ties']['links'],upper['written_ties']['unresolved'])['status'],'pass_declared_written_tie_relations')
        legacy=old_encode(old_extract(self.folder))
        self.assertEqual(upper['written_ties']['links'],legacy['links']);self.assertEqual(upper['written_ties']['unresolved'],legacy['unresolved'])
        return lower,upper

    def test_tied_segments_and_untied_repeats_differ_without_attack_claim(self):
        _,upper=self.run_case([measure([beat(),beat(tie=True),beat(tie=True)])])
        chains=written_tie_chains(upper)['chains'];self.assertEqual(len(chains),1)
        self.assertEqual(len(chains[0]['occurrence_refs']),3);self.assertEqual(chains[0]['nominal_span_q'],'3')
        self.assertEqual(len(upper['input']['events']),3)
        _,repeat=self.run_case([measure([beat(),beat(),beat()])]);self.assertEqual(written_tie_chains(repeat)['chains'],[])

    def test_resolved_notation_with_timing_warning_is_quarantined(self):
        lower,_=self.run_case([measure([beat(),beat(tie=True)])])
        lower['source_coverage']['timing_warnings']=[dict(part_id=0,bar=1,voice=0,reason='voice_overflows_bar',duration_q='5',span_q='4')]
        upper=analyze(lower);chain=written_tie_chains(upper)['chains'][0]
        self.assertTrue(chain['source_timing_uncertain'])
        self.assertEqual(chain['context_eligibility'],'quarantined_source_timing_uncertain')
        self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)

    def test_source_field_comparator_distinguishes_presence_and_numeric_types(self):
        from run_written_tie_context_qa import exact_fields
        self.assertFalse(exact_fields({},dict(tie=None)))
        self.assertFalse(exact_fields(dict(tie=True),dict(tie=1)))
        self.assertFalse(exact_fields(dict(fret=1),dict(fret=1.0)))

    def test_missing_null_false_true_and_numeric_one_roundtrip_distinctly(self):
        lower,upper=self.run_case([measure([beat(),beat(tie=False),beat(tie=None),beat(tie=1),beat(tie=True)])])
        states=[row['fields'].get('tie','missing') for row in lower['tie_notation']['occurrences']]
        self.assertEqual(states,['missing',False,None,1,True])
        self.assertEqual(len(upper['written_ties']['links']),1)
        self.assertFalse(any(r['fields'].get('tie') is True for r in upper['written_ties']['physical_choices']['occurrences']))

    def test_gap_unknown_dead_and_ambiguity_match_accepted_predicate(self):
        rest=dict(duration=[1,4],rest=True,notes=[dict(rest=True)])
        missing=beat(tie=True);missing['notes'][0].pop('fret')
        ambiguous=beat();ambiguous['notes'].append(dict(string=0,fret=5))
        cases=[[beat(),rest,beat(tie=True)],[beat(),missing],[beat(dead=True),beat(dead=True,tie=True)],[ambiguous,beat(tie=True)],[beat(),beat(fret=7,tie=True)]]
        for notes in cases:
            with self.subTest(notes=notes):self.run_case([measure(notes)])

    def test_cross_bar_chain_and_unresolved_incoming_origin_preserved(self):
        _,upper=self.run_case([measure([beat(duration=(1,1),tie=True)]),measure([beat(duration=(1,1),tie=True)])])
        chains=written_tie_chains(upper);self.assertEqual(len(chains['unresolved']),1)
        self.assertTrue(chains['chains'][0]['origin_has_unresolved_incoming_tie'])
        self.assertEqual(chains['chains'][0]['written_end_q'],'8')

    def test_opaque_ids_and_schema3_remain_supported(self):
        lower,_=self.run_case([measure([beat(),beat(tie=True)])])
        mapping={e['id']:f'opaque-{i}' for i,e in enumerate(lower['events'])}
        for e in lower['events']:e['id']=mapping[e['id']]
        for e in lower['tie_notation']['occurrences']:e['occurrence_ref']=mapping[e['occurrence_ref']]
        upper=analyze(lower);self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)
        base=deepcopy(lower);base.pop('tie_notation');base.update(schema='normalized-written-context-facts/3',scope='written_context_facts_geometry_and_optional_source_keys')
        self.assertNotIn('written_ties',analyze(base))

    def test_stale_extra_duplicate_missing_owners_and_position_conflicts_refused(self):
        _,upper=self.run_case([measure([beat(),beat(tie=True)])]);base=strip_lower(upper);cases=[]
        m=deepcopy(base);m['written_ties']['links'][0]['origin']='missing';cases.append(m)
        m=deepcopy(base);m['written_ties']['links'].append(deepcopy(m['written_ties']['links'][0]));cases.append(m)
        m=deepcopy(base);m['written_ties']['links'][0]['extra']='payload';cases.append(m)
        m=deepcopy(base);m['written_ties']['physical_choices']['occurrences'].pop();cases.append(m)
        m=deepcopy(base);m['written_ties']['physical_choices']['occurrences'][0]['fields']['fret']=7;cases.append(m)
        for m in cases:
            with self.assertRaises((ValueError,KeyError)):reconstruct(m,{'variation':0})


if __name__=='__main__':unittest.main()
