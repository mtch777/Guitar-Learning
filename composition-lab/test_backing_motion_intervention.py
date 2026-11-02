"""Authored contrasts for the bounded observed relationship, not artist evidence."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize,reconstruct
import backing_motion_intervention as motion

SOURCE=[f'event:987:0:1:0:{i}:0' for i in range(3)]
TARGET=[f'event:987:0:2:0:{i}:0' for i in range(3)]

def documents():
    def note(s,f): return dict(string=s,fret=f)
    def beat(notes,duration): return dict(duration=duration,notes=notes)
    def measure(beats): return dict(signature=[4,4],voices=[dict(beats=beats+[beat([dict(rest=True)],[3,4])])])
    reference=measure([beat([note(3,7)],[1,16]),beat([note(3,5)],[1,16]),beat([note(3,7)],[1,8])])
    target=measure([beat([note(2,2)],[1,16]),beat([note(2,0)],[1,16]),beat([note(3,2)],[1,8])])
    source_backing=measure([beat([note(5,7),note(3,4),note(2,4),note(1,4)],[1,4])])
    target_backing=measure([beat([note(3,4),note(2,4)],[1,16]),beat([note(3,2),note(2,2)],[1,16]),beat([note(3,4),note(2,4)],[1,8])])
    return {'metadata.json':dict(songId=987,revisionId=1,artist='Fixture',title='Moving backing',tracks=[dict(name='Bass',instrumentId=34),dict(name='Guitar',instrumentId=27)]),
            'track-0.json':dict(songId=987,revisionId=1,partId=0,instrumentId=34,tuning=[43,38,33,28],frets=24,measures=[reference,target]),
            'track-1.json':dict(songId=987,revisionId=1,partId=1,instrumentId=27,tuning=[64,59,55,50,45,40],frets=24,measures=[source_backing,target_backing])}

def model(docs=None):
    before=extract_documents(documents() if docs is None else docs)
    return before,strip_lower(analyze(before))

def controls(level=100,physical=100,seed=0):
    return dict(context_policy=motion.POLICY,melody=level,physical=physical,source_refs=SOURCE,target_refs=TARGET,backing_part=1,seed=seed)

class BackingMotionInterventionTests(unittest.TestCase):
    def test_note_octave_changes_require_separate_explicit_permission(self):
        docs=documents()
        beats=docs['track-0.json']['measures'][1]['voices'][0]['beats']
        for beat,contact in zip(beats,[(0,4),(0,2),(1,4)]):
            beat['notes'][0]=dict(string=contact[0],fret=contact[1])
        before,upper=model(docs);snapshot=deepcopy(upper)
        with self.assertRaisesRegex(ValueError,'NOTE_OCTAVE_PERMISSION_REQUIRED'):
            motion.intervene(upper,controls())
        self.assertEqual(upper,snapshot)
        request=dict(controls(),allow_note_octave_changes=True)
        changed,decision=motion.intervene(upper,request)
        self.assertEqual(decision['chosen']['pitches'],['35','31','35'])
        self.assertTrue(all(r['before_octave']==2 and r['after_octave']==1 for r in decision['pitch_changes']))
        self.assertEqual(motion.intervene(upper,dict(request,melody=0))[0],upper)
        for invalid in (1,'true',None):
            with self.assertRaises(ValueError):motion.validate_controls(dict(request,allow_note_octave_changes=invalid))

    def test_nonconstant_relation_changes_target_through_owned_inverse(self):
        before,upper=model(); edited,decision=motion.intervene(upper,controls())
        self.assertEqual([x['match']['selected_delta'] for x in decision['correspondences']],[0,-2,0])
        self.assertEqual(decision['chosen']['pitches'],['35','31','35'])
        expected=documents(); beats=expected['track-0.json']['measures'][1]['voices'][0]['beats']
        beats[1]['notes'][0]=dict(string=3,fret=3); beats[2]['notes'][0]=dict(string=3,fret=7)
        self.assertEqual(project_documents(realize(edited)),expected)
        self.assertEqual(reconstruct(upper,controls()),realize(edited))
        self.assertEqual(realize(upper),before)
        self.assertEqual(edited['source_origin'],upper['source_origin'])

    def test_zero_literal_and_measured_release(self):
        before,upper=model()
        self.assertEqual(motion.intervene(upper,controls(0,0))[0],upper)
        prepared=motion.prepare(upper,controls())
        from declared_degree_choices import sample
        rates={v:[sample(prepared,dict(voicing=v,seed=s))[1] for s in range(128)] for v in (0,50,100)}
        self.assertFalse(any(x['released'] for x in rates[0]))
        self.assertTrue(all(x['released'] for x in rates[100]))
        self.assertTrue(any(x['released'] for x in rates[50]) and any(not x['released'] for x in rates[50]))
        for seed in (0,1):
            edited,result=motion.intervene(upper,controls(50,seed=seed))
            self.assertEqual(result['released'],rates[50][seed]['released'])
            self.assertEqual(edited==upper,not result['released'])
        self.assertEqual(realize(upper),before)

    def test_physical_lock_refuses_atomically(self):
        _,upper=model(); snapshot=deepcopy(upper)
        with self.assertRaisesRegex(ValueError,'PHYSICAL_LOCK_CONFLICT'):
            motion.intervene(upper,controls(100,0))
        self.assertEqual(upper,snapshot)

    def test_generated_notes_never_become_source_votes(self):
        _,upper=model(); changed,_=motion.intervene(upper,controls())
        snapshot=deepcopy(changed)
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CHAINED_EVIDENCE'):
            motion.intervene(changed,controls())
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CHAINED_EVIDENCE'):
            motion.prepare(changed,controls())
        self.assertEqual(changed,snapshot)
        self.assertEqual(motion.intervene(changed,controls(0))[0],changed)

    def test_target_pitch_cannot_choose_backing_translation(self):
        docs=documents(); docs['track-0.json']['measures'][1]['voices'][0]['beats'][2]['notes'][0]['fret']=8
        _,a=model(); _,b=model(docs)
        request=dict(controls(),allow_note_octave_changes=True)
        pa=motion.prepare(a,request); pb=motion.prepare(b,request)
        self.assertEqual(pa['correspondences'],pb['correspondences'])
        self.assertEqual(pa['options'][0]['pitches'],pb['options'][0]['pitches'])

    def test_unknown_backing_and_focal_execution_refuse(self):
        for which in ('backing','focal'):
            docs=documents()
            note=docs['track-1.json' if which=='backing' else 'track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0]
            note['dead' if which=='backing' else 'slide']=True
            _,upper=model(docs)
            with self.assertRaises(ValueError): motion.intervene(upper,controls())

    def test_invalid_controls(self):
        for key,value in [('melody',True),('melody',float('nan')),('melody',101),('physical',50),('seed',True),('backing_part',False)]:
            with self.assertRaises(ValueError): motion.validate_controls(dict(controls(),**{key:value}))

    def test_actual_source_denied_changed_inverse(self):
        from pathlib import Path
        import tempfile
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        _,upper=model(); edited,_=motion.intervene(upper,controls())
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as temp:
            receipt=execute(code,upper,controls(),realize(edited),Path(temp)/'worker',timeout=40,purpose='observed_backing_motion')
        self.assertEqual(receipt['status'],'PASS',receipt)
        self.assertFalse(receipt['parent_expected_staged'])

if __name__=='__main__': unittest.main()
