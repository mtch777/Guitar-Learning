from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from test_inner_voicing import fixture
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize,reconstruct
import unlabeled_inner_voicing as u


def without_labels(docs):
    docs=deepcopy(docs)
    for p in docs.values():
        for m in p.get('measures',[]):
            for v in m.get('voices',[]):
                for b in v.get('beats',[]):b.pop('chord',None)
    return docs


def prepare(docs,**kwargs):
    lower=extract_documents(docs);upper=strip_lower(analyze(lower,**kwargs))
    return lower,upper,u.catalog(upper)


class UnlabeledInnerTests(unittest.TestCase):
    def test_plain_declared_and_family_owners_use_same_source_patterns(self):
        docs,refs,_=fixture();layouts=[]
        for labeled,kwargs in ((False,{}),(False,{'families':True}),(True,{'declared_chords':True})):
            lower,upper,c=prepare(docs if labeled else without_labels(docs),**kwargs)
            e=u.options(upper,refs[0],c)
            layouts.append([(o['pitches'],o['donor_refs'],o['changed']) for o in e['options']])
            self.assertEqual(realize(upper),lower)
            choice=next(o for o in e['options'] if o['changed'])
            edited=u.apply(upper,e['target'],choice,c);after=realize(edited)
            self.assertEqual(edited['musical_relationships']['schema'],upper['musical_relationships']['schema'])
            notes=project_documents(after)['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes']
            self.assertEqual([n['fret'] for n in notes],[8,5,5,7])
            self.assertTrue(choice['relationship']['degree_roundtrip'])
            for cell in choice['relationship']['edited_set_context']['cells']:
                self.assertFalse(set(cell['excluded_edited_refs'])&set(cell['population']['support_refs']))
        self.assertEqual(layouts[0],layouts[1]);self.assertEqual(layouts[0],layouts[2])

    def test_ambiguous_c6_am7_never_selects_a_root_or_doubles_votes(self):
        docs,refs,_=fixture();docs=without_labels(docs)
        for i,frets in ((5,[15,17,17,7]),(12,[15,5,5,7])):
            beat=docs['track-0.json']['measures'][i//4]['voices'][0]['beats'][i%4]
            for n,f in zip(beat['notes'],frets):n['fret']=f
        _,upper,c=prepare(docs);e=u.options(upper,refs[0],c)
        self.assertGreaterEqual(len(e['all_hypothesis_refs']),2,e)
        changed=next(o for o in e['options'] if o['changed'])
        self.assertEqual(changed['pitches'],['79','64','60','57'])
        self.assertEqual(changed['donor_refs'],['coattack:12'])
        self.assertEqual(len(changed['support']),len(e['all_hypothesis_refs']))
        # Retain an actual assumption but remove its available source-unit mapping.
        # A partial mapping must never silently become universal support.
        lost=e['all_hypothesis_refs'][0]
        c['units']=[x for x in c['units'] if x['id']!=lost]
        c['ledger']=u.build_ledger(c,c['harmonic_evidence'])
        refused=u.options(upper,refs[0],c)
        self.assertFalse(refused['options'])
        self.assertTrue(all(r['reason']=='NOT_SUPPORTED_UNDER_EVERY_RETAINED_ASSUMPTION' for r in refused['rejected']))

    def test_real_isolated_zero_and_change_and_release_probability(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        docs,refs,_=fixture();lower,upper,c=prepare(without_labels(docs));e=u.options(upper,refs[0],c)
        control=dict(context_policy=u.POLICY,voicing=100,register=0,target_ref=refs[0],seed=0)
        # Test a deterministic seed; test setup is not a production song selector.
        control['seed']=next(i for i in range(1000) if u.sample(e,dict(control,seed=i))[1]['changed'])
        after=reconstruct(upper,control);self.assertNotEqual(after,lower)
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as tmp:
            for name,ctrl,expected in [('zero',dict(control,voicing=0),lower),('changed',control,after)]:
                result=execute(code,upper,ctrl,expected,Path(tmp)/name,timeout=60,purpose='voicing_register_intervention')
                self.assertEqual(result['status'],'PASS',result)
        for strength in (0,50,100):
            rows=[u.sample(e,dict(control,voicing=strength,seed=i))[1] for i in range(1000)]
            released=sum(r['released'] for r in rows)
            self.assertTrue(released==strength*10 if strength in (0,100) else 450<released<550)
        self.assertLess(sum(u.sample(e,dict(control,seed=i))[1]['changed'] for i in range(1000)),1000)

    def test_bad_proposal_cannot_add_ignored_degrees_or_disagree_with_owner(self):
        docs,refs,_=fixture();_,upper,c=prepare(without_labels(docs));e=u.options(upper,refs[0],c)
        choice=next(o for o in e['options'] if o['changed'])
        for field in ('pitches','support'):
            broken=deepcopy(choice)
            if field=='pitches':broken[field][1]='65'
            else:broken[field]=[]
            with self.assertRaises(ValueError):u.apply(upper,e['target'],broken,c)
        control=dict(context_policy=u.POLICY,voicing=100,register=0,target_ref=refs[0],seed=0,pitches=[1,2,3,4])
        with self.assertRaises(ValueError):reconstruct(upper,control)


if __name__=='__main__':unittest.main()
