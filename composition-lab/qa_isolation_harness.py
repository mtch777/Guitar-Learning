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


def validate_request(purpose, controls):
    """One unchanged control contract, used before launch and again in worker."""
    if purpose=='exact_zero':
        if not isinstance(controls, dict) or not controls or any(type(v) not in (int, float) or v != 0 for v in controls.values()):
            raise ValueError("Explicit numeric zero controls required")
    elif purpose=='voicing_register_intervention':
        if type(controls)is not dict or set(controls) not in ({'voicing','register','target_ref','seed'},{'voicing','register','target_ref','seed','context_policy'},{'voicing','register','physical','target_ref','seed','context_policy'}):raise ValueError('Declared intervention controls required')
        if any(type(controls[k])is not int or not 0<=controls[k]<=100 for k in ('voicing','register')) or type(controls['seed'])is not int or type(controls['target_ref'])is not str or not controls['target_ref'].startswith('event:'):raise ValueError('Only bounded controls and source identity may enter intervention')
        if controls.get('context_policy','exact_context') not in ('exact_context','pooled_source','pooled_declared_geometry','source_witnessed_fixed_strings','incident_dependencies','joint_source_fingering','transposed_voicing_family','source_lane_context','source_joint_lane_context','source_gesture_context','declared_degree_allocation','declared_degree_nominal_slots','source_inner_degree_component','provisional_contact_inner_preview','all_hypothesis_inner_preview'):raise ValueError('Unknown intervention context policy')
        if 'physical' in controls and (controls.get('context_policy') not in ('joint_source_fingering','transposed_voicing_family','source_lane_context','source_joint_lane_context','source_gesture_context') or type(controls['physical'])is not int or not 0<=controls['physical']<=100):raise ValueError('Unknown physical release')
    elif purpose=='local_step_tempo_intervention':
        if type(controls)is not dict or set(controls)!={'tempo','target_ref','component_ref','seed','context_policy'}or controls['context_policy']!='source_rhythmic_component_tempo':raise ValueError('Declared component-conditioned tempo controls required')
        if type(controls['tempo'])not in(int,float)or not 0<=controls['tempo']<=100 or type(controls['seed'])is not int or any(type(controls[k])is not str for k in('target_ref','component_ref')):raise ValueError('Invalid step-tempo release')
    elif purpose=='local_palm_mute_intervention':
        if type(controls)is not dict or set(controls)!={'palm_mute','target_ref','seed','context_policy'}or controls['context_policy']!='source_local_palm_mute':raise ValueError('Declared palm-mute controls required')
        if type(controls['palm_mute'])not in(int,float)or not 0<=controls['palm_mute']<=100 or type(controls['seed'])is not int or type(controls['target_ref'])is not str:raise ValueError('Invalid palm-mute release')
    elif purpose=='local_group_rhythm_intervention':
        if type(controls)is not dict or set(controls)!={'rhythm','target_ref','seed','context_policy'} or controls['context_policy']!='source_complete_group_rhythm':raise ValueError('Declared local rhythm controls required')
        if type(controls['rhythm'])not in(int,float)or not 0<=controls['rhythm']<=100 or type(controls['seed'])is not int or type(controls['target_ref'])is not str:raise ValueError('Invalid local rhythm release')
    elif purpose=='melody_and_note_register':
        import re
        policy=controls.get('context_policy') if type(controls)is dict else None
        if policy not in ('source_keyboard_note_register','backing_motion_with_note_register'):raise ValueError('Explicit register scope required')
        required={'context_policy','register','target_ref','seed'}|({'melody_controls'}if policy=='backing_motion_with_note_register'else set())
        if set(controls)!=required:raise ValueError('Exact register control fields required')
        if type(controls['register'])not in(int,float)or not math.isfinite(controls['register'])or not 0<=controls['register']<=100 or type(controls['seed'])is not int:raise ValueError('Bounded register release required')
        if type(controls['target_ref'])is not str or not re.fullmatch(r'event:\d+:\d+:\d+:\d+:\d+:\d+',controls['target_ref']):raise ValueError('Explicit register occurrence required')
        # The frozen operator also validates all nested melody controls;
        # no result pitch, octave choice, source path or cache is supplied.
        if policy=='backing_motion_with_note_register'and(type(controls['melody_controls'])is not dict or controls['melody_controls'].get('context_policy')!='observed_backing_motion'):raise ValueError('Declared nested melody operation required')
    elif purpose=='note_rest_timing':
        if type(controls)is not dict or set(controls)!={'context_policy','rhythm','target_ref','seed'} or controls['context_policy']!='source_note_rest_timing':
            raise ValueError('Explicit note/rest timing controls required')
        if type(controls['rhythm'])is not int or not 0<=controls['rhythm']<=100 or type(controls['seed'])is not int or type(controls['target_ref'])is not str or not controls['target_ref'].startswith('source-note-rest:'):
            raise ValueError('Bounded note/rest release and target identity required')
    elif purpose=='melodic_movement':
        legacy={'context_policy','melody','intent','seed'}
        combined=legacy|{'register','register_direction'}
        if type(controls)is not dict or set(controls) not in (legacy,combined):
            raise ValueError('Exact melodic movement controls required')
        if controls['context_policy']!='source_melodic_movement' or controls['intent']not in('repeat_start','follow_reference_motion'):
            raise ValueError('Explicit melodic movement intention required')
        if type(controls['melody'])is not int or not 0<=controls['melody']<=100 or type(controls['seed'])is not int:
            raise ValueError('Bounded integer melody release and seed required')
        if set(controls)==combined and (type(controls['register'])is not int or not 0<=controls['register']<=100 or controls['register_direction'] not in ('up','down')):
            raise ValueError('Bounded integer register release and explicit direction required')
    elif purpose=='musical_cell_phase':
        if type(controls)is not dict or set(controls)!={'context_policy','variation','instance','phase','seed'} or controls['context_policy']!='source_musical_cell_phase':
            raise ValueError('Exact musical-cell controls required')
        if any(type(controls[k])is not int for k in ('variation','instance','phase','seed')) or not 0<=controls['variation']<=100 or controls['instance']<1 or not 0<=controls['phase']<3:
            raise ValueError('Bounded release, later instance, cell phase and typed seed required')
    elif purpose=='bend_gesture':
        # Worker validates this packet before loading the frozen operator.
        if type(controls)is not dict or set(controls)!={'context_policy','bend','intent','seed'}:
            raise ValueError('Explicit bend excursion controls required')
        if controls['context_policy']!='source_bend_excursion' or controls['intent']not in('keep_start','keep_arrival'):
            raise ValueError('Explicit start/arrival intention required')
        if type(controls['bend'])is not int or not 0<=controls['bend']<=100 or type(controls['seed'])is not int:
            raise ValueError('Bounded integer release and seed required')
    elif purpose=='upper_voicing_motion':
        if type(controls)is not dict or set(controls)!={'context_policy','voicing','intent','seed'}:
            raise ValueError('Explicit upper-motion controls required')
        if controls['context_policy']!='source_upper_voicing_motion' or controls['intent']not in('repeat_upper_interval','follow_reference_upper_motion'):
            raise ValueError('Explicit upper-motion intention required')
        if type(controls['voicing'])is not int or not 0<=controls['voicing']<=100 or type(controls['seed'])is not int:
            raise ValueError('Integer percentage and seed required')
    elif purpose=='coattack_treatment':
        if type(controls)is not dict or set(controls)!={'context_policy','melody','intent','allow_note_octave_changes','seed'}:
            raise ValueError('Explicit coattack intention and release required')
        if controls['context_policy']!='source_coattack_treatment' or controls['intent']not in('repeat_reference_pitch','follow_reference_interval_class'):
            raise ValueError('Unknown coattack musical intention')
        if type(controls['melody'])not in(int,float)or not math.isfinite(controls['melody'])or not 0<=controls['melody']<=100 or type(controls['seed'])is not int or type(controls['allow_note_octave_changes'])is not bool:
            raise ValueError('Invalid coattack release or permission')
    elif purpose=='guitar_figure_register':
        if type(controls)is not dict or controls.get('context_policy')not in('observed_guitar_figure_register','source_guitar_figure_register','source_expressive_figure_register','source_muted_figure_register'):raise ValueError('Explicit figure-register operation required')
        compound=controls['context_policy']=='observed_guitar_figure_register'
        expected={'context_policy','register','seed'}|({'melody_controls'}if compound else{'physical'})
        if 'placement_policy' in controls:
            if controls['context_policy']!='source_guitar_figure_register' or type(controls['placement_policy'])is not str or controls['placement_policy']not in('current_strings','minimum_string_changes'):
                raise ValueError('Explicit plain-figure placement scope required')
            expected.add('placement_policy')
        if set(controls)!=expected:raise ValueError('Explicit figure-register controls required')
        if type(controls['register'])not in(int,float)or not math.isfinite(controls['register'])or not 0<=controls['register']<=100 or type(controls['seed'])is not int:raise ValueError('Invalid figure-register release')
        if compound and(type(controls['melody_controls'])is not dict or controls['melody_controls'].get('context_policy')!='observed_backing_motion'):raise ValueError('Declared nested melody operation required')
        if not compound and(type(controls['physical'])is not int or controls['physical']not in(0,100)):raise ValueError('Explicit physical permission required')
        # Nested controls are fully validated by the frozen operator;
        # pitches, chosen octaves and source payloads are not accepted.
    elif purpose=='observed_backing_motion':
        import re
        required={'context_policy','melody','physical','source_refs','target_refs','backing_part','seed'}
        if type(controls)is not dict:raise ValueError('Declared backing-motion scope required')
        mode=controls.get('backing_mode','matched_sonorities')
        if type(mode)is not str or mode not in('matched_sonorities','explicit_occurrence_stream'):raise ValueError('Declared correspondence mode required')
        if mode=='explicit_occurrence_stream':required|={'backing_voice','source_backing_refs','target_backing_refs'}
        if set(controls)-{'allow_note_octave_changes','backing_mode'}!=required or controls['context_policy']!='observed_backing_motion':raise ValueError('Declared backing-motion scope required')
        if type(controls.get('allow_note_octave_changes',False))is not bool:raise ValueError('Explicit Boolean note-octave permission required')
        if type(controls['melody'])not in(int,float)or not math.isfinite(controls['melody'])or not 0<=controls['melody']<=100 or type(controls['physical'])is not int or controls['physical']not in(0,100)or type(controls['seed'])is not int or type(controls['backing_part'])is not int or controls['backing_part']<0:raise ValueError('Invalid bounded backing-motion release')
        for key in('source_refs','target_refs'):
            refs=controls[key]
            if type(refs)is not list or len(refs)<2 or any(type(r)is not str or not re.fullmatch(r'event:\d+:\d+:\d+:\d+:\d+:\d+',r)for r in refs)or len(set(refs))!=len(refs):raise ValueError('Original occurrence identities required')
        if len(controls['source_refs'])!=len(controls['target_refs'])or set(controls['source_refs'])&set(controls['target_refs']):raise ValueError('Disjoint equal-length local passages required')
        if mode=='explicit_occurrence_stream':
            if type(controls['backing_voice'])is not int or controls['backing_voice']<0:raise ValueError('Explicit backing voice required')
            for key in('source_backing_refs','target_backing_refs'):
                refs=controls[key]
                if type(refs)is not list or len(refs)!=len(controls['source_refs'])or any(type(r)is not str or not re.fullmatch(r'event:\d+:\d+:\d+:\d+:\d+:\d+',r)for r in refs):raise ValueError('One explicit backing occurrence per attack required')
    elif purpose=='local_melodic_figure_intervention':
        if type(controls)is not dict or set(controls)!={'melody','target_ref','seed','context_policy'}or controls['context_policy']!='source_local_melodic_figure':raise ValueError('Declared whole-figure melody controls required')
        if type(controls['melody'])not in(int,float)or not math.isfinite(controls['melody'])or not 0<=controls['melody']<=100 or type(controls['seed'])is not int or type(controls['target_ref'])is not str:raise ValueError('Invalid whole-figure melody release')
    elif purpose=='local_melodic_contour_intervention':
        if type(controls)is not dict or set(controls)!={'melody','target_ref','seed','context_policy'} or controls['context_policy']!='source_local_melodic_contour':raise ValueError('Declared melodic contour controls required')
        if type(controls['melody'])not in(int,float)or not 0<=controls['melody']<=100 or type(controls['seed'])is not int or type(controls['target_ref'])is not str:raise ValueError('Invalid melodic contour release')
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


def worker(stage, challenge=None, forbidden=None):
    stage = stage.resolve()
    audit_path, output_path = stage / "audit.json", stage / "output.json"
    read_paths = {stage / "worker.py", stage / "relationships.py", stage / "input.json"}
    write_paths = {audit_path, output_path}
    runtime = Path(sys.base_prefix).resolve()
    events = []
    phase = "audit_challenge" if challenge else "input_contract"
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
            validate_request(purpose, controls)
            # Only this staged module is executable task code. No repo import path.
            # Compile the frozen source directly: importlib otherwise probes an
            # unstaged __pycache__ before reading source, creating a false denial.
            code_path = stage / "relationships.py"
            namespace = {"__name__": "relationships", "__file__": str(code_path)}
            phase = "module_import"
            exec(compile(code_path.read_text(encoding="utf-8"), str(code_path), "exec"), namespace)
            phase = "reconstruction"
            result = namespace["reconstruct"](data["upper"], controls)
            output_path.write_text(json.dumps(result, allow_nan=False), encoding="utf-8")
    except Exception as exc:
        error = dict(type=type(exc).__name__, message=str(exc))
    audit = dict(policy="Python audit allowlist, NOT OS sandbox", events=events,
                 attempted_challenge=attempted, error=error, phase=phase,
                 challenge_denied=bool(challenge and error and error["type"] == "PermissionError" and any(e["denied"] for e in events)))
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return 0 if error is None or audit["challenge_denied"] else 1


def execute(operator_code, upper, controls, expected, output, timeout=10, challenge=None, forbidden=None,purpose='exact_zero', expected_runtime=None, expected_operator_sha256=None):
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
        runtime = dict(implementation=sys.implementation.name, version=list(sys.version_info[:3]),
                       executable=str(Path(sys.executable).resolve()))
        if expected_runtime is not None and runtime != expected_runtime:
            raise ValueError("FROZEN_RUNTIME_MISMATCH")
        if type(operator_code) is not str:
            raise ValueError("EXPLICIT_OPERATOR_SOURCE_REQUIRED")
        operator_hash = hashlib.sha256(operator_code.encode('utf-8')).hexdigest()
        if expected_operator_sha256 is not None and operator_hash != expected_operator_sha256:
            raise ValueError("FROZEN_OPERATOR_UTF8_MISMATCH")
        compile(operator_code, '<frozen-operator>', 'exec')
        if not challenge:
            validate_request(purpose, controls)
        preflight = dict(runtime=runtime, operator_utf8_sha256=operator_hash,
                         expected_runtime_checked=expected_runtime is not None,
                         expected_operator_checked=expected_operator_sha256 is not None)
        shutil.copyfile(__file__, stage / "worker.py")
        (stage / "relationships.py").write_bytes(operator_code.encode("utf-8"))
        (stage / "input.json").write_text(json.dumps(dict(upper=upper, controls=controls,purpose=purpose), allow_nan=False), encoding="utf-8")
    except Exception as exc:
        report = dict(status="FAIL", issues=["Preparation " + type(exc).__name__ + ": " + str(exc)],
                      scope="QA fixture preparation only; no musical-tier acceptance",
                      failure_stage="preflight", reconstruction_started=False)
        (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    hashes = {p.name: sha(p) for p in stage.iterdir()}
    assert hashes["relationships.py"] == operator_hash
    (output / "freeze.json").write_text(json.dumps(hashes, indent=2))
    command = [sys.executable, "-I", "-S", str(stage / "worker.py"), str(stage)]
    if challenge:
        command.extend(["--challenge", challenge, "--forbidden", str(forbidden)])
    environment = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR") if k in os.environ}
    issues = []
    failure_stage = "worker_execution"
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
        audit = strict_json((stage / "audit.json").read_text(encoding="utf-8"))
        failure_stage = audit.get("phase", "worker_execution")
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
                differences = exact_diff(expected, actual)
                issues.extend(differences)
                if differences: failure_stage = "comparison"
        unexpected = {p.name for p in stage.iterdir()} - set(hashes) - {"audit.json", "output.json"}
        if unexpected:
            issues.append("Unexpected staged files")
        if any(not (stage / name).is_file() or sha(stage / name) != value for name, value in hashes.items()):
            issues.append("Frozen worker input/code changed")
    except Exception as exc:
        issues.append(type(exc).__name__ + ": " + str(exc))
    report = dict(status="FAIL" if issues else "PASS", issues=issues, command=command,purpose=purpose,
                  scope="QA worker execution only; not active musical-tier Gate2 acceptance",
                  preflight=preflight, failure_stage=failure_stage if issues else None,
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
