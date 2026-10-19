import copy,json,tempfile,unittest
from pathlib import Path
from fractions import Fraction as F
from open_pair_model import fit,predict,score_rows,train_file
from open_pair_opportunities import join
from performance_opportunities import train
from test_performance_opportunities import report


def event(i,distance,positive):
 f='hammer_on_from_open'
 return dict(song_id=i+1,part_id=0,origin='a',destination='b',family='family'+str(i),artist='Artist',partition='development',flagged=False,context='context',known=[f],labels=[f] if positive else [],fret_distance=distance,origin_duration_q='1/3',destination_duration_q='1/3')

class PairModelTests(unittest.TestCase):
 def test_pair_signal_backoff_and_target_annotation_independence(self):
  events=[event(0,1,True),event(1,8,False)];m=fit(events)
  b,short,s=predict(m,events[0]);_,wide,_=predict(m,events[1]);self.assertGreater(short,b);self.assertLess(wide,b)
  q=copy.deepcopy(events[0]);q['labels']=[];self.assertEqual(predict(m,q),predict(m,events[0]))
  q['fret_distance']=23;bb,p,s=predict(m,q);self.assertEqual(bb,p);self.assertTrue(s['pair_backoff'])
 def test_development_duplicates_unknowns_and_leakage_refused(self):
  a=event(0,1,True)
  for change in ({'partition':'held_out'},{'flagged':True},{'labels':None},{'fret_distance':0},{'destination_duration_q':'0'}):
   with self.assertRaises((ValueError,TypeError)):fit([dict(a,**change)])
  with self.assertRaisesRegex(ValueError,'Duplicate'):fit([a,a])
  m=fit([a])
  with self.assertRaisesRegex(ValueError,'leakage'):score_rows(m,[a],m)
 def test_permutation_preserves_origin_baseline_and_weights(self):
  es=[event(i,1 if i%2 else 8,i%2==1) for i in range(8)];a,b=fit(es),fit(es,True)
  self.assertEqual(a['base'],b['base']);self.assertEqual(sum(v[0] for v in a['pairs'].values()),F(8))
 def test_existing_positive_negative_opportunities_reconcile(self):
  r=report();before=copy.deepcopy(r);m,_=train(r);data=join(r,m,'Artist');self.assertEqual(r,before)
  hammer=[e for e in data['events'] if e['known']==['hammer_on_from_open']]
  self.assertEqual(len(hammer),2);self.assertEqual(sum(bool(e['labels']) for e in hammer),1)
  self.assertTrue(all(F(e['origin_onset_q'])+F(e['origin_duration_q'])==F(e['destination_onset_q']) for e in data['events']))
  changed=copy.deepcopy(m);changed['training_sha256']='wrong'
  with self.assertRaises(ValueError):join(r,changed,'Artist')
 def test_file_fit_source_seal_and_fresh_private_output(self):
  from engine_contract import sha
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'local-artifacts';p.mkdir();baseline=p/'baseline.json';baseline.write_text(json.dumps(dict(training_source_sha256='source',schema='artist-performance-opportunity-v1',weighting='family',alpha='1/2000')),encoding='utf-8');data=p/'data.json';a=event(0,1,True);h=event(1,8,False);h['partition']='held_out'
   data.write_text(json.dumps(dict(schema='joined-existing-open-pair-opportunities-v1',all_existing_opportunities_joined=True,duplicate_or_unknown_joins=0,source={'sha256':'synthetic-source'},baseline_model_sha256=sha(baseline),events=[a,h])),encoding='utf-8');result=train_file(data,baseline,p/'model.json');self.assertEqual(result['training_songs'],[1])
   with self.assertRaises(ValueError):train_file(data,baseline,p/'model.json')
   h['family']=a['family'];data.write_text(json.dumps(dict(schema='joined-existing-open-pair-opportunities-v1',all_existing_opportunities_joined=True,duplicate_or_unknown_joins=0,source={'sha256':'synthetic-source'},baseline_model_sha256=sha(baseline),events=[a,h])),encoding='utf-8')
   with self.assertRaisesRegex(ValueError,'leakage'):train_file(data,baseline,p/'leaky.json')
   self.assertFalse((p/'leaky.json').exists())

if __name__=='__main__':unittest.main()
