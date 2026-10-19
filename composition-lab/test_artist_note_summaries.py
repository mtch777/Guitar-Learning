from copy import deepcopy
import unittest

from artist_note_summaries import summarize_notes,marker_state


def row(i,effects=(),duration='1',tied=False,pitch=40,**extra):
    result=dict(occurrence=f'0:1:0:{i}:0',onset_q=str(i),duration_q=duration,
                tie_destination=tied,midi=pitch,section_start=1,effects=list(effects))
    result.update(extra)
    return result


def song(sid,rows,partition='development',family=None):
    return dict(song_id=sid,artist='A',provisional_partition=partition,
                candidate_work_family=family or str(sid),ai_generated=False,is_junk=False,
                tracks=[dict(part_id=0,guitar_or_bass=True,temporal_relationships_eligible=True,
                             rows=rows,grace_rows=[])])


class NoteSummaryTests(unittest.TestCase):
    def test_binary_float_duration_is_not_silently_made_exact(self):
        with self.assertRaises(ValueError):summarize_notes({'songs':[song(1,[row(0,duration=.1)])]},'A')

    def test_one_bent_note_in_dyad_is_half_notes_not_all_group(self):
        rows=[row(0,['bend']),dict(row(1),onset_q='0')]
        p=summarize_notes({'songs':[song(1,rows)]},'A')
        bend=p['artist_aggregate']['bend']
        self.assertEqual((bend['fresh_note_attacks']['known'],bend['fresh_note_attacks']['positive']),(2,1))
        self.assertEqual(bend['fresh_note_attacks']['pooled_rate'],.5)
        # Independent onset-group perspective is one marked group out of one.
        self.assertEqual(len({r['onset_q'] for r in rows}),1)
        self.assertTrue(any('bend' in r['effects'] for r in rows))

    def test_three_tied_segments_are_one_attack_and_exact_duration_mass(self):
        rows=[row(0,['bend'],duration='1/2'),row(1,duration='1/4',tied=True),row(2,duration='1/4',tied=True)]
        p=summarize_notes({'songs':[song(1,rows)]},'A');m=p['artist_aggregate']['bend']
        self.assertEqual((m['written_regular_segments']['known'],m['fresh_note_attacks']['known']),(3,1))
        self.assertEqual(m['fresh_note_attacks']['pooled_rate'],1)
        self.assertEqual(m['written_note_duration_mass']['known_q'],'1')
        self.assertEqual(m['written_note_duration_mass']['positive_q'],'1/2')

    def test_unknown_coverage_is_not_false_and_unknown_pitch_keeps_marker(self):
        unknown=row(0);unknown.pop('effects')
        marked=row(1,['bend'],pitch=None)
        p=summarize_notes({'songs':[song(1,[unknown,marked])]},'A')
        m=p['artist_aggregate']['bend']['written_regular_segments']
        self.assertEqual((m['known'],m['positive'],m['unknown']),(1,1,1))
        self.assertEqual(p['coverage']['unknown_base_pitch_segments'],1)

    def test_covered_empty_effects_are_known_negatives(self):
        p=summarize_notes({'songs':[song(1,[row(0)])]},'A')
        self.assertTrue(all(m['written_regular_segments']['known']==1 for m in p['artist_aggregate'].values()))
        self.assertTrue(all(m['written_regular_segments']['positive']==0 for m in p['artist_aggregate'].values()))

    def test_null_marker_is_unknown_despite_empty_effect_list(self):
        self.assertEqual(marker_state(row(0,raw_note={'bend':None}),'bend'),(None,'explicit_null_marker'))

    def test_finger_vibrato_requires_note_scope_and_does_not_absorb_arm(self):
        arm=row(0,['vibrato'],raw_note={},raw_beat_effects={'vibrato':True})
        finger=row(1,['leftHandVibrato'],raw_note={'leftHandVibrato':True},raw_beat_effects={})
        uncertain=row(2,['vibrato'])
        p=summarize_notes({'songs':[song(1,[arm,finger,uncertain])]},'A')
        m=p['artist_aggregate']['finger_vibrato']['written_regular_segments']
        self.assertEqual((m['known'],m['positive'],m['unknown']),(2,1,1))

    def test_shared_beat_marker_preserves_provenance_without_chord_or_pedal_labels(self):
        a=row(0,['palmMute'],raw_beat_effects={'palmMute':True})
        b=dict(row(1,['palmMute'],raw_beat_effects={'palmMute':True}),onset_q='0')
        p=summarize_notes({'songs':[song(1,[a,b])]},'A')
        self.assertEqual(p['artist_aggregate']['palm_mute']['positive_evidence_scopes'],{'beat':2})
        self.assertNotIn('power_chord',p['artist_aggregate']);self.assertNotIn('pedal_call',p['artist_aggregate'])

    def test_grace_excluded_and_missing_tie_status_not_fresh_attack(self):
        a=row(0);a.pop('tie_destination')
        s=song(1,[a]);s['tracks'][0]['grace_rows']=[row(9,['bend'])]
        p=summarize_notes({'songs':[s]},'A')
        self.assertEqual(p['coverage']['grace_occurrences_excluded'],1)
        self.assertEqual(p['artist_aggregate']['bend']['fresh_note_attacks']['known'],0)
        self.assertIsNone(p['artist_aggregate']['bend']['fresh_note_attacks']['pooled_rate'])

    def test_polyphonic_mass_adds_notes_not_occupied_time(self):
        p=summarize_notes({'songs':[song(1,[row(0,duration='2'),dict(row(1,duration='2'),onset_q='0')])]},'A')
        self.assertEqual(p['artist_aggregate']['bend']['written_note_duration_mass']['known_q'],'4')

    def test_song_family_prevalence_and_equal_weights(self):
        a=song(1,[row(0,['bend'])],family='same');b=song(2,[row(0)],family='same')
        c=song(3,[row(0)],family='other')
        p=summarize_notes({'songs':[a,b,c]},'A');m=p['artist_aggregate']['bend']['written_regular_segments']
        self.assertAlmostEqual(m['equal_song_rate'],1/3);self.assertEqual(m['family_balanced_rate'],.25)
        self.assertEqual((m['songs_with_annotation'],m['eligible_songs'],m['families_with_annotation']),(1,3,1))
        self.assertEqual((m['minimum_song_rate'],m['maximum_song_rate']),(0,1))

    def test_heldout_changes_do_not_modify_development_inventory(self):
        report={'songs':[song(1,[row(0)]),song(2,[row(0,['bend'])],'held_out')]}
        before=summarize_notes(report,'A');report['songs'][1]['tracks'][0]['rows'][0]['effects']=['dead']
        self.assertEqual(before,summarize_notes(report,'A'))
        held=summarize_notes(report,'A',partition='held_out')
        self.assertEqual(held['source_songs'],[2])
        self.assertEqual(held['artist_aggregate']['dead']['written_regular_segments']['positive'],1)

    def test_split_timing_and_duplicate_guards(self):
        report={'songs':[song(1,[row(0)],family='same'),song(2,[row(0)],'held_out',family='same')]}
        with self.assertRaises(ValueError):summarize_notes(report,'A')
        s=song(1,[row(0)]);s['tracks'][0]['temporal_relationships_eligible']=False
        p=summarize_notes({'songs':[s]},'A');self.assertEqual(p['coverage']['temporal_ineligible_tracks_excluded'],1)
        s=song(1,[row(0),row(0)])
        with self.assertRaises(ValueError):summarize_notes({'songs':[s]},'A')


if __name__=='__main__':unittest.main()
