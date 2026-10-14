import unittest
from fractions import Fraction
from harmonic_gp_bridge import annotate_score,reharmonize_score


def score_fixture():
    def note(n):return {'midi':n,'string':2,'fret':4,'note_id':str(n)}
    def beat(t,notes):return {'onset_q':str(t),'duration_q':'1/3','notes':[note(n) for n in notes]}
    return {'tracks':[{'index':0,'measures':[{'voices':[
        [beat(0,[50,53,57]),beat(Fraction(1,3),[62])],
        [beat(0,[55]),beat(Fraction(1,3),[])]
    ]}]}]}

SOURCE={'0':[{'start':'0','end':'2','root':50,'degrees':[[1,0],[3,3],[5,7]]}]}
TARGET={'0':[{'start':'0','end':'2','root':53,'degrees':[[1,0],[3,4],[5,7]]}]}

class BridgeTests(unittest.TestCase):
    def test_preserve_original_events_and_polyphony(self):
        original=score_fixture()
        x=annotate_score(original,SOURCE)
        self.assertNotIn('harmonic_relation',original['tracks'][0]['measures'][0]['voices'][0][0]['notes'][0])
        self.assertEqual(x['harmonic_annotation_summary']['pitched'],5)
        self.assertEqual(x['harmonic_annotation_summary']['chord_tones'],4)
        self.assertEqual(x['tracks'][0]['measures'][0]['voices'][0][0]['notes'][1]['harmonic_relation']['degree'],3)
    def test_reharmonize_preserves_voices_rhythm_and_chromatic(self):
        x=annotate_score(score_fixture(),SOURCE)
        y=reharmonize_score(x,SOURCE,TARGET)
        voices=y['tracks'][0]['measures'][0]['voices']
        self.assertEqual([n['midi'] for n in voices[0][0]['notes']],[53,57,60])
        self.assertEqual(voices[0][1]['notes'][0]['midi'],65)
        self.assertEqual(voices[1][0]['notes'][0]['midi'],58)
        self.assertEqual(voices[1][1]['notes'],[])
        self.assertEqual(voices[0][1]['onset_q'],'1/3')
        self.assertIsNone(voices[0][0]['notes'][0]['string'])
        self.assertEqual(voices[0][0]['notes'][0]['original_midi'],50)
    def test_missing_harmony_does_not_guess(self):
        x=annotate_score(score_fixture(),{})
        self.assertNotIn('harmonic_relation',x['tracks'][0]['measures'][0]['voices'][0][0]['notes'][0])
    def test_missing_target_harmony_fails(self):
        x=annotate_score(score_fixture(),SOURCE)
        with self.assertRaises(ValueError):reharmonize_score(x,SOURCE,{})
    def test_overlapping_chords_rejected(self):
        bad={'0':SOURCE['0']+[{'start':1,'end':3,'root':53,'degrees':[[1,0]]}]}
        with self.assertRaises(ValueError):annotate_score(score_fixture(),bad)

if __name__=='__main__':unittest.main()