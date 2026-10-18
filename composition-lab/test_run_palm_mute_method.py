import tempfile,json,unittest
from pathlib import Path
from test_learned_performance import fixture
from test_performance_opportunities import report
from gp_author import write_gp
from run_palm_mute_method import run

class PalmMuteRunnerTests(unittest.TestCase):
    def test_retains_existing_playback_and_independent_expectations(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);inputs=p/'inputs';inputs.mkdir();score,_,_=fixture();src=inputs/'piece-100.gp';write_gp(score,src)
            src.with_suffix('.expected.json').write_text(json.dumps(score),encoding='utf-8')
            sidecars={'.playback.json':dict(noteSlightLength=360,noteSlightAmplitude=.25),'.curves.json':[],'.techniques.json':dict(fixture=True)}
            for suffix,value in sidecars.items():src.with_suffix(suffix).write_text(json.dumps(value),encoding='utf-8')
            report_path=p/'report.json';report_path.write_text(json.dumps(report()),encoding='utf-8')
            run(report_path,inputs,p/'out',artist='Artist')
            for target in (p/'out').glob('*.gp'):
                for suffix in sidecars:self.assertEqual(target.with_suffix(suffix).read_bytes(),src.with_suffix(suffix).read_bytes())

if __name__=='__main__':unittest.main()
