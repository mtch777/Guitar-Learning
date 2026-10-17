import tempfile
import unittest
from pathlib import Path
from copy import deepcopy
from gp_author import write_gp
from exact_score import extract_score
from pattern_edits import generate, voicing, FAMILIES
from technique_analysis import classify_group
from technique_strength import released


def fixture(tuning=None):
    tuning=tuning or [40,45,50,55,59,64]
    measures=[]
    for bar in range(4):
        events=[dict(onset_q=str(bar*4+i/2),local_onset_q=str(i/2),duration_q='1/2',notes=[dict(midi=tuning[0]+i%3,string=0,fret=i%3,tie=None,technique_tags=[])]) for i in range(8)]
        measures.append(dict(number=bar+1,onset_q=str(bar*4),time_signature='4/4',voices=[events]))
    return dict(tracks=[dict(index=0,name='Pattern test',program=25,tunings=[tuning],measures=measures)])


class PatternTests(unittest.TestCase):
    def test_all_voicings_in_two_tunings(self):
        for tuning in ([40,45,50,55,59,64],[33,40,45,50,54,59,64]):
            for family in FAMILIES:
                for method in ('compact','upper'):
                    for i in range(8):
                        positions=voicing(tuning,family,i,method)
                        self.assertEqual(len(positions),len({s for p,s,f in positions}))
                        self.assertTrue(all(tuning[s]+f==p and 0<=f<=24 for p,s,f in positions))
                        if family!='pedal_notes':self.assertIn(family,classify_group([dict(midi=p,string=s) for p,s,f in positions]))

    def test_source_edit_locks_roundtrip_and_full_freedom(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.gp';write_gp(fixture(),source)
            other=fixture()
            for m in other['tracks'][0]['measures']:
                for e in m['voices'][0]:
                    for n in e['notes']:n['midi']+=3;n['fret']+=3
            perturbed=root/'other.gp';write_gp(other,perturbed)
            for family in FAMILIES:
                zero=root/(family+'0.gp');generate(source,zero,0,family,0)
                self.assertEqual(source.read_bytes(),zero.read_bytes())
                a=root/(family+'a.gp');b=root/(family+'b.gp')
                audit=generate(source,a,0,family,pitch_unlocked=True,voicing_unlocked=True)
                generate(perturbed,b,0,family,pitch_unlocked=True,voicing_unlocked=True)
                self.assertEqual(audit['changed_events'],32)
                def notes(p):return [[[(n['midi'],n['string'],n['fret']) for n in e['notes']] for e in m['voices'][0]] for m in extract_score(p)['tracks'][0]['measures']]
                self.assertEqual(notes(a),notes(b))

    def test_incompatible_locks_rejected(self):
        with self.assertRaises(ValueError):generate('missing','missing',0,'power_chord',pitch_unlocked=True)

    def test_reference_release_is_nested_and_not_difference_quota(self):
        sets=[{i for i in range(1000) if released(str(i),s)} for s in (0,25,50,75,100)]
        self.assertEqual(len(sets[0]),0);self.assertEqual(len(sets[-1]),1000)
        for a,b in zip(sets,sets[1:]):self.assertLess(a,b)
        self.assertTrue(200<len(sets[1])<300)
        with self.assertRaises(ValueError):released('x',101)


if __name__=='__main__':unittest.main()
