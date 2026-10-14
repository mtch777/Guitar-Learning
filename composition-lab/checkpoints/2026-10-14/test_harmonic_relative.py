import unittest
from fractions import Fraction
from harmonic_relative import Chord, analyze_note, transform_melody, analyze_timed_melody, transform_timed_melody

class HarmonyRelativeTests(unittest.TestCase):
    def setUp(self):
        self.minor_ii = Chord(50,((1,0),(3,3),(5,7)))  # D F A
        self.major_iv = Chord(53,((1,0),(3,4),(5,7))) # F A C

    def test_minor_two_to_major_four_roles(self):
        self.assertEqual(transform_melody([50,53,57],self.minor_ii,self.major_iv),[53,57,60])
    def test_octaves_preserved_relative_to_root(self):
        self.assertEqual(transform_melody([62,65,69],self.minor_ii,self.major_iv),[65,69,72])
    def test_nonchord_tone_is_not_rounded(self):
        # G is not in D minor triad; retains +5 relative to new F root -> Bb.
        self.assertIsNone(analyze_note(55,self.minor_ii).degree)
        self.assertEqual(transform_melody([55],self.minor_ii,self.major_iv),[58])
    def test_same_quality_transposition(self):
        major_d=Chord(50,((1,0),(3,4),(5,7)))
        self.assertEqual(transform_melody([50,54,57],major_d,self.major_iv),[53,57,60])
    def test_missing_extensions_do_not_invent_quality(self):
        extended=Chord(50,((1,0),(3,3),(5,7),(7,10),(9,14)))
        self.assertEqual(transform_melody([64],extended,self.major_iv),[67])
        with self.assertRaises(ValueError):transform_melody([64],extended,self.major_iv,missing='error')
    def test_ambiguous_chord_degrees_are_not_guessed(self):
        duplicate_pitch=Chord(50,((1,0),(8,12)))
        self.assertIsNone(analyze_note(62,duplicate_pitch).degree)
    def test_voice_and_rhythm_untouched(self):
        src=[{'start':'0','end':'3/2','chord':self.minor_ii},
             {'start':'3/2','end':'4','chord':self.major_iv}]
        tgt=[{'start':'0','end':'3/2','chord':self.major_iv},
             {'start':'3/2','end':'4','chord':self.minor_ii}]
        events=[{'onset':Fraction(0),'duration':Fraction(1,3),'voice':2,'pitches':[50,53,57]},
                {'onset':Fraction(3,2),'duration':Fraction(1,2),'voice':1,'pitches':[53,57,60]},
                {'onset':Fraction(2),'duration':Fraction(1,2),'voice':1,'pitches':[]}]
        out=transform_timed_melody(analyze_timed_melody(events,src),tgt)
        self.assertEqual([x['pitches'] for x in out],[[53,57,60],[50,53,57],[]])
        self.assertEqual([(x['onset'],x['duration'],x['voice']) for x in out],
                         [(x['onset'],x['duration'],x['voice']) for x in events])
    def test_undefined_harmony_kept_unclassified(self):
        ev=[{'onset':2,'pitches':[61]}]
        self.assertIsNone(analyze_timed_melody(ev,[])[0]['relative_notes'])
    def test_overlapping_harmony_fails_loudly(self):
        spans=[{'start':0,'end':2,'chord':self.minor_ii},{'start':1,'end':3,'chord':self.major_iv}]
        with self.assertRaises(ValueError):analyze_timed_melody([{'onset':1,'pitches':[53]}],spans)

if __name__=='__main__':unittest.main()