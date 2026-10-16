import tempfile,unittest,json
from fractions import Fraction as F
from pathlib import Path
from external_score_export import project,write_projected_gp,opening_key
from exact_score import extract_score
from sounding_graph import build_sounding,audit_sounding


class ExternalExportTests(unittest.TestCase):
    def test_polyphony_cross_bar_sustain_survives_gp(self):
        info={25:dict(name='guitar',program=25,tunings=[[64,59,55,50,45,40]])}
        score,repairs=project([(F(7,2),F(5,4),60,25),(F(7,2),F(1,2),64,25)],info,2)
        self.assertEqual(len(score['tracks'][0]['measures'][0]['voices']),2)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.gp';write_projected_gp(score,path);read=extract_score(path);graph=build_sounding(read)
            audit=audit_sounding(read,graph);self.assertEqual(audit['sounding_events'],2);self.assertEqual(audit['merged_tie_occurrences'],1)
            self.assertEqual(sorted(F(n['duration_q']) for n in graph['sustains'].values()),[F(1,2),F(5,4)])

    def test_opening_comparison_ignores_titles_but_detects_pitch_changes(self):
        a=[dict(start=0,end=2,pitch=60,part=3),dict(start=1,end=3,pitch=62,part=3)]
        b=[dict(n,pitch=n['pitch']+5) for n in a]
        self.assertNotEqual(opening_key(a),opening_key(b));self.assertEqual(opening_key(a,relative=True),opening_key(b,relative=True))
        self.assertEqual(opening_key(a,part=5),())

    def test_review_audit_checks_actual_zero_based_melody_channel(self):
        from benchmarks.package_external_comparison import prior_audit
        ids=['final-01','final-02','final-06','final-11'];media={}
        for i,ident in enumerate(ids):media[ident]={'notes':[dict(start=0,end=1,pitch=60,part=2),dict(start=5,end=6,pitch=60+i,part=2)]}
        bundle={'manifest':{'cases':[{'id':ident} for ident in ids]},'media':media}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'consolidated-review-v2.json';path.write_text(json.dumps(bundle))
            audit=prior_audit(Path(folder));self.assertEqual(audit['4s_melody_duplicate_groups'],[ids]);self.assertFalse(audit['reported_sweet_first_8s_melody_all_equal'])
            for item in media.values():
                for n in item['notes']:n['part']=3
            path.write_text(json.dumps(bundle))
            with self.assertRaises(ValueError):prior_audit(Path(folder))


if __name__=='__main__':unittest.main()
