"""Independent fixture checks; these do not certify a GP inverse or musical quality."""
import importlib.util,json,unittest
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict

P=Path(__file__).parent/'examples'
spec=importlib.util.spec_from_file_location('realistic_fixture',P/'build_realistic_tier_example.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class RealisticTierExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.d=module.build();cls.r=cls.d['records']
    def test_saved_data_reproduces_and_inputs_are_adjacent(self):
        self.assertEqual(self.d,json.loads((P/'tiered-passage.example.json').read_text(encoding='utf-8')))
        for id,r in self.r.items():
            for ref in r['inputs']:self.assertEqual(self.r[ref]['tier'],r['tier']-1,(id,ref))
        for case in self.d['cases']:
            self.assertIn(case['root'],self.r)
            self.assertTrue(set(case['select'])<=self.r.keys())
    def test_rhythm_pitch_source_and_bar_voice_coverage(self):
        grouped=defaultdict(list)
        for id,r in self.r.items():
            if r['kind'] not in ('note','rest'):continue
            raw=self.r[r['inputs'][0]];rh=raw['rhythm'];duration=F(4,rh['denominator'])*sum((F(1,2**i) for i in range(rh['dots']+1)),F(0));tuplet=rh.get('tuplet',[1,1]);duration*=F(tuplet[1],tuplet[0]);self.assertEqual(F(r['time']['duration']),duration,id)
            bar=self.r['notation']['bars'][r['bar']-1];a=F(r['time']['start']);b=a+duration
            self.assertEqual(a,F(bar['start_q'])+F(raw['offset_q']))
            self.assertLessEqual(b,F(bar['start_q'])+F(bar['duration_q']))
            grouped[r['track'],r['voice'],r['bar']].append((a,b))
            if r['kind']=='note':self.assertEqual(r['pitch_midi'],self.r['notation']['tracks'][r['track']]['tuning'][r['string_highest_is_1']-1]+r['fret'])
        for (track,voice,bi),spans in grouped.items():
            bar=self.r['notation']['bars'][bi-1];cursor=F(bar['start_q'])
            for a,b in sorted(set(spans)):
                self.assertEqual(a,cursor,(track,voice,bi));cursor=b
            self.assertEqual(cursor,F(bar['start_q'])+F(bar['duration_q']))
    def test_ties_transitions_groups_and_bend(self):
        for id in ['tie_high','tie_low']:
            members=[self.r[x] for x in self.r[id]['members']]
            for a,b in zip(members,members[1:]):
                self.assertEqual(F(a['time']['start'])+F(a['time']['duration']),F(b['time']['start']))
                self.assertEqual((a['pitch_midi'],a['string_highest_is_1'],a['voice']),(b['pitch_midi'],b['string_highest_is_1'],b['voice']))
                self.assertFalse(b['attack'])
        for id,direction in [('hammer',1),('pull',-1),('slide',1)]:
            rel=self.r[id];a,b=(self.r[rel[k]] for k in ['origin','destination']);self.assertEqual(a['string_highest_is_1'],b['string_highest_is_1']);self.assertGreater((b['fret']-a['fret'])*direction,0);self.assertEqual(F(a['time']['start'])+F(a['time']['duration']),F(b['time']['start']))
        for r in self.r.values():
            if r['kind']=='coattack':
                notes=[self.r[x] for x in r['members']];self.assertEqual(len({x['time']['start'] for x in notes}),1);self.assertEqual(len(notes),len({x['string_highest_is_1'] for x in notes}))
                pitches=[x['pitch_midi'] for x in notes]
                if 'power_chord' in r['labels']:self.assertEqual({(p-min(pitches))%12 for p in pitches},{0,7})
                else:self.assertEqual(len(pitches),2);self.assertEqual(abs(pitches[0]-pitches[1]),1)
        self.assertEqual(self.r['bend']['peak_midi'],self.r['a4']['pitch_midi']+2)
        self.assertEqual(self.r['a4']['technique']['bend']['points'],[['0','0'],['1/3','2'],['2/3','2'],['1','0']])
    def test_section_membership_is_local_not_global_support(self):
        for r in self.r.values():
            if r['kind'] not in ('section','relationship_region'):continue
            start=F(r['time']['start']);end=start+F(r['time']['duration'])
            for id in r['members']:
                child=self.r[id];self.assertIn('time',child);self.assertIsNotNone(child['time'])
                self.assertGreaterEqual(F(child['time']['start']),start)
                self.assertLessEqual(F(child['time']['start'])+F(child['time']['duration']),end)
        for r in self.r.values():
            if r['kind'] in ('note','rest'):self.assertEqual(self.r[r['track_ref']]['track'],r['track'])

    def test_pattern_realizations_preserve_full_notes_rests_and_explicit_variation(self):
        pattern=self.r['idea']
        for label in ['a','b']:
            occurrence=self.r['occ_'+label];base=F(occurrence['time']['start']);phrase=self.r['phrase_'+label]
            members=[self.r[id] for id in phrase['members']];notes=sorted((r for r in members if r['kind']=='note'),key=lambda r:F(r['time']['start']))
            self.assertEqual(len(notes),len(pattern['relative_onsets_q']))
            for i,n in enumerate(notes):
                self.assertEqual(F(n['time']['start']),base+F(pattern['relative_onsets_q'][i]))
                self.assertEqual(F(n['time']['duration']),F(pattern['durations_q'][i]))
                self.assertEqual(n['pitch_midi'],occurrence['choices']['first_midi']+pattern['baseline_relative_pitches'][i]+occurrence['choices']['pitch_delta_by_member_index'].get(str(i),0))
            actual_rests=sorted((F(r['time']['start'])-base,F(r['time']['duration'])) for r in members if r['kind']=='rest')
            self.assertEqual(actual_rests,[(F(x['start_q']),F(x['duration_q'])) for x in pattern['rest_pattern']])
        self.assertEqual(self.r['occ_b']['choices']['pitch_delta_by_member_index'],{'3':2})
        self.assertIsNone(self.r['b4']['technique']['vibrato']['depth_semitones'])

    def test_pattern_call_order_counts_and_clocks(self):
        for id in ['call_a','call_b']:
            rel=self.r[id];calls=[self.r[x] for x in rel['call']];answers=[self.r[x] for x in rel['answer']]
            self.assertEqual(len({x['pitch_midi'] for x in calls}),1)
            self.assertGreater(min(F(x['time']['start']) for x in answers),max(F(x['time']['start']) for x in calls))
        stats=self.r['bend_share'];population=[r for r in self.r.values() if r['kind']=='note' and r['track']=='lead' and r['attack']]
        self.assertEqual(stats['denominator'],len(population));self.assertEqual(stats['numerator'],sum(bool(x['technique'].get('bend')) for x in population))
        visits=self.r['playback']['visits'];self.assertEqual([v['bar'] for v in visits],[1,2,1,2,3,4,5,6,7,8]);q=F(0);seconds=F(0)
        for v in visits:
            self.assertEqual(F(v['playback_start_q']),q);self.assertEqual(F(v['start_seconds']),seconds);self.assertEqual(F(v['duration_seconds']),F(v['duration_q'])*60/v['bpm']);q+=F(v['duration_q']);seconds+=F(v['duration_seconds'])
        self.assertEqual(q,39);self.assertEqual(F(self.r['playback']['total_written_q']),31);self.assertEqual(F(self.r['playback']['total_seconds']),seconds)

if __name__=='__main__':unittest.main()
