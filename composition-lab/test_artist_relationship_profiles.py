from copy import deepcopy
import unittest
from artist_relationship_profiles import build_relationship_profile,attack_groups,heldout_support,validate_profile_inputs


def row(i,q,pitch=40,section=1,bar=1,effects=(),**extra):
    value=dict(occurrence=f'0:{bar}:0:{i}:0',onset_q=str(q),duration_q='1',
               bar_offset_q=str(q-(bar-1)*4),section_start=section,bar=bar,
               voice=0,string=0,fret=pitch-40 if pitch is not None else 0,
               midi=pitch,tie_destination=False,effects=list(effects),
               raw_note={},raw_beat_effects={})
    value.update(extra)
    return value


def song(sid,rows,partition='development',family=None,tracks=None):
    track=dict(part_id=0,guitar_or_bass=True,temporal_relationships_eligible=True,
               rows=rows,grace_rows=[],coattack_groups=[],hopo_transition_candidates=[])
    return dict(song_id=sid,artist='A',provisional_partition=partition,
                candidate_work_family=family or str(sid),ai_generated=False,is_junk=False,
                tracks=tracks if tracks is not None else [track])


def tables(profile,kind):return [t for t in profile['tables'] if t['kind']==kind]


class RelationshipProfileTests(unittest.TestCase):
    def test_context_conditions_have_counts_and_family_support(self):
        s=song(1,[row(0,0,effects=['palmMute']),row(1,1)])
        p=build_relationship_profile({'songs':[s]}, {},'A')
        t=next(t for t in tables(p,'technique_given_written_harmony_labels') if t['condition']['feature']=='palm_mute')
        self.assertEqual(t['eligible_count'],2)
        self.assertEqual({o['outcome']:o['conditional_probability'] for o in t['outcomes']},{True:.5,False:.5})
        self.assertTrue(all(o['families']==1 and o['songs']==1 for o in t['outcomes']))

    def test_held_out_annotations_do_not_affect_fitted_profile(self):
        r={'songs':[song(1,[row(0,0)]),song(2,[row(0,0,effects=['bend'])],'held_out')]}
        a=build_relationship_profile(r,{},'A');r['songs'][1]['tracks'][0]['rows'][0]['effects']=['palmMute']
        self.assertEqual(a,build_relationship_profile(r,{},'A'))

    def test_family_split_guard_and_timing_exclusion(self):
        r={'songs':[song(1,[row(0,0)],family='same'),song(2,[row(0,0)],'held_out',family='same')]}
        with self.assertRaises(ValueError):build_relationship_profile(r,{},'A')
        r={'songs':[song(1,[row(0,0)])]};r['songs'][0]['tracks'][0]['temporal_relationships_eligible']=False
        p=build_relationship_profile(r,{},'A');self.assertEqual(p['tables'],[])
        self.assertEqual(p['coverage']['excluded_temporal_tracks'],1)

    def test_transitions_do_not_cross_section_instances(self):
        p=build_relationship_profile({'songs':[song(1,[row(0,0),row(1,1,section=2),row(2,2,section=2)])]}, {},'A')
        self.assertEqual(sum(t['eligible_count'] for t in tables(p,'next_written_attack')),1)

    def test_pedal_unknown_coverage_not_negative_and_dead_pitch_not_harmony(self):
        t=song(1,[row(0,0,pitch=None,effects=['dead'])])['tracks'][0]
        g=attack_groups(t,None)[0]
        self.assertNotIn('pedal_call',g['known']);self.assertNotIn('power_chord',g['known'])
        self.assertIn('dead',g['labels'])

    def test_accepted_call_repetition_with_changed_response_pitch(self):
        rows=[row(0,0),row(1,1,45),row(2,2),row(3,3,47)]
        cycles=[dict(call_start_q='0',response_start_q='1',return_q='2',call_members=[rows[0]['occurrence']],response_members=[rows[1]['occurrence']]),
                dict(call_start_q='2',response_start_q='3',return_q='4',call_members=[rows[2]['occurrence']],response_members=[rows[3]['occurrence']])]
        pedal={'tracks':[dict(song_id=1,part_id=0,phrases=[dict(members=[r['occurrence'] for r in rows],roles={r['occurrence']:'call' if i%2==0 else 'response' for i,r in enumerate(rows)},cycles=cycles)])]}
        p=build_relationship_profile({'songs':[song(1,rows)]},pedal,'A')
        self.assertEqual(p['coverage']['accepted_pedal_cycles'],2)
        v=tables(p,'same_pedal_call_answer_variation')[0]['outcomes'][0]['outcome']
        self.assertEqual(v,dict(response_rhythm_same=True,response_pitch_same=False))
        bad=deepcopy(pedal);bad['tracks'][0]['phrases'][0]['cycles'][0]['response_start_q']='0'
        with self.assertRaises(ValueError):build_relationship_profile({'songs':[song(1,rows)]},bad,'A')

    def test_exact_bar_returns_and_track_coattacks(self):
        first=[row(0,0),row(1,1,42),row(0,4,bar=2),row(1,5,42,bar=2)]
        s=song(1,first);other=deepcopy(s['tracks'][0]);other['part_id']=1
        other['rows']=[dict(row(0,0,52),occurrence='1:1:0:0:0')]
        s['tracks'].append(other)
        p=build_relationship_profile({'songs':[s]}, {},'A')
        r=next(t for t in tables(p,'bar_pattern_return') if t['condition']['pattern_kind']=='rhythm')
        outcomes={o['outcome']:o['count'] for o in r['outcomes']}
        self.assertEqual(outcomes['same_section_return'],1)
        self.assertEqual(p['coverage']['simultaneous_track_pairs'],1)

    def test_duplicate_version_within_family_does_not_change_probabilities(self):
        a=song(1,[row(0,0,effects=['palmMute']),row(1,1)],family='work')
        b=song(2,[row(0,0),row(1,1)],family='other')
        p=build_relationship_profile({'songs':[a,b]}, {},'A')
        dup=deepcopy(a);dup['song_id']=3
        q=build_relationship_profile({'songs':[a,b,dup]}, {},'A')
        def rates(profile):return {(t['kind'],str(t['condition']),str(o['outcome'])):o['conditional_probability'] for t in profile['tables'] for o in t['outcomes']}
        for k,v in rates(p).items():self.assertAlmostEqual(v,rates(q)[k])

    def test_existing_shape_details_join_to_context_without_new_curve_inference(self):
        s=song(1,[row(0,0,effects=['bend']),row(1,1,42)])
        s['tracks'][0]['technique_values']=[dict(occurrence='0:1:0:0:0',bend=dict(valid=True,
            peak_semitones='2',initial_semitones='0',final_semitones='2',first_peak_fraction='1/2',
            slopes_semitones_per_quarter=['4'],point_vibrato_flags=0))]
        p=build_relationship_profile({'songs':[s]}, {},'A')
        outcome=tables(p,'mechanical_shape_given_context')[0]['outcomes'][0]['outcome']
        self.assertEqual(outcome['peak_semitones'],'2')
        self.assertEqual(outcome['next_attack_written_minimum_interval'],2)

    def test_heldout_support_is_separate_and_checks_families(self):
        r={'songs':[song(1,[row(0,0)]),song(2,[row(0,0)],'held_out')]}
        dev=build_relationship_profile(r,{},'A');held=build_relationship_profile(r,{},'A',partition='held_out')
        self.assertEqual(held['training_songs'],[])
        self.assertEqual(heldout_support(dev,held)['by_kind']['technique_given_context']['supported_conditions'],
                         len(tables(held,'technique_given_context')))
        held['observed_families']=dev['training_families']
        with self.assertRaises(ValueError):heldout_support(dev,held)

    def test_marker_expansion_keeps_unknown_masks(self):
        s=song(1,[row(0,0,effects=['ghost','harmonic','tremoloBar'])])
        g=attack_groups(s['tracks'][0],None)[0]
        self.assertTrue({'ghost','harmonic','whammy_curve'}<=g['labels'])
        self.assertNotIn('pedal_call',g['known'])

    def test_unrelated_missing_feature_coverage_does_not_reweight_palm(self):
        r={'songs':[song(1,[row(0,0,effects=['palmMute'])]),song(2,[row(0,0)])]}
        pedal={'tracks':[dict(song_id=1,part_id=0,phrases=[])]}
        p=build_relationship_profile(r,pedal,'A')
        t=next(t for t in tables(p,'technique_given_context') if t['condition']['feature']=='palm_mute')
        self.assertEqual({o['outcome']:o['conditional_probability'] for o in t['outcomes']},{True:.5,False:.5})

    def test_unknown_harmony_and_accepted_pedal_negative_stay_distinct(self):
        s=song(1,[row(0,0,None,effects=['dead']),row(1,1)])
        p=build_relationship_profile({'songs':[s]}, {},'A')
        t=[t for t in tables(p,'technique_given_written_harmony_labels') if t['condition']['feature']=='dead']
        self.assertEqual({str(t['condition']['value']) for t in t},
                         {str(dict(known=False,labels=None)),str(dict(known=True,labels=[]))})
        track=s['tracks'][0]
        self.assertEqual(attack_groups(track,None)[0]['role'],'unknown')
        self.assertEqual(attack_groups(track,{})[0]['role'],'not_tagged_in_accepted_pedal')

    def test_shorter_simultaneous_durations_change_rhythm_fingerprint(self):
        rows=[row(0,0),dict(row(1,0,45,duration_q='1/2'),voice=1,string=1),
              row(0,4,bar=2),dict(row(1,4,45,bar=2,duration_q='1/4'),voice=1,string=1)]
        p=build_relationship_profile({'songs':[song(1,rows)]}, {},'A')
        out=tables(p,'adjacent_bar_variation')[0]['outcomes'][0]['outcome']
        self.assertFalse(out['rhythm_same']);self.assertTrue(out['pitch_same'])

    def test_different_bar_span_prevents_false_rhythmic_return(self):
        rows=[row(0,0,bar_span_q='3'),row(0,3,bar=2,bar_offset_q='0',bar_span_q='4')]
        p=build_relationship_profile({'songs':[song(1,rows)]}, {},'A')
        out=tables(p,'adjacent_bar_variation')[0]['outcomes'][0]['outcome']
        self.assertFalse(out['rhythm_same'])

    def test_ambiguous_source_and_accepted_joins_fail_closed(self):
        def fixture():
            rows=[row(0,0),row(1,1,45),row(2,2)]
            r={'songs':[song(1,rows)]}
            c=dict(call_start_q='0',response_start_q='1',return_q='2',call_members=[rows[0]['occurrence']],response_members=[rows[1]['occurrence']])
            ph=dict(members=[x['occurrence'] for x in rows],roles={rows[0]['occurrence']:'call',rows[1]['occurrence']:'response'},cycles=[c])
            p={'tracks':[dict(song_id=1,part_id=0,phrases=[ph])]}
            return r,p
        mutations=[
            lambda r,p:r['songs'].append(deepcopy(r['songs'][0])),
            lambda r,p:r['songs'].append(dict(deepcopy(r['songs'][0]),song_id='1')),
            lambda r,p:r['songs'][0]['tracks'].append(deepcopy(r['songs'][0]['tracks'][0])),
            lambda r,p:r['songs'][0]['tracks'][0]['rows'].append(deepcopy(r['songs'][0]['tracks'][0]['rows'][0])),
            lambda r,p:r['songs'][0]['tracks'][0]['grace_rows'].append(deepcopy(r['songs'][0]['tracks'][0]['rows'][0])),
            lambda r,p:p['tracks'].append(deepcopy(p['tracks'][0])),
            lambda r,p:p['tracks'][0].update(part_id=99),
            lambda r,p:p['tracks'][0].update(song_id='1'),
            lambda r,p:p['tracks'][0].update(part_id='0'),
            lambda r,p:p['tracks'][0]['phrases'][0]['members'].append('missing'),
            lambda r,p:p['tracks'][0]['phrases'][0]['roles'].update(missing='call'),
            lambda r,p:p['tracks'][0]['phrases'][0]['cycles'][0]['call_members'].append('missing'),
            lambda r,p:p['tracks'][0]['phrases'][0]['cycles'].append(deepcopy(p['tracks'][0]['phrases'][0]['cycles'][0])),
            lambda r,p:p['tracks'][0]['phrases'].append(deepcopy(p['tracks'][0]['phrases'][0])),
            lambda r,p:p['tracks'][0]['phrases'][0]['roles'].update({'0:1:0:1:0':'call'}),
            lambda r,p:p['tracks'][0]['phrases'][0]['cycles'][0].update(return_q=None),
        ]
        r,p=fixture()
        self.assertEqual(validate_profile_inputs(r,p)['accepted_untagged_context_members'],1)
        for mutate in mutations:
            r,p=fixture();mutate(r,p)
            with self.subTest(mutation=mutations.index(mutate)):
                with self.assertRaises(ValueError):validate_profile_inputs(r,p)

    def test_program_aliases_and_invalid_values_fail_before_fitting(self):
        r={'songs':[song(1,[row(0,0)])]}
        for programs in [{('1',0):30},{(1,'0'):30},{(1,0):True},{(1,0):-1},{(1,0):128},{(9,0):30}]:
            with self.assertRaises(ValueError):build_relationship_profile(r,{},'A',programs)

    def test_raw_song_and_local_denominators_reconcile_with_outcomes(self):
        r={'songs':[song(1,[row(0,0,effects=['palmMute']),row(1,1)]),song(2,[row(0,0)])]}
        p=build_relationship_profile(r,{},'A')
        song_rows=[s for s in p['technique_song_summaries'] if s['feature']=='palm_mute']
        self.assertEqual([(s['eligible_attack_groups'],s['positive_attack_groups']) for s in song_rows],[(2,1),(1,0)])
        self.assertTrue(all(s['eligible_attack_groups']>0 for s in p['technique_local_summaries']))
        for t in p['tables']:
            self.assertEqual(sum(s['eligible_count'] for s in t['song_eligible_counts']),t['eligible_count'])
            for o in t['outcomes']:
                self.assertEqual(sum(s['count'] for s in o['song_counts']),o['count'])
                self.assertTrue(all(s['family'] for s in o['song_counts']))

    def test_previous_known_mask_is_a_condition_not_only_an_outcome(self):
        r={'songs':[song(1,[row(0,0),row(1,1)]),song(2,[row(0,0),row(1,1)])]}
        p=build_relationship_profile(r,{'tracks':[dict(song_id=1,part_id=0,phrases=[])]},'A')
        ts=tables(p,'next_written_attack')
        self.assertEqual(len(ts),2)
        self.assertEqual({len(t['condition']['previous_known_features']) for t in ts},{19,21})

    def test_beat_whammy_is_not_counted_once_per_chord_note(self):
        a=row(0,0);b=dict(row(0,0,45),occurrence='0:1:0:0:1',string=1)
        s=song(1,[a,b]);shape=dict(valid=True,peak_semitones='1')
        s['tracks'][0]['technique_values']=[dict(occurrence=x['occurrence'],whammy=shape) for x in [a,b]]
        p=build_relationship_profile({'songs':[s]}, {},'A')
        ts=tables(p,'mechanical_shape_given_context')
        self.assertEqual(sum(t['eligible_count'] for t in ts),1)
        self.assertEqual(p['coverage']['shared_whammy_note_records_deduplicated'],1)
        self.assertEqual(ts[0]['outcomes'][0]['outcome']['source_unit'],'beat-scoped whammy')


if __name__=='__main__':unittest.main()
