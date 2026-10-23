"""Musical contrasts, independent exhaustive graph oracle and shared inverse."""
from copy import deepcopy
from fractions import Fraction as F
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,reconstruct
from contextual_note_roles import attach,evaluate,VERSION as ROLE_VERSION
from contextual_chord_motion import VERSION
from test_contextual_note_roles import source as role_source,request as role_request
from test_collection_degrees import candidate
from test_musical_tier2 import facts
import musical_tier2 as music


def source(destination=(45,48,52),melody=(68,69)):
    docs=role_source();docs['track-0.json']['measures'][0]['signature']=[2,4]
    docs['track-0.json']['measures'][0]['voices'][0]['beats']=[dict(duration=[1,4],notes=[dict(string=0,fret=p-40)]) for p in melody]
    docs['track-1.json']['tuning']=[40]*4;docs['track-1.json']['measures'][0]['signature']=[2,4]
    docs['track-1.json']['measures'][0]['voices'][0]['beats']=[dict(duration=[1,4],notes=[dict(string=i,fret=p-40) for i,p in enumerate(chord)]) for chord in ((40,44,47,50),destination)]
    return docs


def request(lower):
    upper=analyze(lower)
    return dict(version=VERSION,occurrence_refs=['event:123:0:1:0:0:0','event:123:0:1:0:1:0'],at_qs=['0','1'],
        candidate_ref=candidate(upper['musical_relationships'],'major'),harmonic_request=dict(start_q='0',end_q='2',part_id=None))


def brute_pairs(lower,evidence,queries):
    """Exhaustive boundary paths/labels for tiny fixtures; no core scorer."""
    from check_harmonic_span_source import check
    raw=[tuple(e[k] for k in ('part_id','bar','pitch','onset_q','duration_q')) for e in lower['events']]
    if check(raw,evidence)['status']!='PASS':raise AssertionError('Independent raw graph checker failed')
    points=list(map(F,evidence['partition_points_q']));forms=(('major',(0,4,7)),('dominant-seventh',(0,4,7,10)),('minor',(0,3,7)),('diminished-seventh',(0,3,6,9)),('half-diminished-seventh',(0,3,6,10)),('diminished',(0,3,6)))
    choices={}
    for stop,pred in enumerate(evidence['optimal_predecessors']):
        for begin in pred:
            counts=[0]*12
            for e in lower['events']:
                if e['pitch'] is not None:
                    counts[int(F(e['pitch'])%12)]+=sum(F(e['onset_q'])<=t<F(e['onset_q'])+F(e['duration_q']) for t in points[begin:stop])
            scored=[]
            for name,form in forms:
                for root in range(12):
                    included={(root+d)%12 for d in form};score=sum(n if pc in included else -n for pc,n in enumerate(counts))-sum(counts[p]==0 for p in included)
                    scored.append((score,(root,name)))
            maximum=max(s for s,l in scored);choices[begin,stop]=[l for s,l in scored if s==maximum]
    def paths(stop):
        if stop==0:yield [];return
        for begin in evidence['optimal_predecessors'][stop]:
            for path in paths(begin):yield path+[(begin,stop)]
    result=set()
    for path in paths(len(points)-1):
        for labels in itertools.product(*(choices[edge] for edge in path)):
            result.add(tuple(next(label for (begin,stop),label in zip(path,labels) if points[begin]<=F(q['at_q'])<points[stop]) for q in queries))
    return result


class ChordMotionTests(unittest.TestCase):
    def test_E7_to_Aminor_versus_C_and_nonmoving_voice(self):
        for destination,melody,root,motion in (((45,48,52),(68,69),9,'1'),((48,52,55),(68,67),0,'-1'),((45,48,52),(68,68),9,'0')):
            lower=extract_documents(source(destination,melody));out=evaluate(lower,[request(lower)])['results'][0]
            self.assertEqual(out['status'],'CONDITIONAL_CHORD_VOICE_RELATIONSHIPS')
            alternatives=[a for a in out['alternatives'] if a['labels'][0]['root_pc']==4 and a['labels'][0]['kind']=='dominant-seventh' and a['labels'][1]['root_pc']==root]
            self.assertTrue(alternatives)
            self.assertEqual(out['source_motion']['motion']['displacement_semitones'],motion)
            self.assertFalse(out['note_reference_coordinates'][0]['in_reference_collection'])
            self.assertIsNone(out['diatonic_displacement'])
            self.assertTrue(all(8 in a['contexts'][0]['chord_tone_pitch_classes_outside_reference'] for a in alternatives))
            self.assertFalse(any('temporary_tonic' in a or 'modulation' in a or 'resolved' in a for a in alternatives))

    def test_same_edge_rejects_impossible_cartesian_label_pairs(self):
        lower=facts([(0,p,0,2) for p in (60,63,66,69)]);upper=music.analyze(lower);e=music.harmonic_span_evidence(upper,'0','2')
        queries=[dict(occurrence_ref='note-0',at_q='0'),dict(occurrence_ref='note-1',at_q='1')]
        result=music.harmonic_label_pair_evidence(upper,e,queries)
        pairs={tuple((l['root_pc'],l['kind']) for l in a['labels']) for a in result['feasible_label_pairs']}
        self.assertEqual(pairs,brute_pairs(lower,e,queries));self.assertGreater(len(pairs),1)
        self.assertTrue(all(a==b for a,b in pairs));self.assertLess(len(pairs),len({a for a,b in pairs})**2)

    def test_multiedge_all_pairs_match_exhaustive_source_oracle(self):
        for pitches in ((60,64,67),(60,63,66),(60,64,69)):
            lower=facts([(0,p,i,1) for i,p in enumerate(pitches)]);upper=music.analyze(lower);e=music.harmonic_span_evidence(upper,'0','3')
            queries=[dict(occurrence_ref='note-0',at_q='0'),dict(occurrence_ref='note-2',at_q='2')]
            result=music.harmonic_label_pair_evidence(upper,e,queries)
            pairs={tuple(None if l is None else (l['root_pc'],l['kind']) for l in a['labels']) for a in result['feasible_label_pairs']}
            self.assertEqual(pairs,brute_pairs(lower,e,queries))

    def test_ties_rests_expression_and_outside_clock_are_not_repaired(self):
        for kind in ('tie','bend','rest'):
            docs=source();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats'];refs=None
            if kind=='rest':beats.insert(1,dict(duration=[1,8],notes=[dict(rest=True)]))
            else:beats[1]['notes'][0][kind]=True if kind=='tie' else dict(tone=100)
            lower=extract_documents(docs);req=request(lower)
            if kind=='rest':req['occurrence_refs'][1]='event:123:0:1:0:2:0';req['at_qs'][1]='3/2'
            result=evaluate(lower,[req])['results'][0]
            self.assertEqual(result['status'],'SOURCE_SEQUENCE_REFUSED')
        lower=extract_documents(source());req=request(lower);req['at_qs'][0]='1'
        with self.assertRaises(ValueError):evaluate(lower,[req])

    def test_new_and_legacy_packages_same_worker_and_stale_rejection(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower=extract_documents(source());upper=attach(analyze(lower),[request(lower)]);bare=strip_lower(upper)
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            result=execute(code,bare,dict(variation=0),lower,Path(folder)/'worker',timeout=60)
            self.assertEqual(result['status'],'PASS',result)
        for mode in ('omit','root','motion'):
            bad=deepcopy(bare);row=bad['contextual_constraints']['results'][0]
            if mode=='omit':row['alternatives'].pop()
            elif mode=='root':row['alternatives'][0]['root_displacement_pc']='14'
            else:row['source_motion']['motion']['displacement_semitones']='14'
            with self.assertRaises(ValueError):reconstruct(bad,dict(variation=0))
        oldlower=extract_documents(role_source());old=attach(analyze(oldlower),[role_request(oldlower)])
        old['contextual_constraints']['version']=ROLE_VERSION
        self.assertEqual(reconstruct(strip_lower(old),dict(variation=0)),oldlower)

    def test_fractional_source_pitch_is_unknown_membership_not_definite_nonmember(self):
        docs=source();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret']=28.5
        lower=extract_documents(docs);out=evaluate(lower,[request(lower)])['results'][0]
        self.assertEqual(out['source_motion']['motion']['displacement_semitones'],'1/2')
        self.assertTrue(out['alternatives'])
        for pair in out['alternatives']:
            context=pair['contexts'][0]['note_against_chord']
            self.assertEqual(context['membership'],'unknown');self.assertIsNone(context['chord_member'])
        # Existing numeric physical relationship owns this exact source value;
        # it does not make a fractional pitch diatonic or a chord nonmember.
        self.assertEqual(reconstruct(strip_lower(analyze(lower)),dict(variation=0)),lower)

    def test_source_arm_vibrato_strings_owned_and_refused_without_detector_changes(self):
        for value in ('wide','slight'):
            docs=source();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['vibratoWithTremoloBar']=value
            lower=extract_documents(docs);upper=analyze(lower);self.assertEqual(upper['unsupported'],[])
            self.assertTrue(any(g['field']=='vibratoWithTremoloBar' for g in upper['owned_parameters']['technique_declarations']['groups']))
            self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)
            self.assertEqual(evaluate(lower,[request(lower)])['results'][0]['status'],'SOURCE_SEQUENCE_REFUSED')


if __name__=='__main__':unittest.main()
