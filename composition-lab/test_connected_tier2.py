"""Unified ownership, exact source recovery and connected retained semantics."""
from copy import deepcopy
import json
import unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,reconstruct,validate


def documents():
    notes=[dict(string=0,fret=5,bend=dict(tone=100,points=[dict(position=0,tone=0),dict(position=60,tone=100)])),dict(string=0,fret=7,hp=True),dict(string=0,fret=9),dict(string=0,fret=7,ghost=True)]
    beats=[dict(duration=[1,4],notes=[n]) for n in notes]
    return {'metadata.json':dict(songId=77,revisionId=3,artist='Fixture',title='Owner test',tracks=[dict(name='Guitar',instrumentId=25)]),'track-0.json':dict(songId=77,revisionId=3,partId=0,name='Guitar',instrumentId=25,tuning=[40,45],measures=[dict(signature=[4,4],voices=[dict(beats=beats)])])}


class ConnectedTierTests(unittest.TestCase):
    def model(self):
        lower=extract_documents(documents());return lower,analyze(lower)

    def test_complete_exact_and_single_pitch_authority(self):
        lower,upper=self.model();self.assertEqual(upper['unsupported'],[])
        stripped=strip_lower(upper);self.assertNotIn('input',stripped);self.assertNotIn('derived_views',stripped)
        actual=reconstruct(stripped,dict(variation=0))
        self.assertEqual(json.dumps(actual,sort_keys=True),json.dumps(lower,sort_keys=True))
        self.assertEqual(len(upper['owned_parameters']['physical_positions']),4)
        self.assertFalse(any(c['fact_ref'].endswith('/fret') for c in upper['owned_parameters']['source_choices']))
        self.assertEqual(project_documents(actual),documents());validate(upper)

    def test_all_retained_fields_match_persisted_baseline_including_histogram_keys(self):
        from freeze_technique_baseline import retained
        from technique_tier2 import comparable_to_baseline
        _,upper=self.model();baseline=json.loads(json.dumps(retained(documents())))
        self.assertTrue(comparable_to_baseline(upper['derived_views']['techniques'],baseline))

    def test_actual_isolated_full_boundary_inverse(self):
        from pathlib import Path
        import tempfile
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower,upper=self.model();code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            result=execute(code,strip_lower(upper),dict(variation=0),lower,Path(folder)/'isolated',timeout=30)
        self.assertEqual(result['status'],'PASS',result)

    def test_chord_annotation_and_downstroke_are_preserved_without_detector_change(self):
        docs=documents();beat=docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]
        beat.update(chord=dict(text='Cmaj7',width=28),downStroke=1)
        lower=extract_documents(docs);upper=analyze(lower)
        self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)
        self.assertTrue(any(c['owner']=='source_chord_annotation' for c in upper['owned_parameters']['source_choices']))
        self.assertTrue(any(g['field']=='downStroke' for g in upper['owned_parameters']['technique_declarations']['groups']))

    def test_unknown_scalar_and_empty_container_block_full_claim(self):
        for value in (60,{},[],dict(hidden=[60,64])):
            docs=documents();docs['track-0.json']['secret']=value
            upper=analyze(extract_documents(docs));self.assertTrue(upper['unsupported'])
            with self.assertRaises(ValueError):reconstruct(strip_lower(upper),dict(variation=0))

    def test_unknown_technique_shape_cannot_fall_back_to_source_choices(self):
        docs=documents();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['bend']=[]
        upper=analyze(extract_documents(docs));self.assertTrue(upper['unsupported'])
        with self.assertRaises(ValueError):reconstruct(strip_lower(upper),dict(variation=0))

    def test_duplicate_owner_raw_skeleton_and_missing_owner_rejected(self):
        _,original=self.model()
        for mode in ('duplicate','raw','missing'):
            upper=strip_lower(original)
            if mode=='duplicate':upper['owned_parameters']['source_choices'].append(deepcopy(upper['owned_parameters']['source_choices'][0]))
            if mode=='raw':upper['source_structure']['facts'][0]['value']=60
            if mode=='missing':upper['owned_parameters']['source_choices'].pop()
            with self.assertRaises((ValueError,KeyError)):reconstruct(upper,dict(variation=0))

    def test_reverse_rejects_timing_unknown_container_and_unreachable_owner(self):
        _,original=self.model()
        upper=strip_lower(original)
        duration=next(c for c in upper['owned_parameters']['source_choices'] if c['fact_ref'].endswith('/duration/1'))
        duration['parameter']['normalized']='8'
        with self.assertRaises(ValueError):reconstruct(upper,dict(variation=0))
        for path in ('/secret','/tuning'):
            upper=strip_lower(original)
            ident='track-0.json#'+path
            # Unknown child or disconnected registered-shaped owner.
            row=dict(id=ident,document='track-0.json',pointer=path,parent='track-0.json#',slot=path[1:],type='object',children=[])
            if path=='/tuning':
                ident='metadata.json#/tracks/7';row.update(id=ident,document='metadata.json',pointer='/tracks/7',parent='metadata.json#/tracks',slot=7)
            upper['source_structure']['facts'].append(row)
            upper['coverage'].append(dict(fact_ref=ident,owner='source_structure'))
            with self.assertRaises(ValueError):reconstruct(upper,dict(variation=0))

    def test_stale_derived_cache_is_not_an_inverse_source(self):
        lower,upper=self.model();upper['derived_views']['techniques']['tracks'][0]['approved_pedal_phrases']=[dict(fake=True)]
        self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)
        with self.assertRaises(ValueError):validate(upper)

    def test_physical_conflict_and_copied_fret_loophole_rejected(self):
        _,original=self.model();upper=strip_lower(original)
        upper['owned_parameters']['physical_positions'][0]['tuning_ref']='track-0.json#/tuning/1'
        with self.assertRaises(ValueError):reconstruct(upper,dict(variation=0))
        upper=strip_lower(original);position=upper['owned_parameters']['physical_positions'].pop()
        upper['owned_parameters']['source_choices'].append(dict(fact_ref=position['fact_ref'],owner='physical_or_note_declaration',parameter=dict(normalized='7',negative_zero=False)))
        with self.assertRaises(ValueError):reconstruct(upper,dict(variation=0))

    def test_technique_time_and_source_connections_have_musical_contrasts(self):
        _,upper=self.model();track=upper['derived_views']['techniques']['tracks'][0]
        refs=track['source_occurrences'];self.assertEqual([r['onset_q'] for r in refs],['0','1','2','3'])
        self.assertTrue(all('/notes/' in r['source_fact_ref'] for r in refs))
        self.assertTrue(all(r['musical_occurrence_ref']=='event:77:'+r['occurrence_ref'] for r in refs))
        self.assertIn('summary',track);self.assertIn('counterexamples',track)
        self.assertEqual(track['retained_field_dispositions']['pedal_candidates'],'replaced_by_approved_pedal_evidence_support_expansion')
        bend=next(g for g in upper['owned_parameters']['technique_declarations']['groups'] if g['field']=='bend')
        self.assertTrue(any(p['parameter'].get('normalized')=='2' for p in bend['parameters']))
        self.assertEqual(track['approved_pedal_phrases'],[])
        self.assertTrue(all(d['known'] is False and d['provenance']=='unspecified' for d in track['dynamics']))
        self.assertIn('harmonics/vibrato remain unresolved',track['sustain_relationships']['limitations'][0])


if __name__=='__main__':unittest.main()
