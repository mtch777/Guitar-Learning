import copy
import unittest
from artist_profiles import connected_families,fit,predict,evaluate,describe,observations,FEATURES


def event(song=1,family='a',partition='development',labels=(),context='short',flagged=False):
    return dict(song_id=song,family=family,partition=partition,labels=list(labels),context=context,flagged=flagged,artist='artist')


class ProfileTests(unittest.TestCase):
    def test_heldout_changes_cannot_change_fit(self):
        rows=[event(labels=['bend']),event(2,'b','held_out')]
        a=fit(rows);rows[-1]['labels']=['slide'];rows[-1]['context']='unknown';rows[-1]['song_id']=99
        self.assertEqual(a,fit(rows))
        self.assertEqual(a['training_songs'],[1])

    def test_connected_duplicate_cannot_cross_split(self):
        songs=[dict(song_id=1,candidate_work_family='a',notation_hash='same',provisional_partition='development'),
               dict(song_id=2,candidate_work_family='b',notation_hash='same',provisional_partition='held_out')]
        with self.assertRaises(ValueError):connected_families(songs)
        songs[1]['provisional_partition']='development'
        self.assertEqual(len(set(connected_families(songs).values())),1)

    def test_family_weight_does_not_reward_duplicate_revision(self):
        rows=[event(labels=['bend'])]*20+[event(2,'b')]*2
        model=fit(rows);rows += [event(3,'a',labels=['bend'])]*20
        revised=fit(rows)
        a=next(t for t in model['tables'] if t['context']=='*')
        b=next(t for t in revised['tables'] if t['context']=='*')
        self.assertEqual(a,b)
        self.assertEqual(a['features']['bend'],'1')
        self.assertEqual(a['total'],'2')
        self.assertEqual(predict(model,rows[0]),predict(revised,rows[0]))

    def test_flagged_and_unknown_artists_are_not_silent_training_data(self):
        model=fit([event(labels=['bend']),event(2,'b',flagged=True,labels=['slide'])])
        self.assertEqual(model['training_songs'],[1])
        sample=event();sample['artist']='unseen'
        self.assertEqual(predict(model,sample),(None,True))

    def test_unseen_context_backs_off_and_scores_finite(self):
        rows=[event(labels=['bend']),event(2,'b','held_out',labels=['slide'],context='long')]
        model=fit(rows);snapshot=copy.deepcopy(model)
        probabilities,backoff=predict(model,rows[-1])
        self.assertTrue(backoff);self.assertTrue(all(0<p<1 for p in probabilities.values()))
        report=evaluate(model,rows)
        self.assertEqual(report['held_out_events'],1)
        self.assertEqual(model,snapshot)
        self.assertEqual(report['metrics']['conditional'],report['metrics']['unconditional'])

    def test_heldout_same_family_is_rejected(self):
        rows=[event(),event(2,'a','held_out')]
        with self.assertRaises(ValueError):evaluate(fit(rows),rows)

    def test_descriptive_denominators_are_explicit(self):
        r=describe([event(labels=['bend'])]*9+[event(2,'b')])['artists'][0]['features']['bend']
        self.assertEqual(r['pooled'],.9);self.assertEqual(r['equal_song'],.5)
        self.assertEqual(r['songs_with_annotation'],1)

    def test_source_observations_are_order_independent_and_keep_beat_vibrato(self):
        a=dict(occurrence='a',midi=40,fret=0,duration_q='1',onset_q='0',bar_offset_q='0',
               tie_destination=False,effects=['vibrato'],raw_note={},raw_beat_effects={'vibrato':True})
        b=dict(a,occurrence='b',midi=47,fret=2,duration_q='3')
        track=dict(part_id=0,guitar_or_bass=True,temporal_relationships_eligible=True,rows=[a,b])
        song=dict(song_id=1,candidate_work_family='a',notation_hash='a',provisional_partition='development',
                  ai_generated=False,is_junk=False,artist='artist',tracks=[track])
        report=dict(songs=[song]);first=observations(report)[0][0]
        self.assertIn('finger_vibrato',first['labels'])
        self.assertNotIn('pedal_call',first['known'])
        track['rows'].reverse();second=observations(report)[0][0]
        self.assertEqual(first['context'],second['context'])
        known=observations(report,pedal_coverage={(1,0)})[0][0]
        self.assertIn('pedal_call',known['known'])
        self.assertNotIn('pedal_call',known['labels'])

    def test_unknown_pedal_data_does_not_train_absence(self):
        e=event();e['known']=[f for f in FEATURES if not f.startswith('pedal_')]
        model=fit([e]);probs,_=predict(model,e)
        self.assertIsNone(probs['pedal_call'])
        self.assertIsNone(describe([e])['artists'][0]['features']['pedal_call']['pooled'])

    def test_all_dead_attacks_are_retained_but_pitch_classes_are_unknown(self):
        note=dict(occurrence='dead',midi=None,fret=0,string=0,duration_q='1',onset_q='0',bar_offset_q='0',
                  tie_destination=False,effects=['dead'],raw_note={'dead':True},raw_beat_effects={})
        track=dict(part_id=0,guitar_or_bass=True,temporal_relationships_eligible=True,rows=[note])
        song=dict(song_id=1,candidate_work_family='a',notation_hash='a',provisional_partition='development',
                  ai_generated=False,is_junk=False,artist='artist',tracks=[track])
        events,_=observations(dict(songs=[song]))
        self.assertEqual(len(events),1);self.assertIn('dead',events[0]['labels'])
        self.assertNotIn('power_chord',events[0]['known'])
        self.assertIn('unknown',events[0]['context'])

    def test_unconditional_prediction_is_not_a_backoff(self):
        data=[event(),event(2,'b','held_out',context='new')]
        report=evaluate(fit(data),data)
        self.assertEqual(report['context_backoff_events'],{'conditional':1})


if __name__=='__main__':unittest.main()
