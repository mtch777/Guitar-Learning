from copy import deepcopy
import unittest
from unittest.mock import patch
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower
from nominal_harmony import analyze as nominal
from check_nominal_harmony import check,expected

def fixture():
    def beat(pitches,duration):return dict(duration=duration,notes=[dict(string=i,fret=p-40)for i,p in enumerate(pitches)])
    docs={'metadata.json':dict(songId=86,revisionId=1,artist='Fixture',title='Complementary written harmony',tracks=[dict(name='Focal',instrumentId=25),dict(name='Other',instrumentId=25)])}
    for pid,beats in [(0,[beat([62],[1,1])]),(1,[beat([60,64,67],[1,2]),beat([67,71,74],[1,2])])]:
        docs[f'track-{pid}.json']=dict(songId=86,revisionId=1,partId=pid,instrumentId=25,tuning=[40]*4,frets=40,measures=[dict(signature=[4,4],voices=[dict(beats=beats)])])
    return docs

def generate(docs):
    lower=extract_documents(docs)
    return lower,nominal(strip_lower(analyze(lower,declared_chords=True)))

class NominalOracleTests(unittest.TestCase):
    def test_literal_populations_and_nonmember_not_self_supported(self):
        lower,view=generate(fixture());self.assertEqual(check(lower,view)['issues'],[])
        self.assertEqual(view,expected(lower));cell=view['cells'][0]
        focal=next(q for q in cell['focal_contexts']if q['occurrence_ref'].startswith('event:86:0:'))
        scope=focal['scopes']['other_parts_only'];pop=next(p for p in cell['populations']if p['id']==scope['population_ref'])
        index=next(i for i,h in enumerate(pop['hypotheses'])if h['root_pc']==0 and h['kind']=='major')
        self.assertEqual(scope['role_results'][index]['status'],'TEMPLATE_NONMEMBER')
        self.assertFalse(scope['direct_focal_support'])

    def test_population_and_temporal_corruptions_fail(self):
        lower,view=generate(fixture())
        changes=[lambda v:v['cells'].pop(),lambda v:v['cells'].append(deepcopy(v['cells'][0])),
            lambda v:v['cells'][0]['active_refs'].pop(),lambda v:v['cells'][0].update(end_q='3'),
            lambda v:v['cells'][0]['populations'][0]['support_refs'].pop(),
            lambda v:v['occurrence_paths'].pop(),lambda v:v['counts'].update(cells=999),
            lambda v:v['frames'][0].update(observed_part_ids=[])]
        for change in changes:
            bad=deepcopy(view);change(bad);self.assertEqual(check(lower,bad)['status'],'FAIL')

    def test_scope_role_and_provenance_corruptions_fail(self):
        docs=fixture();docs['track-0.json']['measures'][0]['voices'][0]['beats'].append(dict(duration=[1,4],notes=[],rest=True))
        lower,view=generate(docs);self.assertEqual(check(lower,view)['issues'],[])
        for field,value in [('scope_refusals',['FAKE']),('focal_refusals',['FAKE']),('direct_focal_support',True),('part_ids',[0])]:
            bad=deepcopy(view);bad['cells'][0]['focal_contexts'][0]['scopes']['other_parts_only'][field]=value
            self.assertEqual(check(lower,bad)['status'],'FAIL')
        bad=deepcopy(view);bad['rest_inventory'][0]['provenance']['structural_ref']='/imaginary'
        self.assertEqual(check(lower,bad)['status'],'FAIL')

    def test_focal_mutation_does_not_change_excluded_context(self):
        docs=fixture();lower,view=generate(docs);changed=deepcopy(docs)
        changed['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret']=26
        other,after=generate(changed);self.assertEqual(check(other,after)['issues'],[])
        def context(v):
            c=v['cells'][0];q=next(q for q in c['focal_contexts']if q['occurrence_ref'].startswith('event:86:0:'));pid=q['scopes']['other_parts_only']['population_ref']
            return next(p for p in c['populations']if p['id']==pid)['hypotheses']
        self.assertEqual(context(view),context(after))

    def test_percussion_unknown_and_duplicate_identity(self):
        for program in (1024,999):
            docs=fixture();docs['track-1.json']['instrumentId']=program
            lower,view=generate(docs);self.assertEqual(check(lower,view)['issues'],[])
        docs=fixture();notes=docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes'];notes.append(dict(string=3,fret=20))
        lower,view=generate(docs);self.assertEqual(check(lower,view)['issues'],[])
        self.assertEqual(len(view['cells'][0]['active_refs']),5)

    def test_expected_mutation_cannot_poison_native_cache(self):
        lower,view=generate(fixture());first=expected(lower)
        first['theory']['version']='forged'
        for pop in first['cells'][0]['populations']:
            if pop['hypotheses']:pop['hypotheses'][0]['formula'].clear()
        self.assertEqual(check(lower,view)['issues'],[])

    def test_native_provenance_does_not_trust_producer_constant(self):
        import musical_tier2 as music
        lower,view=generate(fixture());old=deepcopy(music.THEORY_PROVENANCE)
        try:
            music.THEORY_PROVENANCE['forms_sha256']='0'*64
            bad=deepcopy(view);bad['theory']=deepcopy(music.THEORY_PROVENANCE)
            self.assertEqual(check(lower,bad)['status'],'FAIL')
            self.assertEqual(check(lower,view)['issues'],[])
        finally:music.THEORY_PROVENANCE.clear();music.THEORY_PROVENANCE.update(old)

    def test_independent_raw_addresses_catch_shared_helper_error(self):
        docs=fixture();docs['track-0.json']['measures']=[dict(signature=[4,4],rest=True)]
        lower,view=generate(docs);self.assertEqual(check(lower,view)['issues'],[])
        from source_semantics import rests
        def wrong(*args,**kwargs):
            rows,warnings=rests(*args,**kwargs);rows=deepcopy(rows)
            if rows:rows[0]['provenance']['source_voice_ref']='/measures/0/voices/0'
            return rows,warnings
        with patch('source_semantics.rests',side_effect=wrong):
            report=check(lower,view);self.assertEqual(report['status'],'FAIL')
            self.assertIn('actual source nodes',str(report['issues']))

    def test_rest_flags_and_structural_empty_addresses(self):
        from check_nominal_harmony import _rest_addresses
        from source_semantics import rests,layout
        cases=[dict(signature=[4,4],rest=True),
            dict(signature=[4,4],voices=[dict(rest=True)]),
            dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=[])])]),
            dict(signature=[4,4],rest=True,voices=[dict(rest=True,beats=[dict(duration=[1,1],rest=True,notes=[dict(rest=True)])])])]
        for measure in cases:
            part=fixture()['track-0.json'];part['measures']=[measure];headers,_=layout([part]);rows,_=rests(part,headers,include_provenance=True)
            _rest_addresses(part,rows)
            bad=deepcopy(rows);bad[0]['provenance']['rest_flag_refs'].append('/fake/rest')
            with self.assertRaises(ValueError):_rest_addresses(part,bad)

    def test_complete_source_denominators_and_mutations(self):
        lower,view=generate(fixture());self.assertEqual(check(lower,view)['issues'],[])
        c=view['counts'];self.assertEqual(c['positive_duration_occurrences'],7)
        self.assertEqual(c['pitched_occurrences'],7)
        self.assertEqual(c['point_or_nonpositive_occurrences'],0)
        self.assertEqual(c['crossing_occurrences'],len(view['crossing_occurrence_refs']))
        for key in ('crossing_occurrence_refs','unscoped_positive_occurrence_refs'):
            bad=deepcopy(view);bad[key]=['invented']
            self.assertEqual(check(lower,bad)['status'],'FAIL')
        bad=deepcopy(view);bad['counts']['unknown_domain_occurrences']=1
        self.assertEqual(check(lower,bad)['status'],'FAIL')

    def test_wholly_outside_crossings_are_not_lost(self):
        docs=fixture();part=docs['track-0.json']
        part['measures'][0]['voices'][0]['beats']=[dict(duration=[1,4],notes=[dict(string=0,fret=i)])for i in range(5)]
        lower=extract_documents(docs);view=expected(lower);last='event:86:0:1:0:4:0'
        self.assertIn(last,view['crossing_occurrence_refs'])
        self.assertIn(last,view['unscoped_positive_occurrence_refs'])
        self.assertNotIn(last,{r for c in view['cells']for r in c['active_refs']})

    def test_geometry_unavailable_is_not_no_positive_notes(self):
        lower=extract_documents(fixture())
        with patch('check_nominal_harmony.geometry_relation',side_effect=ValueError('unestablished geometry')):
            view=expected(lower)
        self.assertEqual(view['geometry_status'],'UNAVAILABLE')
        self.assertEqual(view['crossing_occurrence_refs'],[])
        self.assertEqual(view['counts']['unscoped_positive_occurrences'],7)
        self.assertEqual(view['counts']['positive_duration_occurrences'],7)
        self.assertEqual(view['counts']['quarantined_cells'],0)

    def test_focal_domains_are_not_missing_pitched_information(self):
        from check_nominal_harmony import _focal_role
        h=dict(root_pc=0,kind='major',formula=[0,4,7])
        for pitch,domain,status in [(None,'nonpitched','NOT_APPLICABLE_NONPITCHED_DOMAIN'),
            (None,'unknown','UNKNOWN_INSTRUMENT_DOMAIN_ROLE'),('125/2','pitched','OUTSIDE_SUPPORTED_PITCH_CLASS_DOMAIN_ROLE'),
            (None,'pitched','UNKNOWN_WRITTEN_PITCH_ROLE')]:
            self.assertEqual(_focal_role(pitch,domain,h),dict(status=status,degree_relationships=[]))

    def test_focal_status_change_does_not_change_complementary_fit(self):
        cases=[(1024,22,'NOT_APPLICABLE_NONPITCHED_DOMAIN','nonpitched_roles'),
            (999,22,'UNKNOWN_INSTRUMENT_DOMAIN_ROLE','unknown_domain_roles'),
            (25,22.5,'OUTSIDE_SUPPORTED_PITCH_CLASS_DOMAIN_ROLE','unsupported_pitch_roles')]
        baseline=None
        for program,fret,status,count in cases:
            docs=fixture();docs['track-0.json']['instrumentId']=program
            docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret']=fret
            lower=extract_documents(docs);view=expected(lower);cell=view['cells'][0]
            focal=next(q for q in cell['focal_contexts']if q['occurrence_ref'].startswith('event:86:0:'))['scopes']['other_parts_only']
            pop=next(p for p in cell['populations']if p['id']==focal['population_ref'])
            if baseline is None:baseline=deepcopy(pop['hypotheses'])
            self.assertEqual(pop['hypotheses'],baseline)
            self.assertTrue(focal['role_results']);self.assertTrue(all(r==dict(status=status,degree_relationships=[])for r in focal['role_results']))
            self.assertGreater(view['counts'][count],0);self.assertEqual(view['counts']['unknown_roles'],0)
            self.assertEqual(view['counts']['pitched_unknown_pitch_occurrences'],0)
            bad=deepcopy(view);q=next(q for q in bad['cells'][0]['focal_contexts']if q['occurrence_ref'].startswith('event:86:0:'))
            q['scopes']['other_parts_only']['role_results'][0]['status']='UNKNOWN_WRITTEN_PITCH_ROLE'
            self.assertEqual(check(lower,bad)['status'],'FAIL')

if __name__=='__main__':unittest.main()
