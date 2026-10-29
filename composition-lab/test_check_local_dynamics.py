from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from check_local_dynamics import inventory,choices,check

TARGET='track-0.json#/measures/0/voices/0/beats/0/velocity'
def documents():
    measures=[]
    for mi in range(3):
        voices=[]
        for vi in range(2):
            beats=[dict(duration=[1,4],notes=[dict(string=0,fret=0)])for _ in range(4)]
            if vi==0:beats[0]['velocity']=['f','mf','f'][mi]
            elif mi==0:beats[0]['velocity']='fff'
            if vi==0 and mi<2:beats[1]['notes'][0]['velocity']=['pp','p'][mi]
            voices.append(dict(beats=beats))
        measures.append(dict(signature=[4,4],voices=voices))
    return {'metadata.json':dict(songId=93,revisionId=1,title='Dynamics',artist='Authored',tracks=[dict(instrumentId=25)]),
            'track-0.json':dict(songId=93,revisionId=1,partId=0,instrumentId=25,tuning=[60],measures=measures)}
def facts(d):return extract_documents(d)
def edited(d,level,measure=0,voice=0,beat=0,note=None):
    d=deepcopy(d);b=d['track-0.json']['measures'][measure]['voices'][voice]['beats'][beat]
    (b if note is None else b['notes'][note])['velocity']=level;return facts(d)
def option(before,ref,mark):return next(o for o in choices(before,ref)['options']if o['marking']==mark)
def decision(o,released=True):return dict(released=released,changed=o['changed']if released else False,chosen=o if released else None)

class IndependentLocalDynamicsTests(unittest.TestCase):
 def test_complete_region_and_note_override_exclusion(self):
    before=facts(documents());inv=inventory(before);target=next(d for d in inv['declarations']if d['fact_ref']==TARGET)
    self.assertEqual(target['influence_refs'],['event:93:0:1:0:0:0','event:93:0:1:0:2:0','event:93:0:1:0:3:0'])
    self.assertEqual(target['reasons'],[])
    states={s['occurrence_ref']:s for s in inv['states']};self.assertEqual(states['event:93:0:1:0:1:0']['marking'],'pp')
    self.assertEqual(states['event:93:0:1:0:2:0']['origin_fact_ref'],TARGET)
    self.assertEqual(states['event:93:0:1:1:3:0']['marking'],'fff')
 def test_source_marking_votes_once_and_exact_actual_change(self):
    d=documents();before=facts(d);o=option(before,TARGET,'mf');self.assertEqual(len(o['donor_refs']),1)
    after=edited(d,'mf');r=check(before,after,TARGET,o['donor_refs'],decision(o));self.assertEqual(r['issues'],[],r);self.assertEqual(len(r['affected_refs']),3)
    self.assertNotIn('fff',[o['marking']for o in choices(before,TARGET)['options']])
 def test_note_explicit_scope_does_not_mutate_voice_state(self):
    d=documents();before=facts(d);ref='track-0.json#/measures/0/voices/0/beats/1/notes/0/velocity';o=option(before,ref,'p')
    after=edited(d,'p',beat=1,note=0);r=check(before,after,ref,o['donor_refs'],decision(o));self.assertEqual(r['issues'],[]);self.assertEqual(r['affected_refs'],['event:93:0:1:0:1:0'])
 def test_unknown_next_beat_and_note_override_refuse_affected_region(self):
    for unknown in ('mystery',False,0):
        d=documents();d['track-0.json']['measures'][0]['voices'][0]['beats'][2]['velocity']=unknown
        row=next(r for r in inventory(facts(d))['declarations']if r['fact_ref']==TARGET);self.assertIn('UNKNOWN_BEAT_BOUNDARY',row['reasons'])
        d=documents();d['track-0.json']['measures'][0]['voices'][0]['beats'][2]['notes'][0]['velocity']=unknown
        row=next(r for r in inventory(facts(d))['declarations']if r['fact_ref']==TARGET);self.assertIn('UNKNOWN_NOTE_OVERRIDE',row['reasons'])
 def test_null_is_preserved_but_does_not_reset_state(self):
    d=documents();d['track-0.json']['measures'][0]['voices'][0]['beats'][2]['velocity']=None
    inv=inventory(facts(d));target=next(r for r in inv['declarations']if r['fact_ref']==TARGET);self.assertEqual(target['reasons'],[])
    null=next(r for r in inv['declarations']if r['fact_ref'].endswith('/beats/2/velocity'));self.assertFalse(null['known']);self.assertIsNone(null['marking']);self.assertEqual(null['influence_refs'],[])
    s=next(s for s in inv['states']if s['occurrence_ref']=='event:93:0:1:0:2:0');self.assertEqual(s['marking'],'f');self.assertEqual(s['origin_fact_ref'],TARGET)
 def test_unknown_unrelated_voice_does_not_block_note_target(self):
    d=documents();d['track-0.json']['measures'][0]['voices'][1]['beats'][2]['velocity']='unknown'
    inv=inventory(facts(d));ref='track-0.json#/measures/0/voices/0/beats/1/notes/0/velocity';target=next(r for r in inv['declarations']if r['fact_ref']==ref);self.assertEqual(target['reasons'],[])
 def test_zero_and_observed_coincidence_are_distinct_from_change(self):
    before=facts(documents());zero=dict(released=False,changed=False)
    self.assertEqual(check(before,before,TARGET,[],zero)['issues'],[])
    same=option(before,TARGET,'f');self.assertFalse(same['changed']);self.assertEqual(check(before,before,TARGET,same['donor_refs'],decision(same))['issues'],[])
 def test_outside_raw_donor_and_decision_corruption_fail(self):
    d=documents();before=facts(d);o=option(before,TARGET,'mf');after=edited(d,'mf')
    self.assertEqual(check(before,after,TARGET,[],decision(o))['status'],'FAIL')
    bad=deepcopy(after);next(f for f in bad['facts']if f['id'].endswith('/notes/0/fret'))['value']=1
    self.assertEqual(check(before,bad,TARGET,o['donor_refs'],decision(o))['status'],'FAIL')
    wrong=decision(o);wrong['changed']=False;self.assertEqual(check(before,after,TARGET,o['donor_refs'],wrong)['status'],'FAIL')
    wrong=decision(o);wrong['released']=1;self.assertEqual(check(before,after,TARGET,o['donor_refs'],wrong)['status'],'FAIL')
 def test_unknown_targets_and_all_inherited_notes_do_not_create_votes(self):
    d=documents();d['track-0.json']['measures'][1]['voices'][0]['beats'][0]['velocity']='unknown'
    before=facts(d);unknown='track-0.json#/measures/1/voices/0/beats/0/velocity';self.assertEqual(choices(before,unknown)['options'],[])
    inv=inventory(before);self.assertEqual(len(inv['states']),24)
    self.assertTrue(all(s['marking']is None and s['known']is False for s in inv['states']if s['origin_fact_ref']==unknown))
 def test_native_guard_origin_survives_unknown_analytic_state_until_known_reset(self):
    d=documents();beats=d['track-0.json']['measures'][0]['voices'][0]['beats'];beats[2]['velocity']='unknown';beats[3]['notes'][0]['velocity']='unknown_note'
    inv=inventory(facts(d));target=next(r for r in inv['declarations']if r['fact_ref']==TARGET)
    self.assertIn('UNKNOWN_BEAT_BOUNDARY',target['reasons']);self.assertIn('UNKNOWN_NOTE_OVERRIDE',target['reasons'])
    row=next(r for r in inv['states']if r['occurrence_ref']=='event:93:0:1:0:3:0');self.assertEqual(row['provenance'],'note_explicit');self.assertFalse(row['known'])
 def test_unknown_rest_note_override_has_no_dynamic_execution(self):
    d=documents();note=d['track-0.json']['measures'][0]['voices'][0]['beats'][2]['notes'][0];note.update(rest=True,velocity='unknown')
    row=next(r for r in inventory(facts(d))['declarations']if r['fact_ref']==TARGET);self.assertNotIn('UNKNOWN_NOTE_OVERRIDE',row['reasons'])
 def test_cached_independent_choices_and_actual_output_equal_uncached(self):
    from check_local_dynamics import Oracle
    d=documents();before=facts(d);o=Oracle(before)
    self.assertEqual(o.inventory(),inventory(before));self.assertEqual(o.choices(TARGET),choices(before,TARGET))
    choice=option(before,TARGET,'mf');after=edited(d,'mf')
    self.assertEqual(o.check(after,TARGET,choice['donor_refs'],decision(choice)),check(before,after,TARGET,choice['donor_refs'],decision(choice)))
    bad=o.inventory();bad['declarations'].clear();self.assertTrue(o.inventory()['declarations'])
 def test_released_empty_palette_keeps_exact_no_choice(self):
    d=documents();before=facts(d)
    # Voice1 has only one source marking; there is no independent donor.
    ref='track-0.json#/measures/0/voices/1/beats/0/velocity'
    nochoice=dict(status='NO_ADMITTED_CHOICE',released=True,changed=False)
    self.assertEqual(choices(before,ref)['options'],[])
    self.assertEqual(check(before,before,ref,[],nochoice)['issues'],[])
    bad=dict(nochoice,chosen=dict(marking='f',donor_refs=[],changed=True))
    self.assertEqual(check(before,before,ref,[],bad)['status'],'FAIL')
    # Nonempty palettes cannot fabricate an absent selected option.
    self.assertEqual(check(before,before,TARGET,[],nochoice)['status'],'FAIL')
    # A refused boundary also has an empty palette and may retain exact source.
    d['track-0.json']['measures'][0]['voices'][0]['beats'][2]['velocity']='unknown'
    unsafe=facts(d);self.assertEqual(choices(unsafe,TARGET)['options'],[])
    self.assertEqual(check(unsafe,unsafe,TARGET,[],nochoice)['issues'],[])
 def test_actual_change_requires_released_true(self):
    d=documents();before=facts(d);o=option(before,TARGET,'mf');after=edited(d,'mf');wrong=dict(released=False,changed=True,chosen=o)
    self.assertEqual(check(before,after,TARGET,o['donor_refs'],wrong)['status'],'FAIL')
if __name__=='__main__':unittest.main()
