"""Calculation provenance stays separate from counted written units."""
from copy import deepcopy
import unittest
from artist_relationship_profiles import build_relationship_profile, Counts
from test_artist_relationship_profiles import row, song


class CalculationInputTests(unittest.TestCase):
    def profile(self, source, pedals=None):
        report={"songs":[source]}; original=deepcopy(report); entries=[]
        plain=build_relationship_profile(report,pedals or {},"A")
        traced=build_relationship_profile(report,pedals or {},"A",support_sink=entries.append)
        self.assertEqual(plain,traced); self.assertEqual(original,report)
        self.assertTrue(all(e["calculation_inputs"][0]["role"]=="eligibility_metadata" for e in entries))
        return entries

    def test_mechanical_unit_is_not_its_context(self):
        a=row(0,0,effects=["bend"]); chord=row(1,0,47); nxt=row(2,1,52)
        s=song(1,[a,chord,nxt,row(3,2,pitch=None)])
        s["tracks"][0]["technique_values"]=[dict(occurrence=a["occurrence"],bend=dict(valid=True,peak_semitones="2"))]
        entry=next(e for e in self.profile(s) if e["kind"]=="mechanical_shape_given_context")
        self.assertEqual(entry["support"]["members"],[a["occurrence"]])
        byrole={d["role"]:d for d in entry["calculation_inputs"]}
        self.assertEqual(byrole["origin_group"]["members"],[a["occurrence"],chord["occurrence"]])
        self.assertEqual(byrole["next_group"]["members"],[nxt["occurrence"]])
        self.assertEqual(byrole["curve_parameters"]["detail_index"],0)
        self.assertIn("track_register",byrole)

    def test_adjacent_bar_members_exclude_tied_destinations(self):
        rows=[row(0,0),row(1,1,tie_destination=True),row(0,4,bar=2),row(1,5,bar=2,tie_destination=True)]
        entry=next(e for e in self.profile(song(1,rows)) if e["kind"]=="adjacent_bar_variation")
        self.assertEqual(entry["support"]["members"],[rows[0]["occurrence"],rows[2]["occurrence"]])
        self.assertEqual(entry["support"]["bars"],[1,2])

    def test_absent_other_attack_is_not_a_synthetic_rest(self):
        s=song(1,[row(0,0),row(1,1)])
        other=deepcopy(s["tracks"][0]);other["part_id"]=1
        other["rows"]=[dict(row(0,0,52),occurrence="1:1:0:0:0")];s["tracks"].append(other)
        entry=next(e for e in self.profile(s) if e["kind"]=="track_attack_alignment" and e["outcome"]=="left_only")
        check=next(a for a in entry["absence_checks"] if a["predicate"]=="no_eligible_attack_at")
        self.assertEqual((check["part_id"],check["onset_q"]),(1,"1"))
        self.assertEqual(entry["support"]["members"],[s["tracks"][0]["rows"][1]["occurrence"]])

    def test_cycles_have_actual_comparison_locations(self):
        rows=[row(0,0),row(1,1,45),row(2,2),row(3,3,47)]
        cycles=[dict(call_start_q=str(i),response_start_q=str(i+1),return_q=str(i+2),call_members=[rows[i]["occurrence"]],response_members=[rows[i+1]["occurrence"]]) for i in (0,2)]
        pedal={"tracks":[dict(song_id=1,part_id=0,phrases=[dict(members=[r["occurrence"] for r in rows],roles={r["occurrence"]:"call" if i%2==0 else "response" for i,r in enumerate(rows)},cycles=cycles)])]}
        e=next(e for e in self.profile(song(1,rows),pedal) if e["kind"]=="same_pedal_call_answer_variation")
        loc={d["role"]:d for d in e["calculation_inputs"]}
        self.assertEqual(loc["accepted_cycle"]["cycle_index"],1)
        self.assertEqual(loc["previous_comparable_cycle"]["cycle_index"],0)

    def test_sink_descriptors_are_snapshots(self):
        entries=[]; counts=Counts(entries.append); d={"role":"test","members":["a"]}
        counts.add(dict(song_id=1,family="a"),"kind",{},True,calculation_inputs=[d])
        d["members"].append("later")
        self.assertEqual(entries[0]["calculation_inputs"][1]["members"],["a"])

if __name__=="__main__":unittest.main()
