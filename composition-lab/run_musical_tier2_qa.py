"""Actual bounded musical Tier2 QA; private artifacts, no legacy encode/decode."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
import sys
import importlib
from pathlib import Path
from musical_tier2 import analyze, strip_lower, transpose, reconstruct, note_context, tonal_note_context, declared_key_context
from source_key_tier1 import extract
from check_reversible_source import check
from check_musical_tier2_source import check as check_musical_source, check_overlaps, check_declared_keys
from qa_isolation_harness import execute
from three_gate_qa import exact_diff, portability

ROOT = Path(__file__).resolve().parent

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
def projected(events): return [{k:e[k] for k in ("id", "pitch", "onset_q", "duration_q")} for e in events]

def run(capture, output, selection=None):
    capture, output = capture.resolve(), output.resolve()
    if selection: selection = selection.resolve()
    if output.exists(): raise ValueError("Fresh output required; retain failures")
    output.mkdir(parents=True)
    sources = sorted(capture.glob("*.json"))
    # Import retained extraction dependencies BEFORE sealing code/before any data
    # analysis. Seal all loaded local Python modules, including transitive imports.
    api = ROOT/"songsterr_automation/songsterr_api"
    sys.path.insert(0,str(api))
    importlib.import_module("source_semantics"); importlib.import_module("analyze_relationships")
    modules = sorted({Path(m.__file__).resolve() for m in list(sys.modules.values())
                      if getattr(m,"__file__",None) and Path(m.__file__).suffix == ".py"
                      and ROOT in Path(m.__file__).resolve().parents
                      and "local-artifacts" not in Path(m.__file__).parts})
    freeze = dict(source={p.name:digest(p) for p in sources}, code={str(p.relative_to(ROOT)):digest(p) for p in modules}, selection_sha256=digest(selection) if selection else None)
    write(output/"freeze-before-analysis.json", freeze)
    result = dict(scope="T1 written pitch/time/IDs and measure keySignature present/null/absence -> SAME T2 voicing, overlap, tonal evidence and declared-signature relationships", missing=["sounding sustains/ties", "techniques/fingering/rest reconstruction", "base key", "chord-relative mode", "functional note roles", "harmonic spans", "full GP inverse", "style-aware nonzero percentage controls"])
    try:
        lower = extract(capture)
        direct = check(capture, projected(lower["events"]))
        gate1 = portability(capture, selection) if selection else dict(status="REGRESSION_NOT_FRESH")
        result["gate1"] = dict(selection=gate1, source=direct, coverage=lower["source_coverage"], source_key_check=check_declared_keys(capture,lower))
        upper = analyze(lower); blind = strip_lower(upper)
        write(output/"tier2-nested.json", upper); write(output/"tier2-stripped.json", blind)
        worker = execute((ROOT/"musical_tier2.py").read_text(), blind, {"variation":0}, lower, output/"inverse", timeout=120)
        result["gate2"] = dict(worker=worker, removed="ENTIRE input T1 including ALL event absolute pitches, onsets, durations, addresses and coverage; no source staged", retained="bass register per written-start group, member interval/duration/address, group time/part/bar, typed quality counts/warnings, occurrence order, derived context", claim="exact declared T1 only")
        if worker["status"] == "PASS":
            restored = json.loads((output/"inverse/worker/output.json").read_text())
            result["gate2"]["independent_source"] = check(capture, projected(restored["events"]))
            result["gate2"]["independent_source_keys"] = check_declared_keys(capture,restored)
        denials = {}
        for challenge in ("open", "os_open", "network", "process", "repo_import"):
            denials[challenge] = execute((ROOT/"musical_tier2.py").read_text(), blind, {"variation":0}, lower, output/("denial-"+challenge), timeout=30, challenge=challenge, forbidden=(ROOT/"musical_tier2.py" if challenge == "repo_import" else capture/"metadata.json"))["status"]
        result["gate2"]["actual_denial_challenges"] = denials
        changed = reconstruct(transpose(blind,"2"), {"variation":0})
        protected = [{k:v for k,v in e.items() if k!="pitch"} for e in lower["events"]]
        protected_changed = [{k:v for k,v in e.items() if k!="pitch"} for e in changed["events"]]
        intervention = all(b["pitch"] == (str(F(a["pitch"])+2) if a["pitch"] is not None else None) for a,b in zip(lower["events"],changed["events"])) and not exact_diff(protected,protected_changed)
        stale = strip_lower(upper)
        first = next((g for g in stale["coattacks"] if g["bass_register_anchor"] is not None), None)
        refusal = False
        if first:
            first["bass_register_anchor"] = str(F(first["bass_register_anchor"])+1)
            try: reconstruct(stale,{"variation":0})
            except ValueError: refusal = True
        counts = Counter(g["interpretation"]["harmonic_status"] for g in upper["coattacks"])
        trace = next((note_context(upper,m["id"]) for g in upper["coattacks"] if g["interpretation"]["chord_candidates"] for m in g["members"] if m["voicing_interval"] not in (None,"0")),None)
        tonal_trace = None
        if trace:
            tonal_candidate = upper["tonal_evidence"]["scopes"][0]["candidates"][0]
            tonal_trace = tonal_note_context(upper,trace["occurrence_ref"],tonal_candidate["id"])
        declaration_trace = None
        if upper["source_keys"]["occurrences"]:
            declaration = upper["source_keys"]["occurrences"][0]
            declaration_trace = declared_key_context(upper,declaration["part_id"],declaration["onset_q"])
        result["gate3"] = dict(source_declaration_trace=declaration_trace, tonal_candidate_trace=tonal_trace, tonal_evidence_scope="distributional candidates, not established key", status="PENDING_INDEPENDENT_MUSICAL_REVIEW", source_witnesses=check_musical_source(capture, upper), nominal_overlap_witnesses=check_overlaps(capture, upper), written_start_groups=len(upper["coattacks"]), contexts=dict(counts), actual_relation_intervention=intervention, stale_context_refused=refusal, note_trace=trace, interpretation_accuracy="UNTESTED without independently adjudicated source context; exact vocabulary compatibility is not chord truth", full_tier2="INCOMPLETE")
        result["source_unchanged"] = freeze["source"] == {p.name:digest(p) for p in sources}
        result["code_unchanged_during_run"] = freeze["code"] == {str(p.relative_to(ROOT)):digest(p) for p in modules}
    except Exception as exc:
        result["failure"] = dict(type=type(exc).__name__, message=str(exc))
    issues = []
    if "failure" in result: issues.append("Execution failure")
    else:
        g1, g2, g3 = result["gate1"], result["gate2"], result["gate3"]
        if selection and g1["selection"]["status"] != "PASS": issues.append("Fresh selection/source failed")
        if g1["source"]["status"] != "pass_declared_raw_source_fields" or g1["source_key_check"]["status"]!="PASS": issues.append("Source fields differ")
        if g2["worker"]["status"] != "PASS" or g2.get("independent_source",{}).get("status") != "pass_declared_raw_source_fields" or g2.get("independent_source_keys",{}).get("status")!="PASS": issues.append("Exact inverse failed")
        if set(g2["actual_denial_challenges"].values()) != {"PASS"}: issues.append("Denial challenge failed")
        if not g3["actual_relation_intervention"] or not g3["stale_context_refused"] or g3["source_witnesses"]["status"] != "PASS" or g3["nominal_overlap_witnesses"]["status"] != "PASS": issues.append("Musical relation checks failed")
        if not result["source_unchanged"] or not result["code_unchanged_during_run"]: issues.append("Frozen input/code changed")
    result["technical_status"] = "FAIL" if issues else "PASS_DECLARED_SCOPE_PENDING_MUSICAL_REVIEW"
    result["issues"] = issues
    write(output/"result.json",result)
    return result

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("capture",type=Path);p.add_argument("output",type=Path);p.add_argument("--selection",type=Path);a=p.parse_args()
    if "local-artifacts" not in a.output.resolve().parts: p.error("Private output required")
    result=run(a.capture,a.output,a.selection)
    print(json.dumps(result,indent=2))
    raise SystemExit(1 if result["technical_status"] == "FAIL" else 0)
