"""Freeze an unseen-song sampling decision before capture; never replace failure."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import random
import secrets
import sys


ARTIST_PROTOCOL = "songsterr-artist-first100-v1"
ARTIST_NAMES = {"invent animate": "Invent Animate", "currents": "Currents", "erra": "ERRA"}
ARTIST_POOL_RULE = ("first100 public search records for the requested artist query; exact-artist "
                    "IDs deduplicated and previously selected/captured IDs excluded; one uniform "
                    "draw from this bounded eligible population, not uniform catalog sampling")


def artist_key(value):
    if type(value) is not str or not value.strip():
        raise ValueError("Artist must be a nonempty string")
    return " ".join(value.replace(",", " ").casefold().split())


def sample_artist(output, client_root, artist, exclude_corpus=None, seed=None,
                  previous_selections=(), extra_excluded_ids=()):
    """Explicit artist-conditioned protocol; failures retain the single chosen ID.

    This changes the declared population, not the musical admission rules. The
    complete returned ID/artist rows are recorded before metadata/track requests.
    No instrumentation, musical-content or difficulty filters are applied.
    """
    if output.exists():
        raise ValueError("Fresh private selection folder required")
    output.mkdir(parents=True)
    manifest = dict(sampling_protocol=ARTIST_PROTOCOL, requested_artist=artist,
                    seed=secrets.randbits(64) if seed is None else seed,
                    search_size=100, pool_rule=ARTIST_POOL_RULE,
                    status="input_pending", started_utc=datetime.now(timezone.utc).isoformat())
    path = output / "selection.json"
    def save():
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    save()
    try:
        key = artist_key(artist)
        if key not in ARTIST_NAMES:
            raise ValueError("Only Invent Animate, Currents and ERRA are permitted")
        if type(manifest["seed"]) is not int:
            raise ValueError("Seed must be an exact integer")
        query = ARTIST_NAMES[key]
        excluded = [int(p.name) for p in exclude_corpus.iterdir()
                    if p.is_dir() and p.name.isdigit()] if exclude_corpus else []
        excluded.extend(extra_excluded_ids)
        for previous_path in previous_selections:
            previous = json.loads(previous_path.read_text(encoding="utf-8-sig"))
            if "selected_song_id" in previous:
                excluded.append(previous["selected_song_id"])
        if any(type(value) is not int or value <= 0 for value in excluded):
            raise ValueError("Exclusions must be positive exact song IDs")
        excluded = sorted(set(excluded))
        manifest.update(requested_artist=query, query=query, excluded_ids=excluded,
                        status="pool_request_pending")
        save()
        sys.path.insert(0, str(client_root.resolve()))
        from songsterr_dl.client import SongsterrClient
        with SongsterrClient(timeout=30) as client:
            records = client.search(query, size=100)
            if not isinstance(records, list):
                raise ValueError("Search response must be a list")
            # Keep order, duplicates and raw artist spelling; do not retain only
            # matching rows, which would conceal additional selection filters.
            rows = [dict(songId=r.get("songId"), artist=r.get("artist"))
                    if isinstance(r, dict) else dict(invalid_record=r) for r in records]
            manifest.update(returned_population=rows, status="population_recorded")
            save()
            if len(rows) > 100:
                raise ValueError("Search returned more than the declared first100 records")
            identities = {}
            for row in rows:
                sid = row.get("songId")
                if type(sid) is not int or sid <= 0:
                    raise ValueError("Search song ID must be a positive exact integer")
                observed = artist_key(row.get("artist"))
                if sid in identities and identities[sid] != observed:
                    raise ValueError("Conflicting artist identities for one returned song ID")
                identities[sid] = observed
            pool = sorted(sid for sid, observed in identities.items()
                          if observed == key and sid not in excluded)
            manifest.update(candidate_ids=pool, status="pool_frozen_before_draw")
            save()
            if not pool:
                raise ValueError("Empty unseen artist sampling pool; no automatic replacement")
            sid = random.Random(manifest["seed"]).choice(pool)
            manifest.update(selected_song_id=sid, status="selected_before_capture")
            save()
            meta = client.meta(sid)
            capture = output / "capture"
            capture.mkdir()
            (capture / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            if not isinstance(meta, dict) or artist_key(meta.get("artist")) != key:
                raise ValueError("Captured metadata artist differs from requested artist")
            if type(meta.get("songId")) is not int or meta["songId"] != sid:
                raise ValueError("Captured metadata song ID differs from selected song")
            if type(meta.get("revisionId")) is not int or meta["revisionId"] <= 0:
                raise ValueError("Captured revision must be a positive exact integer")
            if not isinstance(meta.get("tracks"), list):
                raise ValueError("Captured tracks must be a list")
            for part in range(len(meta["tracks"])):
                payload = client.track(sid, meta["revisionId"], meta["image"], part)
                (capture / f"track-{part}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest.update(status="captured", artist=meta["artist"], title=meta.get("title"),
                            revision_id=meta["revisionId"], tracks=len(meta["tracks"]))
    except Exception as error:
        manifest.update(status="failed_selection_or_capture", error=type(error).__name__ + ": " + str(error))
        save()
        raise
    save()
    return manifest


def sample(output,client_root,exclude_corpus=None,seed=None,previous_selections=(),extra_excluded_ids=(),*,artist=None):
    if artist is not None:
        return sample_artist(output, client_root, artist, exclude_corpus, seed,
                             previous_selections, extra_excluded_ids)
    if output.exists():raise ValueError("Fresh private selection folder required")
    output.mkdir(parents=True)
    seed=secrets.randbits(64) if seed is None else seed
    rng=random.Random(seed);query=rng.choice("abcdefghijklmnopqrstuvwxyz")
    excluded=sorted(int(p.name) for p in exclude_corpus.iterdir() if p.is_dir() and p.name.isdigit()) if exclude_corpus else []
    excluded=sorted(set(excluded)|set(map(int,extra_excluded_ids))|{json.loads(p.read_text())["selected_song_id"] for p in previous_selections if "selected_song_id" in json.loads(p.read_text())})
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("output",type=Path);p.add_argument("--client-root",type=Path,required=True);p.add_argument("--exclude-corpus",type=Path);p.add_argument("--previous-selection",type=Path,action="append",default=[]);p.add_argument("--seed",type=int);p.add_argument("--artist",help="Opt in to exact-artist first100 protocol: Invent Animate, Currents or ERRA");a=p.parse_args()
    if "local-artifacts" not in a.output.resolve().parts:p.error("Private output required")
    result=sample(a.output,a.client_root,a.exclude_corpus,a.seed,a.previous_selection,artist=a.artist)
    print(json.dumps({k:v for k,v in result.items() if k not in {"candidate_ids","excluded_ids","returned_population"}}))


if __name__=="__main__":main()
