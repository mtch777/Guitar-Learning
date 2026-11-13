# Riff walkthrough

A local Python 3.10+ server with browser HTML/JS UI. Standard library only. Keep sibling `seed-scoring` and `weighted-scoring` directories alongside `riff-walkthrough`; the original approved generator code is imported, not copied into a new algorithm.

Windows launch (PowerShell):
```
$env:RIFF_CSV='C:\Users\User\riff-csv-engine\full-export\all_riffs_phrase_composition.csv'
$env:RIFF_TIMING='C:\Users\User\riff-csv-engine\pitch-free-all-lengths\pitch_free_all_lengths_phrase_rhythms.json'
python riff-walkthrough\server.py --host 127.0.0.1 --port 8768
```

Open http://127.0.0.1:8768. Initial full-corpus load takes about 30 seconds in the cloud test and uses several GB of memory. The browser reports loading, not fake progress. Do not open multiple server processes. Stop the server before replacing source code.

For same-LAN access, explicitly bind `--host 0.0.0.0` and test the actual machine address. Do not change firewall, router, or network-security settings. LAN connectivity is not proof of Android device connectivity. No public proxy/tunnel or credential is configured. This app exposes no raw file paths or file browsing API and rejects cross-origin generation requests. Session state is browser-cookie-scoped and lives in server memory; a server restart resets it.

This package is an incremental build. Check BUILD_STATUS.json before describing completed stages. The corpus is not bundled; use the verified existing data paths above. Source hashes available in /api/config. UI output is engine-derived only. Current strict scale compatibility and carry-in pitch blockers remain explicit.
