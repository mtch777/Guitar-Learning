import unittest,copy,random,tempfile
from pathlib import Path
from structure_learning_v8 import sections,train_structure,plan,compose


def fake(name,labels):
    measures=[{'number':i+1,'section':labels.get(i+1)} for i in range(max(labels)+2)]
    return {'source_file':name,'measure_count':len(measures),'tracks':[{'measures':measures}]}

class StructureTests(unittest.TestCase):
    def test_variable_section_lengths(self):
        s=fake('jazz',{1:'Head',4:'Solo',9:'Head'})
        p=sections(s)
        self.assertEqual([v['bars'] for v in p],[3,5,3])
        self.assertEqual([v['relationship'] for v in p],['new','new','return'])
    def test_revised_labels(self):
        s=fake('x',{1:'[B] (0:24)',5:"[B'] (2:05)"})
        self.assertEqual(sections(s)[1]['relationship'],'return')
    def test_no_labels(self):
        s=fake('x',{1:None})
        self.assertEqual(len(sections(s)),1)
    def test_model_learns_lengths(self):
        a=train_structure([fake('a',{1:'A',4:'B',9:'A'})])
        self.assertEqual(a['durations']['new'][3],1)
        self.assertEqual(a['durations']['new'][5],1)
        self.assertEqual(a['durations']['return'][3],1)
    def test_seed_and_bar_count(self):
        a=train_structure([fake('a',{1:'A',4:'B',9:'A'})])
        self.assertEqual(plan(a,37,12),plan(a,37,12))
        self.assertEqual(sum(x['bars'] for x in plan(a,37,12)),37)
    def test_source_changes_plan(self):
        a=train_structure([fake('a',{1:'A',4:'B',9:'A'})])
        b=train_structure([fake('b',{1:'A',8:'B',15:'C'})])
        self.assertNotEqual(a['durations'],b['durations'])
    def test_no_forced_return(self):
        a=train_structure([fake('b',{1:'A',8:'B',15:'C'})])
        self.assertTrue(all(s['relationship']=='new' for s in plan(a,35,17)))
    def test_gp_export(self):
        root=Path('/mnt/data')
        songs=[root/'Cloud Cascade (Tuned Down).gp',root/'Nocturne_ Lost Faith (Tuned Down).gp',root/'Immolation of Night (Tuned Down).gp']
        if not all(p.exists() for p in songs):self.skipTest('Source files not mounted')
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'v8.gp'
            r=compose(songs[0],out,songs,bars=24,seed=17)
            self.assertEqual(r['measures'],24)
            self.assertEqual(sum(s['bars'] for s in r['structure_plan']),24)
            self.assertGreater(r['notes'],0)
            # Import is scoped to existing tooling if present; otherwise zip check below.
            import zipfile
            with zipfile.ZipFile(out) as z:self.assertIn('Content/score.gpif',z.namelist())

if __name__=='__main__':unittest.main()