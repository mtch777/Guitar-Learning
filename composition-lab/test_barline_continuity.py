import copy,unittest
import test_role_pitch_transfer as transfer_fixture
from test_form_returns import case
from barline_continuity import apply,fit_register,apply_register,boundary_observations
from generation_freedom import facets,mix
from role_pitch_transfer import propose,locked_context
from form_returns import apply as returns

class BarlineTests(unittest.TestCase):
    def setup(self):
        c,r,m,roles=transfer_fixture.TransferTests().setup()
        return c,r,m,roles,[dict(start=0,length=2,identity=0)]
    def test_zero_and_unsupported_intermediate(self):
        c,r,m,roles,s=self.setup()
        self.assertEqual(apply(r,roles,None,None,s,freedom=0)[0],r)
        for f in (True,50,-1,101):
            with self.assertRaises(ValueError):apply(r,roles,c,m,s,freedom=f)
    def test_reset_matches_existing_and_other_dimensions_lock(self):
        c,r,m,roles,s=self.setup();p,_=propose(locked_context(r,roles),roles,c,m,17)
        expected=returns(mix(r,p,{'melody':100},roles)[0],s,roles,{'melody':100})[0]
        self.assertEqual(apply(r,roles,c,m,s,mode='bar_reset')[0],expected)
        out,a=apply(r,roles,c,m,s)
        for key in ('harmony','bass','rhythm','form','instrumentation','performance'):
            self.assertEqual(facets(r,roles)[key],facets(out,roles)[key])
    def test_unlocked_ignores_original_melody_pitch(self):
        c,r,m,roles,s=self.setup();other=copy.deepcopy(r)
        for bar in other['tracks'][1]['measures']:
            for e in bar['voices'][0]:
                for n in e['notes']:n['midi']+=1;n['fret']+=1
        self.assertEqual(apply(r,roles,c,m,s),apply(other,roles,c,m,s))
    def test_return_history_is_final_and_exact(self):
        c,_,m,roles,_=self.setup();r,s,roles=case();out,a=apply(r,roles,c,m,s)
        self.assertEqual(a['returns']['changed_track_bars'],0)
        for i in (0,1):
            self.assertEqual([e['notes'] for e in out['tracks'][1]['measures'][i]['voices'][0]],
                             [e['notes'] for e in out['tracks'][1]['measures'][i+2]['voices'][0]])
    def test_register_prior_requires_development_and_provenance(self):
        c,r,m,roles,s=self.setup();sid=c['training_songs'][0]
        row=dict(partition='development',role='melody',song_id=sid,family=m['training_families'][0],register=12)
        model=fit_register([row],c);out,a=apply(r,roles,c,m,s,mode='register_carry',register_model=model)
        model['source_composer_sha256']='wrong'
        with self.assertRaises(ValueError):apply(r,roles,c,m,s,mode='register_carry',register_model=model)
        row['partition']='held_out'
        with self.assertRaises(ValueError):fit_register([row],c)
    def test_fixed_factor_and_invalid_model_refusal(self):
        model=dict(schema='experimental-boundary-register-prior-v1',alpha=.0001,probabilities={'1':1})
        p=apply_register([.5,.5],0,model);self.assertGreater(p[1],p[0]);self.assertAlmostEqual(sum(p),1)
        model['alpha']=0
        with self.assertRaises(ValueError):apply_register([.5,.5],0,model)

    def test_source_boundaries_exclude_unknown_sections_and_dead_notes(self):
        from test_corpus_composer import fixture,model_for
        report,raw=fixture();c=model_for(report,raw)
        data=boundary_observations(c,report)
        self.assertEqual(len(data['events']),2)
        for change in ('unknown','dead','tie'):
            r=copy.deepcopy(report)
            for track in r['songs'][0]['tracks']:
                for n in track['rows']:
                    if n['onset_q']=='4':
                        if change=='unknown':n['section_start']=None
                        elif change=='dead':n['raw_note']={'dead':True}
                        else:n['tie_destination']=True
            self.assertEqual(boundary_observations(c,r)['events'],[])

    def test_source_pitch_join_discrepancy_refused(self):
        from test_corpus_composer import fixture,model_for
        report,raw=fixture();c=model_for(report,raw)
        for t in report['songs'][0]['tracks']:
            for n in t['rows']:
                if n['onset_q']=='4':n['midi']+=1
        with self.assertRaisesRegex(ValueError,'pitch join'):boundary_observations(c,report)

    def test_export_refuses_locked_bass_change_and_existing_output(self):
        import tempfile,json
        from pathlib import Path
        from gp_author import write_gp
        from barline_continuity import export
        c,r,m,roles,s=self.setup()
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'core.gp';target=Path(directory)/'out.gp'
            write_gp(r,source)
            source.with_suffix('.expected.json').write_text(json.dumps(r),encoding='utf-8')
            altered=copy.deepcopy(r)
            n=altered['tracks'][2]['measures'][0]['voices'][0][0]['notes'][0]
            n['midi']+=1;n['fret']+=1
            with self.assertRaisesRegex(ValueError,'melody pitches only'):export(source,altered,target,roles)
            self.assertFalse(target.exists())
            target.write_bytes(b'preserve')
            with self.assertRaises(FileExistsError):export(source,r,target,roles)
            self.assertEqual(target.read_bytes(),b'preserve')

    def test_carry_requires_contiguous_notes_and_same_section(self):
        from barline_continuity import _propose
        c,r,m,roles,s=self.setup()
        for t in r['tracks']:
            for mi,bar in enumerate(t['measures']):
                bar['voices']=[[dict(onset_q=str(mi*4+i),local_onset_q=str(i),duration_q='1',
                    notes=[dict(midi=t['tunings'][0][0]+5,string=0,fret=5,tie=None,technique_tags=[])]) for i in range(4)]]
        def boundary(score,sections=s):
            _,ds=_propose(score,roles,c,m,sections,17,True)
            return [d for d in ds if d['track']==1 and d['bar']==2][0]
        self.assertTrue(boundary(r)['carried_at_bar_start'])
        for mi,ei in ((0,-1),(1,0)):
            other=copy.deepcopy(r);other['tracks'][1]['measures'][mi]['voices'][0][ei]['notes']=[]
            self.assertFalse(boundary(other)['carried_at_bar_start'])
            self.assertIsNone(boundary(other)['input_previous'])
        self.assertFalse(boundary(r,[dict(start=0,length=1,identity=0),dict(start=1,length=1,identity=1)])['carried_at_bar_start'])

if __name__=='__main__':unittest.main()
