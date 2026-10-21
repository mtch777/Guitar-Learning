"""Freeze an unseen-song sampling decision before capture; never replace failure."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import random
import secrets
import sys


def sample(output,client_root,exclude_corpus=None,seed=None,previous_selections=()):
    if output.exists():raise ValueError("Fresh private selection folder required")
    output.mkdir(parents=True)
    seed=secrets.randbits(64) if seed is None else seed
    rng=random.Random(seed);query=rng.choice("abcdefghijklmnopqrstuvwxyz")
    excluded=sorted(int(p.name) for p in exclude_corpus.iterdir() if p.is_dir() and p.name.isdigit()) if exclude_corpus else []
    excluded=sorted(set(excluded)|{json.loads(p.read_text())["selected_song_id"] for p in previous_selections if "selected_song_id" in json.loads(p.read_text())})
    manifest=dict(seed=seed,query=query,excluded_ids=excluded,pool_rule="first100 public search results for seed-selected alphabet letter, valid previously uncaptured IDs only; not uniform catalog sampling",status="pool_request_pending",started_utc=datetime.now(timezone.utc).isoformat())
    path=output/"selection.json"
    def save():path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    save()
    try:
        sys.path.insert(0,str(client_root.resolve()))
        from songsterr_dl.client import SongsterrClient
        with SongsterrClient(timeout=30) as client:
            records=client.search(query,size=100)
            pool=sorted({int(r["songId"]) for r in records if r.get("songId") and int(r["songId"]) not in excluded})
            manifest["candidate_ids"]=pool
            if not pool:raise ValueError("Empty unseen sampling pool; no automatic replacement")
            sid=rng.choice(pool);manifest.update(selected_song_id=sid,status="selected_before_capture");save()
            meta=client.meta(sid);capture=output/"capture";capture.mkdir()
            (capture/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
            for part in range(len(meta["tracks"])):
                payload=client.track(sid,meta["revisionId"],meta["image"],part)
                (capture/f"track-{part}.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
            manifest.update(status="captured",artist=meta.get("artist"),title=meta.get("title"),revision_id=meta["revisionId"],tracks=len(meta["tracks"]))
    except Exception as error:
        manifest.update(status="failed_selection_or_capture",error=type(error).__name__+": "+str(error));save();raise
    save();return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("output",type=Path);p.add_argument("--client-root",type=Path,required=True);p.add_argument("--exclude-corpus",type=Path);p.add_argument("--previous-selection",type=Path,action="append",default=[]);p.add_argument("--seed",type=int);a=p.parse_args()
    if "local-artifacts" not in a.output.resolve().parts:p.error("Private output required")
    result=sample(a.output,a.client_root,a.exclude_corpus,a.seed,a.previous_selection)
    print(json.dumps({k:v for k,v in result.items() if k not in {"candidate_ids","excluded_ids"}}))


if __name__=="__main__":main()
