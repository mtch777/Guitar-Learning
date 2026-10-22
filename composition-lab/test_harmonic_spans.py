"""Frozen analytical contrasts and independent exhaustive DAG verification."""
from fractions import Fraction as F
from itertools import combinations
import unittest
from test_musical_tier2 import facts
from copy import deepcopy
from musical_tier2 import analyze, strip_lower, reconstruct, harmonic_template_scores, harmonic_span_evidence, harmonic_note_context

# Defined before running this method; these are analytical witnesses, not fitting.
CONTRASTS={
 'arpeggio':[(0,60,0,1),(0,64,1,1),(0,67,2,1),(0,72,3,1)],
 'repeated_triad':[(0,p,t,1) for t in (0,1,2) for p in (60,64,67)],
 'passing_note':[(0,p,0,4) for p in (48,52,55)]+[(0,72,0,1),(0,74,1,1),(0,76,2,2)],
 'held_context_change':[(0,60,0,4),(0,64,0,2),(0,67,0,2),(0,65,2,2),(0,69,2,2)],
}


def brute_paths(notes,start,end):
    rows=[(max(F(a),F(start)),min(F(a)+F(d),F(end)),p) for _,p,a,d in notes if F(a)<F(end) and F(a)+F(d)>F(start)]
    points=sorted({F(start),F(end)}|{t for a,b,_ in rows for t in (a,b)})
    templates=[{(root+s)%12 for s in form} for form in ((0,4,7),(0,4,7,10),(0,3,7),(0,3,6,9),(0,3,6,10),(0,3,6)) for root in range(12)]
    def score(i,j):
        weights=[0]*12
        for a,b,p in rows:
            for t in points[i:j]:
                if a<=t<b:weights[p%12]+=1
        if not any(weights):return 0
        return max(sum(weights[p] if p in template else -weights[p] for p in range(12))-sum(weights[p]==0 for p in template) for template in templates)
    paths=[]
    for count in range(len(points)-2+1):
        for middle in combinations(range(1,len(points)-1),count):
            path=(0,)+middle+(len(points)-1,);paths.append((sum(score(a,b) for a,b in zip(path,path[1:])),path))
    optimum=max(s for s,_ in paths)
    return optimum,[p for s,p in paths if s==optimum]


class HarmonicSpanTests(unittest.TestCase):
    def test_published_hand_computable_score_and_ties(self):
        weights=[0]*12;weights[0]=4;weights[4]=4;weights[2]=1
        rows=harmonic_template_scores(weights)
        self.assertEqual(len(rows),72)
        for root,kind in ((0,'major'),(9,'minor')):
            row=next(r for r in rows if r['root_pc']==root and r['kind']==kind)
            self.assertEqual((row['positive'],row['negative'],row['missing'],row['score']),(8,1,1,6))

    def test_all_optimal_paths_match_independent_exhaustive_search(self):
        for name,notes in CONTRASTS.items():
            with self.subTest(name=name):
                end=3 if name=='repeated_triad' else 4
                result=harmonic_span_evidence(strip_lower(analyze(facts(notes))),'0',str(end),0)
                best,paths=brute_paths(notes,0,end)
                self.assertEqual(result['optimal_score'],best)
                self.assertEqual(int(result['optimal_boundary_path_count']),len(paths))
                # Backpointers to unreachable optimal-prefix nodes need not be
                # globally reachable. Reconstruct ALL paths to terminal.
                def walk(j):
                    if j==0:return [(0,)]
                    return [p+(j,) for i in result['optimal_predecessors'][j] for p in walk(i)]
                self.assertEqual(set(walk(len(result['partition_points_q'])-1)),set(paths))

    def test_arpeggio_has_chord_context_without_simultaneous_triad(self):
        upper=analyze(facts(CONTRASTS['arpeggio']))
        self.assertTrue(all(not g['interpretation']['chord_candidates'] for g in upper['coattacks']))
        result=harmonic_span_evidence(upper,'0','4',0)
        self.assertEqual(len(result['canonical_display_path']),1)
        labels=result['canonical_display_path'][0]['candidates']
        self.assertEqual([(c['root_pc'],c['kind']) for c in labels],[(0,'major')])
        self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),facts(CONTRASTS['arpeggio']))

    def test_repeats_do_not_force_new_harmony_and_ties_not_hidden(self):
        result=harmonic_span_evidence(analyze(facts(CONTRASTS['repeated_triad'])),'0','3',0)
        self.assertEqual(result['optimal_boundary_path_count'],'4')
        self.assertEqual(len(result['canonical_display_path']),1)
        self.assertEqual(result['mandatory_boundary_indices'],[0,3])
        self.assertTrue(all(r['status']=='unanimous_under_this_objective' for r in result['all_optimal_path_cell_consensus']))

    def test_held_note_is_included_at_request_edge_without_new_attack(self):
        result=harmonic_span_evidence(analyze(facts(CONTRASTS['held_context_change'])),'1','4',0)
        self.assertIn('note-0',result['minimal_cells'][0]['already_active_at_request_refs'])
        self.assertEqual(result['minimal_cells'][0]['start_q'],'1')
        roots=[(s['start_q'],s['end_q'],[(c['root_pc'],c['kind']) for c in s['candidates']]) for s in result['canonical_display_path']]
        self.assertEqual(roots,[('1','2',[(0,'major')]),('2','4',[(5,'major')])])

    def test_resource_limit_never_truncates_or_chooses_easier_scope(self):
        result=harmonic_span_evidence(analyze(facts(CONTRASTS['arpeggio'])),'0','4',0,max_edges=1)
        self.assertEqual(result['status'],'NOT_RUN_RESOURCE_LIMIT')
        self.assertEqual(result['request']['end_q'],'4')
        self.assertEqual(result['required_edges'],10)
        self.assertNotIn('canonical_display_path',result)

    def test_held_note_context_changes_using_same_coordinate_equation(self):
        upper=analyze(facts(CONTRASTS['held_context_change']))
        evidence=harmonic_span_evidence(upper,'0','4',0)
        before=harmonic_note_context(upper,'note-0',evidence,0,1)
        after=harmonic_note_context(upper,'note-0',evidence,1,2)
        self.assertEqual(before['coordinates'][0]['semitones_mod12'],'0')
        self.assertEqual(after['coordinates'][0]['semitones_mod12'],'7')
        self.assertEqual((before['context_end_q'],after['context_start_q']),('2','2'))
        stale=deepcopy(evidence);stale['optimal_score']+=1
        with self.assertRaises(ValueError):harmonic_note_context(upper,'note-0',stale,0,1)
        unknown=analyze(facts([(0,None,0,1)]));result=harmonic_span_evidence(unknown,'0','1',0)
        self.assertEqual(harmonic_note_context(unknown,'note-0',result,0,1)['coordinates'],[])

    def test_unknown_notes_empty_region_and_timing_quarantine_explicit(self):
        lower=facts([(0,60,0,1),(0,None,2,1)])
        result=harmonic_span_evidence(analyze(lower),'0','4',0)
        self.assertIn('note-1',result['excluded_member_refs']['unknown_pitch'])
        self.assertTrue(result['unknown_regions'])
        lower['source_coverage']['timing_warnings']=[dict(part_id=0,bar=1,voice=0,reason='voice_overflows_bar',duration_q='5',span_q='4')]
        blocked=harmonic_span_evidence(analyze(lower),'0','4',0)
        self.assertEqual(blocked['status'],'NOT_RUN_SOURCE_TIMING_UNCERTAIN')

    def test_unknown_boundaries_cannot_multiply_pitched_evidence(self):
        notes=[(0,p,0,4) for p in (60,64,67)]
        original=harmonic_span_evidence(analyze(facts(notes)),'0','4',0)
        changed_upper=analyze(facts(notes+[(0,None,1,1)]))
        changed=harmonic_span_evidence(changed_upper,'0','4',0)
        self.assertEqual(changed['partition_points_q'],original['partition_points_q'])
        self.assertEqual(changed['optimal_score'],original['optimal_score'])
        self.assertEqual(changed['canonical_display_path'][0]['pitch_class_note_cell_weights'],original['canonical_display_path'][0]['pitch_class_note_cell_weights'])
        self.assertEqual(changed['unknown_pitch_overlays'][0]['start_q'],'1')
        self.assertEqual(changed['canonical_display_path'][0]['status'],'partial_known_pitch_scored_alternatives')
        self.assertEqual(harmonic_note_context(changed_upper,'note-0',changed,0,1)['evidence_status'],'partial_known_pitch_evidence')

    def test_actual_isolated_query_and_inverse_use_only_stripped_package(self):
        import tempfile
        from pathlib import Path
        from run_harmonic_span_qa import isolated
        lower=facts(CONTRASTS['arpeggio']);upper=analyze(lower)
        request=dict(start_q='0',end_q='4',part_id=0,max_edges=50000)
        evidence=harmonic_span_evidence(upper,**request)
        with tempfile.TemporaryDirectory() as directory:
            result=isolated(Path(__file__).with_name('musical_tier2.py').read_text(encoding='utf-8'),upper,lower,request,evidence,Path(directory)/'actual')
            self.assertEqual(result['status'],'PASS',result)

    def test_consensus_mandatory_cuts_labels_and_empty_options_by_enumeration(self):
        for notes in (CONTRASTS['arpeggio'],CONTRASTS['repeated_triad'],CONTRASTS['held_context_change'],[(0,60,0,1)],[(0,60,0,1),(0,64,2,1)]):
            end=max(a+d for _,_,a,d in notes)
            result=harmonic_span_evidence(analyze(facts(notes)),'0',str(end),0)
            _,paths=brute_paths(notes,0,end)
            mandatory=set(paths[0]).intersection(*map(set,paths[1:]))
            self.assertEqual(result['mandatory_boundary_indices'],sorted(mandatory))
            points=list(map(F,result['partition_points_q']))
            forms=(('major',(0,4,7)),('dominant-seventh',(0,4,7,10)),('minor',(0,3,7)),('diminished-seventh',(0,3,6,9)),('half-diminished-seventh',(0,3,6,10)),('diminished',(0,3,6)))
            for cell,summary in enumerate(result['all_optimal_path_cell_consensus']):
                union=set();empty=False
                for path in paths:
                    i,j=next((i,j) for i,j in zip(path,path[1:]) if i<=cell<j)
                    weights=[0]*12
                    for _,p,a,d in notes:
                        for t in points[i:j]:
                            if F(a)<=t<F(a+d):weights[p%12]+=1
                    if not any(weights):empty=True;continue
                    scores=[]
                    for kind,form in forms:
                        for root in range(12):
                            pcs={(root+x)%12 for x in form}
                            score=sum(w if p in pcs else -w for p,w in enumerate(weights))-sum(weights[p]==0 for p in pcs)
                            scores.append((score,root,kind))
                    best=max(s for s,_,_ in scores);union|={(r,k) for s,r,k in scores if s==best}
                self.assertEqual({(c['root_pc'],c['kind']) for c in summary['candidate_labels']},union)
                self.assertEqual(summary['no_pitched_evidence_possibility'],empty)

    def test_boundary_diagnostic_ignores_same_chord_restatement(self):
        from check_harmonic_boundaries import compare
        reference=[dict(start_q=str(a),reference_root_pc=root,reference_formula=formula) for a,root,formula in ((0,0,[0,4,7]),(1,0,[0,4,7]),(2,7,[0,4,7]))]
        evidence=dict(partition_points_q=['0','1','2','3'],mandatory_boundary_indices=[0,2,3],canonical_display_path=[dict(start_q=str(i)) for i in (0,1,2)])
        result=compare(reference,evidence)
        self.assertEqual(result['canonical_display_cuts']['precision'],.5)
        self.assertEqual(result['canonical_display_cuts']['recall'],1)
        self.assertEqual(result['all_path_mandatory_cuts']['precision'],1)


if __name__=='__main__':unittest.main()
