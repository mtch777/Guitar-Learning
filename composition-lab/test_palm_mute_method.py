import tempfile,unittest,copy
from pathlib import Path
from fractions import Fraction as F
from artist_profiles import fit
from test_learned_performance import fixture
from gp_author import write_gp
from exact_score import extract_score
from palm_mute_method import apply,observations
from test_performance_opportunities import report

def model():
    events=[dict(artist='Artist',song_id=1,family='f',partition='development',flagged=False,context='training',known=['palm_mute'],labels=['palm_mute'])]
    m=fit(events,alpha=F(1,10**9));m.update(schema='eligible-palm-mute-v1',source_training_sha256='fixture');return m

class PalmMuteTests(unittest.TestCase):
    def test_zero_and_full_reference_invariance(self):
        score,_,_=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp')
            zero=apply(p/'base.gp',p/'zero.gp',None,'Artist',0);self.assertTrue(zero['byte_identity'])
            a=apply(p/'base.gp',p/'a.gp',model(),'Artist',100)
            b=apply(p/'a.gp',p/'b.gp',model(),'Artist',100)
            self.assertEqual((p/'a.gp').read_bytes(),(p/'b.gp').read_bytes());self.assertTrue(a['locked_xml_verified'])
            self.assertTrue(all(d['proposed_selected'] for d in a['decisions']))

    def test_chord_uses_one_shared_decision(self):
        score,_,_=fixture();score['tracks'][0]['tunings']=[[40,45]]
        for m in score['tracks'][0]['measures']:
            for e in m['voices'][0]:e['notes'].append(dict(midi=45,string=1,fret=0,tie=None,technique_tags=[]))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp');audit=apply(p/'base.gp',p/'out.gp',model(),'Artist',100)
            self.assertEqual(len(audit['decisions']),8)
            for m in extract_score(p/'out.gp')['tracks'][0]['measures']:
                for e in m['voices'][0]:self.assertTrue(all('PalmMuted' in n['property_names'] for n in e['notes']))

    def test_denominator_and_ties(self):
        r=report();track=r['songs'][0]['tracks'][0]
        for n in track['rows']:n['raw_beat_effects']['palmMute']=True
        events=observations(r);self.assertEqual(len(events),4);self.assertTrue(all(e['labels']==['palm_mute'] for e in events))
        track['sustain_relationships']=dict(chains=[dict(members=['0','1'])])
        self.assertEqual(len(observations(r)),2)

    def test_mixed_source_group_is_not_all_muted_label(self):
        r=report();track=r['songs'][0]['tracks'][0];a=track['rows'][0];a['raw_beat_effects']['palmMute']=True
        b=copy.deepcopy(a);b.update(occurrence='extra',string=1,midi=45);b['raw_beat_effects']={};track['rows'].append(b)
        events,inventory=observations(r,True);self.assertEqual(inventory['development:mixed'],1);self.assertEqual(len(events),3)

if __name__=='__main__':unittest.main()
