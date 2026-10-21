"""Complete written co-onsets and a genuinely joint tie/voicing constraint solve."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_reversible_ties import capture,measure,beat
from reversible_annotations import extract
from reversible_relationships import ConstraintError,realize_numeric,solve
import reversible_ties as ties
from reversible_voicings import encode,decode,equations,hypotheses


def chord(frets=(0,2),strings=(0,1)):
    return dict(duration=[1,4],notes=[dict(string=s,fret=f) for s,f in zip(strings,frets)])


class ReversibleVoicingTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def run_case(self,measures):
        capture(self.folder,measures);facts=extract(self.folder);prior=ties.encode(facts);upper=encode(prior)
        self.assertEqual(decode(upper),facts);return facts,upper

    def test_joint_tie_origin_hole_and_shared_transposed_voicing(self):
        tied=beat(fret=2,tie=True);tied["notes"][0]["string"]=1
        facts,model=self.run_case([measure([chord(),tied,chord((2,4)),dict(duration=[1,4],rest=True,notes=[dict(rest=True)])])])
        self.assertEqual(len(model["definitions"]),1);self.assertEqual(len(model["occurrences"]),2)
        self.assertEqual(next(iter(model["definitions"].values()))["intervals"],["0","7"])
        origin=model["lower"]["links"][0]["origin"]
        self.assertIn(origin,model["occurrences"][0]["members"][1:])
        ctx=ties.context(model["lower"]["lower"]["physical"])
        self.assertIsNone(ctx[origin]["position"])
        with self.assertRaises(ConstraintError):ties.decode(model["lower"])
        eq,params,holes=equations(model)
        self.assertEqual(ties.decode(model["lower"],eq,params,holes),facts)
        self.assertTrue(all(set(o)=={"definition","members"} for o in model["occurrences"]))

    def test_overflow_clock_collision_cannot_join_different_source_bars(self):
        first=measure([beat(),beat(),beat(),beat()]);first["signature"]=[3,4]
        answer=beat(fret=0);answer["notes"][0]["string"]=1
        second=measure([answer]);second["signature"]=[3,4]
        facts,model=self.run_case([first,second])
        self.assertEqual(model["occurrences"],[])
        from check_reversible_source import check_voicing_relations
        self.assertEqual(check_voicing_relations(self.folder,model)["differences"],[])

    def test_same_bar_different_voices_still_form_one_complete_group(self):
        low=beat(fret=5);high=beat(fret=7);high["notes"][0]["string"]=1
        bar=measure([low]);bar["voices"].append(dict(beats=[high]))
        _,model=self.run_case([bar])
        self.assertEqual(len(model["occurrences"]),1)
        self.assertEqual(len(model["occurrences"][0]["members"]),2)
        from check_reversible_source import check_voicing_relations
        self.assertEqual(check_voicing_relations(self.folder,model)["differences"],[])

    def test_joint_equations_are_order_independent(self):
        tied=beat(fret=2,tie=True);tied["notes"][0]["string"]=1
        facts,model=self.run_case([measure([chord(),tied,chord((2,4))])])
        ctx=ties.context(model["lower"]["lower"]["physical"]);extra,parameters,holes=equations(model)
        required=set(holes)|{r["destination"] for r in model["lower"]["links"]}
        known={f"{field}:{ident}":r[field] for ident,r in ctx.items() for field in ("onset","duration","position") if r[field] is not None};known.update(parameters)
        all_equations=ties.tie_equations(model["lower"]["links"],ctx)+extra
        a=solve(all_equations,known,[f"position:{i}" for i in required]);b=solve(list(reversed(all_equations)),known,[f"position:{i}" for i in required])
        self.assertEqual(a,b)
        original=ties.tie_equations
        with patch.object(ties,"tie_equations",side_effect=lambda links,c:list(reversed(original(links,c)))):self.assertEqual(decode(model),facts)

    def test_complete_group_rejects_unknown_member_instead_of_partial_dyad(self):
        group=chord();group["notes"].append(dict(string=99,fret=5))
        _,model=self.run_case([measure([group])])
        self.assertEqual(model["occurrences"],[])
        reasons={r["reason"] for r in model["excluded"]}
        self.assertEqual(reasons,{"unknown_written_position","incomplete_candidate"})
        self.assertEqual(len(model["excluded"]),3)

    def test_dead_grace_duplicate_string_and_ties_are_explicit_exclusions(self):
        group=chord();group["notes"][1]["dead"]=True
        _,model=self.run_case([measure([group])]);self.assertEqual(model["occurrences"],[])
        self.assertIn("dead_note",{r["reason"] for r in model["excluded"]})
        group=chord(strings=(0,0));_,model=self.run_case([measure([group])]);self.assertEqual({r["reason"] for r in model["excluded"]},{"ambiguous_string_at_onset"})
        group=chord();group["graceNote"]=True;_,model=self.run_case([measure([group])]);self.assertEqual({r["reason"] for r in model["excluded"]},{"zero_metric_duration"})
        group=chord();group["notes"][1]["tie"]=True
        _,model=self.run_case([measure([group])]);self.assertEqual(model["occurrences"],[])
        self.assertIn("explicit_tie_destination",{r["reason"] for r in model["excluded"]})

    def test_unisons_octaves_and_classification_do_not_replace_exact_intervals(self):
        # Different strings have identical nominal pitch at40, then octave52.
        group=chord((0,-5));group["notes"][1]["fret"]=0
        # Retune synthetic second string to40 so valid open positions form a unison.
        capture(self.folder,[measure([group])]);part=json.loads((self.folder/"track-0.json").read_text());part["tuning"]=[40,40]
        part["measures"][0]["voices"][0]["beats"].append(chord((0,12)))
        (self.folder/"track-0.json").write_text(json.dumps(part))
        facts=extract(self.folder);model=encode(ties.encode(facts));self.assertEqual(decode(model),facts)
        self.assertEqual({tuple(d["intervals"]) for d in model["definitions"].values()},{("0","0"),("0","12")})
        before=deepcopy(model);hypotheses(model);self.assertEqual(model,before)

    def test_corrupt_holes_anchors_members_and_hidden_caches_refused(self):
        _,base=self.run_case([measure([chord(),chord((2,4))])]);cases=[]
        m=deepcopy(base);m["occurrences"][0]["members"].reverse();cases.append(m)
        m=deepcopy(base);m["occurrences"][0]["members"][1]="missing";cases.append(m)
        m=deepcopy(base);m["definitions"]["unused"]={"intervals":["0","7"]};cases.append(m)
        m=deepcopy(base);next(iter(m["definitions"].values()))["raw_pitches"]=[40,47];cases.append(m)
        m=deepcopy(base);m["excluded"].append(dict(id="missing",reason="dead_note"));cases.append(m)
        for i,model in enumerate(cases):
            with self.subTest(case=i):
                with self.assertRaises(ConstraintError):decode(model)
        eq,known,holes=equations(base);ctx=ties.context(base["lower"]["lower"]["physical"])
        retained=base["occurrences"][0]["members"][0]
        with self.assertRaises(ConstraintError):ties.decode(base["lower"],eq,{**known,f"position:{retained}":"99"},holes)
        with self.assertRaises(ConstraintError):ties.decode(base["lower"],eq,{**known,"unused_cache":"47"},holes)
        with self.assertRaises(ConstraintError):ties.decode(base["lower"],eq+[{"unused_cache":F(0)}],{**known,"unused_cache":"47"},holes)

    def test_opaque_note_ids_do_not_change_group_selection(self):
        capture(self.folder,[measure([chord(),chord((2,4))])]);facts=extract(self.folder)
        ids={n["id"]:f"opaque-{i}" for i,n in enumerate(facts["physical"]["topology"]["notes"])}
        for n in facts["physical"]["topology"]["notes"]:n["id"]=ids[n["id"]]
        for p in facts["physical"]["positions"]:p["id"]=ids[p["id"]]
        model=encode(ties.encode(facts));self.assertEqual(len(model["occurrences"]),2);self.assertEqual(decode(model),facts)


if __name__=="__main__":unittest.main()
