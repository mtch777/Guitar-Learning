from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from source_fact_tier1 import extract_documents
from source_tie_tier1 import extract_documents as written
from connected_tier2 import analyze,strip_lower,reconstruct
from contextual_note_roles import evaluate,attach
from contextual_passage_roles import VERSION,interval_theory_compatibility
from chord_degree_relations import note_role,pitch_from_degree
from chord_degree_definitions import CHORD_DEGREE_DEFINITIONS
from test_contextual_note_roles import source as motion_source
from test_contextual_chord_motion import source,brute_pairs
from test_collection_degrees import candidate


def request(lower,end='2',reference=False):
    upper=analyze(lower)
    return dict(version=VERSION,harmonic_request=dict(start_q='0',end_q=end,part_id=None),
                reference_candidate_ref=candidate(upper['musical_relationships'],'major',0) if reference else None)


class PassageRolesTests(unittest.TestCase):
    def test_incomplete_arpeggiated_union_keeps_minor7_major6_and_halfdim(self):
        edge=dict(start_q='0',end_q='3',pitch_class_note_cell_weights=[0]*12,partial_known_pitch_evidence=False)
        events=[]
        for i,pitch in enumerate((40,55,62)):
            edge['pitch_class_note_cell_weights'][pitch%12]+=1
            events.append(dict(id=str(i),pitch=str(pitch),onset_q=str(i),duration_q='1'))
        domains={e['id']:'pitched' for e in events};out,_=interval_theory_compatibility(edge,events,domains,100000)
        labels={(r['label']['root_pc'],r['label']['kind']):r for r in out['incomplete_compatible_templates']}
        self.assertEqual(labels[4,'minor-seventh']['unobserved_template_pitch_classes'],[11])
        self.assertEqual(labels[7,'major-sixth']['unobserved_template_pitch_classes'],[11])
        self.assertEqual(labels[4,'half-diminished-seventh']['unobserved_template_pitch_classes'],[10])
        edge['pitch_class_note_cell_weights'][11]+=1
        events.append(dict(id='b',pitch='59',onset_q='2',duration_q='1'));domains['b']='pitched'
        out,_=interval_theory_compatibility(edge,events,domains,100000)
        exact={(r['label']['root_pc'],r['label']['kind']) for r in out['exact_templates']}
        self.assertIn((4,'minor-seventh'),exact);self.assertIn((7,'major-sixth'),exact)
        self.assertIsNone(out['physical_technique_classification'])
        edge['partial_known_pitch_evidence']=True
        self.assertTrue(interval_theory_compatibility(edge,events,domains,100000)[0]['partial_evidence'])
        events.append(dict(id='point-only',pitch='50',onset_q='1',duration_q='0'));domains['point-only']='pitched'
        out,_=interval_theory_compatibility(edge,events,domains,100000)
        self.assertFalse(any(n['occurrence_ref']=='point-only' for group in ('exact_templates','incomplete_compatible_templates') for r in out[group] for n in r['known_note_roles']))

    def test_reference_connects_unplayed_B_vs_Bflat_without_establishing_center(self):
        edge=dict(start_q='0',end_q='3',pitch_class_note_cell_weights=[0]*12,partial_known_pitch_evidence=False)
        events=[]
        for i,pitch in enumerate((40,55,62)):
            edge['pitch_class_note_cell_weights'][pitch%12]+=1
            events.append(dict(id=str(i),pitch=str(pitch),onset_q=str(i),duration_q='1'))
        reference=dict(id='explicit-G-major',tonic_pc=7,reference_intervals=[0,2,4,5,7,9,11])
        out,_=interval_theory_compatibility(edge,events,{e['id']:'pitched' for e in events},100000,reference)
        rows={(r['label']['root_pc'],r['label']['kind']):r for r in out['incomplete_compatible_templates']}
        self.assertEqual(rows[4,'minor-seventh']['conditional_reference_comparison']['unobserved_pitch_classes_in_reference'],[11])
        self.assertEqual(rows[4,'half-diminished-seventh']['conditional_reference_comparison']['unobserved_pitch_classes_outside_reference'],[10])
        lower=extract_documents(motion_source());req=request(lower,'3',True)
        req['reference_candidate_ref']=candidate(analyze(lower)['musical_relationships'],'major',7)
        result=evaluate(lower,[req])['results'][0]
        context=result['provisional_reference']
        self.assertTrue(any(c['tonic_pc']==4 and c['reference_collection']=='natural_minor_reference_only' for c in context['collection_equivalent_candidates']))
        self.assertTrue(all(r['conditional_reference_coordinate'] is not None for r in result['occurrence_inventory']))
        self.assertIn('NOT_ESTABLISHED',context['status'])

    def test_boolean_degree_aliases_are_not_theory_definitions(self):
        role=note_role('60',dict(root_pc=0,kind='major',formula=[0,4,7]))['degree_relationships'][0]
        for field in ('degree','alteration','theoretical_semitones','pitch_class','relative_octaves'):
            bad=deepcopy(role);bad[field]=bool(bad[field])
            with self.assertRaises(ValueError):pitch_from_degree(0,'major',bad)
        with self.assertRaises(ValueError):note_role(True,dict(root_pc=0,kind='major',formula=[0,4,7]))

    def test_partial_scored_edge_can_outlast_clean_onset_snapshot(self):
        docs=source();docs['track-0.json']['measures'][0]['voices'][0]['beats']=[dict(duration=[1,2],notes=[dict(string=0,fret=28)])]
        docs['track-1.json']['measures'][0]['voices'][0]['beats']=[dict(duration=[1,2],notes=[dict(string=i,fret=p-40) for i,p in enumerate((40,44,47,50))])]
        docs['track-2.json']=dict(songId=123,revisionId=1,partId=2,instrumentId=25,tuning=[40],measures=[dict(signature=[2,4],voices=[dict(beats=[dict(duration=[1,4],rest=True,notes=[dict(rest=True)]),dict(duration=[1,4],notes=[dict(string=0,fret=1,dead=True)])])])])
        docs['metadata.json']['tracks'].append(dict(instrumentId=25))
        lower=extract_documents(docs);out=evaluate(lower,[request(lower)])['results'][0]
        self.assertFalse(out['observed_sonorities']['0']['unresolved_occurrences'])
        self.assertTrue(all(e['partial_known_pitch_evidence'] for e in out['optimal_edges']))
        self.assertTrue(all(a['supporting_edge_partial_known_pitch_evidence'] for a in out['edge_label_role_assignments']))

    def test_percussion_unknown_domains_and_empty_evidence_remain_accounted(self):
        for instrument,expected in ((1024,'EXCLUDED_EXPLICIT_NONPITCHED'),(9999,'UNKNOWN_PITCHED_DOMAIN')):
            docs=source()
            for part in ('track-0.json','track-1.json'):docs[part]['instrumentId']=instrument
            lower=extract_documents(docs);out=evaluate(lower,[request(lower)])['results'][0]
            self.assertTrue(out['occurrence_inventory'])
            self.assertEqual({r['status'] for r in out['occurrence_inventory']},{expected})
            if instrument==1024:
                self.assertTrue(all(l is None for e in out['optimal_edges'] for l in e['labels']))
                self.assertTrue(all(not a['notes'] for a in out['edge_label_role_assignments']))
            else:
                self.assertTrue(all(e['partial_known_pitch_evidence'] for e in out['optimal_edges']))
                self.assertFalse(any(n['role']['degree_relationships'] for a in out['edge_label_role_assignments'] for n in a['notes']))
        docs=source()
        for part in ('track-0.json','track-1.json'):
            for beat in docs[part]['measures'][0]['voices'][0]['beats']:
                for note in beat['notes']:note['dead']=True
        lower=extract_documents(docs);out=evaluate(lower,[request(lower)])['results'][0]
        self.assertTrue(all(l is None for e in out['optimal_edges'] for l in e['labels']))
        self.assertFalse(any(n['role']['degree_relationships'] for a in out['edge_label_role_assignments'] for n in a['notes']))

    def test_resource_refusal_keeps_complete_inventory_and_invalid_reference_fails(self):
        lower=extract_documents(source());req=request(lower)
        with patch('contextual_passage_roles.MAX_OCCURRENCES',1):out=evaluate(lower,[req])['results'][0]
        self.assertEqual(out['status'],'NOT_RUN_OCCURRENCE_RESOURCE_LIMIT')
        self.assertEqual(len(out['occurrence_inventory']),9)
        req['reference_candidate_ref']='invented-key'
        with self.assertRaises(ValueError):evaluate(lower,[req])

    def test_all_degree_slots_roots_registers_use_same_exact_equation(self):
        for kind,formula,slots in CHORD_DEGREE_DEFINITIONS:
            for root in range(12):
                label=dict(root_pc=root,kind=kind,formula=sorted({s[4] for s in slots}))
                for token,degree,alteration,semitones,pc in slots:
                    for octave in (1,4,6):
                        pitch=str(root+semitones+12*octave)
                        matches=note_role(pitch,label)['degree_relationships']
                        self.assertTrue(any(d['token']==token for d in matches))
                        self.assertTrue(all(pitch_from_degree(root,kind,d)==pitch for d in matches))
        diminished=note_role('69',dict(root_pc=0,kind='diminished-seventh',formula=[0,3,6,9]))
        sixth=note_role('69',dict(root_pc=0,kind='major-sixth',formula=[0,4,7,9]))
        self.assertEqual(diminished['degree_relationships'][0]['degree'],7)
        self.assertEqual(sixth['degree_relationships'][0]['degree'],6)
        bad=deepcopy(sixth['degree_relationships'][0]);bad['theoretical_semitones']=0
        with self.assertRaises(ValueError):pitch_from_degree(0,'major-sixth',bad)

    def test_complete_inventory_and_held_third_changes_to_nonmember(self):
        docs=source(destination=(48,52,55));docs['track-0.json']['measures'][0]['voices'][0]['beats']=[dict(duration=[1,2],notes=[dict(string=0,fret=28)])]
        lower=extract_documents(docs);package=evaluate(lower,[request(lower)]);out=package['results'][0]
        self.assertEqual(out['status'],'COMPLETE_CONDITIONAL_PASSAGE_ROLES')
        self.assertEqual(len(out['occurrence_inventory']),8)
        held=next(r for r in out['held_note_role_changes'] if r['occurrence_ref']=='event:123:0:1:0:0:0')
        self.assertTrue(any(a['role_changed'] and a['roles'][0]['degree_relationships'][0]['degree']==3 and a['roles'][1]['status']=='TEMPLATE_NONMEMBER' for a in held['alternatives']))
        evidence=package['harmonic_evidence'][out['harmonic_evidence_ref']]
        normalized=written(docs)
        expected=brute_pairs(normalized,evidence,[dict(occurrence_ref=held['occurrence_ref'],at_q='1/2'),dict(occurrence_ref=held['occurrence_ref'],at_q='3/2')])
        actual={tuple((l['root_pc'],l['kind']) for l in a['labels']) for a in held['alternatives']}
        self.assertEqual(actual,expected)

    def test_root_fifth_keeps_unplayed_third_and_quality_alternatives(self):
        docs=source();docs['track-0.json']['measures'][0]['voices'][0]['beats']=[dict(duration=[1,2],notes=[dict(string=0,fret=0)])]
        docs['track-1.json']['measures'][0]['voices'][0]['beats']=[dict(duration=[1,2],notes=[dict(string=0,fret=0),dict(string=1,fret=7)])]
        lower=extract_documents(docs);out=evaluate(lower,[request(lower)])['results'][0]
        labels=[l for e in out['optimal_edges'] for l in e['labels'] if l and l['root_pc']==4]
        self.assertTrue({'major','minor'}<={l['kind'] for l in labels})
        missing=[n['template_against_observation']['unobserved_template_pitch_classes'] for a in out['edge_label_role_assignments'] for n in a['notes']]
        self.assertIn([7],missing);self.assertIn([8],missing)

    def test_existing_passing_neighbor_logic_and_refusals_reused(self):
        for pitches,expected in (((60,62,64),'passing_like'),((60,62,60),'neighbor_like'),((60,60,64),None)):
            lower=extract_documents(motion_source(pitches));out=evaluate(lower,[request(lower,'3',True)])['results'][0]
            lead=[r for r in out['passing_neighbor_analysis'] if r['occurrence_refs']==[f'event:123:0:1:0:{i}:0' for i in range(3)]][0]
            roles=[role for a in lead['alternatives'] for role in a['conditional_roles']]
            if expected:self.assertIn(expected,roles)
            else:self.assertEqual(roles,[])

    def test_stripped_actual_worker_and_stale_degree_rejection(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower=extract_documents(source());upper=attach(analyze(lower),[request(lower)])
        with tempfile.TemporaryDirectory() as folder:
            result=execute(bundle(Path(__file__).parent)[0],strip_lower(upper),dict(variation=0),lower,Path(folder)/'worker',timeout=60)
            self.assertEqual(result['status'],'PASS',result)
        bad=strip_lower(upper);rows=bad['contextual_constraints']['results'][0]['edge_label_role_assignments']
        degree=next(n['role']['degree_relationships'][0] for r in rows for n in r['notes'] if n['role']['degree_relationships'])
        degree['degree']=99
        with self.assertRaises(ValueError):reconstruct(bad,dict(variation=0))
        bad=strip_lower(upper)
        completion=next(c for e in bad['contextual_constraints']['results'][0]['optimal_edges'] for c in e['unscored_theory_compatibility']['incomplete_compatible_templates'])
        completion['unobserved_template_pitch_classes']=[]
        with self.assertRaises(ValueError):reconstruct(bad,dict(variation=0))


if __name__=='__main__':unittest.main()
