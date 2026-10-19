import copy,json,tempfile,unittest,zipfile
from pathlib import Path
from fractions import Fraction as F
from xml.etree import ElementTree as ET
from artist_profiles import fit
from learned_performance import apply,FAMILIES,native_curve_exact,learn_shapes
from contextual_bends import segment_properties
from gp_author import write_gp
from technique_analysis import analyze
from exact_score import extract_score
from technique_edits import transact


def fixture():
    measures=[]
    for bar in range(2):
        events=[]
        for i,fret in enumerate((0,5,0,7)):
            events.append(dict(onset_q=str(bar*4+i),local_onset_q=str(i),duration_q='1',notes=[dict(midi=40+fret,string=0,fret=fret,tie=None,technique_tags=[])]))
        measures.append(dict(number=bar+1,onset_q=str(bar*4),time_signature='4/4',voices=[events]))
    score=dict(tracks=[dict(index=0,name='guitar',program=30,tunings=[[40]],measures=measures)])
    events=[dict(song_id=1,family='f',partition='development',flagged=False,artist='Artist',context='training',labels=list(FAMILIES))]
    model=fit(events,alpha=F(1,10**9))
    model['schema']='artist-performance-opportunity-v1'
    model['training_source_sha256']='fixture-source'
    props=segment_properties([(F(0),F(0)),(F(1,2),F(2)),(F(1),F(2))],F(0),F(1))
    shapes=dict(schema='training-bend-shapes-v1',artist='Artist',training_source_sha256='fixture-source',training_songs=[1],training_sha256='fixture',families={'f':{'1':[dict(properties=props)]}})
    return score,model,shapes


class LearnedPerformanceTests(unittest.TestCase):
    def test_backoff_is_for_requested_feature_not_unrelated_features(self):
        score,model,shapes=fixture()
        model['tables'].append(dict(artist='Artist',context='single|medium|inside_bar|high|fretted',
            total='1',known={'bend':'1'},features={'bend':'1'}))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp')
            audit=apply(p/'base.gp',p/'out.gp',model,shapes,'Artist',{f:100 for f in FAMILIES})
            self.assertTrue(any(d['family']=='bend' and not d['context_backoff'] for d in audit['decisions']))
            self.assertTrue(all(d['context_backoff'] for d in audit['decisions'] if d['family']=='finger_vibrato'))

    def test_training_displacement_resolution_is_explicit(self):
        rows=[dict(tie_destination=False,duration_q='1',raw_note=dict(bend=dict(points=[dict(position=0,tone=0),dict(position=60,tone=tone)]))) for tone in (25,50,75,12.5,37.5,-12.5)]
        report=dict(songs=[dict(song_id=1,artist='Artist',provisional_partition='development',ai_generated=False,is_junk=False,
            tracks=[dict(guitar_or_bass=True,temporal_relationships_eligible=True,rows=rows)])])
        shapes=learn_shapes(report,'Artist')
        self.assertEqual(sum(len(v) for f in shapes['families'].values() for v in f.values()),3)
        self.assertEqual(shapes['excluded']['native_reader_displacement_resolution'],3)

    def test_native_curve_normalization_gate(self):
        linear=[(F(0),F(1)),(F(1,2),F(1,2)),(F(1),F(0))]
        nonlinear=[(F(0),F(1)),(F(1,8),F(1,2)),(F(1),F(0))]
        rise_fall=[(F(0),F(0)),(F(1,4),F(1)),(F(3,4),F(1)),(F(1),F(0))]
        for points,expected in [(linear,True),(nonlinear,False),(rise_fall,True)]:
            self.assertEqual(native_curve_exact(points,segment_properties(points,F(0),F(1))),expected)

    def test_polyphonic_voices_do_not_create_monophonic_opportunities(self):
        score,model,shapes=fixture()
        for m in score['tracks'][0]['measures']:m['voices'].append(copy.deepcopy(m['voices'][0]))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp')
            audit=apply(p/'base.gp',p/'out.gp',model,shapes,'Artist',{'bend':100,'finger_vibrato':100})
            self.assertTrue(audit['byte_identity']);self.assertFalse(audit['decisions'])

    def test_harmonics_and_muted_are_locked(self):
        score,model,shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp');s=extract_score(p/'base.gp');edits={};permissions={}
            for m in s['tracks'][0]['measures']:
                for e in m['voices'][0]:
                    for n in e['notes']:
                        if n['fret']:
                            key=('note',n['note_id'],'property');permissions[key]={'HarmonicType'};edits[key]=['<Property name="HarmonicType"><HType>Natural</HType></Property>']
            transact(p/'base.gp',p/'harmonic.gp',edits,permissions)
            audit=apply(p/'harmonic.gp',p/'out.gp',model,shapes,'Artist',{f:100 for f in FAMILIES})
            self.assertTrue(audit['byte_identity']);self.assertFalse(audit['decisions'])

    def test_intermediate_release_is_nested(self):
        score,model,shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp')
            a=apply(p/'base.gp',p/'a.gp',model,shapes,'Artist',{f:50 for f in FAMILIES})
            b=apply(p/'base.gp',p/'b.gp',model,shapes,'Artist',{f:100 for f in FAMILIES})
            def ids(a):return {json.dumps({k:v for k,v in d.items() if k!='released'},sort_keys=True) for d in a['decisions'] if d['released']}
            self.assertLessEqual(ids(a),ids(b))

    def test_existing_sidecar_preserved_before_gp_write(self):
        score,model,shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp');(p/'out.playback.json').write_text('PRESERVE')
            with self.assertRaises(FileExistsError):apply(p/'base.gp',p/'out.gp',model,shapes,'Artist',{'finger_vibrato':100})
            self.assertFalse((p/'out.gp').exists());self.assertEqual((p/'out.playback.json').read_text(),'PRESERVE')

    def test_wrong_artist_rejected(self):
        score,model,shapes=fixture();shapes['artist']='Other'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp')
            with self.assertRaises(ValueError):apply(p/'base.gp',p/'out.gp',model,shapes,'Artist',{'bend':100})

    def test_zero_is_byte_identity(self):
        score,model,shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp')
            audit=apply(p/'base.gp',p/'zero.gp',model,shapes,'Artist',{})
            self.assertTrue(audit['byte_identity'])

    def test_all_features_preserve_pitch_and_timing_and_rebuild_open_links(self):
        score,model,shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp')
            audit=apply(p/'base.gp',p/'out.gp',model,shapes,'Artist',{f:100 for f in FAMILIES})
            self.assertTrue(audit['locked_xml_verified'])
            out=analyze(extract_score(p/'out.gp'))
            self.assertTrue(out['tracks'][0]['explicit_hopo'])
            self.assertFalse(out['tracks'][0]['hopo_warnings'])
            self.assertTrue(any(d['proposed_selected'] for d in audit['decisions']))

    def test_100_does_not_use_hidden_performance_reference(self):
        score,model,shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'base.gp')
            apply(p/'base.gp',p/'annotated.gp',model,shapes,'Artist',{f:100 for f in FAMILIES},seed=8)
            apply(p/'base.gp',p/'a.gp',model,shapes,'Artist',{f:100 for f in FAMILIES},seed=17)
            apply(p/'annotated.gp',p/'b.gp',model,shapes,'Artist',{f:100 for f in FAMILIES},seed=17)
            self.assertEqual((p/'a.gp').read_bytes(),(p/'b.gp').read_bytes())


if __name__=='__main__':unittest.main()
