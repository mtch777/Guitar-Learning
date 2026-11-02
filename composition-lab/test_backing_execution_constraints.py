"""Synthetic counterexamples for the shared execution guard, not musical fit."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import backing_execution_constraints as guard
import backing_pitch_ownership as owner
from connected_tier2 import analyze,strip_lower,realize,validate
from source_fact_tier1 import extract_documents
from test_execution_dependencies import documents,n


def ref(beat,note=0,voice=0):return f'event:86:0:1:{voice}:{beat}:{note}'
def source(kind='hp'):
    notes=[n(2,**({'hp':True}if kind=='hp'else{'slide':'shift'})),n(7),n(8),n(9)]
    return documents(notes)
def tier(docs):return extract_documents(docs)
def top(docs,refs):
    docs=deepcopy(docs)
    other=dict(songId=86,revisionId=1,partId=1,instrumentId=25,tuning=[64,59,55,50,45,40],frets=24,
               measures=[dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=[dict(string=0,fret=0)])])])])
    docs['track-1.json']=other;docs['metadata.json']['tracks'].append(dict(name='Backing',instrumentId=25))
    before=tier(docs);out=strip_lower(analyze(before))
    bindings=[dict(occurrence_ref=r,backing_ref='event:86:1:1:0:0:0')for r in refs]
    out['musical_relationships']=owner.lift(out['musical_relationships'],bindings,tier1=before,preserve_execution=True)
    return before,out

def alter_interval(upper,ref,delta):
    out=deepcopy(upper);row=next(r for r in out['musical_relationships']['relationships']if r['occurrence_ref']==ref)
    row['interval_semitones']=str(int(row['interval_semitones'])+delta)
    return out

def string_edit(upper,reference,string):
    _,part,bar,voice,beat,note=owner.address(reference);ident=f'track-{part}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}/notes/{note}/string'
    row=next(r for r in upper['owned_parameters']['source_choices']if r['fact_ref']==ident)
    row['parameter']['normalized']=str(string)


class ExecutionGuardTests(unittest.TestCase):
    def test_distance_change_passes_but_hopo_direction_and_string_do_not(self):
        before=tier(source());refs=[ref(1)];scope=guard.build(before,refs);unchanged=deepcopy(before)
        guard.proposed(scope,before,refs,{ref(1):dict(string=5,fret=8)})
        self.assertEqual(before,unchanged)
        for contact in (dict(string=5,fret=1),dict(string=4,fret=2)):
            with self.assertRaises(ValueError):guard.proposed(scope,before,refs,{ref(1):contact})
        self.assertEqual(before,unchanged)
        self.assertFalse(any(k in json.dumps(scope)for k in ('fret_distance','interval_semitones','"pitch"','"fret"')))

    def test_slide_distance_changes_but_direction_does_not(self):
        before=tier(source('slide'));refs=[ref(1)];scope=guard.build(before,refs)
        guard.proposed(scope,before,refs,{ref(1):dict(string=5,fret=9)})
        with self.assertRaises(ValueError):guard.proposed(scope,before,refs,{ref(1):dict(string=5,fret=1)})

    def test_coupled_string_moves_keep_execution_kind_when_contacts_remain_valid(self):
        before=tier(source());refs=[ref(0),ref(1)];scope=guard.build(before,refs)
        guard.proposed(scope,before,refs,{ref(0):dict(string=4,fret=9),ref(1):dict(string=4,fret=15)})
        # Fretted hammer stays a fretted hammer; neither absolute strings nor
        # the old five-semitone distance are secretly frozen in the guard.

    def test_affected_unknown_refuses_but_distant_unknown_is_disclosed(self):
        docs=documents([n(2,hp=True),n(2),n(4),n(6)])
        with self.assertRaisesRegex(ValueError,'UNRESOLVED_AFFECTED_EXECUTION'):
            guard.build(tier(docs),[ref(1)])
        scope=guard.build(tier(docs),[ref(3)])
        self.assertEqual(len(scope['unresolved_outside_neighborhood']),1)
        guard.validate(scope,tier(docs),[ref(3)])

    def test_unspecified_exit_and_ring_end_do_not_create_backward_or_distant_links(self):
        docs=documents([n(2),n(4),n(6),n(7,slide='downwards')])
        scope=guard.build(tier(docs),[ref(2)])
        self.assertEqual(scope['unresolved_outside_neighborhood'][0]['status'],'exit_target_unspecified')
        docs=documents([n(2),dict(string=4,fret=2),dict(string=4,fret=4),n(7)],{0:dict(letRing=True)})
        scope=guard.build(tier(docs),[ref(3)])
        self.assertEqual(scope['unresolved_outside_neighborhood'][0]['status'],'declaration_only_unknown_end')

    def test_failed_tie_prefix_does_not_claim_later_notes_as_dependencies(self):
        for field in ({'hp':True},{'slide':'legato'}):
            docs=documents([n(2,**field),n(3,tie=True),n(5),n(6)])
            scope=guard.build(tier(docs),[ref(2)])
            self.assertEqual(len(scope['unresolved_outside_neighborhood']),1)
        docs=documents([n(2,slide='legato',tie=True),n(3),n(5),n(6)])
        scope=guard.build(tier(docs),[ref(1)])
        self.assertEqual(scope['unresolved_outside_neighborhood'][0]['status'],'origin_tie_requires_chain')

    def test_neighborhood_uses_each_approved_primitive_sort_order(self):
        from fractions import Fraction as F
        def node(beat,q):
            return dict(ref=ref(beat),part=0,voice=0,string=5,string_valid=True,
                        onset=F(q),duration=F(1),grace=False,tie_destination=False,
                        pitch=42,fret=2,bar=1,beat=beat,note=0,
                        occurrence=f'0:1:0:{beat}:0')
        nodes={ref(i):node(i,q)for i,q in [(0,0),(2,1),(10,1)]}
        hp=dict(kind='hopo',status='unresolved',slide_type=None,origin_ref=ref(0),member_refs=[ref(0)])
        slide=dict(kind='slide',status='same_fret',slide_type='shift',origin_ref=ref(0),member_refs=[ref(0)])
        self.assertEqual(guard._neighborhood(hp,nodes),{ref(0),ref(10)})
        self.assertEqual(guard._neighborhood(slide,nodes),{ref(0),ref(2)})

    def test_all_voice_written_collision_refuses_without_claiming_ring_end(self):
        docs=documents([n(0),dict(string=4,fret=2),n(4),n(5)])
        docs['track-0.json']['measures'][0]['voices'].append(dict(beats=[dict(duration=[1,1],notes=[dict(string=3,fret=0)])]))
        before=tier(docs);refs=[ref(1)];scope=guard.build(before,refs)
        with self.assertRaisesRegex(ValueError,'WRITTEN_STRING_COLLISION'):
            guard.proposed(scope,before,refs,{ref(1):dict(string=3,fret=0)})
        self.assertEqual(scope['written_string_occupancy']['sounding_ring_end'],'not_inferred')

    def test_deleted_stale_or_extra_payload_is_refused(self):
        before=tier(source());refs=[ref(1)];scope=guard.build(before,refs)
        for mode in ('removed','payload','stale'):
            bad=deepcopy(scope)
            if mode=='removed':bad['obligations']=[]
            elif mode=='payload':bad['obligations'][0]['old_pitch']=47
            else:bad['obligations'][0]['direction']='pull_off'
            with self.assertRaises(ValueError):guard.validate(bad,before,refs)

    def test_v3_source_zero_inverse_and_direct_corruptions(self):
        before,upper=top(source(),[ref(1)])
        self.assertEqual(upper['musical_relationships']['schema'],owner.EXECUTION_SCHEMA)
        self.assertEqual(realize(upper),before);self.assertEqual(validate(upper),before)
        allowed=alter_interval(upper,ref(1),1)
        expected=deepcopy(before);row=next(r for r in expected['facts']if r['id']=='track-0.json#/measures/0/voices/0/beats/1/notes/0/fret');row['value']=8
        self.assertEqual(realize(allowed),expected)
        with self.assertRaises(ValueError):realize(alter_interval(upper,ref(1),-6))
        wrong=deepcopy(upper);string_edit(wrong,ref(1),4)
        with self.assertRaises(ValueError):realize(wrong)
        missing=deepcopy(upper);del missing['musical_relationships']['execution_constraints']
        with self.assertRaises(ValueError):realize(missing)
        emptied=deepcopy(upper);emptied['musical_relationships']['execution_constraints']['obligations']=[]
        with self.assertRaises(ValueError):realize(emptied)
        self.assertEqual(allowed['source_origin'],upper['source_origin'])

    def test_actual_isolated_inverse_uses_the_guard_without_source(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before,upper=top(source(),[ref(1)]);code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as tmp:
            zero=execute(code,upper,{'variation':0},before,Path(tmp)/'zero',timeout=40)
            self.assertEqual(zero['status'],'PASS',zero)
            wrong=alter_interval(upper,ref(1),-6);folder=Path(tmp)/'wrong'
            bad=execute(code,wrong,{'variation':0},before,folder,timeout=40)
            self.assertEqual(bad['status'],'FAIL')
            audit=json.loads((folder/'worker/audit.json').read_text())
            self.assertIn('EXECUTION_OBLIGATIONS_CHANGED',audit['error']['message'])
            self.assertFalse((folder/'worker/output.json').exists())


if __name__=='__main__':unittest.main()
