from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from conditional_bass_factor import fit
from run_conditional_bass_study import adjusted,evaluated,combined,verify_clean_models,sha
from test_conditional_bass_factor import fixture


class BassStudyTests(unittest.TestCase):
    def test_clean_model_provenance_rejects_empty_or_incomplete_inventories(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);clean=root/'clean';study=root/'study';clean.mkdir();study.mkdir()
            (clean/'manifest.json').write_text('{}');(study/'selection-before-test.json').write_text('{}')
            paths=[clean/'manifest.json',Path(__file__).with_name('ordered_tonal_factor.py'),Path(__file__).with_name('run_clean_tonal_study.py')]
            frozen={str(p.resolve()):sha(p) for p in paths};models={}
            for kind in ('ordered','marginal','shuffled_predecessor'):
                p=study/(kind+'-research-model.json');p.write_text('{}');models[kind]=sha(p)
            report=dict(status='COMPLETED_CLEAN_SOURCE_REFIT',unchanged=True,clean_manifest_sha256=sha(clean/'manifest.json'),selection_sha256=sha(study/'selection-before-test.json'),model_sha256=models)
            (study/'result.json').write_text(json.dumps(report));(study/'plan-before-fitting.json').write_text(json.dumps(dict(frozen=frozen)))
            self.assertEqual(len(verify_clean_models(clean,study)),3)
            for inventory in ({},{'ordered':models['ordered']}):
                (study/'result.json').write_text(json.dumps(dict(report,model_sha256=inventory)))
                with self.assertRaises(ValueError):verify_clean_models(clean,study)
            (study/'result.json').write_text(json.dumps(report));(study/'plan-before-fitting.json').write_text(json.dumps(dict(frozen={})))
            with self.assertRaises(ValueError):verify_clean_models(clean,study)

    def test_complete_source_inference_separate_teacher_scoring(self):
        pieces,features=fixture();piece=pieces[0];model,_=fit(pieces,features)
        observed=[dict(r) for r in piece['source_observations']]
        pred=dict(rows=[dict(observation_ref=r['id'],start_q=r['start_q'],end_q=r['end_q'],posterior=[1/24]*24,marginal_map_state=0) for r in observed])
        result=adjusted(pred,observed,features['train'],model,10)
        self.assertEqual(len(result['rows']),8)
        piece=deepcopy(piece)
        for r in piece['rows']:r['duration_q']='1'
        piece['rows'][1]['quarantine_reasons']=['NO_LABEL'];piece['rows'][1]['target']=None
        metric=evaluated(piece,result);summary=combined([metric])
        self.assertEqual(summary['evaluation_cells'],7)
        self.assertEqual(summary['duration_q'],7)
        self.assertAlmostEqual(sum(b['duration_q'] for b in summary['calibration_bins']),7)
        self.assertGreaterEqual(summary['calibration_ece'],0)
        self.assertLessEqual(summary['calibration_ece'],1)

    def test_feature_clocks_and_duplicate_predictions_cannot_pass_join(self):
        pieces,features=fixture();model,_=fit(pieces,features);observed=pieces[0]['source_observations']
        pred=dict(rows=[dict(observation_ref=r['id'],start_q=r['start_q'],end_q=r['end_q'],posterior=[1/24]*24) for r in observed])
        bad=deepcopy(features['train']);bad[0]['end_q']='2'
        with self.assertRaises(ValueError):adjusted(pred,observed,bad,model,10)
        pred['rows'][-1]=pred['rows'][0]
        with self.assertRaises(ValueError):adjusted(pred,observed,features['train'],model,10)


if __name__=='__main__':unittest.main()
