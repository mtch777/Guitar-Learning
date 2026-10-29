"""Executed Python-audited callable QA; no musical engine or tier is implemented.

Expected answers remain in the parent. Python audit is NOT an OS sandbox and
cannot certify hostile native code. Only reviewed pure-Python operators qualify.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("Non-finite JSON constant: " + value)

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number")
        return number

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def worker(stage, challenge=None, forbidden=None):
    stage = stage.resolve()
    audit_path, output_path = stage / "audit.json", stage / "output.json"
    read_paths = {stage / "worker.py", stage / "relationships.py", stage / "input.json"}
    write_paths = {audit_path, output_path}
    runtime = Path(sys.base_prefix).resolve()
    events = []
    sys.dont_write_bytecode = True

    def guard(event, args):
        deny = False
        item = None
        if event == "open":
            raw, mode, flags = args
            path = None if isinstance(raw, int) else Path(raw).resolve()
            write = (isinstance(mode, str) and any(x in mode for x in "wax+")) or bool(
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            allowed = path in write_paths if write else path in read_paths or (path is not None and path.is_relative_to(runtime))
            deny = not allowed
            item = dict(event=event, path=str(path), operation="write" if write else "read", denied=deny)
        elif event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"} or event.startswith(("socket.", "ctypes.")):
            deny = True
            item = dict(event=event, denied=True)
        elif event in {"os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.link", "os.symlink",
                       "os.chmod", "os.chown", "os.truncate", "os.utime", "os.chdir"} or event.startswith("shutil."):
            deny = True
            item = dict(event=event, denied=True)
        elif event in {"os.listdir", "os.scandir"}:
            raw = args[0] if args else None
            path = stage if raw is None else None if isinstance(raw, int) else Path(raw).resolve()
            deny = path is None or not (path == stage or path.is_relative_to(runtime))
            item = dict(event=event, path=str(path), operation="list", denied=deny)
        if item:
            item["event_id"] = len(events)
            events.append(item)
        if deny:
            raise PermissionError("QA audited operation denied")

    sys.addaudithook(guard)
    result = None
    error = None
    attempted = None
    try:
        if challenge:
            attempted = challenge
            if challenge == "open":
                Path(forbidden).read_text()
            elif challenge == "os_open":
                descriptor = os.open(forbidden, os.O_RDONLY)
                os.close(descriptor)
            elif challenge == "write":
                Path(forbidden).write_text("forbidden")
            elif challenge == "network":
                import socket
                socket.socket()
            elif challenge == "process":
                subprocess.Popen([sys.executable, "-c", "pass"])
            elif challenge == "system":
                os.system("echo forbidden")
            elif challenge == "repo_import":
                spec = importlib.util.spec_from_file_location("forbidden_module", forbidden)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            elif challenge == "remove":
                os.remove(forbidden)
            elif challenge == "rename":
                os.rename(forbidden, str(forbidden) + ".moved")
            elif challenge == "listdir":
                os.listdir(Path(forbidden).parent)
            elif challenge == "chdir":
                os.chdir(Path(forbidden).parent)
            else:
                raise ValueError("Unknown challenge")
            result = dict(challenge_denied=False)
        else:
            data = strict_json((stage / "input.json").read_text(encoding="utf-8"))
            controls = data["controls"]
            purpose=data.get('purpose','exact_zero')
            if purpose=='exact_zero':
                if not isinstance(controls, dict) or not controls or any(type(v) not in (int, float) or v != 0 for v in controls.values()):
                    raise ValueError("Explicit numeric zero controls required")
            elif purpose=='voicing_register_intervention':
                if type(controls)is not dict or set(controls) not in ({'voicing','register','target_ref','seed'},{'voicing','register','target_ref','seed','context_policy'},{'voicing','register','physical','target_ref','seed','context_policy'}):raise ValueError('Declared intervention controls required')
                if any(type(controls[k])is not int or not 0<=controls[k]<=100 for k in ('voicing','register')) or type(controls['seed'])is not int or type(controls['target_ref'])is not str or not controls['target_ref'].startswith('event:'):raise ValueError('Only bounded controls and source identity may enter intervention')
                if controls.get('context_policy','exact_context') not in ('exact_context','pooled_source','pooled_declared_geometry','source_witnessed_fixed_strings','incident_dependencies','joint_source_fingering','transposed_voicing_family','source_lane_context','source_joint_lane_context','source_gesture_context','declared_degree_allocation','declared_degree_nominal_slots','source_inner_degree_component','provisional_contact_inner_preview','all_hypothesis_inner_preview'):raise ValueError('Unknown intervention context policy')
                if 'physical' in controls and (controls.get('context_policy') not in ('joint_source_fingering','transposed_voicing_family','source_lane_context','source_joint_lane_context','source_gesture_context') or type(controls['physical'])is not int or not 0<=controls['physical']<=100):raise ValueError('Unknown physical release')
            elif purpose=='local_accents_intervention':
                import re
                if type(controls)is not dict or set(controls)!={'accents','target_ref','seed','context_policy'} or controls['context_policy']!='source_local_note_accent':raise ValueError('Declared local accent controls required')
                level=controls['accents']
                if type(level)not in (int,float)or not math.isfinite(level)or not 0<=level<=100 or type(controls['seed'])is not int:raise ValueError('Bounded accent release and typed seed required')
                if type(controls['target_ref'])is not str or not re.fullmatch(r'event:\d+:\d+:\d+:\d+:\d+:\d+',controls['target_ref']):raise ValueError('Source note identity required')
            elif purpose=='local_dynamics_intervention':
                import re
                if type(controls)is not dict or set(controls)!={'dynamics','target_ref','seed','context_policy'} or controls['context_policy']not in ('source_local_dynamic_level','source_local_dynamic_transition'):raise ValueError('Declared local dynamics controls required')
                level=controls['dynamics']
                if type(level)not in (int,float)or not math.isfinite(level)or not 0<=level<=100 or type(controls['seed'])is not int:raise ValueError('Bounded dynamic release and typed seed required')
                if type(controls['target_ref'])is not str or not re.fullmatch(r'track-\d+\.json#/measures/\d+/voices/\d+/beats/\d+(?:/notes/\d+)?/velocity',controls['target_ref']):raise ValueError('Source dynamic declaration identity required')
            else:raise ValueError('Unknown audited execution purpose')
            # Only this staged module is executable task code. No repo import path.
            # Compile the frozen source directly: importlib otherwise probes an
            # unstaged __pycache__ before reading source, creating a false denial.
            code_path = stage / "relationships.py"
            namespace = {"__name__": "relationships", "__file__": str(code_path)}
            exec(compile(code_path.read_text(encoding="utf-8"), str(code_path), "exec"), namespace)
            result = namespace["reconstruct"](data["upper"], controls)
            output_path.write_text(json.dumps(result, allow_nan=False), encoding="utf-8")
    except Exception as exc:
        error = dict(type=type(exc).__name__, message=str(exc))
    audit = dict(policy="Python audit allowlist, NOT OS sandbox", events=events,
                 attempted_challenge=attempted, error=error,
                 challenge_denied=bool(challenge and error and error["type"] == "PermissionError" and any(e["denied"] for e in events)))
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return 0 if error is None or audit["challenge_denied"] else 1


def execute(operator_code, upper, controls, expected, output, timeout=10, challenge=None, forbidden=None,purpose='exact_zero'):
    """Run reviewed code, never stage expected lower representation.

    A helper PASS certifies only audited execution/exact comparison on this input.
    Parameter ownership, musical meaning, full tier scope remain independent.
    """
    from three_gate_qa import exact_diff
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Fresh output required")
    output.mkdir(parents=True)
    stage = output / "worker"; stage.mkdir()
    try:
        shutil.copyfile(__file__, stage / "worker.py")
        (stage / "relationships.py").write_text(operator_code, encoding="utf-8")
        (stage / "input.json").write_text(json.dumps(dict(upper=upper, controls=controls,purpose=purpose), allow_nan=False), encoding="utf-8")
    except Exception as exc:
        report = dict(status="FAIL", issues=["Preparation " + type(exc).__name__ + ": " + str(exc)],
                      scope="QA fixture preparation only; no musical-tier acceptance")
        (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    hashes = {p.name: sha(p) for p in stage.iterdir()}
    (output / "freeze.json").write_text(json.dumps(hashes, indent=2))
    command = [sys.executable, "-I", "-S", str(stage / "worker.py"), str(stage)]
    if challenge:
        command.extend(["--challenge", challenge, "--forbidden", str(forbidden)])
    environment = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR") if k in os.environ}
    issues = []
    try:
        # Stream logs to parent-owned files rather than accumulating unbounded
        # stdout in parent memory. Wall time bounded; disk quota is NOT enforced.
        with (output / "stdout.txt").open("wb") as out_log, (output / "stderr.txt").open("wb") as err_log:
            process = subprocess.run(command, cwd=stage, env=environment, stdin=subprocess.DEVNULL,
                                     stdout=out_log, stderr=err_log, timeout=timeout)
        if process.returncode:
            issues.append("Worker failed")
        if (output / "stdout.txt").stat().st_size or (output / "stderr.txt").stat().st_size:
            issues.append("Undeclared stdout/stderr output")
        audit = strict_json((stage / "audit.json").read_text())
        if challenge:
            if audit["attempted_challenge"] != challenge or not audit["challenge_denied"]:
                issues.append("Denial challenge not executed/denied")
        else:
            if audit["error"]:
                issues.append("Worker reported error")
            if any(event["denied"] for event in audit["events"]):
                issues.append("Operator attempted undeclared source/fallback access")
            if not (stage / "output.json").is_file():
                issues.append("No actual reconstructed output")
            else:
                actual = strict_json((stage / "output.json").read_text())
                issues.extend(exact_diff(expected, actual))
        unexpected = {p.name for p in stage.iterdir()} - set(hashes) - {"audit.json", "output.json"}
        if unexpected:
            issues.append("Unexpected staged files")
        if any(not (stage / name).is_file() or sha(stage / name) != value for name, value in hashes.items()):
            issues.append("Frozen worker input/code changed")
    except Exception as exc:
        issues.append(type(exc).__name__ + ": " + str(exc))
    report = dict(status="FAIL" if issues else "PASS", issues=issues, command=command,purpose=purpose,
                  scope="QA worker execution only; not active musical-tier Gate2 acceptance",
                  policy="Python audit, NOT OS sandbox", frozen_files=hashes,
                  parent_expected_staged=False, transitive_runtime_lock=False,
                  native_memory_limit_enforced=False,
                  disk_quota_enforced=False,
                  reviewed_python_code_only=True)
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", type=Path)
    parser.add_argument("--challenge")
    parser.add_argument("--forbidden")
    args = parser.parse_args()
    raise SystemExit(worker(args.stage, args.challenge, args.forbidden))
