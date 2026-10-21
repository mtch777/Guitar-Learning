"""Shared-equation reversibility and explicit failure gates, no source scores."""
from copy import deepcopy
from fractions import Fraction as F
import random
import unittest
from reversible_relationships import encode,decode,solve,ConstraintError


def facts(pitches=(60,64,67),start=F(0),unit=F(1,3),bar=1):
    return dict(events=[dict(id=f"event:fixture:0:{bar}:0:{i}:0",part_id=0,bar=bar,voice=0,beat=i,note=0,pitch=str(p) if p is not None else None,onset_q=str(start+i*unit),duration_q=str(unit)) for i,p in enumerate(pitches)])


class ReversibleRelationshipTests(unittest.TestCase):
    def test_same_solver_solves_both_directions_and_refuses_gaps(self):
        eq=[{"pitch":1,"anchor":-1,"interval":-1}]
        self.assertEqual(solve(eq,{"pitch":67,"anchor":60},["interval"])["interval"],7)
        self.assertEqual(solve(eq,{"interval":7,"anchor":60},["pitch"])["pitch"],67)
        with self.assertRaises(ConstraintError):solve(eq,{"interval":7},["pitch"])
        with self.assertRaises(ConstraintError):solve(eq,{"interval":7,"anchor":60,"pitch":68},["pitch"])

    def test_arbitrary_unseen_sequences_exact_rational_roundtrip(self):
        rng=random.Random(941)
        for _ in range(100):
            source=facts([rng.randrange(24,100) if rng.random()>.1 else None for _ in range(rng.randrange(1,20))],F(rng.randrange(100),7),F(rng.randrange(1,10),rng.randrange(1,30)))
            expected=sorted([{k:e[k] for k in ("id","pitch","onset_q","duration_q")} for e in source["events"]],key=lambda e:e["id"])
            self.assertEqual(decode(encode(source)),expected)

    def test_patterns_share_across_transposition_translation_and_scale(self):
        a=facts();b=facts((65,69,72),F(12),F(2,3),bar=2)
        result=encode(dict(events=a["events"]+b["events"]))
        self.assertEqual(len(result["definitions"]),1)
        self.assertEqual(result["abstraction"]["occurrences_using_shared_definitions"],2)
        self.assertNotIn("pitch",str(result["definitions"].values()).split("pitch_known")[0])

    def test_changed_anchors_use_same_equations(self):
        upper=encode(facts());old=decode(upper)
        occurrence=upper["occurrences"][0];occurrence["pitch_anchor"]=str(F(occurrence["pitch_anchor"])+5)
        occurrence["time_anchor_q"]="9";occurrence["time_unit_q"]=str(F(occurrence["time_unit_q"])*2)
        new=decode(upper)
        for a,b in zip(old,new):
            self.assertEqual(F(b["pitch"]),F(a["pitch"])+5)
            self.assertEqual(F(b["onset_q"]),9+2*F(a["onset_q"]))
            self.assertEqual(F(b["duration_q"]),2*F(a["duration_q"]))

    def test_graces_unknowns_polyphony_and_invalid_inputs(self):
        source=facts((None,60,67));source["events"][0]["duration_q"]="0"
        source["events"][1]["onset_q"]="0"
        self.assertEqual(len(decode(encode(source))),3)
        upper=encode(source);upper["occurrences"][0]["pitch_anchor"]=None
        with self.assertRaises(ConstraintError):decode(upper)
        upper=encode(source);upper["lower_tier"]=source
        with self.assertRaises(ConstraintError):decode(upper)
        source["events"][0]["duration_q"]="-1"
        with self.assertRaises(ConstraintError):encode(source)
        self.assertEqual(decode(encode(dict(events=[]))),[])


    def test_nonuniform_exact_rhythms_and_positive_simultaneity(self):
        source=facts((60,64,67,72))
        onsets=[F(2,7),F(2,7),F(11,21),F(31,14)]
        durations=[F(5,12),F(7,9),F(1,28),F(13,10)]
        for i,event in enumerate(source["events"]):
            event.update(onset_q=str(onsets[i]),duration_q=str(durations[i]))
        # Both simultaneous members have positive duration; this is not a grace test.
        source["events"][1].update(beat=0,note=1)
        source["events"][1]["id"]="event:fixture:0:1:0:0:1"
        expected=sorted([{k:e[k] for k in ("id","pitch","onset_q","duration_q")} for e in source["events"]],key=lambda e:e["id"])
        restored=decode(encode(source))
        self.assertEqual(restored,expected)
        self.assertEqual(sum(F(e["onset_q"])==F(2,7) and F(e["duration_q"])>0 for e in restored),2)

    def test_multiple_parts_voices_and_bars_keep_independent_regions(self):
        events=[]
        for part,bar,voice,anchor,start,unit in [(0,1,0,60,F(0),F(1,3)),(0,1,1,48,F(0),F(1,2)),(0,2,0,65,F(4),F(2,3)),(1,1,0,36,F(1,7),F(1,4))]:
            region=facts((anchor,anchor+4,anchor+7),start,unit,bar=bar)
            for event in region["events"]:
                event.update(part_id=part,voice=voice,id=f"event:fixture:{part}:{bar}:{voice}:{event['beat']}:0")
            events.extend(region["events"])
        upper=encode(dict(events=list(reversed(events))))
        self.assertEqual({tuple(o["region"]) for o in upper["occurrences"]},{(0,1,0),(0,1,1),(0,2,0),(1,1,0)})
        self.assertEqual(len(upper["definitions"]),1)
        self.assertEqual(decode(upper),sorted([{k:e[k] for k in ("id","pitch","onset_q","duration_q")} for e in events],key=lambda e:e["id"]))

    def test_all_grace_unknown_region_uses_declared_gauge_only(self):
        source=facts((None,None,None))
        for event in source["events"]:event.update(onset_q="5/7",duration_q="0")
        upper=encode(source);occurrence=upper["occurrences"][0]
        self.assertIsNone(occurrence["pitch_anchor"])
        self.assertEqual(occurrence["unit_basis"],"all_zero_duration_gauge_no_performed_timing_claim")
        self.assertEqual(occurrence["time_unit_q"],"1")
        self.assertEqual(decode(upper),sorted([{k:e[k] for k in ("id","pitch","onset_q","duration_q")} for e in source["events"]],key=lambda e:e["id"]))
        shifted=deepcopy(upper);shifted["occurrences"][0]["time_unit_q"]="11/13"
        self.assertEqual(decode(shifted),decode(upper))

    def test_duplicate_source_identity_is_rejected_before_encoding(self):
        source=facts();source["events"].append(deepcopy(source["events"][0]))
        with self.assertRaises(ConstraintError):encode(source)

    def test_missing_definition_and_nonboolean_mask_are_explicit_failures(self):
        upper=encode(facts());upper["definitions"].clear()
        with self.assertRaises(ConstraintError):decode(upper)
        for invalid in (1,"true",None):
            upper=encode(facts());definition=next(iter(upper["definitions"].values()))
            definition["pitch_known"][0]=invalid
            with self.subTest(mask=invalid):
                with self.assertRaises(ConstraintError):decode(upper)


if __name__=="__main__":unittest.main()
