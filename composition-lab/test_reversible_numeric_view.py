"""Channel view parity and intentionally incomplete parent distinction."""
from copy import deepcopy
import unittest
from reversible_relationships import factor_numeric,realize_numeric,ConstraintError
from reversible_numeric_view import project


def model():
    channels=dict(time=dict(translated=True,scale="unit"),duration=dict(translated=False,scale="unit"),written=dict(translated=False,scale="identity"))
    return factor_numeric([dict(id="voice",unit="1/2",rows=[dict(id="a",values=dict(time="3",duration="1/2",written="1"),symbols=dict(rest=False)),dict(id="b",values=dict(time="7/2",duration="0",written="1/4"),symbols=dict(grace="before"))])],channels)


class NumericViewTests(unittest.TestCase):
    def test_projection_uses_same_values_units_members_and_symbols(self):
        parent=model();before=deepcopy(parent);rows=realize_numeric(parent)
        view=project(parent,["written","duration"])
        self.assertEqual(view,project(parent,["duration","written"]))
        self.assertEqual(realize_numeric(view),[dict(r,values={k:r["values"][k] for k in ["duration","written"]}) for r in rows])
        self.assertEqual(view["occurrences"][0]["unit"],"1/2");self.assertEqual(parent,before)

    def test_missing_unselected_anchor_does_not_require_guessed_time(self):
        parent=model();del parent["occurrences"][0]["anchors"]["time"]
        self.assertEqual([r["values"]["duration"] for r in realize_numeric(project(parent,["duration"]))],["1/2","0"])
        with self.assertRaises(ConstraintError):realize_numeric(parent)
        with self.assertRaises(ConstraintError):project(parent,["time"])

    def test_empty_unknown_duplicate_selections_refused(self):
        for fields in [[],["absent"],["duration","duration"],"duration"]:
            with self.assertRaises(ConstraintError):project(model(),fields)

    def test_recanonicalization_merges_only_matching_selected_patterns(self):
        channels=dict(time=dict(translated=True,scale="unit"),duration=dict(translated=False,scale="unit"))
        regions=[]
        for region,gap,duration in [("first","1","1"),("second","2","1"),("third","1","2")]:
            regions.append(dict(id=region,unit="1/2",rows=[dict(id=region+"-a",values=dict(time="0",duration=duration),symbols=dict(rest=False)),dict(id=region+"-b",values=dict(time=gap,duration=duration),symbols=dict(rest=False))]))
        parent=factor_numeric(regions,channels);self.assertEqual(len(parent["definitions"]),3)
        view=project(parent,["duration"])
        self.assertEqual(view["sharing"],dict(definitions=2,occurrences=3,shared_definitions=1,unique_definitions=1))
        self.assertEqual([o["region_id"] for o in view["occurrences"]],["first","second","third"])
        self.assertEqual([o["members"] for o in view["occurrences"]],[o["members"] for o in parent["occurrences"]])
        self.assertTrue(all(o["unit"]=="1/2" for o in view["occurrences"]))
        self.assertEqual([r["values"]["duration"] for r in realize_numeric(view)],["1","1","1","1","2","2"])

    def test_projection_success_does_not_validate_malformed_unselected_parent(self):
        parent=model();definition=next(iter(parent["definitions"].values()));definition["parameters"]["time"]=[]
        self.assertEqual(len(realize_numeric(project(parent,["duration"]))),2)
        # Even restoring the real anchor cannot cure a malformed other channel.
        with self.assertRaises(ConstraintError):realize_numeric(parent)


if __name__=="__main__":unittest.main()
