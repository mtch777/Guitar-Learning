"""The indexed search must give the literal scan's exact result and error."""
from copy import deepcopy
from fractions import Fraction as F
import random
import unittest

import backing_execution_constraints as guard


def literal_occupancy(nodes,refs):
    """Independent unchanged predicate from before the indexing optimization."""
    for ref in refs:
        a=nodes[ref]
        if a['grace']or a['duration']<=0 or not a['string_valid']:
            raise ValueError('UNVERIFIED_OWNED_WRITTEN_CONTACT')
        for other,b in nodes.items():
            if ref==other or a['part']!=b['part']:continue
            if b['grace']:
                if a['onset']<=b['onset']<a['onset']+a['duration']:
                    raise ValueError('UNVERIFIED_GRACE_CONTACT_ORDER: no performed duration inferred')
                continue
            if b['duration']<=0:continue
            if max(a['onset'],b['onset'])>=min(a['onset']+a['duration'],b['onset']+b['duration']):continue
            if not b['string_valid']:raise ValueError('UNVERIFIED_OVERLAPPING_STRING')
            if a['string']==b['string']:
                raise ValueError(f'WRITTEN_STRING_COLLISION: {ref} overlaps {other}')


def node(onset,duration=1,**changes):
    result=dict(part=0,voice=0,string=0,string_valid=True,onset=F(onset),
                duration=F(duration),grace=False,pitch=60)
    result.update(changes)
    return result


def outcome(function,nodes,refs):
    try:
        function(nodes,refs)
        return None
    except Exception as error:
        return type(error),str(error)


class OccupancyIndexTests(unittest.TestCase):
    def compare(self,nodes,refs):
        before=deepcopy(nodes)
        expected=outcome(literal_occupancy,nodes,refs)
        self.assertEqual(outcome(guard._occupancy,nodes,refs),expected)
        self.assertEqual(nodes,before)
        return expected

    def test_half_open_intervals_and_grace_points_at_both_boundaries(self):
        own=node(2,2)
        for onset in (F(1),F(2),F(3),F(4),F(5)):
            for duration in (-1,0,1):
                nodes={'own':own,'grace':node(onset,duration,grace=True)}
                result=self.compare(nodes,['own'])
                self.assertEqual(result is not None,2<=onset<4)
        for onset,duration,overlap in ((0,2,False),(4,2,False),(0,3,True),(3,2,True)):
            result=self.compare({'own':own,'other':node(onset,duration)},['own'])
            self.assertEqual(result is not None,overlap)

    def test_long_hold_is_found_after_many_nonoverlapping_short_notes(self):
        nodes={'hold':node(-100,200)}
        nodes.update({f'short-{i}':node(i,F(1,4),string=1)for i in range(40)})
        nodes['own']=node(50,1)
        result=self.compare(nodes,['own'])
        self.assertEqual(result[1],'WRITTEN_STRING_COLLISION: own overlaps hold')

    def test_dead_unknown_string_and_other_voices_keep_original_refusals(self):
        own=node(0)
        for other in (node(0,pitch=None),node(0,voice=4),node(0,string=None,string_valid=False)):
            self.assertIsNotNone(self.compare({'own':own,'other':other},['own']))
        self.assertIsNone(self.compare({'own':own,'other':node(0,part=1,string_valid=False)},['own']))

    def test_zero_negative_and_invalid_owned_contacts(self):
        for duration in (-1,0):
            nodes={'own':node(0),'other':node(0,duration,string_valid=False)}
            self.assertIsNone(self.compare(nodes,['own']))
            self.assertEqual(self.compare(nodes,['other'])[1],'UNVERIFIED_OWNED_WRITTEN_CONTACT')
        for own in (node(0,grace=True),node(0,string_valid=False)):
            self.assertEqual(self.compare({'own':own},['own'])[1],'UNVERIFIED_OWNED_WRITTEN_CONTACT')
        self.compare({},[])
        self.assertEqual(self.compare({},['absent']),(KeyError,"'absent'"))

    def test_first_refusal_uses_source_insertion_order_not_time_or_voice(self):
        own=node(2,4)
        for others in (
            [('later',node(4)),('earlier',node(1,2))],
            [('collision',node(2,voice=3)),('grace',node(2,grace=True))],
            [('unknown',node(2,string_valid=False)),('collision',node(2))],
        ):
            for order in (others,list(reversed(others))):
                nodes=dict(order);nodes['own']=own
                self.assertIsNotNone(self.compare(nodes,['own']))
        nodes={'own':own,'collision':node(4),'invalid':node(10,0)}
        self.assertIn('COLLISION',self.compare(nodes,['own','invalid'])[1])
        self.assertIn('OWNED',self.compare(nodes,['invalid','own'])[1])

    def test_index_is_rebuilt_from_current_contacts_after_an_edit(self):
        nodes={'own':node(0),'other':node(2)}
        self.assertIsNone(self.compare(nodes,['own']))
        nodes['other']['onset']=F(1,2)
        self.assertIsNotNone(self.compare(nodes,['own']))
        nodes['other']['string']=1
        self.assertIsNone(self.compare(nodes,['own']))

    def test_deterministic_random_authored_contacts_match_literal_scan(self):
        rng=random.Random(882710)
        outcomes=set()
        for case in range(800):
            rows=[]
            for i in range(rng.randint(2,50)):
                rows.append((str(i),node(F(rng.randrange(-16,64),4),
                    F(rng.choice((-4,0,1,2,4,16,128)),4),
                    part=rng.randrange(3),voice=rng.randrange(3),
                    string=rng.randrange(6),string_valid=rng.random()>.06,
                    grace=rng.random()<.05,pitch=None if rng.random()<.1 else 60)))
            rng.shuffle(rows);nodes=dict(rows)
            refs=rng.sample(list(nodes),rng.randint(1,min(5,len(nodes))))
            with self.subTest(case=case):outcomes.add(self.compare(nodes,refs))
        self.assertIn(None,outcomes)
        self.assertTrue(any(result and 'OWNED' in result[1]for result in outcomes))
        self.assertTrue(any(result and 'COLLISION' in result[1]for result in outcomes))
        self.assertTrue(any(result and 'GRACE' in result[1]for result in outcomes))
        self.assertTrue(any(result and 'OVERLAPPING_STRING' in result[1]for result in outcomes))


if __name__=='__main__':unittest.main()
