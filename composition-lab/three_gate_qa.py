"""Fail-closed QA evidence checks. No analysis or generation engine lives here.

Machine-checkable obligations are necessary, never sufficient for a musical
meaning verdict. Current research without an inverse cannot receive a tier PASS.
"""
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def exact_diff(expected, actual, path="$"):
    """JSON type exact; absent differs from null and false differs from zero."""
    if type(expected) is not type(actual):
        return [path + ": type/value differs"]
    if isinstance(expected, dict):
        result = []
        for key in sorted(set(expected) | set(actual)):
            at = path + "." + key
            if key not in expected or key not in actual:
                result.append(at + ": missing/extra")
            else:
                result.extend(exact_diff(expected[key], actual[key], at))
        return result
    if isinstance(expected, list):
        result = [] if len(expected) == len(actual) else [path + ": length differs"]
        for i, (left, right) in enumerate(zip(expected, actual)):
            result.extend(exact_diff(left, right, f"{path}[{i}]"))
        return result
    return [] if expected == actual else [path + ": value differs"]


def result(status, scope, issues=(), **details):
    return dict(status=status, scope=scope, issues=list(issues), **details)


def freeze_valid(selection):
    """Reproduce the existing sampler, including its letter draw and sorted pool."""
    issues = []
    required = {"seed", "query", "candidate_ids", "excluded_ids", "selected_song_id", "revision_id"}
    if not required <= selection.keys():
        return ["Incomplete frozen selection"]
    pool = selection["candidate_ids"]
    if not pool or pool != sorted(set(pool)):
        return ["Candidate pool is empty or not canonical"]
    if set(pool) & set(selection["excluded_ids"]):
        issues.append("Previously excluded song in candidate pool")
    rng = random.Random(selection["seed"])
    if rng.choice("abcdefghijklmnopqrstuvwxyz") != selection["query"]:
        issues.append("Seed/query mismatch")
    if rng.choice(pool) != selection["selected_song_id"]:
        issues.append("Seed/pool selection mismatch")
    return issues


def portability(capture, selection_path):
    """Run existing source extraction; independent checker imports no extractor.

    This verifies declared base pitch, NOT sounding harmonic/bend pitch; full
    source preservation and extraction coverage are separate explicit scopes.
    """
    from run_reversible_tier_qa import extract
    from check_reversible_source import check
    selection = load(selection_path)
    issues = freeze_valid(selection)
    metadata = load(capture / "metadata.json")
    if (metadata["songId"], metadata["revisionId"]) != (
            selection["selected_song_id"], selection["revision_id"]):
        issues.append("Captured source differs from frozen selection")
    paths = [capture / "metadata.json", *sorted(capture.glob("track-*.json"))]
    before = {p.name: digest(p) for p in paths}
    facts = extract(capture)
    fields = ("id", "pitch", "onset_q", "duration_q")
    check_result = check(capture, [{k: e[k] for k in fields} for e in facts["events"]])
    if check_result["status"] != "pass_declared_raw_source_fields":
        issues.append("Independent source arithmetic differs")
    if before != {p.name: digest(p) for p in paths}:
        issues.append("Source changed while checking")
    markings = {}
    for p in paths[1:]:
        for m in load(p).get("measures", []):
            for voice in m.get("voices", []):
                for beat in voice.get("beats", []):
                    for note in beat.get("notes", []):
                        for key in note:
                            if key not in {"fret", "string", "rest"}:
                                markings[key] = markings.get(key, 0) + 1
    return result("FAIL" if issues else "PASS", "T0→existing extraction: occurrence identity/base pitch/rational onset/duration only",
                  issues, independent_check=check_result, source_coverage=facts["source_coverage"],
                  source_hashes=before, selection_sha256=digest(selection_path),
                  source_note_field_counts=markings,
                  limits=["Frozen capture; novelty depends on exclusion audit, not seed replay alone",
                          "Selection chronology is historical evidence, not proven by replaying its seed",
                          "No annotation-backed harmony accuracy or full T1 fidelity claim",
                          "Natural-harmonic sounding pitch and technique execution are outside base-pitch scope"])


def reversal(record):
    """Check evidence obligations; never accept a declared pass by itself.

    Evidence producer must execute the inverse and independent comparator. This
    validator does not manufacture that missing operation for a retired design.
    """
    if record is None:
        return result("NOT RUN", "Active musical tiers", ["No active same-relationships inverse exists"])
    issues = []
    if record.get("architecture") != "active":
        issues.append("Historical codec cannot certify active musical tiers")
    for field in ("tier_boundary", "compared_fields", "shared_relationship_sha256",
                  "stripped_input_sha256", "worker_command", "independent_comparison"):
        if not record.get(field):
            issues.append("Missing " + field)
    controls = record.get("controls")
    if not isinstance(controls, dict) or not controls or any(type(v) not in (int, float) or v != 0 for v in controls.values()):
        issues.append("All declared controls must be explicitly numeric zero")
    if record.get("configuration_contains_source_answers") is not False:
        issues.append("Configuration ownership not cleared")
    for field in ("lower_payload_removed", "source_denied", "cache_denied", "network_denied",
                  "denial_tests_passed", "read_audit_passed", "shared_relations_verified"):
        if record.get(field) is not True:
            issues.append("Missing verified isolation/relation obligation: " + field)
    comparison = record.get("independent_comparison", {})
    if comparison.get("exact_differences") != [] or comparison.get("compared_count", 0) <= 0:
        issues.append("Independent exact comparison missing or differs")
    # A complete signed evidence bundle is still required; flags alone are not proof.
    for field in ("input_evidence_path", "output_evidence_path", "audit_evidence_path"):
        item = record.get(field, {})
        path = Path(item.get("path", ""))
        if not path.is_file() or item.get("sha256") != digest(path):
            issues.append("Missing/stale file evidence: " + field)
    return result("FAIL" if issues else "INCONCLUSIVE", record.get("tier_boundary", "unspecified"), issues,
                  limits=["Evidence validation alone cannot certify worker honesty; executable adapter review required"])


def musical_abstraction(contracts, inverse_status):
    """Verify necessary contracts, references/time, ownership and review binding.

    Deliberately cannot infer emotional meaning, correct harmony or music quality.
    """
    if not contracts:
        return result("FAIL", "Active T2+ musical analysis", ["No implemented active analysis-tier contract/trace/inverse"])
    issues = []
    for contract in contracts:
        tier = contract.get("tier")
        if type(tier) is not int or tier < 2:
            issues.append("Analysis tier must be an integer >=2")
            continue
        prefix = f"T{tier}: "
        allowed = {"tier", "input_tier", "musical_question", "new_relationship", "ownership",
                   "removed_or_transformed_fields", "realization_parameter_meanings", "inverse_obligations",
                   "source_to_tier_to_source_trace", "predecessor_schema", "predecessor_sha256",
                   "predecessor_path", "relationship_intervention_evidence", "duplicates_lower_payload",
                   "operation_kind", "preceding_evidence", "examples", "planner_review",
                   "claims_emotion_or_artist_fidelity", "listening_dependent_claims_verified"}
        if set(contract) - allowed:
            issues.append(prefix + "undeclared payload fields: " + ",".join(sorted(set(contract) - allowed)))
        if contract.get("input_tier") != tier - 1:
            issues.append(prefix + "input must be immediately preceding tier")
        for key in ("musical_question", "new_relationship", "ownership", "removed_or_transformed_fields",
                    "realization_parameter_meanings", "inverse_obligations", "source_to_tier_to_source_trace",
                    "predecessor_schema", "predecessor_sha256", "relationship_intervention_evidence"):
            if not contract.get(key):
                issues.append(prefix + "missing " + key)
        if contract.get("duplicates_lower_payload") is not False:
            issues.append(prefix + "lower payload duplication not ruled out")
        if contract.get("operation_kind") in {"rename", "nest", "compress", "coordinate_change"}:
            issues.append(prefix + "structural operation alone adds no musical relationship")
        evidence = contract.get("preceding_evidence", {})
        predecessor = None
        predecessor_path = Path(contract.get("predecessor_path", ""))
        if not predecessor_path.is_file() or contract.get("predecessor_sha256") != digest(predecessor_path):
            issues.append(prefix + "missing/stale actual predecessor file")
        else:
            predecessor = load(predecessor_path)
            if predecessor.get("tier") != tier - 1 or predecessor.get("schema") != contract.get("predecessor_schema"):
                issues.append(prefix + "actual predecessor tier/schema mismatch")
        events = {e["id"]: e for e in (predecessor or {}).get("events", [])}
        if predecessor and len(events) != len(predecessor.get("events", [])):
            issues.append(prefix + "duplicate predecessor occurrences")
        examples = contract.get("examples", [])
        categories = {e.get("kind") for e in examples}
        if not {"support", "contrast", "ambiguous"} <= categories:
            issues.append(prefix + "support/contrast/ambiguity examples required")
        fingerprints = set()
        for example in examples:
            if example.get("interpretation_status") not in {"observed", "inferred", "ambiguous", "unknown"}:
                issues.append(prefix + "missing interpretation uncertainty")
            refs = example.get("evidence_refs", [])
            fingerprint = (tuple(refs), example.get("claim"))
            if not example.get("claim") or fingerprint in fingerprints:
                issues.append(prefix + "examples lack distinct explicit claims")
            fingerprints.add(fingerprint)
            if not refs:
                issues.append(prefix + "example has no preceding evidence")
            for ref in refs:
                if ref not in evidence:
                    issues.append(prefix + "dangling evidence reference")
                    continue
                item = evidence[ref]
                try:
                    start, end = Fraction(item["start_q"]), Fraction(item["end_q"])
                    if start < 0 or end < start:
                        raise ValueError("invalid interval")
                    if not item.get("occurrence_refs"):
                        raise ValueError("no occurrences")
                    members = [events[r] for r in item["occurrence_refs"]]
                    actual_start = min(Fraction(e["onset_q"]) for e in members)
                    actual_end = max(Fraction(e["onset_q"]) + Fraction(e["duration_q"]) for e in members)
                    if start != actual_start or end != actual_end:
                        raise ValueError("evidence envelope disagrees with predecessor occurrences")
                except (KeyError, ValueError, ZeroDivisionError, TypeError):
                    issues.append(prefix + "invalid timed evidence")
        review = contract.get("planner_review", {})
        unsigned = {k: v for k, v in contract.items() if k != "planner_review"}
        current_hash = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if review.get("contract_sha256") != current_hash or review.get("verdict") != "approved":
            issues.append(prefix + "missing/stale Planner review")
        if contract.get("listening_dependent_claims_verified") is not True and contract.get("claims_emotion_or_artist_fidelity"):
            issues.append(prefix + "unsupported emotion/artist claim")
    if inverse_status != "PASS":
        issues.append("Exact active-tier reversal has not passed")
    return result("FAIL" if issues else "INCONCLUSIVE", "Declared T2+ contracts", issues,
                  limits=["Contract checks are necessary, not an automated musical-quality verdict",
                          "References/timing require independent source adjudication; Planner text is not machine proof"])


def check_intervention(before, after, expected_changed_paths, refused=False, protected=None):
    """Necessary anti-decoration check; expected paths come from reviewed contract.

    Refusal must be verified by the executable adapter, not asserted here. This
    helper only checks an executed edit's recorded output for the no-op loophole.
    """
    if refused:
        return result("INCONCLUSIVE", "Relationship intervention", ["Conflict refusal requires adapter evidence"])
    differences = exact_diff(before, after)
    issues = []
    if not expected_changed_paths:
        issues.append("No declared relationship consequence")
    for path in expected_changed_paths:
        if not any(d.startswith(path + ":") or d.startswith(path + ".") or d.startswith(path + "[") for d in differences):
            issues.append("Relationship edit ignored at " + path)
    for path in protected or []:
        if any(d.startswith(path + ":") or d.startswith(path + ".") or d.startswith(path + "[") for d in differences):
            issues.append("Protected dimension changed at " + path)
    return result("FAIL" if issues else "PASS", "Executed-output anti-decoration check only", issues)


def run(capture, selection_path, output, evidence=None):
    if output.exists():
        raise ValueError("Fresh output directory required; preserve failure history")
    output.mkdir(parents=True)
    evidence = {} if evidence is None else evidence
    resources = evidence.get("resources") if isinstance(evidence, dict) else None
    lab = Path(__file__).resolve().parent
    execution_files = [Path(__file__), lab / "run_reversible_tier_qa.py",
                       lab / "check_reversible_source.py",
                       lab / "songsterr_automation/songsterr_api/source_semantics.py",
                       lab / "songsterr_automation/songsterr_api/analyze_relationships.py"]
    inputs = [selection_path, capture / "metadata.json", *sorted(capture.glob("track-*.json"))]
    if resources is not None:
        execution_files.append(lab / "source_resource_qa.py")
        if isinstance(resources, dict):
            inputs.extend(Path(resources[k]) for k in ("baseline_path", "supplemental_metadata", "supplemental_text")
                          if isinstance(resources.get(k), str))
    frozen_paths = [p for p in execution_files + inputs if p.is_file()]
    frozen = {str(p.resolve()): digest(p) for p in frozen_paths}
    (output / "before-analysis-freeze.json").write_text(json.dumps(dict(
        utc=datetime.now(timezone.utc).isoformat(), files=frozen,
        note="Selected direct extractor/checker dependencies; not a transitive environment lock"), indent=2), encoding="utf-8")
    try:
        gate1 = portability(capture, selection_path)
        if resources is not None:
            if not isinstance(resources, dict) or "baseline_path" not in resources:
                resource_result = result("FAIL", "Requested resource provenance", ["Invalid resource evidence request"])
            elif set(resources) - {"baseline_path", "supplemental_metadata", "supplemental_text", "claims"}:
                resource_result = result("FAIL", "Requested resource provenance", ["Undeclared resource evidence fields"])
            else:
                from source_resource_qa import audit as audit_resources
                resource_result = audit_resources(capture, resources["baseline_path"],
                                                 resources.get("supplemental_metadata"), resources.get("supplemental_text"),
                                                 resources.get("claims"))
            gate1["resource_provenance"] = resource_result
            if resource_result["status"] != "PASS_PROVENANCE_ONLY":
                gate1["status"] = "FAIL"
                gate1["issues"].append("Requested source-resource provenance check failed")
    except Exception as error:
        gate1 = result("FAIL", "Source extraction", [type(error).__name__ + ": " + str(error)])
    changed = [p for p in frozen_paths if not p.is_file() or digest(p) != frozen[str(p.resolve())]]
    if changed:
        gate1["status"] = "FAIL"
        gate1["issues"].append("Frozen input/code changed during extraction")
    try:
        gate2 = reversal(evidence.get("reversal"))
    except Exception as error:
        gate2 = result("FAIL", "Reversal evidence validation", [type(error).__name__ + ": " + str(error)])
    try:
        gate3 = musical_abstraction(evidence.get("musical_contracts", []), gate2["status"])
    except Exception as error:
        gate3 = result("FAIL", "Musical evidence validation", [type(error).__name__ + ": " + str(error)])
    report = dict(schema="three-gate-qa/1", utc=datetime.now(timezone.utc).isoformat(),
                  gates={"1_portability": gate1, "2_exact_reversal": gate2, "3_musical_abstraction": gate3},
                  completion_allowed=all(g["status"] == "PASS" for g in (gate1, gate2, gate3)),
                  runner_sha256=digest(__file__),
                  before_analysis_freeze_sha256=digest(output / "before-analysis-freeze.json"),
                  input_evidence=evidence,
                  pending_implementation=["Registered executable active inverse adapter and pairwise/composed worker isolation tests",
                                          "Executed upper-artifact ownership/consumed-field audit and preceding-only forward-input check",
                                          "Executed relationship intervention/conflict checks bound to actual shared relation adapter",
                                          "General nested predecessor adapters beyond flat tier/schema/events evidence",
                                          "Independent musical interpretation adjudication beyond structural evidence checks"])
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    if "local-artifacts" not in args.output.resolve().parts:
        parser.error("Private output required")
    report = run(args.capture, args.selection, args.output, load(args.evidence) if args.evidence else None)
    print(json.dumps({k: dict(status=v["status"], scope=v["scope"], issues=v["issues"]) for k, v in report["gates"].items()}, indent=2))
    return 0 if report["completion_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
