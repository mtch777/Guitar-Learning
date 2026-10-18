import unittest,copy
from performance_opportunities import train,opportunities
from artist_profiles import predict

def report():
    rows=[]
    for i,fret in enumerate((0,5,0,7)):
        rows.append(dict(occurrence=str(i),voice=0,string=0,fret=fret,midi=40+fret,onset_q=str(i),duration_q='1',
            bar_offset_q=str(i),bar=1,section_start=1,tie_destination=False,effects=['hp'] if i==0 else [],
            raw_note=dict(hp=True) if i==0 else {},raw_beat_effects={}))
    return dict(songs=[dict(song_id=1,artist='Artist',provisional_partition='development',ai_generated=False,is_junk=False,
        tracks=[dict(guitar_or_bass=True,temporal_relationships_eligible=True,part_id=0,rows=rows,
            hopo_transition_candidates=[dict(origin='0',destination='1')])])])

class OpportunityTests(unittest.TestCase):
    def test_open_hammer_denominator_is_eligible_pairs(self):
        model,events=train(report());eligible=[e for e in events if e['known']==['hammer_on_from_open']]
        self.assertEqual(len(eligible),2);self.assertEqual(sum(bool(e['labels']) for e in eligible),1)
        probs,_=predict(model,dict(artist='Artist',context='not-seen'))
        self.assertAlmostEqual(probs['hammer_on_from_open'],.5)

    def test_dead_harmonic_and_tied_not_opportunities(self):
        r=report();rows=r['songs'][0]['tracks'][0]['rows']
        rows[1]['raw_note']['harmonic']=True;rows[3]['raw_note']['dead']=True
        events,_=opportunities(r)
        self.assertFalse(events)

    def test_heldout_changes_cannot_change_training(self):
        r=report();held=copy.deepcopy(r['songs'][0]);held.update(song_id=2,provisional_partition='held_out');r['songs'].append(held)
        a,_=train(r);held['tracks'][0]['rows'][0]['effects']=[];held['tracks'][0]['hopo_transition_candidates']=[]
        b,_=train(r);self.assertEqual(a,b)

if __name__=='__main__':unittest.main()
