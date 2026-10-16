from fractions import Fraction as F
import unittest
from technique_analysis import classify_group,hopo_pairs,pedal_runs,effect_inventory


def r(i,pitch=60,string=0,fret=5,onset=0,duration=1,**extra):
    return dict(occurrence=str(i),order=i,midi=pitch,string=string,fret=fret,onset_q=str(onset),duration_q=str(duration),
                voice=0,bar=1,section='A',tie_origin=False,tie_destination=False,hopo_origin=False,hopo_destination=False,**extra)


class TechniqueTests(unittest.TestCase):
    def test_nonexclusive_dyad_labels(self):
        self.assertEqual(classify_group([r(0),r(1,61,1)]),['double_stop','close_interval_texture'])
        self.assertEqual(classify_group([r(0),r(1,67,1)]),['double_stop','power_chord'])
    def test_close_dyad_requires_absolute_distance_and_distinct_strings(self):
        self.assertNotIn('close_interval_texture',classify_group([r(0),r(1,73,1)]))
        self.assertEqual(classify_group([r(0),r(1,61,0)]),[])
        self.assertNotIn('close_interval_texture',classify_group([r(0),r(1,61,1),r(2,67,2)]))
    def test_power_chord_octaves_and_inversions(self):
        self.assertIn('power_chord',classify_group([r(0),r(1,67,1),r(2,72,2)]))
        self.assertNotIn('power_chord',classify_group([r(0,55),r(1,60,1)]))
        self.assertNotIn('power_chord',classify_group([r(0),r(1,72,1)]))
    def test_extended_one_color_class(self):
        self.assertIn('extended_power_chord',classify_group([r(0),r(1,67,1),r(2,74,2)]))
        self.assertNotIn('extended_power_chord',classify_group([r(0),r(1,67,1),r(2,74,2),r(3,76,3)]))
    def test_explicit_open_hopo_directions(self):
        a=r(0,fret=0);a['hopo_origin']=True
        b=r(1,62,fret=2,onset=1);b.update(hopo_destination=True,hopo_origin=True)
        c=r(2,fret=0,onset=2);c['hopo_destination']=True
        observed,eligible,warnings=hopo_pairs([a,b,c])
        self.assertEqual([(x['direction'],x['context']) for x in observed],[('hammer_on','from_open'),('pull_off','to_open')])
        self.assertEqual(warnings,[])
    def test_no_cross_string_or_rest_link(self):
        a=r(0);a['hopo_origin']=True
        b=r(1,62,string=1,fret=7,onset=1);b['hopo_destination']=True
        self.assertEqual(hopo_pairs([a,b])[0],[])
        b.update(string=0,onset_q='2')
        self.assertEqual(hopo_pairs([a,b])[0],[])
    def test_eligibility_is_not_annotation(self):
        observed,eligible,warnings=hopo_pairs([r(0),r(1,62,fret=7,onset=1)])
        self.assertEqual(observed,[]);self.assertEqual(len(eligible),1)
        self.assertEqual(eligible[0]['annotation_status'],'eligibility_only')
    def test_hopo_never_links_across_voices(self):
        a=r(0);a['hopo_origin']=True
        b=r(1,62,fret=7,onset=1);b.update(voice=1,hopo_destination=True)
        self.assertEqual(hopo_pairs([a,b])[0],[])
    def test_unison_is_double_stop_but_not_power_or_close_interval(self):
        self.assertEqual(classify_group([r(0),r(1,60,1)]),['double_stop'])
    def test_link_after_explicit_tied_sustain(self):
        a=r(0);a.update(tie_origin=True,hopo_origin=True)
        b=r(1,onset=1);b['tie_destination']=True
        c=r(2,62,fret=7,onset=2);c['hopo_destination']=True
        self.assertEqual(len(hopo_pairs([a,b,c])[0]),1)
    def test_pedal_alternation_and_counterexamples(self):
        rows=[r(i,pitch=p,onset=i) for i,p in enumerate([40,64,40,67,40,38])]
        runs,repeats=pedal_runs(rows)
        self.assertEqual(len(runs),1);self.assertEqual(runs[0]['contrast_intervals'],[24,27,-2])
        self.assertEqual(pedal_runs([r(i,onset=i) for i in range(8)])[0],[])
    def test_effect_preserves_scope_payload(self):
        e=effect_inventory('<Beat><Properties><Property name="VibratoWTremBar"><Strength>Wide</Strength></Property></Properties><Tremolo>16th</Tremolo></Beat>')
        self.assertEqual([x['name'] for x in e],['VibratoWTremBar','Tremolo'])
        self.assertIn('Wide',e[0]['xml'])

    def test_end_boundary_changes_sounding_group_without_new_attack(self):
        import tempfile
        from pathlib import Path
        from gp_author import write_gp
        from exact_score import extract_score
        from technique_analysis import analyze
        def event(onset,duration,pitch=None,string=0,fret=0):
            return dict(onset_q=str(onset),local_onset_q=str(onset),duration_q=str(duration),
                        notes=[] if pitch is None else [dict(midi=pitch,string=string,fret=fret,tie=None,technique_tags=[])])
        score=dict(tracks=[dict(index=0,name='Authored guitar',program=25,tunings=[[40,45,50,55,59,64]],
                   measures=[dict(number=1,onset_q='0',time_signature='4/4',voices=[
                       [event(0,4,60,3,5)],
                       [event(0,1,67,4,8),event(1,3)],
                       [event(0,2,64,5,0),event(2,2)]])])])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.gp';write_gp(score,path)
            result=analyze(extract_score(path))['tracks'][0]
        groups=result['simultaneous_groups']
        self.assertIn('extended_power_chord',groups[0]['labels'])
        self.assertEqual(groups[1]['onset_q'],'1')
        self.assertEqual(groups[1]['end_q'],'2')
        self.assertEqual(groups[1]['labels'],['double_stop'])
        self.assertFalse(groups[1]['coattack'])


if __name__=='__main__':unittest.main()
