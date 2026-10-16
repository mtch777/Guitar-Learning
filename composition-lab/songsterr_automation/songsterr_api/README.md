# Songsterr API endpoint smoke tests

Run from this directory with Python 3.9+ (no dependencies, no API key):

```bash
python test_endpoints.py --artist "Pink Floyd" --output songsterr_api_results.json
python test_endpoints.py --include-extras
```

The script probes all **five** request patterns illustrated by the supplied publicapis.io directory (best match, tab view, legacy keyword search, legacy artist search, modern song search) plus two modern endpoints discussed in Composition Lab (artist songs, song metadata). Optional extras probe three additional routes cited by other public directories. All requests are GET; one-second spacing is the default. Output includes HTTP status, JSON validity, basic response shape, latency and errors. Exit code 1 means one or more probes failed.

**Important:** These are publicly described/observed endpoints, not an exhaustive list of all private Songsterr endpoints. Songsterr's legacy API docs may be outdated; modern APIs are unofficial. ID-based probes use an illustrative ID and may return 404 if that ID is invalid. Treat failures individually. Do not confuse HTML error pages with successful JSON responses. The test does not fetch/download GP scores or run the separate downloader.

Sources:
- https://publicapis.io/songsterr-music-api
- https://www.songsterr.com/a/wa/api/
- https://shipapis.dev/api/songsterr
- https://greatapis.com/api/songsterr/

Run this from a machine with network access. A test suite committed to GitHub is **not** proof that the remote Songsterr endpoints have passed.
