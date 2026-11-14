import copy, types, unittest
from fractions import Fraction as Q
import selective_edit as X
import engine as E


def notes(pitches=(28,30),starts=(0,.5)):
 out=[]
 for i,(p,t) in enumerate(zip(pitches,starts),1):
  n={'note_slot':i,'start_beats':t,'end_beats':t+.25,'duration_beats':.25,'start_exact':str(Q(t)),'end_exact':str(Q(t+.25)),'carry_in':False,'overlaps_note_slots':[]}
  if p is not None:n.update(midi_pitch=p,source_midi_pitch=p,target_attack_group=i,source_attack_group=i)
  out.append(n)
 return out

def fixture():
 rows=[];phrases=[]
 for i,p in enumerate([(28,30),(40,42),(28,30),(35,37)],1):
  rows.append({'Phrase #':i,'Length (beats)':2,'Start position (beats)':2*(i-1),'End position (beats)':2*i,'Phrase role':'riff','Dominant texture':'single_note','Accent function':'none','Intended same notes and timing as (phrase #s)':'3' if i==1 else '1' if i==3 else '', 'Intended same rhythm and holds as (phrase #s)':'2' if i==1 else '1' if i==2 else ''})
  phrases.append({'phrase':i,'start_beats':2*(i-1),'length_beats':2,'role':'riff','notes':notes(p)})
 state={'dataset':{'csv_sha256':'csv','timing_sha256':'timing'},'stages':[
  {'id':'1','output':{'summary':{'Riff':'seed'}}},
  {'id':'2','output':{'details':{'blueprint':{'phrases':rows},'field_weights':E.DEFAULT_FIELD_WEIGHTS}}},
  {'id':'3','output':{},'applied':copy.deepcopy(E.DEFAULTS['3'])},
  {'id':'4','output':{},'applied':copy.deepcopy(E.DEFAULTS['4'])},
  {'id':'5','output':{},'applied':copy.deepcopy(E.DEFAULTS['5'])}]}
 candidate_notes=notes((None,None),(0,1))
 candidate={'key':('donor',1),'notes':candidate_notes,'categories':X.C.categories(rows[0]),'row':{'Phrase role':'riff','Dominant texture':'single_note','Category - dominant texture':'single_note','Accent function':'none'},'features':X.C.features(candidate_notes,2)}
 class Pitch:
  def __init__(self):self.calls=[];self.fail=False
  def run(self,seed,rhythm,out,rng,**kw):
   self.calls.append(copy.deepcopy(kw))
   if self.fail:return {'selection_performed':False,'reason':'No suitable donor'}
   ns=copy.deepcopy(rhythm['selected_rhythm'])
   for i,n in enumerate(ns):n.update(midi_pitch=(31,33)[i%2],source_midi_pitch=(31,33)[i%2],target_attack_group=i+1,source_attack_group=i+1)
   return {'selection_performed':True,'notes':ns,'selected':{'riff_id':'pitchdonor','phrase':1,'tier':1}}
 class Engine:
  hashes=state['dataset']
  def __init__(self):
   self.pitch=Pitch();self.rhythm=types.SimpleNamespace(lengths={Q(2):[candidate]},items={('donor',1):candidate},by={'donor':[('donor',1)]})
  def scores(self,*args):return {'donor':85,'pitchdonor':90}
 return state,phrases,Engine()

class SelectiveTests(unittest.TestCase):
 def test_plan_repeat_scopes_and_no_mutation(self):
  state,phrases,e=fixture();before=copy.deepcopy((state,phrases))
  p=X.plan_selection(state,phrases,[3,3],'pitches');self.assertEqual(p['affected'],[1,3]);self.assertEqual(p['rhythm_affected'],[])
  p=X.plan_selection(state,phrases,[3,4],'both');self.assertEqual(p['rhythm_affected'],[1,2,3,4]);self.assertEqual(p['pitch_affected'],[1,3,4]);self.assertEqual(p['pitch_preserved'],[2])
  self.assertEqual((state,phrases),before)
 def test_rhythm_regeneration_excludes_identical_timing_donors(self):
  state,phrases,e=fixture();alternative=e.rhythm.lengths[Q(2)][0]
  same=copy.deepcopy(alternative);same['key']=('same',1);same['notes']=notes((None,None),(0,.5))
  # Equivalent fraction spelling, reversed list and changed slots do not make new timing.
  same['notes'].reverse();same['notes'][0]['start_exact']='2/4'
  e.rhythm.by['same']=[('same',1)];e.rhythm.items[('same',1)]=same
  e.rhythm.lengths[Q(2)]=[same]*20+[alternative]
  before=copy.deepcopy(phrases)
  for seed in range(20):
   r=X.SelectiveEditor(e).regenerate(state,phrases,[3],'rhythm',seed)
   self.assertNotEqual(X._timing_signature(r['phrases'][0]['notes']),X._timing_signature(phrases[0]['notes']))
   self.assertEqual(r['decisions'][0]['same_timing_excluded'],20)
   self.assertEqual(r['phrases'][3],before[3])
  self.assertEqual(phrases,before)
 def test_out_of_bounds_alternatives_are_excluded_before_draw(self):
  state,phrases,e=fixture();bad=copy.deepcopy(e.rhythm.lengths[Q(2)][0]);bad['notes'][1]['end_beats']=3;bad['notes'][1]['end_exact']='3'
  e.rhythm.lengths[Q(2)]=[bad]*20+e.rhythm.lengths[Q(2)]
  r=X.SelectiveEditor(e).regenerate(state,phrases,[3],'rhythm',22)
  self.assertEqual(r['decisions'][0]['out_of_bounds_excluded'],20)
  self.assertEqual(r['phrases'][0]['notes'][1]['end_beats'],1.25)
 def test_no_different_rhythm_is_explicit_and_transactional(self):
  state,phrases,e=fixture();c=e.rhythm.lengths[Q(2)][0];c['notes']=notes((None,None),(0,.5))
  before=copy.deepcopy((state,phrases))
  with self.assertRaisesRegex(X.EditBlocked,'no different rhythm'):
   X.SelectiveEditor(e).regenerate(state,phrases,[3],'rhythm',22)
  self.assertEqual((state,phrases),before)
 def test_consecutive_rhythm_regeneration_avoids_immediately_previous_timing(self):
  state,phrases,e=fixture();alt=copy.deepcopy(e.rhythm.lengths[Q(2)][0]);alt['key']=('other',1);alt['notes']=notes((None,None),(0,.75))
  e.rhythm.by['other']=[('other',1)];e.rhythm.items[('other',1)]=alt;e.rhythm.lengths[Q(2)].append(alt)
  for seed in range(6):
   r=X.SelectiveEditor(e).regenerate(state,phrases,[3],'rhythm',seed)
   self.assertNotEqual(X._timing_signature(phrases[0]['notes']),X._timing_signature(r['phrases'][0]['notes']))
   phrases=r['phrases']
 def test_pitch_only_preserves_all_timing_and_other_phrases(self):
  state,phrases,e=fixture();before=copy.deepcopy((state,phrases));r=X.SelectiveEditor(e).regenerate(state,phrases,[3],'pitches',22)
  self.assertEqual(r['phrases'][1],phrases[1]);self.assertEqual(r['phrases'][3],phrases[3])
  self.assertEqual(r['phrases'][0]['notes'],r['phrases'][2]['notes']);self.assertNotEqual(r['phrases'][0]['notes'],phrases[0]['notes'])
  for old,new in zip(phrases,r['phrases']):self.assertEqual(X.S.stripped(old['notes']),X.S.stripped(new['notes']))
  self.assertEqual(e.pitch.calls[0]['current_scales'],X.T.from_notes(phrases[1]['notes']+phrases[3]['notes']))
  self.assertEqual((state,phrases),before)
 def test_rhythm_only_retains_each_ordered_pitch_sequence(self):
  state,phrases,e=fixture();r=X.SelectiveEditor(e).regenerate(state,phrases,[3],'rhythm',22)
  self.assertEqual(e.pitch.calls,[]);self.assertEqual(r['phrases'][3],phrases[3])
  for i in range(3):
   self.assertEqual([n['midi_pitch'] for n in r['phrases'][i]['notes']],[n['midi_pitch'] for n in phrases[i]['notes']]);self.assertEqual(r['phrases'][i]['notes'][1]['start_beats'],1)
 def test_both_retains_rhythm_only_sibling_pitches(self):
  state,phrases,e=fixture();r=X.SelectiveEditor(e).regenerate(state,phrases,[3],'both',22)
  self.assertEqual(r['pitch_preserved'],[2]);self.assertEqual(r['phrases'][3],phrases[3]);self.assertEqual([n['midi_pitch'] for n in r['phrases'][1]['notes']],[40,42]);self.assertEqual(r['phrases'][0]['notes'],r['phrases'][2]['notes'])
 def test_failed_pitch_is_transactional(self):
  state,phrases,e=fixture();e.pitch.fail=True;before=copy.deepcopy((state,phrases))
  with self.assertRaisesRegex(X.EditBlocked,'No suitable donor'):X.SelectiveEditor(e).regenerate(state,phrases,[3],'both',22)
  self.assertEqual((state,phrases),before)
 def test_multiple_selection_transitive_changes_and_late_failure_atomicity(self):
  state,phrases,e=fixture();before=copy.deepcopy((state,phrases))
  r=X.SelectiveEditor(e).regenerate(state,phrases,[3,4],'both',22)
  self.assertEqual(r['affected'],[1,2,3,4]);self.assertEqual(r['pitch_affected'],[1,3,4]);self.assertEqual(len(e.pitch.calls),2)
  self.assertEqual((state,phrases),before)
  oldrun=e.pitch.run;calls=[]
  def later_failure(*args,**kwargs):
   calls.append(1)
   if len(calls)==2:return {'selection_performed':False,'reason':'Later phrase blocked'}
   return oldrun(*args,**kwargs)
  e.pitch.run=later_failure
  with self.assertRaisesRegex(X.EditBlocked,'Later phrase blocked'):X.SelectiveEditor(e).regenerate(state,phrases,[3,4],'both',22)
  self.assertEqual((state,phrases),before)
 def test_all_phrase_pitch_edit_starts_without_old_tonal_gate(self):
  state,phrases,e=fixture();r=X.SelectiveEditor(e).regenerate(state,phrases,[1,2,3,4],'pitches',22)
  self.assertIsNone(e.pitch.calls[0]['current_scales']);self.assertTrue(e.pitch.calls[1]['current_scales'])
  self.assertEqual(r['pitch_affected'],[1,2,3,4])
 def test_no_pitch_compatible_rhythm_does_not_relax(self):
  state,phrases,e=fixture();e.rhythm.lengths[Q(2)][0]['notes']=notes((None,), (0,));before=copy.deepcopy(phrases)
  with self.assertRaisesRegex(X.EditBlocked,'no positive-weight'):X.SelectiveEditor(e).regenerate(state,phrases,[3],'rhythm',22)
  self.assertEqual(phrases,before);self.assertEqual(e.pitch.calls,[])
 def test_hash_selection_and_boundary_guards(self):
  state,phrases,e=fixture();state['dataset']={}
  with self.assertRaisesRegex(X.EditBlocked,'Dataset'):X.SelectiveEditor(e).regenerate(state,phrases,[3],'both',22)
  state['dataset']=e.hashes
  for selected in [[],[0],[True],[9]]:
   with self.assertRaises(X.EditBlocked):X.plan_selection(state,phrases,selected,'pitches')
  phrases[0]['notes'][0]['end_beats']=3
  with self.assertRaisesRegex(X.EditBlocked,'boundary'):X.SelectiveEditor(e).regenerate(state,phrases,[1],'both',22)
 def test_silence_preserved_without_pitch_call(self):
  state,phrases,e=fixture();phrases[3]['notes']=[]
  r=X.SelectiveEditor(e).regenerate(state,phrases,[4],'pitches',22)
  self.assertEqual([p['notes'] for p in r['phrases']],[p['notes'] for p in phrases]);self.assertEqual(e.pitch.calls,[]);self.assertEqual(r['audio']['length_beats'],8)
 def test_changed_provenance_is_not_stale_and_untouched_tail_preserved(self):
  state,phrases,e=fixture()
  for p in phrases:p.update(source_riff='old donor',source_phrase=7,method='Old selection',tier=2)
  phrases[3]['notes'][1]['end_beats']=3;phrases[3]['notes'][1]['duration_beats']=2.5
  before=copy.deepcopy(phrases)
  r=X.SelectiveEditor(e).regenerate(state,phrases,[3],'pitches',22)
  self.assertEqual(r['phrases'][3],before[3])
  for i in (0,2):
   self.assertNotIn('source_riff',r['phrases'][i]);self.assertNotIn('tier',r['phrases'][i]);self.assertEqual(r['phrases'][i]['edit_provenance']['pitch']['source_riff'],'pitchdonor')
  self.assertEqual(phrases,before)
 def test_changed_candidate_outside_shared_scale_rejected(self):
  state,phrases,e=fixture();before=copy.deepcopy(phrases)
  def badrun(*args,**kwargs):
   ns=notes((28,29));return {'selection_performed':True,'notes':ns,'selected':{'riff_id':'bad','phrase':1,'tier':1}}
  # Frozen set itself deliberately has all 12 classes, forbidding any edit before lookup.
  phrases[3]['notes']=[{**notes((28,), (0,))[0],'midi_pitch':p} for p in range(24,36)]
  with self.assertRaisesRegex(X.EditBlocked,'Unchanged phrases'):X.SelectiveEditor(e).regenerate(state,phrases,[1],'pitches',22)

if __name__=='__main__':unittest.main()
