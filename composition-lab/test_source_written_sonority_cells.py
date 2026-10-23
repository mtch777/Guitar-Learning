from copy import deepcopy
import unittest
import tempfile
from pathlib import Path
from source_tie_tier1 import extract_documents
from source_written_sonority_cells import extract_cells
from research_observation_cuts import prepare,canonicalize,restore
from test_contextual_note_roles import source


class WrittenCellTests(unittest.TestCase):
    def test_actual_stripped_worker_recovers_observation_packet(self):
        from run_source_cut_qa import inverse_code
        from qa_isolation_harness import execute
        view=extract_cells(extract_documents(source()))
        packet,_=prepare(view['observations'],view['supports'],view['boundary_events'])
        with tempfile.TemporaryDirectory() as folder:
            result=execute(inverse_code(Path(__file__).parent),canonicalize(packet),dict(variation=0),packet,Path(folder)/'worker',timeout=30)
            self.assertEqual(result['status'],'PASS',result)

    def test_real_source_rearticulation_and_tie_boundaries_survive(self):
        docs=source();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[1]['notes'][0]['fret']=beats[0]['notes'][0]['fret'];beats[1]['notes'][0]['tie']=True
        lower=extract_documents(docs);view=extract_cells(lower)
        packet,_=prepare(view['observations'],view['supports'],view['boundary_events'])
        canonical=canonicalize(packet)
        self.assertEqual(canonical['observations'],view['observations'])
        self.assertEqual(restore(canonical),packet)
        self.assertTrue(any('written_tie_declaration:' in w for r in view['rows'] for w in r['boundary_events']))
        self.assertNotEqual(view['supports'][0],view['supports'][1])

    def test_unknown_pitch_quarantines_without_guessing(self):
        docs=source();docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['dead']=True
        view=extract_cells(extract_documents(docs))
        quarantined=[r for r in view['rows'] if r['quarantine_reasons']]
        self.assertTrue(quarantined);self.assertTrue(all(r['unresolved_note_refs'] for r in quarantined))
        self.assertNotIn(quarantined[0]['observation']['id'],view['supports'])
        self.assertIsNone(view['observations'][-1]['previous_mask'])

    def test_percussion_cannot_change_observation_grid_or_pitches(self):
        docs=source();base=extract_cells(extract_documents(docs))
        extra=deepcopy(docs['track-0.json']);extra.update(partId=2,instrumentId=1024)
        for beat in extra['measures'][0]['voices'][0]['beats']:beat['duration']=[1,8]
        docs['track-2.json']=extra;docs['metadata.json']['tracks'].append(dict(instrumentId=1024))
        view=extract_cells(extract_documents(docs))
        self.assertEqual(view['observations'],base['observations'])
        self.assertTrue(view['excluded_nonpitched_refs'])

    def test_unreliable_source_time_is_explicit_refusal(self):
        lower=extract_documents(source());lower['source_coverage']['timing_warnings']=[dict(reason='overflow')]
        with self.assertRaises(ValueError):extract_cells(lower)


if __name__=='__main__':unittest.main()
