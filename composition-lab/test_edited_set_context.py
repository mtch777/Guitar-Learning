from copy import deepcopy
import unittest
from test_nominal_harmony import part,beat,run
import nominal_harmony as n


class EditedSetContextTests(unittest.TestCase):
    def fixture(self):
        docs={'metadata.json':dict(songId=77,revisionId=3,title='Authored edited-set contrast',artist='Fixture'),
            'track-0.json':part(0,[62,65],[beat([1,1],[0,1])]),
            'track-1.json':part(1,[48,52,55,50,54,57],[beat([1,2],[0,1,2]),beat([1,2],[3,4,5])])}
        _,upper,view=run(docs);c=n.prepare(upper)
        refs=['event:77:0:1:0:0:0','event:77:0:1:0:0:1']
        after=deepcopy(c['events']);after[refs[0]]['pitch']='64';after[refs[1]]['pitch']='67'
        return docs,upper,c,view,after,refs

    def test_all_changed_notes_excluded_together_across_held_context_changes(self):
        _,_,c,view,after,refs=self.fixture()
        report=n.edited_set_context(c,view,after,refs)
        rows=[r for r in report['cells'] if r['scope']=='ensemble_minus_edited']
        self.assertEqual([(r['start_q'],r['end_q']) for r in rows],[('0','2'),('2','4')])
        for row,root in zip(rows,[0,2]):
            self.assertEqual(set(row['excluded_edited_refs']),set(refs))
            self.assertFalse(set(refs)&set(row['population']['support_refs']))
            self.assertTrue(any(h['root_pc']==root and h['kind']=='major' for h in row['population']['hypotheses']))
            self.assertEqual(len(row['queries']),2)
        own=[r for r in report['cells'] if r['scope']=='focal_part_minus_edited']
        self.assertTrue(all(not r['population']['support_refs'] and not r['population']['hypotheses'] for r in own))
        self.assertTrue(all('INSUFFICIENT_DISTINCT_PITCH_CLASSES' in r['population']['refusals'] for r in own))

    def test_unknown_support_does_not_turn_into_a_selected_chord(self):
        docs,_,_,_,_,refs=self.fixture()
        docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['dead']=True
        _,upper,view=run(docs);c=n.prepare(upper);after=deepcopy(c['events'])
        after[refs[0]]['pitch']='64';after[refs[1]]['pitch']='67'
        report=n.edited_set_context(c,view,after,refs)
        row=next(r for r in report['cells'] if r['scope']=='ensemble_minus_edited' and r['start_q']=='0')
        self.assertIn('UNKNOWN_WRITTEN_PITCH',row['population']['refusals'])
        self.assertEqual(row['population']['hypotheses'],[])
        self.assertTrue(all(not q['role_changes'] for q in row['queries']))

    def test_original_single_note_view_unchanged_by_edited_set_query(self):
        _,upper,c,view,after,refs=self.fixture();original=deepcopy(view)
        n.edited_set_context(c,view,after,refs)
        self.assertEqual(view,original);self.assertEqual(n.analyze(upper),original)
        with self.assertRaises(ValueError):n.edited_set_context(c,view,after,refs+['invented'])


if __name__=='__main__':unittest.main()
