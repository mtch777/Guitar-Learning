"""Preflight and run AnalysisGNN on independently exported source MusicXML.
No automatic labels, no claims of accuracy without human ground truth.
"""
import argparse, csv, hashlib, json, shutil, subprocess, sys
from pathlib import Path

DEPENDENCIES = ("torch", "torch_geometric", "partitura", "graphmuse", "analysisgnn")
TASKS = "cadence,localkey,quality,root,bass,inversion,romanNumeral"


def probe_dependency(name):
    """A package directory existing does not prove its native libraries load."""
    result = subprocess.run([sys.executable, '-c',
        'import importlib; importlib.import_module('+repr(name)+')'],
        capture_output=True, text=True, timeout=90)
    return dict(importable=result.returncode == 0, error=result.stderr[-2000:] if result.returncode else None)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("musicxml", nargs="*", type=Path)
    p.add_argument("--out", type=Path, default=Path("analysisgnn-results"))
    p.add_argument("--checkpoint", type=Path)
    p.add_argument("--run", action="store_true")
    p.add_argument('--tasks',default=TASKS)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    installed = {}
    for name in DEPENDENCIES:
        try: installed[name] = probe_dependency(name)
        except (OSError, subprocess.TimeoutExpired) as exc:
            installed[name] = dict(importable=False, error=str(exc))
    cli = shutil.which("analysisgnn-predict")
    ready = all(x['importable'] for x in installed.values())
    report = {"upstream": "https://github.com/manoskary/analysisgnn",
              "dependencies": installed, "cli": cli, "ready": ready,
              "tasks": args.tasks, "scores": [], "accuracy_evaluated": False,
              "input_status": "provided" if args.musicxml else "blocked_missing_source_musicxml",
              "python": sys.version, "executable": sys.executable}
    if args.checkpoint and args.checkpoint.is_file():
        report['checkpoint_sha256']=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    for score in args.musicxml:
        record = {"path": str(score), "exists": score.is_file()}
        if score.is_file():
            record["sha256"] = hashlib.sha256(score.read_bytes()).hexdigest()
        if not score.is_file():
            record["status"] = "missing_input"
        elif not args.run:
            record["status"] = "preflight_only"
        elif not ready:
            record["status"] = "blocked_missing_dependencies"
        elif args.checkpoint and not args.checkpoint.is_file():
            record["status"] = "blocked_missing_checkpoint"
        else:
            output_dir = (args.out / record['sha256'][:16]).resolve()
            if output_dir.exists():
                record['status'] = 'blocked_existing_output_choose_fresh_directory'
                report['scores'].append(record)
                continue
            output_dir.mkdir(parents=True)
            inputs=output_dir/'inputs';inputs.mkdir()
            snapshot=inputs/score.name;shutil.copy2(score,snapshot)
            record['input_snapshot']=str(snapshot)
            command = [sys.executable, '-m', 'analysisgnn.inference.predict_analysis',
                       "--input_score", str(snapshot), "--output_dir", str(output_dir),
                       "--tasks", args.tasks, "--export_csv"]
            if args.checkpoint:
                command += ["--checkpoint_path", str(args.checkpoint.resolve())]
            try:
                result = subprocess.run(command, capture_output=True,
                                        text=True, timeout=1800, cwd=output_dir)
                predictions = []
                for path in output_dir.glob('*.csv'):
                    with path.open(encoding='utf-8',newline='') as handle:
                        rows = list(csv.DictReader(handle))
                    predictions.append(dict(path=str(path), rows=len(rows),
                        missing_tasks=sorted(set(args.tasks.split(','))-set(rows[0] if rows else [])),
                        columns=list(rows[0]) if rows else [], sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                record.update(status="predictions_produced" if result.returncode == 0 and any(x['rows'] and not x['missing_tasks'] for x in predictions) else "failed",
                              exit_code=result.returncode,
                              command=command, predictions=predictions,
                              stdout_tail=result.stdout[-4000:],
                              stderr_tail=result.stderr[-4000:])
            except (OSError, subprocess.TimeoutExpired) as exc:
                record.update(status="failed", error=str(exc))
        report["scores"].append(record)
    (args.out / "manifest.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if args.run and (not args.musicxml or not all(s['status']=='predictions_produced' for s in report['scores'])):
        raise SystemExit(2)

if __name__ == "__main__":
    main()
