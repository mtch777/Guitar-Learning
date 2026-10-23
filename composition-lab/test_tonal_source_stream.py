from copy import deepcopy
import unittest
from tonal_source_stream import project_source_cells,observations
from tonal_context_observations import target_cells
from ordered_tonal_factor import public_observations


def cells():
    return [dict(span_q=[str(i),str(i+1)],context=[None,[0,4,7],None],active_note_refs=[f'note:{i}'],
                 context_eligibility='UNBRANCHED_WRITTEN_CONTEXT_ONLY',internal_annotation_change=False,
                 target_eligibility='PRIMARY_LABELS_RETAINED_NOT_VERIFIED_TRUTH',
                 target_overlaps=[dict(targets=[dict(globalkey='C',localkey='I',label='I')])]) for i in range(3)]


class SourceStreamTests(unittest.TestCase):
    def test_annotations_cannot_change_inference_rows_or_predecessors(self):
        source=cells();expected=observations(project_source_cells(source));mutated=deepcopy(source)
        mutated[1].update(internal_annotation_change=True,target_eligibility='QUARANTINED_UNPARSED_ALTERNATIVES',target_overlaps=[])
        self.assertEqual(observations(project_source_cells(mutated)),expected)
        self.assertEqual(len(expected['observations']),3)
        self.assertEqual(expected['observations'][-1]['previous_mask'],145)
        self.assertNotEqual(public_observations(target_cells(source)),public_observations(target_cells(mutated)))

    def test_only_source_quarantine_and_real_gaps_break_sequence(self):
        source=project_source_cells(cells());source[1]['source_context_eligible']=False
        result=observations(source)
        self.assertEqual([r['id'] for r in result['observations']],[0,2])
        self.assertIsNone(result['observations'][-1]['previous_mask'])
        source=project_source_cells(cells());source[1].update(start_q='4',end_q='5');source[2].update(start_q='5',end_q='6')
        result=observations(source)['observations']
        self.assertIsNone(result[1]['previous_mask']);self.assertEqual(result[2]['sequence'],1)

    def test_targets_and_type_aliases_cannot_enter_projected_interface(self):
        for alter in ('target','eligibility','identity','witness'):
            rows=project_source_cells(cells())
            if alter=='target':rows[0]['target']=dict(state=0)
            elif alter=='eligibility':rows[0]['source_context_eligible']=1
            elif alter=='identity':rows[0]['id']=False
            else:rows[0]['active_note_refs']=['duplicate','duplicate']
            with self.assertRaises(ValueError):observations(rows)

    def test_bad_order_overlap_identity_and_unknown_source_status_fail(self):
        for quarantine in (False,True):
            rows=project_source_cells(cells());rows[1]['source_context_eligible']=not quarantine
            rows[1]['start_q']='1/2'
            with self.assertRaises(ValueError):observations(rows)
            rows=project_source_cells(cells());rows[0],rows[1]=rows[1],rows[0]
            with self.assertRaises(ValueError):observations(rows)
        rows=project_source_cells(cells());rows[0]['id']=-1
        with self.assertRaises(ValueError):observations(rows)
        source=cells();source[0]['context_eligibility']='QUARANTIND'
        with self.assertRaises(ValueError):project_source_cells(source)


if __name__=='__main__':unittest.main()
