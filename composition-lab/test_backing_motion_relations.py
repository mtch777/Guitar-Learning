"""Authored mathematical fixtures; not evidence of musical style or fit."""
from copy import deepcopy
import unittest

from backing_motion_relations import (maximum_translations, solve_pitch,
                                     physical_contacts, minimum_string_changes)


def occurrences(prefix, pitches):
    return [dict(ref=f'{prefix}:{i}', pitch=p) for i,p in enumerate(pitches)]


class BackingMotionRelationTests(unittest.TestCase):
    def test_nonconstant_correspondence_uses_same_equation_both_ways(self):
        source = occurrences('source', [47,54,59,63])
        targets = [[54,59],[52,57],[54,59]]
        shifts = [maximum_translations(source, occurrences('target', p))['selected_delta'] for p in targets]
        self.assertEqual(shifts, [0,-2,0])
        original = [35,33,35]
        output = [solve_pitch(source_pitch=p, delta=d)['target_pitch'] for p,d in zip(original,shifts)]
        self.assertEqual(output,[35,31,35])
        recovered = [solve_pitch(delta=d, target_pitch=p)['source_pitch'] for p,d in zip(output,shifts)]
        self.assertEqual(recovered,original)
        self.assertEqual([solve_pitch(source_pitch=a,target_pitch=b)['delta']for a,b in zip(original,output)],shifts)

    def test_different_cardinality_retains_all_matches_and_unmatched_tones(self):
        a=occurrences('a',[47,54,59,63]);b=occurrences('b',[52,57])
        r=maximum_translations(a,b)
        self.assertEqual(r['selected_delta'],-2)
        winner=r['maxima'][0]
        self.assertEqual(winner['matched'],[
            dict(source_pitch=54,target_pitch=52,source_refs=['a:1'],target_refs=['b:0']),
            dict(source_pitch=59,target_pitch=57,source_refs=['a:2'],target_refs=['b:1'])])
        self.assertEqual([x['pitch']for x in winner['unmatched_source']],[47,63])
        self.assertEqual(winner['unmatched_target'],[])
        self.assertEqual([x['delta']for x in r['alternatives']],sorted({y['pitch']-x['pitch']for x in a for y in b}))

    def test_symmetric_reverse_matches_and_cardinality(self):
        a=occurrences('a',[47,54,59,63]);b=occurrences('b',[52,57])
        forward=maximum_translations(a,b);back=maximum_translations(b,a)
        self.assertEqual(back['selected_delta'],-forward['selected_delta'])
        self.assertEqual(back['max_cardinality'],forward['max_cardinality'])
        self.assertEqual(back['maxima'][0]['unmatched_target'],forward['maxima'][0]['unmatched_source'])
        self.assertEqual(back['maxima'][0]['unmatched_source'],forward['maxima'][0]['unmatched_target'])

    def test_ambiguous_alignment_retains_every_maximum(self):
        r=maximum_translations(occurrences('a',[60,64]),occurrences('b',[60,64,68]))
        self.assertEqual(r['status'],'AMBIGUOUS_MAXIMUM_TRANSLATION')
        self.assertIsNone(r['selected_delta'])
        self.assertEqual([x['delta']for x in r['maxima']],[0,4])
        self.assertTrue(all(x['distinct_pitch_matches']==2 for x in r['maxima']))

    def test_occurrence_duplicates_do_not_inflate_distinct_pitch_support(self):
        r=maximum_translations(occurrences('a',[60]*12),occurrences('b',[62]*10))
        self.assertEqual(r['max_cardinality'],1)
        self.assertIsNone(r['selected_delta'])
        self.assertEqual(len(r['maxima'][0]['matched'][0]['source_refs']),12)
        self.assertEqual(len(r['maxima'][0]['matched'][0]['target_refs']),10)
        r=maximum_translations(occurrences('a',[60,60,64]),occurrences('b',[62,62,66]))
        self.assertEqual(r['max_cardinality'],2)
        self.assertEqual(r['selected_delta'],2)

    def test_unknown_and_fractional_notes_never_silently_qualify(self):
        for value,reason in ((None,'UNKNOWN_WRITTEN_PITCH'),('121/2','NONINTEGER_WRITTEN_PITCH')):
            for side in ('source','target'):
                a=occurrences('a',[60,64]);b=occurrences('b',[62,66])
                (a if side=='source'else b).append(dict(ref='missing',pitch=value))
                r=maximum_translations(a,b)
                self.assertEqual(r['status'],'INCOMPLETE_WRITTEN_PITCH_CONTEXT')
                self.assertIsNone(r['selected_delta'])
                self.assertEqual(r['max_cardinality'],2)
                self.assertEqual(r['unavailable_'+side],[dict(ref='missing',reason=reason)])

    def test_strict_identity_and_number_shapes(self):
        good=occurrences('a',[60,64])
        for bad in (True,60.0,float('nan'),'60.0','1/0','nonsense'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                maximum_translations([dict(ref='x',pitch=bad)],good)
        for bad in ([dict(ref='x',pitch=60),dict(ref='x',pitch=64)],
                    [dict(ref='',pitch=60)],[dict(ref='x',pitch=60,focal_target_pitch=62)]):
            with self.assertRaises(ValueError):maximum_translations(bad,good)

    def test_context_time_refs_and_qualifications_are_preserved_without_mutation(self):
        a=occurrences('a',['60','64']);b=occurrences('b',['62','66'])
        sc=dict(time_q='13/4',context_refs=['a:0','a:1','tie-origin'],qualifications=['written_tie'])
        tc=dict(time_q='7/2',context_refs=['b:0','b:1'],qualifications=['slide_sounding_endpoint_unknown'])
        before=deepcopy((a,b,sc,tc));r=maximum_translations(a,b,source_context=sc,target_context=tc)
        self.assertEqual((a,b,sc,tc),before)
        self.assertEqual(r['source_context']['time_q'],'13/4')
        self.assertEqual(r['target_context']['qualifications'],tc['qualifications'])
        self.assertEqual(r['selected_delta'],2) # Written equation only, not execution approval.
        r['target_context']['qualifications'].clear()
        self.assertTrue(tc['qualifications'])
        with self.assertRaises(ValueError):maximum_translations(a,b,source_context=dict(sc,context_refs=['a:0']))

    def test_pitch_equation_refuses_conflict_underdetermination_and_nonintegers(self):
        self.assertEqual(solve_pitch(source_pitch='-1',delta='13'),
                         dict(source_pitch=-1,delta=13,target_pitch=12))
        self.assertEqual(solve_pitch(delta=13,target_pitch=12)['source_pitch'],-1)
        for args in (dict(source_pitch=60),dict(source_pitch=60,delta=2,target_pitch=63),
                     dict(source_pitch=True,delta=2),dict(source_pitch='121/2',delta=2)):
            with self.assertRaises(ValueError):solve_pitch(**args)

    def test_no_register_collapse(self):
        r=maximum_translations(occurrences('a',[48,55]),occurrences('b',[60,67]))
        self.assertEqual(r['selected_delta'],12)
        self.assertEqual(solve_pitch(source_pitch=35,delta=12)['target_pitch'],47)

    def test_nominal_contacts_all_strings_and_declared_limits(self):
        tuning=[43,38,33,28]
        self.assertEqual(physical_contacts(35,tuning,max_fret=24),[dict(string=2,fret=2),dict(string=3,fret=7)])
        self.assertEqual(physical_contacts(31,tuning,max_fret=24),[dict(string=3,fret=3)])
        self.assertEqual(physical_contacts(31,tuning,max_fret=2),[])
        self.assertEqual(physical_contacts(35,tuning,capo=2,max_fret=24),[dict(string=2,fret=0),dict(string=3,fret=5)])
        self.assertEqual(physical_contacts(100,[28]),[dict(string=0,fret=72)])
        self.assertEqual(physical_contacts(100,[28],max_fret=24),[])

    def test_existing_string_preserved_and_only_necessary_change_made(self):
        r=minimum_string_changes([35,31,35],[2,2,3],[43,38,33,28],max_fret=24)
        self.assertEqual(r['minimum_changes'],1)
        self.assertEqual(r['assignments'],[[dict(string=2,fret=2),dict(string=3,fret=3),dict(string=3,fret=7)]])
        for contact,pitch in zip(r['assignments'][0],[35,31,35]):
            self.assertEqual(solve_pitch(source_pitch=[43,38,33,28][contact['string']],delta=contact['fret'])['target_pitch'],pitch)

    def test_all_equal_cost_assignments_remain_no_arbitrary_first_choice(self):
        r=minimum_string_changes([64,64],[0,0],[70,60,55],max_fret=12)
        self.assertEqual(r['minimum_changes'],2)
        self.assertEqual(len(r['assignments']),4)
        self.assertEqual({tuple(c['string']for c in assignment)for assignment in r['assignments']},
                         {(1,1),(1,2),(2,1),(2,2)})
        self.assertEqual(minimum_string_changes([64],[1],[70,60,55])['minimum_changes'],0)

    def test_unavailable_contacts_do_not_partially_apply_or_invent_pitch(self):
        args=([35,20],[2,3],[43,38,33,28]);before=deepcopy(args)
        r=minimum_string_changes(*args,max_fret=24)
        self.assertEqual(args,before)
        self.assertEqual(r['status'],'NO_NOMINAL_CONTACT_ASSIGNMENT')
        self.assertEqual(r['assignments'],[]);self.assertIsNone(r['minimum_changes'])
        self.assertEqual(r['unresolved_note_indices'],[1])

    def test_physical_domain_strict(self):
        for args,kwargs in (((31,[28]),dict(capo=-1)),((31,[28]),dict(max_fret=True)),
                            ((31,[]),{}),((31,[True]),{}),(('63/2',[28]),{})):
            with self.assertRaises(ValueError):physical_contacts(*args,**kwargs)
        for original in ([True],[-1],[1],[]):
            with self.assertRaises(ValueError):minimum_string_changes([31],original,[28])


if __name__=='__main__':unittest.main()
