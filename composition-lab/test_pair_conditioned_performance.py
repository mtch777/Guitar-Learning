import copy,json,tempfile,unittest
from pathlib import Path
from fractions import Fraction as F
from test_learned_performance import fixture
from pair_conditioned_performance import apply,load_model
from gp_author import write_gp
from artist_profiles import stable_hash
from engine_contract import _read,_value
from technique_edits import transact,enable_property


def models():
 score,base,shapes=fixture();base['alpha']='1/2000';globalrow=next(t for t in base['tables'] if t['context']=='*')
 model=dict(base={(f,'*'):[F(globalrow['known'][f]),F(globalrow['features'][f])] for f in ('hammer_on_from_open','pull_off_to_open')},pairs={},families={'f'},songs={1},artist='Artist',baseline_model_content_sha256=stable_hash(base),training_source_sha256='fixture-source')
 return score,base,shapes,model

class PairConsumerTests(unittest.TestCase):
 def test_zero_and_intermediate_literal_locks(self):
  score,base,shapes,model=models();freedom={'hammer_on_from_open':50,'pull_off_to_open':50}
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);write_gp(score,p/'source.gp');apply(p/'source.gp',p/'zero.gp',None,None,None,{k:0 for k in freedom});self.assertEqual((p/'source.gp').read_bytes(),(p/'zero.gp').read_bytes())
   a=apply(p/'source.gp',p/'half.gp',base,shapes,model,freedom);b=apply(p/'source.gp',p/'repeat.gp',base,shapes,model,freedom);self.assertEqual(a['decisions'],b['decisions']);self.assertEqual((p/'half.gp').read_bytes(),(p/'repeat.gp').read_bytes())
   _,_,_,before=_read(p/'source.gp');_,_,_,after=_read(p/'half.gp')
   for d in a['decisions']:
    if not d['released']:
     for oid,n in ((d['origin'],'HopoOrigin'),(d['destination'],'HopoDestination')):self.assertEqual(_value(before[oid]['note'],'property',{n}),_value(after[oid]['note'],'property',{n}))
 def test_full_freedom_target_perturbation_shared_endpoints(self):
  score,base,shapes,model=models();freedom={'hammer_on_from_open':100,'pull_off_to_open':100}
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);write_gp(score,p/'source.gp');_,_,_,rows=_read(p/'source.gp');perms={('note',r['note']['note_id'],'property'):{'HopoOrigin','HopoDestination'} for r in rows.values()};transact(p/'source.gp',p/'on.gp',{k:[enable_property(n) for n in sorted(v)] for k,v in perms.items()},perms)
   a=apply(p/'source.gp',p/'a.gp',base,shapes,model,freedom);b=apply(p/'on.gp',p/'b.gp',base,shapes,model,freedom);self.assertEqual(a['decisions'],b['decisions']);self.assertTrue(a['locked_xml_verified']);self.assertTrue(a['archive_members_verified'])
   origins={d['origin'] for d in a['decisions']};destinations={d['destination'] for d in a['decisions']};self.assertTrue(origins&destinations)
   self.assertTrue(all(d['released'] and d['context_backoff'] for d in a['decisions']))
 def test_provenance_and_existing_outputs_refused_before_mutation(self):
  score,base,shapes,model=models()
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);write_gp(score,p/'source.gp');wrong=copy.deepcopy(model);wrong['baseline_model_content_sha256']='wrong'
   with self.assertRaisesRegex(ValueError,'provenance'):apply(p/'source.gp',p/'bad.gp',base,shapes,wrong,{'hammer_on_from_open':100})
   self.assertFalse((p/'bad.hidden.gp').exists());(p/'out.gp').write_bytes(b'keep')
   with self.assertRaises(FileExistsError):apply(p/'source.gp',p/'out.gp',base,shapes,model,{'hammer_on_from_open':100})
   self.assertEqual((p/'out.gp').read_bytes(),b'keep');self.assertFalse((p/'out.hidden.gp').exists())
 def test_model_missing_provenance_and_duplicate_cells_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'model.json';p.write_text('{}',encoding='utf-8')
   with self.assertRaises(ValueError):load_model(p)
   row=dict(key=['hammer_on_from_open','*'],mass='1',selected='1');d=dict(schema='experimental-open-pair-conditioned-v1',artist='Artist',baseline_model_content_sha256='base',training_source_sha256='source',prior_mass='1',baseline_alpha='1/2000',training_families=['f'],training_songs=[1],base=[row,row],pairs=[]);p.write_text(json.dumps(d),encoding='utf-8')
   with self.assertRaisesRegex(ValueError,'duplicate'):load_model(p)

if __name__=='__main__':unittest.main()
