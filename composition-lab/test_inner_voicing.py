from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,realize
from test_check_declared_allocation import fixture as base_fixture
from inner_voicing import catalog,options,apply,sample,POLICY,component_links,verify


def fixture():
    docs,_,refs,donor=base_fixture()
    # Physical evidence is a whole UNLABELED shape elsewhere, at another fret.
    beat=docs['track-0.json']['measures'][4]['voices'][0]['beats'][2]
    beat.pop('chord')
    for n,f in zip(beat['notes'],[10,7,7,9]):n['fret']=f
    return docs,refs,donor


def analyzed(docs):
    lower=extract_documents(docs);upper=strip_lower(analyze(lower,declared_chords=True));return lower,upper,catalog(upper)


class InnerVoicingTests(unittest.TestCase):
    def test_zero_duration_occurrence_at_left_boundary_is_not_free_hand(self):
        from inner_voicing import overlaps,overlap_index,outside_overlap
        nodes={'a':dict(part_id=1,onset_q='4',duration_q='1'),'grace':dict(part_id=1,onset_q='4',duration_q='0'),'end':dict(part_id=1,onset_q='5',duration_q='0')}
        self.assertEqual(overlaps(nodes,['a']),['grace'])
        self.assertTrue(outside_overlap(overlap_index(nodes),nodes,['a']))

    def test_index_matches_literal_rational_overlap_predicate(self):
        from inner_voicing import overlaps,overlap_index,outside_overlap
        from fractions import Fraction as F
        import random
        rng=random.Random(408)
        for _ in range(100):
            nodes={str(i):dict(part_id=rng.randrange(2),onset_q=str(F(rng.randrange(24),rng.choice([1,2,4]))),duration_q=str(F(rng.randrange(5),rng.choice([1,2,4])))) for i in range(30)}
            index=overlap_index(nodes)
            for ref in nodes:self.assertEqual(bool(overlaps(nodes,[ref])),outside_overlap(index,nodes,[ref]))

    def test_new_inner_combination_preserves_outer_notes_through_actual_inverse(self):
        docs,refs,donor=fixture();lower,upper,c=analyzed(docs);target=next(u for u in c['units'] if u['member_refs']==refs)
        e=options(upper,target['id'],c);changed=[o for o in e['options'] if o['changed']]
        self.assertTrue(changed,e);choice=changed[0];after=realize(apply(upper,target,choice['roles']))
        from source_fact_tier1 import project_documents
        notes=project_documents(after)['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes']
        self.assertEqual([n['fret'] for n in notes],[8,5,5,7])
        self.assertEqual(choice['relationship']['melody_identity'],'UNKNOWN')
        self.assertIn('context_observation',choice['relationship'])
        control=dict(context_policy=POLICY,voicing=100,register=0,target_ref=target['id'],seed=0)
        control['seed']=next(i for i in range(1000) if sample(e,dict(control,seed=i))[0]==choice)
        from qa_isolation_harness import execute
        from run_connected_tier2_qa import bundle
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as tmp:
            for name,ctrl,expected,purpose in [('zero',dict(control,voicing=0),lower,'voicing_register_intervention'),('changed',control,after,'voicing_register_intervention')]:
                result=execute(code,upper,ctrl,expected,Path(tmp)/name,timeout=40,purpose=purpose)
                self.assertEqual(result['status'],'PASS',result)
        for strength in (0,50,100):
            reports=[sample(e,dict(control,voicing=strength,seed=i))[1] for i in range(1000)]
            released=sum(r['released'] for r in reports)
            self.assertTrue(released==strength*10 if strength in (0,100) else 450<released<550)
        self.assertLess(sum(sample(e,dict(control,seed=i))[1]['changed'] for i in range(1000)),1000)

    def test_geometry_is_whole_independent_closed_shape_not_a_span_heuristic(self):
        for mode in ('absent','partial','open','instrument','tuning','overlap'):
            docs,refs,_=fixture();beat=docs['track-0.json']['measures'][4]['voices'][0]['beats'][2]
            if mode=='absent':
                for n,f in zip(beat['notes'],[8,10,9,7]):n['fret']=f
            if mode=='partial':beat['notes'].pop()
            if mode=='open':
                for n,f in zip(beat['notes'],[3,0,0,2]):n['fret']=f
            if mode=='overlap':docs['track-0.json']['measures'][4]['voices'][0]['beats'][1]['duration']=[1,2]
            if mode in ('instrument','tuning'):
                # Move the only witness to an incompatible part.
                extra=deepcopy(docs['track-0.json']);extra['partId']=1
                extra['instrumentId']=27 if mode=='instrument' else 26
                if mode=='tuning':extra['tuning'][5]=41
                docs['track-1.json']=extra;docs['metadata.json']['tracks'].append(dict(instrumentId=extra['instrumentId']))
                for n,f in zip(beat['notes'],[8,10,9,7]):n['fret']=f
            _,upper,c=analyzed(docs);e=options(upper,refs[0],c)
            self.assertFalse(any(o['changed'] for o in e['options']),mode)

    def test_execution_remains_hard_and_no_change_outside_inner_frets(self):
        docs,refs,_=fixture();lower,upper,c=analyzed(docs);target=next(u for u in c['units'] if u['id']==refs[0]);link=next(l for l in component_links(c,target) if l['changed']);after=realize(apply(upper,target,link['roles']))
        for kind in ('outer','outside','metadata'):
            bad=deepcopy(after)
            key={'outer':'track-0.json#/measures/1/voices/0/beats/1/notes/0/fret','outside':'track-0.json#/measures/0/voices/0/beats/0/notes/0/fret','metadata':'metadata.json#/title'}[kind]
            next(f for f in bad['facts'] if f['id']==key)['value']=11 if kind!='metadata' else 'different'
            with self.assertRaises(ValueError):verify(c,bad,target,link['donor'])
        # The neighboring slide is kept even though exact path-copying is not required.
        docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][1]['slide']=1
        _,upper,c=analyzed(docs);e=options(upper,refs[0],c)
        self.assertFalse(any(o['changed'] for o in e['options']))

    def test_unseen_plain_string_context_is_reported_not_melody_invention(self):
        docs,refs,_=fixture()
        for i in (11,13):
            beat=docs['track-0.json']['measures'][i//4]['voices'][0]['beats'][i%4]
            for n in beat['notes'][1:3]:n['fret']+=1
        _,upper,c=analyzed(docs);e=options(upper,refs[0],c);changed=[o for o in e['options'] if o['changed']]
        self.assertTrue(changed,e)
        self.assertIn('NO_INDEPENDENT_SOURCE_',str(changed[0]['relationship']['context_observation']))
        self.assertEqual(changed[0]['relationship']['melody_identity'],'UNKNOWN')


if __name__=='__main__':unittest.main()
