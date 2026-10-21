"""Independent tests for dimension-declared numeric factoring, not musical inference."""
from copy import deepcopy
from fractions import Fraction as F
import unittest
from reversible_relationships import factor_numeric,realize_numeric,numeric_equations,solve,ConstraintError


CHANNELS={"height":{"translated":True,"scale":"identity"},"clock":{"translated":True,"scale":"unit"},"length":{"translated":False,"scale":"unit"}}


def region(ident="a",anchor=60,start=F(1,7),unit=F(1,3)):
    return dict(id=ident,unit=str(unit),rows=[dict(id=f"{ident}:{i}",values=dict(height=str(anchor+d),clock=str(start+t*unit),length=str(length*unit)),symbols={"kind":"ordinary","slot":i}) for i,(d,t,length) in enumerate([(0,0,1),(4,2,3),(7,5,2)])])


def normalized(regions):
    return {r["id"]:dict(values={k:str(F(v)) if v is not None else None for k,v in r["values"].items()},symbols=r["symbols"]) for region in regions for r in region["rows"]}


class ReversibleNumericTests(unittest.TestCase):
    def assert_restored(self,regions,model):
        restored=realize_numeric(model)
        self.assertEqual({r["id"]:dict(values=r["values"],symbols=r["symbols"]) for r in restored},normalized(regions))

    def test_exact_irregular_rational_channels_masks_and_symbols(self):
        a=region();a["rows"][1]["values"]["height"]=None
        a["rows"][1]["values"]["clock"]=a["rows"][0]["values"]["clock"]
        a["rows"][2]["values"]["length"]="0"
        a["rows"][2]["symbols"]={"kind":"grace","explicit":False,"optional":None}
        before=deepcopy(a);model=factor_numeric([a],CHANNELS)
        self.assert_restored([a],model);self.assertEqual(a,before)
        self.assertEqual(model["channels"],CHANNELS)
        self.assertEqual(next(iter(model["definitions"].values()))["masks"]["height"],[True,False,True])

    def test_sharing_is_dimension_declared_and_not_pitch_named(self):
        a=region();b=region("b",65,F(9,5),F(2,3))
        model=factor_numeric([a,b],CHANNELS)
        self.assertEqual(len(model["definitions"]),1);self.assert_restored([a,b],model)
        # Deliberately name a time-scaled UNTRANSLATED channel pitch: semantics
        # must follow the declaration, never the name.
        channels={"pitch":{"translated":False,"scale":"unit"}}
        regions=[dict(id="x",unit="2",rows=[dict(id="x:0",values={"pitch":"6"},symbols={})]),dict(id="y",unit="5",rows=[dict(id="y:0",values={"pitch":"15"},symbols={})])]
        scaled=factor_numeric(regions,channels)
        self.assertEqual(len(scaled["definitions"]),1);self.assert_restored(regions,scaled)

    def test_changed_units_affect_only_declared_dimensions(self):
        model=factor_numeric([region()],CHANNELS);old={r["id"]:r for r in realize_numeric(model)}
        occurrence=model["occurrences"][0];occurrence["unit"]=str(F(occurrence["unit"])*2)
        occurrence["anchors"]["clock"]="13/7";occurrence["anchors"]["height"]="72"
        for r in realize_numeric(model):
            original=old[r["id"]]["values"]
            self.assertEqual(F(r["values"]["height"]),F(original["height"])+12)
            self.assertEqual(F(r["values"]["clock"]),F(13,7)+2*(F(original["clock"])-F(1,7)))
            self.assertEqual(F(r["values"]["length"]),2*F(original["length"]))

    def test_same_declared_equations_detect_conflicts_and_missing_inputs(self):
        masks={"clock":[True]};channels={"clock":{"translated":True,"scale":"unit"}}
        equations=numeric_equations(masks,channels,"2/3")
        solved=solve(equations,{"value:clock:0":"7/3","anchor:clock":"1","parameter:clock:0":"2"},["value:clock:0"])
        self.assertEqual(solved["value:clock:0"],F(7,3))
        with self.assertRaises(ConstraintError):solve(equations,{"value:clock:0":"8/3","anchor:clock":"1","parameter:clock:0":"2"},["value:clock:0"])
        with self.assertRaises(ConstraintError):solve(equations,{"parameter:clock:0":"2"},["value:clock:0"])

    def test_malformed_channel_specs_fail_explicitly(self):
        for bad in ({"translated":1,"scale":"unit"},{"translated":True,"scale":"guess"},{"translated":True},{"translated":True,"scale":"identity","extra":"raw"}):
            channels=deepcopy(CHANNELS);channels["height"]=bad
            with self.subTest(spec=bad):
                with self.assertRaises(ConstraintError):factor_numeric([region()],channels)
        channels=deepcopy(CHANNELS);del channels["height"]
        with self.assertRaises(ConstraintError):factor_numeric([region()],channels)

    def test_malformed_definitions_and_memberships_fail_explicitly(self):
        base=factor_numeric([region()],CHANNELS)
        cases=[]
        m=deepcopy(base);m["definitions"].clear();cases.append(m)
        m=deepcopy(base);next(iter(m["definitions"].values()))["masks"]["height"][0]=1;cases.append(m)
        m=deepcopy(base);next(iter(m["definitions"].values()))["parameters"]["clock"].pop();cases.append(m)
        m=deepcopy(base);next(iter(m["definitions"].values()))["masks"]["height"][0]=False;cases.append(m)
        m=deepcopy(base);m["occurrences"][0]["members"][1]=m["occurrences"][0]["members"][0];cases.append(m)
        m=deepcopy(base);m["occurrences"][0]["unit"]="0";cases.append(m)
        m=deepcopy(base);del m["occurrences"][0]["anchors"]["height"];cases.append(m)
        for i,model in enumerate(cases):
            with self.subTest(case=i):
                with self.assertRaises(ConstraintError):realize_numeric(model)
        duplicate=region();duplicate["rows"][1]["id"]=duplicate["rows"][0]["id"]
        with self.assertRaises(ConstraintError):factor_numeric([duplicate],CHANNELS)


if __name__=="__main__":unittest.main()
