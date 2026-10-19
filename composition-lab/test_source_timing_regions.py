"""Conservative recovery metadata and explicit unpitched notation continuity."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
from source_timing_regions import local_timing_regions,relationship_region
from source_semantics import unpitched_tie_continuity,sustain_context


def row(i,onset,duration='1',**kw):
    return dict(occurrence=str(i),onset_q=str(onset),duration_q=duration,voice=0,string=0,fret=0,
                midi=None,effects=['dead'],raw_note=dict(dead=True),tie_destination=i!=0,**kw)


def fixture():
    p=dict(measures=[dict(voices=[dict(beats=[{}]),dict(beats=[{}])]) for _ in range(5)])
    h=[dict(start_q=str(4*i),span_q='4') for i in range(5)]
    return p,h


class LocalTimingTests(unittest.TestCase):
    def test_overflow_blocks_own_voice_and_intrusion_but_never_changes_source(self):
        p,h=fixture();before=deepcopy(p)
        result=local_timing_regions(p,h,[dict(bar=2,voice=0,reason='voice_overflows_bar',duration_q='17/4')])
        self.assertEqual(p,before)
        self.assertEqual([(r['start_bar'],r['end_bar']) for r in result['voice_regions']['0']],[(1,1),(4,5)])
        self.assertEqual([(r['start_bar'],r['end_bar']) for r in result['voice_regions']['1']],[(1,5)])
        self.assertEqual(result['all_voice_regions'],result['voice_regions']['0'])
        regions=result['voice_regions']['0']
        self.assertEqual(relationship_region(regions,[dict(onset_q='12',duration_q='4')]),1)
        self.assertIsNone(relationship_region(regions,[dict(onset_q='3',duration_q='10')]))
        self.assertIsNone(relationship_region(regions,[dict(onset_q='0',duration_q='1'),dict(onset_q='12',duration_q='1')]))
        self.assertIsNone(relationship_region(regions,[dict(onset_q='12',duration_q='0')]))

    def test_exact_boundary_and_multi_bar_overrun(self):
        p,h=fixture()
        for d,expected in [('8',[(1,1),(4,5)]),('33/4',[(1,1),(5,5)])]:
            r=local_timing_regions(p,h,[dict(bar=2,voice=0,reason='voice_overflows_bar',duration_q=d)])
            self.assertEqual([(x['start_bar'],x['end_bar']) for x in r['voice_regions']['0']],expected)

    def test_missing_duration_layout_ambiguity_and_absent_voice_are_barriers(self):
        p,h=fixture();p['measures'][2]['voices'].pop()
        r=local_timing_regions(p,h,[dict(bar=2,voice=0,reason='missing_duration')],[dict(bar=4,reason='conflicting_track_meter')])
        self.assertEqual([(x['start_bar'],x['end_bar']) for x in r['all_voice_regions']],[(1,1)])
        self.assertEqual(local_timing_regions(p,h,[dict(reason='unlocated')])['all_voice_regions'],[])
        h[2]['start_q']='9'
        with self.assertRaises(ValueError):local_timing_regions(p,h,[])


class UnpitchedTieTests(unittest.TestCase):
    def test_explicit_dead_chain_is_separate_and_pitched_behavior_unchanged(self):
        rows=[row(0,'0'),row(1,'1'),row(2,'2')];before=deepcopy(rows)
        pitched_before=sustain_context(rows,[])
        r=unpitched_tie_continuity(rows)
        self.assertEqual(len(r['links']),2);self.assertEqual(r['chains'][0]['members'],['0','1','2'])
        self.assertIsNone(r['chains'][0]['sounding_pitch']);self.assertEqual(r['chains'][0]['written_end_q'],'3')
        self.assertEqual(rows,before);self.assertEqual(sustain_context(rows,[]),pitched_before)
        self.assertEqual(len(pitched_before['warnings']),2)

    def test_mixed_unknown_and_noncontiguous_are_never_joined(self):
        for mutation in ('pitched','unknown','gap','fret','lane','zero','negative_fret'):
            a,b=row(0,'0'),row(1,'1')
            if mutation=='pitched':b.update(midi=40,effects=[],raw_note={})
            if mutation=='unknown':b.update(effects=[],raw_note={})
            if mutation=='gap':b['onset_q']='3/2'
            if mutation=='fret':b['fret']=2
            if mutation=='lane':b['voice']=1
            if mutation=='zero':b['duration_q']='0'
            if mutation=='negative_fret':a['fret']=b['fret']=-1
            self.assertEqual(unpitched_tie_continuity([a,b])['links'],[],mutation)

    def test_ambiguous_simultaneous_same_lane_cannot_supply_predecessor(self):
        rows=[row(0,'0'),row(9,'0'),row(1,'1')]
        self.assertEqual(unpitched_tie_continuity(rows)['links'],[])
        r=unpitched_tie_continuity([row(1,'0'),row(2,'1')])
        self.assertTrue(r['chains'][0]['origin_is_tie_destination'])


if __name__=='__main__':unittest.main()
