import copy
import tempfile
import unittest
from pathlib import Path

from engine_contract import proposal_context, request, audit_existing_edit, _selected
from gp_author import write_gp
from learned_performance import apply, FAMILIES
from test_learned_performance import fixture
from artist_profiles import fit
from palm_mute_method import apply as apply_palm

METHOD_SOURCE=Path(__file__).with_name('learned_performance.py')


def support():
    return dict(known=True, eligible_mass_q='3/2',
                denominator_unit='family_weighted_eligible_mass', model_sha256='a'*64)


class EngineContractTests(unittest.TestCase):
    def test_original_targets_cannot_enter_context(self):
        a=dict(duration_q='1/3', midi=60, fret=5, bend='<original/>', provenance={'source':'private'})
        b=copy.deepcopy(a); b['bend']='<different/>'; b['provenance']={'source':'other'}
        self.assertEqual(proposal_context('continuous_expression', a), proposal_context('continuous_expression', b))
        transition=proposal_context('directed_transition',dict(origin=a,destination=a,gap_q='0'))
        self.assertNotIn('bend',transition['origin'])
        transition['origin']['fret']=9
        self.assertEqual(a['fret'],5)
        with self.assertRaises(ValueError):
            proposal_context('sequence_context',dict(previous_output_state={'original':True}))
        for bad in ({'midi':'<original/>'},{'duration_q':'<original/>'},{'duration_q':.1},{'fret':True}):
            with self.assertRaises(ValueError):proposal_context('continuous_expression',bad)
        self.assertEqual(proposal_context('sequence_context',dict(duration_q='1/3',previous_output_state=True)),
                         dict(duration_q='1/3',previous_output_state=True))
        self.assertEqual(proposal_context('role_harmony',dict(tuning=[28,33],locked_harmony=[40,47],target='hidden')),
                         dict(tuning=[28,33],locked_harmony=[40,47]))

    def test_refusals_and_zero_lock(self):
        self.assertEqual(request('bend','written_curve',0,None)['status'],'locked')
        self.assertEqual(request('bend','written_curve',100,None)['reason'],'unknown_support')
        self.assertEqual(request('melody','function_relative_octave',100,support())['reason'],'unsupported_representation')
        self.assertEqual(request('bend','written_curve',100,support(),conflicts=['lock'])['reason'],'conflicting_locks')
        s=support();s['eligible_mass_q']=.1
        with self.assertRaises(ValueError):request('bend','written_curve',100,s)

    def test_disabled_marker_is_not_selection(self):
        for xml, expected in [('<Enable/>',True),('<Disable/>',False),('',False)]:
            note=dict(note_xml='<Note><Properties><Property name="PalmMuted">'+xml+'</Property></Properties></Note>')
            self.assertEqual(_selected(note,'palm_mute',{'PalmMuted'}),expected)

    def test_actual_edit_and_tampered_claims(self):
        score, model, shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'source.gp')
            freedoms={f:100 for f in FAMILIES}
            audit=apply(p/'source.gp',p/'out.gp',model,shapes,'Artist',freedoms)
            supports={f:support() for f in FAMILIES}
            def check(a):
                return audit_existing_edit(p/'source.gp',p/'out.gp',a,freedoms,supports,method='learned_performance.apply',method_source=METHOD_SOURCE)
            result=check(audit)
            self.assertGreater(len(result['decisions']),0)
            self.assertEqual(result['validation']['native_playback'],'not_checked_here')
            altered=copy.deepcopy(audit);altered['decisions'][0]['proposed_selected']=not altered['decisions'][0]['proposed_selected']
            with self.assertRaises(AssertionError):check(altered)
            altered=copy.deepcopy(audit);altered['sha256']='0'*64
            with self.assertRaises(ValueError):check(altered)
            altered=copy.deepcopy(audit);altered['decisions'][0]['released']=False
            with self.assertRaises(AssertionError):check(altered)
            altered=copy.deepcopy(audit);altered['decisions'].append(copy.deepcopy(altered['decisions'][0]))
            with self.assertRaises(ValueError):check(altered)
            altered=copy.deepcopy(audit)
            pair=next(d for d in altered['decisions'] if 'origin' in d)
            pair['origin'],pair['destination']=pair['destination'],pair['origin']
            with self.assertRaises(ValueError):check(altered)

    def test_actual_zero_method_is_byte_identical(self):
        score,model,shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'source.gp')
            audit=apply(p/'source.gp',p/'zero.gp',model,shapes,'Artist',{})
            result=audit_existing_edit(p/'source.gp',p/'zero.gp',audit,{'bend':0},{},method='learned_performance.apply',method_source=METHOD_SOURCE)
            self.assertEqual(result['source_sha256'],result['output_sha256'])

    def test_whole_coattack_and_intermediate_release_are_verified(self):
        score,_,_=fixture()
        for measure in score['tracks'][0]['measures']:
            for event in measure['voices'][0]:
                other=copy.deepcopy(event['notes'][0]);other.update(midi=other['midi']+7,string=1)
                event['notes'].append(other)
        score['tracks'][0]['tunings']=[[40,47]]
        model=fit([dict(song_id=1,family='f',partition='development',flagged=False,
                        artist='Artist',context='training',labels=['palm_mute'])])
        model.update(schema='eligible-palm-mute-v1',source_training_sha256='fixture')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'source.gp')
            audit=apply_palm(p/'source.gp',p/'out.gp',model,'Artist',50)
            def check(a):
                return audit_existing_edit(p/'source.gp',p/'out.gp',a,{'palm_mute':50},
                    {'palm_mute':support()},method='palm_mute_method.apply',
                    method_source=Path(__file__).with_name('palm_mute_method.py'))
            self.assertEqual(len(check(audit)['decisions']),8)
            broken=copy.deepcopy(audit);broken['decisions'][0]['members'].pop()
            with self.assertRaises(ValueError):check(broken)
            broken=copy.deepcopy(audit);broken['decisions'][0]['released']=not broken['decisions'][0]['released']
            with self.assertRaises(AssertionError):check(broken)


if __name__ == '__main__':unittest.main()
