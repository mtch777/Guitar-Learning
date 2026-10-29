"""Authored musical contrasts; not artist/listening evidence."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import context_membership as lock
import nominal_harmony as nominal
import musical_tier2 as music
from connected_tier2 import realize,strip_lower,reconstruct
from test_nominal_harmony import documents,run,beat
from check_context_membership import check

REF='event:77:0:1:0:0:0'
REQUEST=dict(edited_refs=[REF],scope='ensemble_minus_edited')


def fixture(pitch=60):
    docs=documents();docs['track-0.json']['tuning']=[pitch]
    return run(docs)


def change(upper,pitch):
    out=deepcopy(upper);core=out['musical_relationships']
    group=next(g for g in core['coattacks'] if any(m['id']==REF for m in g['members']))
    assert len(group['members'])==1
    group['bass_register_anchor']=str(pitch)
    out['musical_relationships']=music.strip_lower(music.analyze(music.realize(core)))
    return out


class MembershipLockTests(unittest.TestCase):
    def test_tier1_projection_is_identical_to_existing_owned_projection(self):
        before,upper,view=fixture()
        self.assertEqual(nominal.build(nominal.prepare_tier1(before)),view)

    def test_member_pitch_can_change_but_unknown_role_is_not_permission(self):
        before,upper,_=fixture();bound=lock.attach(upper,REQUEST)
        edited=change(bound,64);after=realize(edited)
        self.assertNotEqual(after,before)
        self.assertEqual(lock.assess(after,bound['membership_lock'])['status'],'SUPPORTED')
        self.assertEqual(check(before,after,bound['membership_lock'])['status'],'PASS_INDEPENDENT_CONTEXT_MEMBERSHIP')
        with self.assertRaisesRegex(ValueError,'CONTRADICTED'):realize(change(bound,62))

    def test_nonmember_lock_does_not_automatically_force_chord_tones(self):
        before,upper,_=fixture(62);bound=lock.attach(upper,REQUEST)
        self.assertEqual(lock.assess(realize(change(bound,65)),bound['membership_lock'])['status'],'SUPPORTED')
        with self.assertRaisesRegex(ValueError,'CONTRADICTED'):realize(change(bound,64))

    def test_zero_and_allowed_change_use_actual_source_denied_worker(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before,upper,_=fixture();bound=lock.attach(upper,REQUEST);code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            for name,value,expected in [('zero',bound,before),('changed',change(bound,64),realize(change(bound,64)))]:
                result=execute(code,strip_lower(value),dict(variation=0),expected,Path(folder)/name,timeout=30)
                self.assertEqual(result['status'],'PASS',result)
        self.assertEqual(reconstruct(strip_lower(bound),dict(variation=0)),before)

    def test_held_note_checks_later_harmony_too(self):
        docs=documents();docs['track-0.json']['tuning']=[60]
        docs['track-1.json']['tuning']=[48,52,55,59,62]
        docs['track-1.json']['measures'][0]['voices'][0]['beats']=[beat([1,2],[0,1,2]),beat([1,2],[2,3,4])]
        before,upper,_=run(docs);packet=lock.compile_lock(before,REQUEST)['packet']
        after=realize(change(upper,69));reported=lock.assess(after,packet)
        self.assertEqual(reported['status'],'AMBIGUOUS')
        self.assertEqual(check(before,after,packet,reported=reported)['status'],'PASS_INDEPENDENT_CONTEXT_MEMBERSHIP')

    def test_missing_later_support_cannot_be_ignored(self):
        docs=documents();docs['track-0.json']['tuning']=[60]
        docs['track-1.json']['measures'][0]['voices'][0]['beats']=[beat([1,2],[0,1,2]),dict(duration=[1,2],notes=[dict(rest=True)])]
        before,upper,_=run(docs)
        self.assertEqual(lock.compile_lock(before,REQUEST)['status'],'MISSING')
        with self.assertRaisesRegex(ValueError,'unavailable'):lock.attach(upper,REQUEST)
        self.assertEqual(realize(upper),before)

    def test_edited_notes_never_certify_other_edited_notes(self):
        before,upper,_=fixture()
        request=dict(REQUEST,edited_refs=sorted([REF,'event:77:1:1:0:0:1','event:77:1:1:0:0:2']))
        self.assertEqual(lock.compile_lock(before,request)['status'],'MISSING')

    def test_expression_qualification_is_missing_not_nonmember(self):
        for pid in (0,1):
            docs=documents();docs[f'track-{pid}.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['vibrato']=True
            before,upper,_=run(docs)
            self.assertEqual(lock.compile_lock(before,REQUEST)['status'],'MISSING')

    def test_omitted_context_and_boolean_corruption_are_rejected(self):
        before,upper,_=fixture();packet=lock.compile_lock(before,REQUEST)['packet']
        corrupt=deepcopy(packet);corrupt['contexts'][0]['memberships'][0]['values']=[1]
        with self.assertRaisesRegex(ValueError,'Boolean'):lock.assess(before,corrupt)
        corrupt=deepcopy(packet);corrupt['contexts'][0]['support_refs'].pop()
        self.assertEqual(lock.assess(before,corrupt)['status'],'MISSING')
        corrupt=deepcopy(packet);corrupt['original_pitch']=60
        with self.assertRaises(ValueError):lock.assess(before,corrupt)

    def test_values_cannot_move_between_occurrences_with_equal_total(self):
        docs=documents();docs['track-0.json']['tuning']=[60,64]
        docs['track-0.json']['measures'][0]['voices'][0]['beats']=[beat([1,1],[0,1])]
        docs['track-1.json']['tuning']=[48,52,55,57]
        docs['track-1.json']['measures'][0]['voices'][0]['beats']=[beat([1,1],[0,1,2,3])]
        before,_,_=run(docs)
        request=dict(REQUEST,edited_refs=[REF,'event:77:0:1:0:0:1'])
        packet=lock.compile_lock(before,request)['packet']
        a,b=packet['contexts'][0]['memberships']
        self.assertEqual(len(a['values']),2);a['values'].append(b['values'].pop())
        with self.assertRaisesRegex(ValueError,'Per-occurrence'):lock.assess(before,packet)


if __name__=='__main__':unittest.main()
