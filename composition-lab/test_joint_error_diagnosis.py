"""Accounting categories preserve uncertainty rather than manufacture certainty."""
import unittest
from copy import deepcopy
from diagnose_tier2_joint_errors import classify, account


class JointErrorDiagnosisTests(unittest.TestCase):
    def test_categories_and_ambiguity(self):
        chord=dict(reference_root_pc=0,reference_formula=[0,4,7])
        c=dict(root_pc=0,formula=[0,4,7]);g=dict(root_pc=7,formula=[0,4,7])
        self.assertEqual(classify([[0,'major']],[c],(0,'major'),chord),'both_agree')
        self.assertEqual(classify([[7,'major']],[c],(0,'major'),chord),'key_only_disagrees')
        self.assertEqual(classify([[0,'major']],[g],(0,'major'),chord),'chord_only_disagrees')
        self.assertEqual(classify([[7,'major']],[g],(0,'major'),chord),'both_disagree')
        self.assertEqual(classify([[0,'major']],[c,g],(0,'major'),chord),'ambiguous_or_unknown')
        self.assertEqual(classify([],[],(0,'major'),chord,True),'unsupported_vocabulary')
        self.assertEqual(classify([[0,'major']],[c],(0,'major'),chord,no_evidence=True),'ambiguous_or_unknown')

    def test_complete_rational_accounting_rejects_coverage_gap(self):
        frame=dict(frame_ref='measure:1',predictions=dict(window0=[[0,'major']],window4=[[0,'major']]),reference_slices=[dict(start_q='0',end_q='1',reference_tonic_pc=0,reference_mode='major')])
        temporal=dict(annotated_evaluation=dict(frames=[frame],alignment=dict(source_end_q='1')))
        chord=dict(start_q='0',end_q='1',reference_root_pc=0,reference_formula=[0,4,7],outside_published_vocabulary=False)
        hresult=dict(annotated_evaluation=dict(reference_spans=[chord]))
        harmonic=dict(all_optimal_path_cell_consensus=[dict(start_q='0',end_q='1',candidate_labels=[dict(root_pc=0,formula=[0,4,7])],no_pitched_evidence_possibility=False)])
        self.assertEqual(account(temporal,hresult,harmonic)['duration_by_class']['window4'],{'both_agree':'1'})
        missing=deepcopy(harmonic);missing['all_optimal_path_cell_consensus'][0]['start_q']='1/2'
        with self.assertRaises(ValueError):account(temporal,hresult,missing)
        duplicate=deepcopy(hresult);duplicate['annotated_evaluation']['reference_spans'].append(chord)
        with self.assertRaises(ValueError):account(temporal,duplicate,harmonic)

    def test_key_change_inside_measure_has_exact_representability_ceiling(self):
        frame=dict(frame_ref='measure:1',predictions=dict(window0=[[0,'major']],window4=[[0,'major']]),reference_slices=[dict(start_q='0',end_q='1/4',reference_tonic_pc=0,reference_mode='major'),dict(start_q='1/4',end_q='1',reference_tonic_pc=7,reference_mode='major')])
        temporal=dict(annotated_evaluation=dict(frames=[frame],alignment=dict(source_end_q='1')))
        chord=dict(start_q='0',end_q='1',reference_root_pc=0,reference_formula=[0,4,7],outside_published_vocabulary=False)
        harmonic=dict(all_optimal_path_cell_consensus=[dict(start_q='0',end_q='1',candidate_labels=[dict(root_pc=0,formula=[0,4,7])],no_pitched_evidence_possibility=False)])
        result=account(temporal,dict(annotated_evaluation=dict(reference_spans=[chord])),harmonic)
        self.assertEqual(result['one_key_per_measure_oracle_ceiling_q'],'3/4')
        self.assertEqual(result['unavoidable_key_disagreement_q'],'1/4')


if __name__=='__main__':unittest.main()
