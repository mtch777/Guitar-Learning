"""Whole-after gesture checks: no producer enumeration or partial-output proof."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,realize
from check_family_policy import normalized_units
from check_voicing_gesture import check
from check_voicing_context import check as single_check
from voicing_register import apply_family_choices


def documents():
    tuning=[64,59,55,50,45,40]
    def bar(e):return dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=[dict(string=s,fret=p-tuning[s])for p,s in zip([48,e,55],[5,4,3])])])])
    return {'metadata.json':dict(songId=91,revisionId=1,artist='Fixture',title='Atomic gesture',tracks=[dict(instrumentId=25)]),'track-0.json':dict(songId=91,revisionId=1,partId=0,instrumentId=25,tuning=tuning,frets=24,measures=[bar(52 if i in(3,4)else 64)for i in range(12)])}


def fixture():
    docs=documents();lower=extract_documents(docs);upper=strip_lower(analyze(lower,families=True));units=normalized_units(docs)[0]
    targets=[u for u in units if u['bar']in(4,5)];donors=[u for u in units if u['bar']in(9,10)]
    choices=[(t,dict(anchor=t['realization']['anchor'],intervals=d['realization']['intervals'],strings=d['fixed_output_strings']))for t,d in zip(targets,donors)]
    return lower,upper,targets,donors,choices


class GestureOracleTests(unittest.TestCase):
    def test_atomic_original_definition_pool_survives_swap(self):
        from test_musical_tier2 import facts
        import musical_tier2 as music
        import voicing_families as families
        lower=facts([(0,p,t,1)for t,ps in((0,[48,52,55]),(1,[48,64,55]))for p in ps])
        shared=families.lift(music.strip_lower(music.analyze(lower)))
        groups=shared['core']['coattacks'];a=[m['id']for m in groups[0]['members']];b=[m['id']for m in groups[1]['members']]
        choices=[(a,['0','16','7']),(b,['0','4','7'])]
        self.assertEqual(families.choose_many(shared,choices),families.choose_many(shared,list(reversed(choices))))
        with self.assertRaises(ValueError):families.choose(families.choose(shared,*choices[0]),*choices[1])

    def test_atomic_positive_single_edit_negative_and_order_independence(self):
        before,upper,targets,donors,choices=fixture();frozen=deepcopy(upper)
        forward=apply_family_choices(upper,choices);reverse=apply_family_choices(upper,list(reversed(choices)))
        self.assertEqual(forward,reverse);self.assertEqual(upper,frozen)
        after=realize(forward);tg=[u['member_refs']for u in targets];dg=[u['member_refs']for u in donors]
        result=check(before,after,tg,dg)
        self.assertEqual(result['status'],'PASS_INDEPENDENT_VOICING_GESTURE',result)
        self.assertEqual(result['group_count'],2)
        self.assertGreater(result['witness_count'],5)
        partial=realize(apply_family_choices(upper,choices[:1]))
        self.assertEqual(single_check(before,partial,tg[0],[donors[0]['id']],True)['status'],'FAIL_INDEPENDENT_VOICING_CONTEXT')

    def test_exact_zero_coincident_gesture_and_no_lower_answer(self):
        before,upper,targets,donors,choices=fixture()
        self.assertEqual(realize(upper),before)
        self.assertNotIn('input',upper)
        zero=[(t,dict(t['realization'],strings=t['fixed_output_strings']))for t in donors]
        exact=realize(apply_family_choices(upper,zero));self.assertEqual(exact,before)
        groups=[u['member_refs']for u in donors];other=[u['member_refs']for u in normalized_units(documents())[0]if u['bar']in(11,12)]
        self.assertEqual(check(before,exact,groups,other)['status'],'PASS_INDEPENDENT_VOICING_GESTURE')

    def test_skipped_reversed_partial_duplicate_and_overlapping_groups_rejected(self):
        before,upper,targets,donors,choices=fixture();after=realize(apply_family_choices(upper,choices));tg=[u['member_refs']for u in targets];dg=[u['member_refs']for u in donors]
        for a,b in ((tg[:1],dg[:1]),(list(reversed(tg)),dg),(tg,[dg[1],dg[0]]),(tg,[dg[0],dg[0]]),(tg,tg),(tg,[dg[0][:-1],dg[1]])):
            self.assertEqual(check(before,after,a,b)['status'],'FAIL_INDEPENDENT_VOICING_GESTURE')

    def test_unselected_source_metadata_or_member_change_rejected(self):
        before,upper,targets,donors,choices=fixture();after=realize(apply_family_choices(upper,choices));tg=[u['member_refs']for u in targets];dg=[u['member_refs']for u in donors]
        for kind in('metadata','outside','pc'):
            changed=deepcopy(after)
            if kind=='metadata':row=next(r for r in changed['facts']if r['id'].endswith('/artist'));row['value']='Changed'
            elif kind=='outside':row=next(r for r in changed['facts']if r['id'].endswith('/measures/0/voices/0/beats/0/notes/1/fret'));row['value']+=1
            else:row=next(r for r in changed['facts']if r['id'].endswith('/measures/3/voices/0/beats/0/notes/1/fret'));row['value']+=1
            self.assertEqual(check(before,changed,tg,dg)['status'],'FAIL_INDEPENDENT_VOICING_GESTURE',kind)


if __name__=='__main__':unittest.main()
