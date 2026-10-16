import unittest
from bend_analysis import bend_shape, summary, tie_chains, chain_summary, conditional_tables


def row(i, onset, duration, bend=None, origin=False, destination=False, voice=0):
    return dict(occurrence=str(i), onset_q=onset, duration_q=duration, bend=bend,
                tie_origin=origin, tie_destination=destination, voice=voice,
                string=1, midi=60, vibrato=False)


class BendAnalysisTests(unittest.TestCase):
    def test_curve_units_and_release(self):
        b = bend_shape('<Note><Properties><Property name="Bended"><Enable/></Property>'
                       '<Property name="BendMiddleValue"><Float>100</Float></Property>'
                       '</Properties></Note>')
        self.assertEqual(b['peak_semitones'], '2')
        self.assertEqual(b['shape'], 'rise-and-fall')
        self.assertFalse(b['prebent'])
        self.assertEqual(b['points'][-1]['semitones'], '0')

    def test_disabled_and_unmarked_not_bends(self):
        self.assertIsNone(bend_shape('<Note><Properties><Property name="Bended"/></Properties></Note>'))
        self.assertIsNone(bend_shape('<Note/>'))

    def test_bend_on_tied_destination_counts_sustain_not_new_attack(self):
        bend = {'peak_semitones':'2','shape':'rise','prebent':False}
        rows = [row(1,'0','1',origin=True), row(2,'1','3/2',bend,destination=True)]
        s = summary(rows)
        self.assertEqual(s['bend_attack_rate']['numerator'],0)
        self.assertEqual(s['bend_occurrence_rate']['numerator'],1)
        chains, unresolved, dangling = tie_chains(rows)
        self.assertEqual((len(chains), unresolved, dangling),(1,[],0))
        c = chain_summary(chains)
        self.assertEqual(c['bend_anywhere_in_sustain_rate']['percent'],100)
        self.assertEqual(c['median_bent_sustain_q'],'5/2')

    def test_ties_do_not_cross_voice_or_gap(self):
        rows = [row(1,'0','1',origin=True), row(2,'1','1',destination=True,voice=1),
                row(3,'2','1',destination=True)]
        chains, unresolved, dangling = tie_chains(rows)
        self.assertEqual(len(chains),3)
        self.assertEqual(unresolved,['2','3'])
        self.assertEqual(dangling,1)

    def test_empty_denominators_are_unknown(self):
        self.assertIsNone(summary([])['bend_attack_rate']['percent'])
        self.assertIsNone(chain_summary([])['median_bent_sustain_q'])

    def test_conditional_denominator_includes_nonbends(self):
        rows = [dict(row(1,'0','1',{'peak_semitones':'2'}), fret=5,local_onset_q='0'),
                dict(row(2,'1','1'), fret=5,local_onset_q='1')]
        self.assertEqual(conditional_tables(rows)['fret']['5']['percent'],50)


if __name__ == '__main__':
    unittest.main()
