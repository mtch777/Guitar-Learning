"""Frozen whole-corpus regression; no case reselection or source repair.

Private outputs contain source-derived artifacts. Hash scope is the declared
execution files below, not an operating-system or all-dependency guarantee.
"""
import argparse,hashlib,json,time,traceback
from pathlib import Path
from run_reversible_tier_qa import run

ENGINE_NAMES=("reversible_relationships.py","reversible_topology.py","reversible_positions.py","reversible_annotations.py","reversible_ties.py","reversible_voicings.py","reversible_temporal.py","reversible_song.py","reverse_tier_worker.py","run_reversible_tier_qa.py","check_reversible_source.py","check_reversible_temporal.py","run_reversible_corpus_qa.py","technique_analysis.py","pedal_patterns.py")
API_NAMES=("source_semantics.py","analyze_relationships.py","source_dynamics.py","source_relationship_details.py")


def hashes(folder):return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob("*") if p.is_file()}
def file_hash(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
def code_hashes():
    base=Path(__file__).resolve().parent
    paths=[base/name for name in ENGINE_NAMES]+[base/"songsterr_automation/songsterr_api"/name for name in API_NAMES]
    return {str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
def save(path,value):path.write_text(json.dumps(value,indent=2),encoding="utf-8")


def batch(corpus,output,previous=None):
    corpus=corpus.resolve();output=output.resolve()
    if output.exists() or output.is_relative_to(corpus):raise ValueError("Fresh output outside corpus required")
    folders=sorted((p for p in corpus.iterdir() if p.is_dir()),key=lambda p:p.name)
    if not folders:raise ValueError("Empty corpus")
    baseline_paths={p.name:previous/("case-"+p.name)/"isolated/tier2-only.json" for p in folders} if previous else {}
    baseline_hashes={k:file_hash(p) for k,p in baseline_paths.items()}
    output.mkdir(parents=True);originals={p.name:hashes(p) for p in folders};engine=code_hashes()
    save(output/"manifest.json",dict(cases=[dict(id=p.name,source=str(p)) for p in folders],original_hashes=originals,engine_hashes=engine,baseline_hashes=baseline_hashes,previous=str(previous) if previous else None,mode="song",selection="ALL existing directories; malformed cases retained"))
    results=[]
    for folder in folders:
        if code_hashes()!=engine:
            save(output/"blocked.json",dict(reason="engine_changed_mid_batch",completed=len(results)));raise RuntimeError("Engine changed; keep this batch and start a new freeze")
        start=time.monotonic();target=output/("case-"+folder.name)
        try:
            if hashes(folder)!=originals[folder.name]:raise ValueError("Original inputs changed")
            report=run(folder,target,song=True)
            item=dict(id=folder.name,status=report["status"],events=report["events"],owned_roundtrip=report["owned_song_roundtrip"],temporal=report["independent_temporal_check"],ownership=report["independent_ownership_check"])
            if previous:
                if baseline_hashes[folder.name] is None:raise ValueError("Frozen comparison baseline missing")
                if file_hash(baseline_paths[folder.name])!=baseline_hashes[folder.name]:raise ValueError("Comparison baseline changed since freeze")
                old=json.loads((previous/("case-"+folder.name)/"isolated/tier2-only.json").read_text(encoding="utf-8-sig"));new=json.loads((target/"isolated/tier2-only.json").read_text(encoding="utf-8-sig"))
                item["music_unchanged"]=new["music"]==(old["music"] if old.get("schema")=="owned-song-stages/1" else old)
                if not item["music_unchanged"]:item["status"]="changed_music_preserved_case"
        except Exception as error:
            item=dict(id=folder.name,status="failed_preserved_case",error_type=type(error).__name__,message=str(error))
            target.mkdir(exist_ok=True)
            artifact=next((name for name in ("qa.json","reverse-process.json","owned-checker-only.json","tier1-checker-only.json") if (target/name).exists()),None)
            save(target/"batch-error.json",dict(traceback=traceback.format_exc(),last_persisted_artifact=artifact,stage_note="Artifact boundary, not exact failing function"))
        item.update(seconds=round(time.monotonic()-start,3),originals_unchanged=hashes(folder)==originals[folder.name],engine_unchanged=code_hashes()==engine)
        if not item["originals_unchanged"] or not item["engine_unchanged"]:item["status"]="integrity_failed_preserved_case"
        results.append(item)
        with (output/"results.jsonl").open("a",encoding="utf-8") as handle:handle.write(json.dumps(item)+"\n")
        save(output/"summary.json",dict(total=len(folders),completed=len(results),passed=sum(x["status"]=="pass_declared_scope" for x in results),failed=sum(x["status"]!="pass_declared_scope" for x in results),results=results))
        print(json.dumps(dict(id=item["id"],status=item["status"],completed=len(results),total=len(folders))),flush=True)
    original_names={p.name for p in folders};current_names={p.name for p in corpus.iterdir() if p.is_dir()}
    final=dict(added_directories=sorted(current_names-original_names),removed_directories=sorted(original_names-current_names),baseline_hash_mismatches=[k for k,p in baseline_paths.items() if file_hash(p)!=baseline_hashes[k]],source_hash_mismatches=[p.name for p in folders if hashes(p)!=originals[p.name]],engine_unchanged=code_hashes()==engine)
    save(output/"end-integrity.json",final)
    return dict(cases=len(results),passed=sum(x["status"]=="pass_declared_scope" for x in results),integrity=final)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("corpus",type=Path);p.add_argument("output",type=Path);p.add_argument("--previous",type=Path);a=p.parse_args()
    if "local-artifacts" not in a.output.resolve().parts:p.error("Private output required")
    result=batch(a.corpus,a.output,a.previous);print(json.dumps(result))
    if result["passed"]!=result["cases"] or result["integrity"]["source_hash_mismatches"] or result["integrity"]["added_directories"] or result["integrity"]["removed_directories"] or result["integrity"]["baseline_hash_mismatches"] or not result["integrity"]["engine_unchanged"]:raise SystemExit(1)


if __name__=="__main__":main()
