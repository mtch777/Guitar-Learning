import copy,unittest
from test_corpus_composer import fixture,model_for
from source_harmony_transitions import extract

class TransitionSourceTests(unittest.TestCase):
    def test_exact_source_counter_and_clock_reconciliation(self):
        report,raw=fixture();composer=model_for(report,raw);before=copy.deepcopy((composer,report));result=extract(composer,report)
        self.assertEqual(result['inventory']['rows'],7);self.assertTrue(result['inventory']['exact_historical_track_counters'])
        self.assertEqual(result['inventory']['denominators']['unknown_section'],0);self.assertEqual((composer,report),before)
        for row in result['events']:self.assertEqual(row['origin_register']+row['step'],row['destination_register'])
    def test_counter_and_duration_discrepancies_refused(self):
        report,raw=fixture();composer=model_for(report,raw);bad=copy.deepcopy(composer)
        for ps in bad['parts']['harmony'].values():
            for p in ps:p['root_steps']={'0':999}
        with self.assertRaisesRegex(AssertionError,'counter mismatch'):extract(bad,report)
        changed=copy.deepcopy(report)
        for t in changed['songs'][0]['tracks']:
            for n in t['rows']:n['duration_q']='2'
        with self.assertRaisesRegex(AssertionError,'duration join'):extract(composer,changed)
    def test_wrong_partition_and_duplicate_songs_refused(self):
        report,raw=fixture();composer=model_for(report,raw);report['songs'][0]['provisional_partition']='held_out'
        with self.assertRaisesRegex(ValueError,'Development'):extract(composer,report)
        report['songs'].append(copy.deepcopy(report['songs'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate'):extract(composer,report)

if __name__=='__main__':unittest.main()
