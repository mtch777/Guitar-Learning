"""Authored discovery boundaries, not fresh-song or musical preference evidence."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

import connected_tier2 as connected
import melodic_approach_discovery as discovery
import melodic_arrival_relation as arrival
import musical_tier2 as music
from source_fact_tier1 import extract_documents
from source_observation_evidence import digest


def documents(pitches=(60, 62, 64), durations=((1, 4), (1, 4), (1, 2))):
    beats = [dict(duration=list(d), notes=[dict(string=0, fret=p-48)])
             for p,d in zip(pitches,durations)]
    tracks = [dict(name='Name does not select this line', instrumentId=27),
              dict(name='Backing', instrumentId=89)]
    docs = {'metadata.json':dict(songId=901, revisionId=1, artist='Authored fixture',
                title='Consecutive approaches', tracks=tracks)}
    for i, spec in enumerate(tracks):
        notes = [dict(string=j, fret=0) for j in range(3)]
        docs[f'track-{i}.json'] = dict(songId=901, revisionId=1, partId=i, **spec,
            tuning=[48, 52, 55], frets=48,
            measures=[dict(signature=[4, 4], voices=[dict(beats=beats if i==0 else
                [dict(duration=[1, 1], notes=notes)])])])
    return docs


def model(docs=None):
    return connected.strip_lower(connected.analyze(extract_documents(docs or documents())))


def lane(pitches):
    return [dict(attack_ref=str(i), pitch=str(p), start_q=str(i), end_q=str(i+1),
                 refusal_reasons=[]) for i,p in enumerate(pitches)]


MAJOR = dict(id='C-major', tonic_pc=0, intervals=[0,2,4,5,7,9,11])


class ApproachDiscoveryTests(unittest.TestCase):
    def test_all_runs_deterministic_read_only_and_one_inverse(self):
        t2 = model(); before = deepcopy(t2)
        with patch.object(discovery.connected, 'realize', wraps=connected.realize) as inverse:
            report = discovery.discover(t2)
        self.assertEqual(inverse.call_count, 1)
        self.assertEqual(t2, before)
        self.assertEqual(report['input_sha256'], digest(t2))
        self.assertEqual(report, json.loads(json.dumps(report)))
        self.assertEqual(report, discovery.discover(json.loads(json.dumps(t2))))
        self.assertEqual(report['guitar_parts'], [0])
        self.assertEqual(len(report['runs']), 1)
        row = report['runs'][0]
        self.assertEqual(row['status'], 'RELATION_AND_FLIP_ADMITTED')
        self.assertEqual(arrival.realize(row['relation']), ['60','62','64'])
        self.assertEqual(row['proposed_pitches'], ['67','65','64'])
        self.assertTrue(all(not ref.startswith('event:901:0:')
            for rank in row['rankings'] for ref in rank['used_member_refs']))
        self.assertEqual(report['ownership_admission'], 'NOT_TESTED')

    def test_maximal_runs_and_shared_turningpoint_never_shorten(self):
        rows = lane([60,62,64,65,64,62,60])
        runs, pairs = discovery.maximal_runs(rows, [MAJOR])
        self.assertEqual([[a['attack_ref'] for a in r['attacks']] for r in runs],
                         [['0','1','2','3'], ['3','4','5','6']])
        self.assertTrue(all(not p['refusal_reasons'] for p in pairs))
        docs = documents((60,62,64,65), ((1,4),)*4)
        report = discovery.discover(model(docs))
        self.assertEqual(len(report['runs']), 1)
        self.assertEqual(len(report['runs'][0]['attacks']), 4)

    def test_numeric_program_and_every_voice_define_population_not_part_name(self):
        docs=documents()
        docs['track-0.json']['name']='Percussion label does not matter'
        docs['track-0.json']['instrumentId']=24
        voices=docs['track-0.json']['measures'][0]['voices']
        voices.append(deepcopy(voices[0]))
        docs['track-1.json']['instrumentId']=31
        report=discovery.discover(model(docs))
        self.assertEqual(report['guitar_parts'],[0,1])
        self.assertEqual([(r['part_id'],r['voice']) for r in report['attack_lanes']],[(0,0),(0,1),(1,0)])
        self.assertEqual(report['counts']['raw_guitar_occurrences'],9)
        self.assertTrue(any(r['part_id']==1 for r in report['barriers']))

    def test_exact_profile_ties_and_undefined_contexts_are_not_cherry_picked(self):
        r = discovery.ranking([dict(id='c',score=None),dict(id='b',score=.5),
                               dict(id='a',score=.5),dict(id='d',score=.4)], 'score')
        self.assertEqual([x['id'] for x in r['exact_maxima']], ['a','b'])
        self.assertEqual(len(r['ranking']), 4)
        with self.assertRaisesRegex(ValueError, 'NO_DEFINED_MAXIMUM'):
            discovery.contexts_from_rankings([dict(exact_maxima=[])])
        # D is supported by C major but absent in this second interpretation.
        contexts = [MAJOR, dict(id='other',tonic_pc=0,intervals=[0,1,4,5,7,9,11])]
        runs, pairs = discovery.maximal_runs(lane([60,62,64]), contexts)
        self.assertEqual(runs, [])
        self.assertTrue(all('OUTSIDE_GLOBAL_COLLECTION' in p['refusal_reasons'] for p in pairs))

    def test_tied_holds_are_one_attack_with_all_written_members(self):
        docs = documents((60,62,62,64), ((1,4),)*4)
        beats = docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[2]['notes'][0]['tie'] = True
        t2 = model(docs); report = discovery.discover(t2); row = report['runs'][0]
        self.assertEqual(report['counts']['tie_continuations_collapsed'], 1)
        self.assertEqual([len(a['member_refs']) for a in row['attacks']], [1,2,1])
        self.assertEqual([(a['start_q'],a['end_q']) for a in row['attacks']], [('0','1'),('1','3'),('3','4')])
        self.assertEqual(row['status'], 'RELATION_AND_FLIP_ADMITTED')
        context = discovery.backing_context(t2, row)
        self.assertEqual([(c['start_q'],c['end_q']) for c in context['cells']], [('0','1'),('1','3'),('3','4')])

    def test_complete_coattack_dead_grace_unknown_and_unresolved_tie_barriers(self):
        for kind, reason in [('coattack','COATTACK_NOT_ONE_COMPLETE_LINE'),
                ('dead','DEAD_MEMBER'), ('unknown','UNKNOWN_WRITTEN_PITCH'),
                ('grace','GRACE_OR_NONPOSITIVE_DURATION'), ('tie','UNRESOLVED_WRITTEN_TIE:')]:
            with self.subTest(kind=kind):
                docs = documents(); beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
                if kind=='coattack': beats[1]['notes'].append(dict(string=1,fret=13))
                elif kind=='dead': beats[1]['notes'][0]['dead']=True
                elif kind=='unknown': beats[1]['notes'][0].pop('fret')
                elif kind=='grace': beats[1]['graceNote']='beforeBeat'
                else: beats[1]['notes'][0]['tie']=True
                t2=model(docs);before=deepcopy(t2);report=discovery.discover(t2)
                self.assertEqual(report['runs'], [])
                self.assertTrue(any(x.startswith(reason) for b in report['barriers'] for x in b['refusal_reasons']))
                self.assertEqual(t2,before)

    def test_rest_and_positive_gap_break_run_without_erasing_short_remainder(self):
        docs=documents((60,62,64),((1,4),)*3)
        beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats.insert(1,dict(duration=[1,4],rest=True,notes=[]))
        report=discovery.discover(model(docs))
        self.assertEqual(report['runs'], [])
        self.assertEqual(len(report['short_maximal_runs']),1)
        self.assertTrue(any('POSITIVE_REST_OR_GAP_POLICY' in r['refusal_reasons'] for r in report['pair_inventory']))

    def test_observed_technique_is_not_silently_excluded_as_unsafe_to_edit(self):
        docs=documents();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['notes'][0]['slide']='shift';beats[1]['notes'][0]['tremolo']=True
        report=discovery.discover(model(docs))
        self.assertEqual(report['runs'][0]['status'],'RELATION_AND_FLIP_ADMITTED')
        self.assertEqual(report['runs'][0]['attacks'][0]['source_note_flags'],[dict(slide='shift')])
        self.assertEqual(report['execution_and_playback'],'NOT_TESTED')

    def test_failed_maximal_run_remains_whole_instead_of_retrying_shorter_prefix(self):
        docs=documents((60,62,64,65),((1,4),)*4)
        original=discovery.profile_rows
        def local_g_major(groups,label):
            rows=original(groups,label)
            if ':bars' in label:
                for row in rows:
                    row['exact_maxima']=[c for c in row['ranking']
                        if c['tonic_pc']==7 and c['reference_intervals']==MAJOR['intervals']]
            return rows
        # A controlled ambiguous local result: C,D,E fit both; the final F does
        # not. The failed complete C,D,E,F run must not become an admitted prefix.
        with patch.object(discovery,'profile_rows',side_effect=local_g_major):
            report=discovery.discover(model(docs))
        self.assertEqual(len(report['runs']),1)
        self.assertEqual(report['runs'][0]['original_pitches'],['60','62','64','65'])
        self.assertEqual(report['runs'][0]['status'],'ORIGINAL_RELATION_REFUSED')
        self.assertEqual(report['runs'][0]['refusal_reasons'],['LOCAL_OR_TIMED_INTERPRETATION_NOT_SUPPORTED'])

    def test_context_reports_held_backing_intervals_and_rejects_stale_or_tampered_row(self):
        t2=model(); before=deepcopy(t2); row=discovery.discover(t2)['runs'][0]
        context=discovery.backing_context(t2,row)
        self.assertEqual(len(context['cells']),3)
        first=context['cells'][0]
        self.assertEqual([r['original'] for r in first['intervals']], ['12','8','5'])
        self.assertEqual([r['proposed'] for r in first['intervals']], ['19','15','12'])
        self.assertEqual(t2,before)
        bad=deepcopy(row);bad['proposed_pitches'][0]='99'
        with self.assertRaisesRegex(ValueError,'same relationship'):
            discovery.backing_context(t2,bad)
        changed=deepcopy(t2)
        changed['musical_relationships']=music.transpose(changed['musical_relationships'],'1')
        with self.assertRaisesRegex(ValueError,'Stale'):
            discovery.backing_context(changed,row)
        after=discovery.discover(changed)
        self.assertNotEqual(after['input_sha256'], row['input_sha256'])
        self.assertNotEqual(after['runs'][0]['id'], row['id'])
        self.assertEqual(after['runs'][0]['original_pitches'],['61','63','65'])
        self.assertEqual(changed['source_origin'], t2['source_origin'])


if __name__=='__main__': unittest.main()
