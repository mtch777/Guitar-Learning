"""Frozen musical positive/negative contrasts and actual stripped worker."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,reconstruct
from contextual_note_roles import VERSION,evaluate,attach,role_predicate,partial_path_possibilities
from test_collection_degrees import candidate


def source(pitches=(60,62,64),transpose=0):
    melody=[dict(duration=[1,4],notes=[dict(string=0,fret=p+transpose-40)]) for p in pitches]
    chord=[dict(duration=[3,4],notes=[dict(string=i,fret=p+transpose-40) for i,p in enumerate((48,52,55))])]
    parts={f'track-{i}.json':dict(songId=123,revisionId=1,partId=i,name=name,instrumentId=25,tuning=[40]*3,measures=[dict(signature=[3,4],voices=[dict(beats=beats)])]) for i,(name,beats) in enumerate((('Melody',melody),('Chord',chord)))}
    return dict({'metadata.json':dict(songId=123,revisionId=1,title='Definition contrast',artist='Authored test',tracks=[dict(name='Melody',instrumentId=25),dict(name='Chord',instrumentId=25)])},**parts)


def request(lower,tonic=0,quality='major',refs=None):
    upper=analyze(lower)
    return dict(version=VERSION,occurrence_refs=refs or [f'event:123:0:1:0:{i}:0' for i in range(3)],candidate_ref=candidate(upper['musical_relationships'],quality,tonic),harmonic_request=dict(start_q='0',end_q='3',part_id=None))


class ContextualRoles(unittest.TestCase):
    def test_predicate_exhaustive_memberships_and_motion_definitions(self):
        import itertools
        for vector in itertools.product(('chord_member','nonmember','unknown'),repeat=3):
            for shape in ('strictly_monotonic','departure_and_return','contains_repetition'):
                actual=role_predicate(shape,[True,True],list(vector))
                expected=[] if list(vector)!=['chord_member','nonmember','chord_member'] or shape=='contains_repetition' else ['passing_like'] if shape=='strictly_monotonic' else ['neighbor_like']
                self.assertEqual(actual,expected)
                self.assertEqual(role_predicate(shape,[True,True],list(vector),partial=True),[])
                self.assertEqual(role_predicate(shape,[True,True],list(vector),eligible=False),[])
                self.assertEqual(role_predicate(shape,[True,False],list(vector)),[])

    def test_passing_neighbor_leap_and_all_chord_members(self):
        for pitches,expected in (((60,62,64),'passing_like'),((64,62,60),'passing_like'),((60,62,60),'neighbor_like'),((60,62,67),None),((60,64,67),None)):
            with self.subTest(pitches=pitches):
                lower=extract_documents(source(pitches));out=evaluate(lower,[request(lower)])['results'][0]
                roles={r for a in out['alternatives'] for r in a['conditional_roles']}
                self.assertEqual(roles,set() if expected is None else {expected},out['status'])
                self.assertIsNone(out['reference_motion']['established_key'])
                self.assertIsNone(out['joint_context']['chord_mode'])

    def test_source_tie_grace_expression_gap_simultaneity_and_intervening_notes(self):
        for kind in ('tie','bend','slide','harmonic','vibrato','grace','gap','simultaneous','intervening'):
            docs=source();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats'];refs=None
            if kind in ('tie','vibrato'):beats[1]['notes'][0][kind]=True
            elif kind in ('bend','slide','harmonic'):beats[1]['notes'][0][kind]=dict(type='unresolved')
            elif kind=='grace':beats[1]['notes'][0]['graceNote']=True
            elif kind=='gap':
                beats.insert(1,dict(duration=[1,8],notes=[dict(rest=True)]));refs=[f'event:123:0:1:0:{i}:0' for i in (0,2,3)]
            elif kind=='simultaneous':beats[1]['notes'].append(dict(string=1,fret=24))
            else:
                beats.insert(1,dict(duration=[1,8],notes=[dict(string=0,fret=21)]));refs=[f'event:123:0:1:0:{i}:0' for i in (0,2,3)]
            lower=extract_documents(docs);out=evaluate(lower,[request(lower,refs=refs)])['results'][0]
            self.assertEqual(out['status'],'SOURCE_SEQUENCE_REFUSED',kind)
            self.assertTrue(out['source_refusals']);self.assertEqual(out['alternatives'],[])

    def test_transposition_same_conditional_meaning(self):
        signatures=[]
        for shift in (0,1,5,11):
            lower=extract_documents(source(transpose=shift));result=evaluate(lower,[request(lower,shift)])['results'][0]
            signatures.append((result['status'],[(r['memberships'],r['conditional_roles']) for r in result['alternatives']]))
        self.assertTrue(all(s==signatures[0] for s in signatures))

    def test_harmonic_ambiguity_retains_qualifying_and_disqualifying_paths(self):
        docs=source();beat=docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]
        beat['notes']=beat['notes'][:1]
        lower=extract_documents(docs);out=evaluate(lower,[request(lower)])['results'][0]
        self.assertEqual(out['status'],'CONDITIONAL_ROLE_SOME_MEMBERSHIP_VECTORS')
        self.assertEqual({tuple(a['conditional_roles']) for a in out['alternatives']},{(),('passing_like',)})
        self.assertTrue(all(a['one_valid_path_and_label_witness'] for a in out['alternatives']))

    def test_fractional_chord_display_width_exactly_preserved(self):
        docs=source();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['chord']=dict(text='C',width=17.1240234375)
        lower=extract_documents(docs);upper=analyze(lower)
        self.assertEqual(upper['unsupported'],[])
        self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)

    def test_all_optimal_paths_not_only_clean_stored_witness(self):
        # One membership vector can be witnessed by either0->1->2->3 or0->3.
        # All queries occur before2. The first path's supporting0->1 edge is
        # clean; the alternate0->3 edge includes an unknown overlay at5/2.
        graph=dict(status='SCORED_NOT_MUSICAL_TRUTH',partition_points_q=['0','1','2','3'],
            optimal_predecessors=[[],[0],[1],[0,2]],unknown_pitch_overlays=[dict(start_q='5/2',end_q='3')])
        queries=[dict(at_q=q) for q in ('0','1/4','1/2')]
        self.assertEqual(partial_path_possibilities(graph,queries),[True]*3)
        graph['optimal_predecessors'][-1]=[2]
        self.assertEqual(partial_path_possibilities(graph,queries),[False]*3)

    def test_equivalent_expression_declarations_and_zero_harmonic_fret_refused(self):
        for scope,field,value in (('note','leftHandVibrato','wide'),('note','wideVibrato',True),('note','harmonicFret',0),('note','bend',{}),('beat','tremoloBar',{}),('beat','wideVibrato',True),('beat','harmonic',True)):
            docs=source();beat=docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]
            (beat['notes'][0] if scope=='note' else beat)[field]=value
            lower=extract_documents(docs);out=evaluate(lower,[request(lower)])['results'][0]
            self.assertEqual(out['status'],'SOURCE_SEQUENCE_REFUSED',(scope,field))

    def test_verified_percussion_not_missing_pitch_but_dead_or_unknown_stays_uncertain(self):
        original=extract_documents(source());base=evaluate(original,[request(original)])
        for instrument,dead,expected in ((1024,False,'explicit_nonpitched'),(25,True,'pitched'),(9999,False,'unknown')):
            docs=source();docs['metadata.json']['tracks'].append(dict(name='No name inference',instrumentId=instrument))
            docs['track-2.json']=dict(songId=123,revisionId=1,partId=2,name='No name inference',instrumentId=instrument,tuning=[],
                measures=[dict(signature=[3,4],voices=[dict(beats=[dict(duration=[3,4],notes=[dict(string=0,fret=38,dead=dead)])])])])
            lower=extract_documents(docs);out=evaluate(lower,[request(lower)])
            domain=next(r for r in out['pitch_domains'] if r['occurrence_ref'].startswith('event:123:2:'))
            self.assertEqual(domain['domain'],expected)
            self.assertEqual(len(out['pitch_domains']),7)
            row=out['results'][0]
            if instrument==1024:
                self.assertEqual(row['status'],base['results'][0]['status'])
                self.assertEqual(row['alternatives'],base['results'][0]['alternatives'])
                evidence=out['harmonic_evidence'][row['harmonic_evidence_ref']]
                self.assertEqual(evidence['unknown_pitch_overlays'],[])
                self.assertEqual(evidence['excluded_member_refs']['explicit_nonpitched'],['event:123:2:1:0:0:0'])
            else:
                self.assertTrue(all(r['partial_pitch_evidence'] for r in row['alternatives']))
                self.assertFalse(any(r['conditional_roles'] for r in row['alternatives']))
            upper=attach(analyze(lower),[request(lower)])
            self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)

    def test_same_actual_inverse_checks_roles_and_rejects_corruption(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower=extract_documents(source());upper=attach(analyze(lower),[request(lower)]);bare=strip_lower(upper)
        self.assertEqual(reconstruct(bare,dict(variation=0)),lower)
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            result=execute(code,bare,dict(variation=0),lower,Path(folder)/'worker',timeout=60)
            self.assertEqual(result['status'],'PASS',result)
        for kind in ('role','omitted_alternative','reference'):
            bad=deepcopy(bare);row=bad['contextual_constraints']['results'][0]
            if kind=='role':row['alternatives'][0]['conditional_roles']=['invented_role']
            elif kind=='omitted_alternative':row['alternatives'].pop()
            else:row['reference_motion']['pairs'][0]['signed_diatonic_displacement']=14
            with self.assertRaises(ValueError):reconstruct(bad,dict(variation=0))


if __name__=='__main__':unittest.main()
