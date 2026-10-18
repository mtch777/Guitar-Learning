import unittest
from pedal_register import analyze_register
from test_pedal_regions import rows


class RegisterTests(unittest.TestCase):
    def test_single_answer_with_many_notes_is_not_repeated_exchange(self):
        self.assertFalse(analyze_register(rows([[28],[28],[55],[59],[28]]))['accepted'])

    def test_changing_low_anchor_can_continue_same_register_exchange(self):
        r=analyze_register(rows([[35,42],[35,42],[58,59],[32,39],[32,39],[70,71],[32,39]]))
        self.assertTrue(r['accepted'])
        self.assertEqual(r['anchor_pitches'],[32,35,39,42])
        self.assertEqual(len(r['cycles']),2)

    def test_high_coattack_does_not_become_an_anchor(self):
        r=analyze_register(rows([[57,71],[60],[64],[57]]*3))
        self.assertEqual(r['anchor_pitches'],[57])
        self.assertEqual(r['roles']['0:0'],'call')
        self.assertEqual(r['roles']['0:1'],'response')
        self.assertIn('0:1',r['cycles'][0]['response_members'])

    def test_unknown_interrupts_and_tie_does_not_count_as_return(self):
        self.assertFalse(analyze_register(rows([[40],[55],[None],[40],[59],[40]]))['accepted'])
        data=rows([[40],[55],[40],[59],[40]])
        data[2]['tie_destination']=True
        self.assertFalse(analyze_register(data)['accepted'])

    def test_fixed_chord_arpeggio_and_chord_only_playing_abstain(self):
        self.assertFalse(analyze_register(rows([[40],[44],[47],[44]]*3))['accepted'])
        self.assertFalse(analyze_register(rows([[40,47,52],[42,49,54]]*4))['accepted'])

    def test_transposition_preserves_source_membership(self):
        data=rows([[40],[52],[40],[55],[40]])
        first=analyze_register(data)
        for n in data:n['midi']-=17
        other=analyze_register(data)
        self.assertEqual(first['roles'],other['roles'])
        self.assertEqual([p-17 for p in first['anchor_pitches']],other['anchor_pitches'])

    def test_final_return_burst_and_trailing_answer_are_not_discarded(self):
        data=rows([[40],[52],[40],[55],[40],[40],[40],[59]])
        r=analyze_register(data)
        self.assertEqual(r['roles']['6:0'],'call')
        self.assertEqual(r['roles']['7:0'],'response')


if __name__=='__main__':unittest.main()
