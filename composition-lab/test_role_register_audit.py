import unittest
from copy import deepcopy
from role_register_audit import extract,summarize,alternative_bounds,verify_raw


class RoleRegisterTests(unittest.TestCase):
    def fixture(self):
        def part(pid,tuning,root):return dict(part_id=pid,song_id=1,bar=2,tuning=tuning,root_events=[dict(local_q='0',duration_q='1',root=root)])
        composer=dict(parts=dict(melody={'f':[part(3,[40],64)]},harmony={'f':[part(2,[28],35)]}))
        e=dict(partition='development',role='melody',song_id=1,part_id=3,bar=2,onset_q='4',family='f',target=64,anchor=35,register=24)
        return dict(events=[e]),composer

    def test_exact_decomposition_and_unknown_preserved(self):
        obs,composer=self.fixture();unknown=deepcopy(obs['events'][0]);unknown.update(bar=3,anchor=None);obs['events'].append(unknown)
        rows,missing=extract(obs,composer);self.assertEqual(missing,1)
        self.assertEqual((rows[0]['H'],rows[0]['harmony_own_register'],rows[0]['tuning_offset']),( -5,7,-12))
        result=summarize(rows);self.assertEqual(result['means']['H'],-5);self.assertEqual(result['same_part_boundaries'],0)

    def test_ambiguous_selection_and_wrong_anchor_refused(self):
        obs,composer=self.fixture();composer['parts']['harmony']['f'].append(deepcopy(composer['parts']['harmony']['f'][0]))
        with self.assertRaisesRegex(ValueError,'Ambiguous'):extract(obs,composer)
        obs,composer=self.fixture();obs['events'][0]['anchor']=36
        with self.assertRaisesRegex(ValueError,'harmony identity'):extract(obs,composer)

    def test_multiple_harmony_parts_reported_without_reassignment(self):
        obs,composer=self.fixture();other=deepcopy(composer['parts']['harmony']['f'][0]);other.update(part_id=8,tuning=[40]);composer['parts']['harmony']['f'].append(other)
        rows,_=extract(obs,composer)
        self.assertEqual(rows[0]['harmony_part'],2);self.assertEqual(summarize(rows)['multiple_harmony_choices'],1)
        bounds=alternative_bounds(rows,composer)
        self.assertEqual(bounds['multiple_active_choices'],1)
        self.assertEqual(bounds['bounds']['H_min_mean'],bounds['bounds']['H_max_mean'])
        self.assertEqual(bounds['bounds']['own_min_mean'],-5)
        self.assertEqual(bounds['bounds']['own_max_mean'],7)

    def test_raw_pitch_and_tuning_checked_separately(self):
        obs,composer=self.fixture();rows,_=extract(obs,composer)
        report=dict(songs=[dict(song_id=1,shared_layout=[dict(bar=2,start_q='4')],tracks=[
            dict(part_id=2,rows=[dict(voice=0,onset_q='4',midi=35,string=0,fret=7)]),
            dict(part_id=3,rows=[dict(voice=0,onset_q='4',midi=64,string=0,fret=24)])])])
        self.assertEqual(verify_raw(rows,report),dict(pitch_groups=2,note_tunings=2))
        report['songs'][0]['tracks'][0]['rows'][0]['fret']=8
        with self.assertRaisesRegex(ValueError,'tuning differs'):verify_raw(rows,report)


if __name__=='__main__':unittest.main()
