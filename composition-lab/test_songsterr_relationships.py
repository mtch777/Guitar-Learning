"""Adversarial source-notation tests, independent of private music files."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('relationships',Path(__file__).parent/'songsterr_automation/songsterr_api/analyze_relationships.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


def beat(*notes, duration=(1,4), **fields):
    return dict(duration=list(duration),notes=list(notes),**fields)


def note(string=0,fret=0,**fields):
    return dict(string=string,fret=fret,**fields)


def part(measures):
    return dict(partId=3,instrumentId=30,tuning=[40,45,50],measures=measures)


def measure(*beats, marker=None, signature=(4,4)):
    return dict(signature=list(signature),marker=marker,voices=[dict(beats=list(beats))])


class RelationshipsTests(unittest.TestCase):
    def test_exact_timing_grace_and_repeated_section_instances(self):
        p=part([measure(beat(note(),duration=(1,32),graceNote=True),beat(note(),duration=(1,12)),marker='Verse',signature=(1,4)),
                measure(beat(note(),duration=(3,8)),marker='Verse',signature=(3,8))])
        rows,grace,sections,warnings=a.occurrences(p)
        self.assertEqual([r['onset_q'] for r in rows],['0','1'])
        self.assertEqual([r['duration_q'] for r in rows],['1/3','3/2'])
        self.assertEqual([r['section_start'] for r in rows],[1,2])
        self.assertEqual(sections[-1]['end_q'],'5/2')
        self.assertEqual(len(grace),1);self.assertEqual(warnings,[])

    def test_hopo_tie_chain_and_open_string_direction(self):
        p=part([measure(beat(note(hp=True)),beat(note(tie=True)),beat(note(fret=5,hp=True)),beat(note()))])
        t=a.track_analysis(p);pairs=t['hopo_transition_candidates']
        self.assertEqual([(x['direction'],x['context']) for x in pairs],[('hammer_on','from_open'),('pull_off','to_open')])
        self.assertEqual(t['summary']['attacks'],3)
        self.assertEqual(t['summary']['marker_shares']['hp'],dict(numerator=2,denominator=4,percent=50))

    def test_hopo_does_not_bridge_rest_grace_or_unknown_dead_pitch(self):
        cases=[([beat(note(hp=True)),beat(dict(rest=True)),beat(note(fret=5))],'gap_or_overlap'),
               ([beat(note(hp=True)),beat(note(fret=3),duration=(1,32),graceNote=True),beat(note(fret=5))],'grace_at_transition'),
               ([beat(note(hp=True,dead=True)),beat(note(fret=5))],'unknown_pitch')]
        for beats,reason in cases:
            with self.subTest(reason=reason):
                t=a.track_analysis(part([measure(*beats)]))
                self.assertEqual(t['hopo_transition_candidates'],[])
                self.assertEqual(t['unresolved_hp'][0]['reason'],reason)

    def test_cross_voice_coattacks_and_half_step_near_miss(self):
        m=dict(signature=[4,4],voices=[dict(beats=[beat(note(fret=6)),beat(note(fret=7))]),
                                     dict(beats=[beat(note(string=1)),beat(note(string=1))])])
        t=a.track_analysis(part([m]))
        self.assertEqual([g['labels'] for g in t['coattack_groups']],[['double_stop','close_interval_texture'],['double_stop']])
        self.assertEqual(t['counterexamples'][0]['written_semitones'],2)
        # Tied continuations are not new attacks or coattack dyads.
        m['voices'][1]['beats'][0]['notes'][0]['tie']=True
        self.assertNotIn('close_interval_texture',[k for g in a.track_analysis(part([m]))['coattack_groups'] for k in g['labels']])

    def test_power_and_extended_power_use_bass_root_and_only_one_color(self):
        t=a.track_analysis(part([measure(beat(note(),note(string=1,fret=2)),
                                        beat(note(),note(string=1,fret=2),note(string=2,fret=1)),
                                        beat(note(fret=7),note(string=1,fret=7)))]))
        labels=[g['labels'] for g in t['coattack_groups']]
        self.assertIn('power_chord',labels[0]);self.assertIn('extended_power_chord',labels[1])
        self.assertNotIn('power_chord',labels[2])

    def test_conditionals_beat_marker_inheritance_and_monophonic_context(self):
        t=a.track_analysis(part([measure(beat(note(bend={'tone':50}),palmMute=True),beat(note(fret=2),duration=(1,2)))]))
        v=t['summary']['conditional']['bend']
        self.assertEqual(v['marked']['mean_written_duration_q'],'1')
        self.assertEqual(v['unmarked']['mean_written_duration_q'],'2')
        self.assertEqual(v['marked']['next_same_voice_monophonic_interval'],{'2':1})
        self.assertEqual(t['summary']['marker_pairs']['bend+palmMute'],1)
        self.assertEqual(t['sections'][0]['summary']['note_segments'],2)

    def test_raw_bend_curve_values_and_conditional_marker_denominators(self):
        curve=dict(points=[dict(position=0,tone=0),dict(position=30,tone=50),dict(position=60,tone=25)])
        t=a.track_analysis(part([measure(beat(note(bend=curve),palmMute=True,velocity=70),beat(note(fret=2)))]))
        hist=t['summary']['marker_value_histograms']
        self.assertEqual(hist['bend_peak_semitones'],{'1':1})
        self.assertEqual(hist['bend_first_peak_fraction_of_written_segment'],{'1/2':1})
        self.assertEqual(hist['bend_final_semitones'],{'1/2':1})
        self.assertEqual(hist['explicit_velocity'],{'70':1})
        shares=t['summary']['conditional']['bend']['marked']['other_marker_shares']
        self.assertEqual(shares['palmMute'],dict(numerator=1,denominator=1,percent=100))

    def test_missing_duration_reports_unrecoverable_onset_and_overflow(self):
        p=part([measure(dict(notes=[note()]),beat(note())),measure(beat(note(),duration=(2,1)))])
        rows,_,_,warnings=a.occurrences(p)
        self.assertEqual(len(rows),1)
        self.assertEqual({w['reason'] for w in warnings},{'missing_duration','voice_overflows_bar'})
        self.assertEqual(rows[0]['onset_q'],'4')

    def test_ghost_dynamics_inherit_without_changing_raw_or_local_counts(self):
        p=part([measure(beat(note(),velocity='p'),beat(note(ghost=True))),
                measure(beat(note(ghost=True)))])
        t=a.track_analysis(p)
        self.assertEqual(t['summary']['marker_value_histograms']['explicit_velocity'],{'p':1})
        self.assertEqual(t['summary']['marker_value_histograms']['effective_written_dynamic'],{'p':3})
        marked=t['summary']['conditional']['ghost']['marked']
        self.assertEqual(marked['dynamic_markings'],{'p':2})
        self.assertEqual(marked['dynamic_unknown_segments'],0)
        self.assertEqual(t['rows'][2]['dynamic']['provenance'],'inherited_explicit')
        self.assertNotIn('velocity',t['rows'][2]['raw_note'])
        self.assertNotIn('velocity',t['rows'][2]['raw_beat_effects'])

    def test_invalid_timing_preserves_markers_but_quarantines_relationships(self):
        t=a.track_analysis(part([measure(beat(note(hp=True),note(string=1,fret=2),duration=(2,1)),beat(note(fret=5)))]))
        self.assertFalse(t['temporal_relationships_eligible'])
        self.assertEqual(t['summary']['marker_shares']['hp']['numerator'],1)
        self.assertEqual(t['coattack_groups'],[])
        self.assertEqual(t['hopo_transition_candidates'],[])
        self.assertEqual(t['pedal_candidates'],[])

    def test_catalog_flags_families_and_private_evidence_are_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for sid,title,ai,junk in [(1,'Example (ver 1)',False,False),(2,'Example (ver 2)',True,False),(3,'Other',False,True)]:
                folder=root/str(sid);folder.mkdir()
                (folder/'metadata.json').write_text(json.dumps(dict(songId=sid,revisionId=20+sid,title=title,artist='Fixture',aiGenerated=ai,isJunk=junk)))
                (folder/'track-0.json').write_text(json.dumps(part([measure(beat(note(bend={'tone':50})))])))
            report=a.analyze(root);public=a.aggregate(report)
            self.assertEqual(report['candidate_family_groups'],[[1,2]])
            self.assertEqual(report['exact_notation_duplicate_groups'],[[1,2,3]])
            self.assertEqual(report['songs'][0]['provisional_partition'],report['songs'][1]['provisional_partition'])
            self.assertEqual(report['songs'][0]['provisional_partition'],report['songs'][2]['provisional_partition'])
            self.assertEqual(public['cohorts']['all_entries']['note_segments'],3)
            self.assertEqual(public['cohorts']['neither_ai_nor_junk_flagged']['note_segments'],1)
            text=json.dumps(public)
            for field in ['raw_note','title','occurrence','artist','revision_id']:
                self.assertNotIn('"'+field+'"',text)

    def test_private_evidence_rejects_occurrence_corruption(self):
        spec=importlib.util.spec_from_file_location('evidence',Path(__file__).parent/'songsterr_automation/songsterr_api/build_analysis_evidence.py')
        evidence=importlib.util.module_from_spec(spec);spec.loader.exec_module(evidence)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'1';folder.mkdir()
            (folder/'metadata.json').write_text(json.dumps(dict(songId=1,revisionId=2,title='Fixture',artist='Fixture',aiGenerated=False,isJunk=False)))
            (folder/'track-3.json').write_text(json.dumps(part([measure(beat(note(bend={'tone':50})),beat(note(fret=2)))])))
            report=a.analyze(root);pack=evidence.build(report,root)
            self.assertGreater(pack['raw_occurrences_verified'],0)
            self.assertIsNotNone(pack['examples'][0]['unmarked_duration_matched_control'])
            track=report['songs'][0]['tracks'][0];row=track['rows'][0]
            row['raw_note']={'fret':99}
            with self.assertRaises(ValueError):evidence.check_occurrence(root,1,track,row)


if __name__=='__main__':unittest.main()
