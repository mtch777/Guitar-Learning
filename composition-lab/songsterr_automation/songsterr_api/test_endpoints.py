#!/usr/bin/env python3
"""Read-only smoke tests for documented and observed Songsterr GET endpoints.

No API key. Standard library only. Run:
    python test_endpoints.py
    python test_endpoints.py --artist "Pink Floyd" --output results.json
    python test_endpoints.py --include-extras

Results include status, content type, elapsed time, response shape, and errors.
An endpoint returning HTTP 200 with an HTML error page is NOT a pass.
This is an inventory of publicly documented/discovered routes, not a claim
to enumerate Songsterr's private/internal API.
"""
import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://www.songsterr.com"
HEADERS = {"User-Agent": "CompositionLab-Songsterr-Endpoint-SmokeTest/1.0", "Accept": "application/json, text/html;q=0.8"}
ENDPOINTS = [
    ("legacy_best_match", "/a/wa/bestMatchForQueryStringPart", {"s": "comfortably numb"}, "json"),
    ("legacy_view", "/a/wa/view", {"r": "79"}, "html"),
    ("legacy_keyword_search", "/a/ra/songs.json", {"pattern": "comfortably numb"}, "json"),
    ("legacy_artist_songs", "/a/ra/songs/byartists.json", {"artists": "pink floyd"}, "json"),
    ("modern_song_search", "/api/songs", {"pattern": "pink floyd", "size": "5"}, "json"),
    ("modern_artist_songs", "/api/artists/79/songs", {}, "json"),
    ("modern_song_metadata", "/api/meta/79", {}, "json"),
]
# Supplementary probes are NOT part of the user-supplied directory's documentation.
EXTRAS = [
    ("modern_songs_limit", "/api/songs", {"limit": "5"}, "json"),
    ("modern_songs_page", "/api/songs", {"page": "1"}, "json"),
    ("modern_search", "/api/search", {"query": "pink floyd"}, "json"),
]

def request(name, path, params, expected, timeout, max_bytes):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    result = {"name": name, "method": "GET", "url": url, "expected": expected}
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, headers=HEADERS, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(max_bytes + 1)
        truncated = len(raw) > max_bytes
        raw = raw[:max_bytes]
        result.update(status=status, content_type=content_type, truncated=truncated,
                      bytes_sampled=len(raw))
        if expected == "json":
            try:
                parsed = json.loads(raw)
                result["shape"] = type(parsed).__name__
                if isinstance(parsed, list):
                    result["items"] = len(parsed)
                    if parsed and isinstance(parsed[0], dict):
                        result["sample_keys"] = list(parsed[0])[:25]
                elif isinstance(parsed, dict):
                    result["sample_keys"] = list(parsed)[:25]
                result["ok"] = status == 200 and not truncated
            except (ValueError, UnicodeDecodeError):
                result["ok"] = False
                result["error"] = "Response is not valid JSON (or exceeds max bytes)"
                result["sample"] = raw[:160].decode("utf-8", errors="replace")
        else:
            sample = raw[:250].decode("utf-8", errors="replace")
            result["sample"] = sample
            result["ok"] = status == 200 and ("html" in content_type.lower() or "<html" in sample.lower())
    except urllib.error.HTTPError as error:
        result.update(status=error.code, ok=False, error=f"HTTP {error.code}: {error.reason}")
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        result.update(status=None, ok=False, error=f"{type(error).__name__}: {error}")
    result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artist", default="Pink Floyd", help="Artist for keyword searches")
    parser.add_argument("--output", type=Path, default=Path("songsterr_api_results.json"))
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between calls")
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--include-extras", action="store_true")
    args = parser.parse_args()
    if args.timeout <= 0 or args.delay < 0 or args.max_bytes < 100:
        parser.error("timeout must be positive; delay nonnegative; max-bytes >= 100")
    endpoints = ENDPOINTS + (EXTRAS if args.include_extras else [])
    results = []
    for index, (name, path, params, expected) in enumerate(endpoints):
        if index:
            time.sleep(args.delay)
        params = dict(params)
        if name == "legacy_artist_songs":
            params["artists"] = args.artist.lower()
        elif name == "modern_song_search":
            params["pattern"] = args.artist
        item = request(name, path, params, expected, args.timeout, args.max_bytes)
        results.append(item)
        print(f"{'PASS' if item['ok'] else 'FAIL'}  {name:25s} HTTP {item.get('status')}  {item['elapsed_ms']}ms")
        if item.get("error"):
            print("      " + item["error"])
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": "https://publicapis.io/songsterr-music-api",
        "note": "Legacy view and modern ID-based probes use example ID 79; a 404 may indicate an invalid song ID, not a broken endpoint.",
        "total": len(results), "passed": sum(bool(x["ok"]) for x in results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{report['passed']}/{report['total']} passed. Saved {args.output}")
    return 0 if report["passed"] == report["total"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
