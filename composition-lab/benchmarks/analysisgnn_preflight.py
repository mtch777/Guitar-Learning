"""Preflight and run AnalysisGNN on independently exported source MusicXML.
No automatic labels, no claims of accuracy without human ground truth.
"""
import argparse, hashlib, importlib.util, json, shutil, subprocess
from pathlib import Path

DEPENDENCIES = ("torch", "torch_geometric", "partitura", "graphmuse", "analysisgnn")
TASKS = "cadence,localkey,romanNumeral"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("musicxml", nargs="*", type=Path)
    p.add_argument("--out", type=Path, default=Path("analysisgnn-results"))
    p.add_argument("--checkpoint", type=Path)
    p.add_argument("--run", action="store_true")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    installed = {name: importlib.util.find_spec(name) is not None for name in DEPENDENCIES}
    cli = shutil.which("analysisgnn-predict")
    ready = all(installed.values()) and cli is not None
    report = {"upstream": "https://github.com/manoskary/analysisgnn",
              "dependencies": installed, "cli": cli, "ready": ready,
              "tasks": TASKS, "scores": [], "accuracy_evaluated": False}
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
            command = [cli, "--input_score", str(score.resolve()),
                       "--tasks", TASKS, "--export_csv"]
            if args.checkpoint:
                command += ["--checkpoint_path", str(args.checkpoint.resolve())]
            try:
                result = subprocess.run(command, capture_output=True,
                                        text=True, timeout=1800)
                record.update(status="completed" if result.returncode == 0 else "failed",
                              exit_code=result.returncode,
                              stdout_tail=result.stdout[-4000:],
                              stderr_tail=result.stderr[-4000:])
            except (OSError, subprocess.TimeoutExpired) as exc:
                record.update(status="failed", error=str(exc))
        report["scores"].append(record)
    (args.out / "manifest.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
