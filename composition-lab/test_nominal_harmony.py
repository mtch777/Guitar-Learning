"""Musical contrasts and source-only reversibility of conditional contexts."""
from copy import deepcopy
import unittest
import nominal_harmony as n
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,reconstruct


def beat(duration,strings):
    return dict(duration=duration,notes=[dict(string=s,fret=0) for s in strings])


def part(pid,tuning,beats):
    return dict(songId=77,revisionId=3,partId=pid,name=f'Part {pid}',instrumentId=25,tuning=tuning,
                measures=[dict(signature=[4,4],voices=[dict(beats=beats)])])


def documents():
    return {'metadata.json':dict(songId=77,revisionId=3,artist='Authored contrast',title='Conditional roles'),
            'track-0.json':part(0,[62],[beat([1,1],[0])]),
            'track-1.json':part(1,[48,52,55],[beat([1,1],[0,1,2])])}


def run(docs):
    docs=deepcopy(docs)
    docs['metadata.json']['tracks']=[dict(name=p['name'],instrumentId=p['instrumentId']) for k,p in sorted(docs.items()) if k.startswith('track-')]
    lower=extract_documents(docs);upper=strip_lower(analyze(lower));return lower,upper,n.analyze(upper)


def query(view,ref='event:77:0:1:0:0:0',cell=0,scope='other_parts_only'):
    c=view['cells'][cell];q=next(q for q in c['focal_contexts'] if q['occurrence_ref']==ref)['scopes'][scope]
    return q,next(p for p in c['populations'] if p['id']==q['population_ref'])


class NominalHarmonyTests(unittest.TestCase):
    def test_existing_owner_loads_in_a_fresh_process(self):
        import json,subprocess,sys,tempfile
        from pathlib import Path
        _,upper,_=run(documents())
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'upper.json';path.write_text(json.dumps(upper))
            script='import json,sys;from pathlib import Path;from nominal_harmony import analyze;assert analyze(json.loads(Path(sys.argv[1]).read_text()))["counts"]["raw_note_occurrences"]==4'
            p=subprocess.run([sys.executable,'-c',script,str(path)],cwd=Path(__file__).parent,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_actual_source_denied_context_recomputation(self):
        from pathlib import Path
        import tempfile
        from run_nominal_harmony_qa import bundle
        from qa_isolation_harness import execute
        _,upper,view=run(documents());code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            result=execute(code,upper,dict(variation=0),view,Path(folder)/'isolated',timeout=30)
        self.assertEqual(result['status'],'PASS',result)

    def test_excluded_D_over_C_major_is_conditional_nonmember_and_exact(self):
        lower,upper,v=run(documents());q,p=query(v)
        i=next(i for i,h in enumerate(p['hypotheses']) if h['root_pc']==0 and h['kind']=='major')
        self.assertEqual(q['role_results'][i]['status'],'TEMPLATE_NONMEMBER')
        self.assertFalse(q['direct_focal_support']);self.assertEqual(q['role_results'][i]['root_interval'],'62')
        self.assertEqual(reconstruct(upper,dict(variation=0)),lower)
        self.assertEqual(n.validate(upper,v),v)

    def test_excluded_focal_pitch_cannot_choose_its_context(self):
        d=documents();_,_,before=run(d);d['track-0.json']['tuning']=[66];_,_,after=run(d)
        qa,pa=query(before);qb,pb=query(after)
        self.assertEqual(pa,pb);self.assertNotEqual(qa['role_results'],qb['role_results'])

    def test_full_population_inclusion_is_explicit_and_missing_third_not_completed(self):
        d=documents();d.pop('track-1.json');p=d['track-0.json'];p['tuning']=[48,55,52]
        p['measures'][0]['voices']=[dict(beats=[beat([1,1],[0,1])]),dict(beats=[dict(duration=[1,4],notes=[dict(rest=True)]),beat([3,4],[2])])]
        _,_,v=run(d);ref='event:77:0:1:1:1:0'
        full,fp=query(v,ref,1,'full_focal_part');minus,mp=query(v,ref,1,'focal_part_minus_focal')
        self.assertTrue(full['direct_focal_support']);self.assertFalse(minus['direct_focal_support'])
        self.assertTrue(any(h['kind']=='major' and h['root_pc']==0 for h in fp['hypotheses']))
        self.assertFalse(any(h['kind']=='major' for h in mp['hypotheses']))
        self.assertEqual(len(mp['included_refs']),2)

    def test_same_held_C_changes_role_without_new_attack(self):
        d=documents();d['track-0.json']['tuning']=[60];p=d['track-1.json'];p['tuning']=[48,52,55,59,62]
        p['measures'][0]['voices'][0]['beats']=[beat([1,2],[0,1,2]),beat([1,2],[2,3,4])]
        _,_,v=run(d);a,pa=query(v);b,pb=query(v,cell=1)
        ar=next(r for h,r in zip(pa['hypotheses'],a['role_results']) if h['root_pc']==0 and h['kind']=='major')
        br=next(r for h,r in zip(pb['hypotheses'],b['role_results']) if h['root_pc']==7 and h['kind']=='major')
        self.assertEqual(ar['status'],'TEMPLATE_CHORD_TONE');self.assertEqual(br['status'],'TEMPLATE_NONMEMBER')
        self.assertIn('event:77:0:1:0:0:0',v['cells'][1]['continuing_refs'])
        self.assertNotIn('event:77:0:1:0:0:0',v['cells'][1]['starting_refs'])

    def test_duplicate_pitch_is_a_separate_witness(self):
        d=documents();d.pop('track-1.json');p=d['track-0.json'];p['tuning']=[48,48,52,55]
        p['measures'][0]['voices'][0]['beats']=[beat([1,1],[0,1,2,3])]
        _,_,v=run(d);q,pop=query(v,scope='focal_part_minus_focal')
        self.assertEqual(len(pop['included_refs']),3)
        self.assertIn('event:77:0:1:0:0:1',pop['included_refs'])
        self.assertTrue(any(h['root_pc']==0 and h['kind']=='major' for h in pop['hypotheses']))

    def test_sequential_notes_are_not_a_simultaneous_chord(self):
        d=documents();d.pop('track-1.json');p=d['track-0.json'];p['tuning']=[48,52,55]
        p['measures'][0]['voices'][0]['beats']=[beat([1,4],[0]),beat([1,4],[1]),beat([1,2],[2])]
        _,_,v=run(d);self.assertEqual(v['counts']['hypotheses'],0)

    def test_unknown_focal_keeps_known_complement_but_not_known_role(self):
        d=documents();d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['dead']=True
        _,_,v=run(d);q,p=query(v);self.assertTrue(p['hypotheses'])
        self.assertTrue(all(r['status']=='UNKNOWN_WRITTEN_PITCH_ROLE' for r in q['role_results']))

    def test_nonpitched_and_unknown_domain_do_not_claim_missing_pitched_roles(self):
        d=documents();_,_,baseline=run(d);_,original=query(baseline)
        for program,status in ((1024,'NOT_APPLICABLE_NONPITCHED_DOMAIN'),(999,'UNKNOWN_INSTRUMENT_DOMAIN_ROLE')):
            d['track-0.json']['instrumentId']=program;_,_,v=run(d);q,p=query(v)
            self.assertEqual(p,original)
            self.assertTrue(q['role_results']);self.assertTrue(all(r['status']==status for r in q['role_results']))

    def test_known_fractional_focal_is_outside_domain_not_missing(self):
        d=documents();d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret']=0.5
        _,_,v=run(d);q,p=query(v)
        self.assertTrue(p['hypotheses']);self.assertTrue(all(r['status']=='OUTSIDE_SUPPORTED_PITCH_CLASS_DOMAIN_ROLE' for r in q['role_results']))
        self.assertEqual(v['counts']['pitched_unknown_pitch_occurrences'],0)

    def test_expression_is_nominal_not_sounding(self):
        d=documents();d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['bend']=dict(tone=100)
        _,_,v=run(d);q,p=query(v);self.assertTrue(q['role_results'])
        row=next(r for r in v['occurrence_inventory'] if r['occurrence_ref']=='event:77:0:1:0:0:0')
        self.assertIn('unresolved_sounding_pitch_bend',row['written_pitch_qualifications'])

    def test_missing_track_frame_is_not_observed_rest(self):
        d=documents();d['track-0.json']['measures'].append(dict(voices=[dict(beats=[beat([1,1],[0])])]))
        _,_,v=run(d);q,p=query(v,'event:77:0:2:0:0:0',1)
        self.assertIn('MISSING_SOURCE_PART_FRAME',q['scope_refusals']);self.assertEqual(q['role_results'],[])
        self.assertEqual(v['frames'][1]['missing_part_ids'],[1])

    def test_crossing_interval_quarantines_destination_too(self):
        d=documents();p=d['track-0.json'];p['measures'][0]['voices'][0]['beats'][0]['duration']=[5,4]
        p['measures'].append(dict(voices=[dict(beats=[beat([1,1],[0])])]))
        d['track-1.json']['measures'].append(deepcopy(d['track-1.json']['measures'][0]))
        _,_,v=run(d);c=next(c for c in v['cells'] if c['start_q']=='4')
        self.assertIn('event:77:0:1:0:0:0',c['crossing_refs'])
        self.assertIn('CROSSING_SOURCE_INTERVAL',next(r['reasons'] for r in c['part_refusals'] if r['part_id']==0))

    def test_empty_gaps_and_rest_provenance_are_retained(self):
        d=documents();d.pop('track-1.json');d['track-0.json']['measures'][0]['voices'][0]['beats']=[beat([1,4],[0]),dict(duration=[1,4],notes=[dict(rest=True)])]
        _,_,v=run(d);self.assertEqual(v['counts']['cells'],3);self.assertEqual(v['counts']['empty_note_cells'],2)
        self.assertTrue(v['cells'][1]['rest_refs']);self.assertEqual(v['cells'][2]['rest_refs'],[])
        self.assertEqual(v['rest_inventory'][0]['provenance']['rest_flag_refs'],['/measures/0/voices/0/beats/1/notes/0/rest'])

    def test_label_and_name_masking_does_not_change_population_fits(self):
        d=documents();_,_,a=run(d);d['track-1.json']['name']='Lead bass accompaniment';d['track-1.json']['measures'][0]['voices'][0]['beats'][0]['chord']=dict(text='F#7')
        _,_,b=run(d);self.assertEqual(a,b)

    def test_forged_context_is_rejected(self):
        _,u,v=run(documents());v['cells'][0]['active_refs'].pop()
        with self.assertRaises(ValueError):n.validate(u,v)

    def test_output_mutation_cannot_poison_the_relation(self):
        _,u,v=run(documents());baseline=deepcopy(v)
        v['theory']['version']='forged'
        self.assertEqual(n.analyze(u),baseline)

    def test_transposition_preserves_conditional_roles_and_interval_math(self):
        d=documents();_,_,a=run(d)
        for key,part in d.items():
            if key.startswith('track-'):part['tuning']=[p+3 for p in part['tuning']]
        _,_,b=run(d);qa,pa=query(a);qb,pb=query(b)
        self.assertEqual([h['kind'] for h in pa['hypotheses']],[h['kind'] for h in pb['hypotheses']])
        self.assertEqual([(h['root_pc']+3)%12 for h in pa['hypotheses']],[h['root_pc'] for h in pb['hypotheses']])
        self.assertEqual(qa['role_results'],qb['role_results'])

    def test_grace_is_a_point_and_tie_constituents_keep_identity(self):
        d=documents();p=d['track-0.json'];p['tuning']=[60]
        grace=beat([1,16],[0]);grace['graceNote']='beforeBeat'
        tail=beat([1,2],[0]);tail['notes'][0]['tie']=True
        p['measures'][0]['voices'][0]['beats']=[grace,beat([1,2],[0]),tail]
        _,_,v=run(d)
        self.assertEqual(v['frames'][0]['point_refs'],['event:77:0:1:0:0:0'])
        self.assertNotIn('event:77:0:1:0:0:0',v['cells'][0]['active_refs'])
        self.assertIn('event:77:0:1:0:1:0',v['cells'][0]['active_refs'])
        self.assertNotIn('event:77:0:1:0:1:0',v['cells'][1]['active_refs'])
        self.assertIn('event:77:0:1:0:2:0',v['cells'][1]['active_refs'])


class RestProvenanceTests(unittest.TestCase):
    def test_opt_in_preserves_default_and_all_literal_flags(self):
        from source_semantics import layout,rests
        p=documents()['track-0.json'];m=p['measures'][0];v=m['voices'][0];b=v['beats'][0]
        m['rest']=v['rest']=b['rest']=True;b['notes']=[dict(rest=True)]
        h,_=layout([p]);plain,w=rests(p,h);rich,rw=rests(p,h,include_provenance=True)
        self.assertEqual(w,rw);self.assertEqual(plain,[{k:v for k,v in r.items() if k!='provenance'} for r in rich])
        self.assertEqual(len(rich[0]['provenance']['rest_flag_refs']),4)
        with self.assertRaises(ValueError):rests(p,h,include_provenance=1)

    def test_synthetic_whole_rest_has_no_invented_voice_pointer(self):
        from source_semantics import layout,rests
        p=part(0,[60],[]);p['measures']=[dict(signature=[4,4],rest=True)]
        h,_=layout([p]);rows,_=rests(p,h,include_provenance=True)
        self.assertIsNone(rows[0]['provenance']['source_voice_ref'])
        self.assertEqual(rows[0]['provenance']['rest_flag_refs'],['/measures/0/rest'])


if __name__=='__main__':unittest.main()
