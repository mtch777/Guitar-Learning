# F-drive runtime

Canonical runtime: F:\dot-workspaces\Guitar-Learning-rhythm\riff-generator-runtime
Canonical source: F:\dot-workspaces\Guitar-Learning-rhythm\riff-generator-source

Run start-runtime.ps1 only after existing generator/companion processes are stopped. It validates dataset and preset hashes, uses F for app code, datasets, renderer states/worker/lock, editor snapshots, generated MIDI repository, render artifacts, temporary files, caches, and stdout/stderr logs. Python bytecode writes are disabled for inherited processes. The launcher writes logs/launch.json with the exact configured paths and process IDs.

Installed Python, Kontakt plugin, and licensed libraries remain on C as read-only dependencies. The project-created `kontakt-render-test/venv312` also remains on C by explicit user instruction and must not be removed while the renderer uses it; legacy project copies on C are preserved but must not be used for development or launching. This does not guarantee that Windows or third-party installed software never writes its own application state or crash diagnostics.

The standalone start-companion.ps1 is retired to avoid incomplete configuration.

Verified preset rollout: 45 of 56 installed Hydra presets currently have independent initialized-state/render verification. Only those entries are exposed. The remaining 11 are not selectable yet.

## Path hardening - 2026-11-14
- [x] Replace stale QA data/import/worker/editor paths with existing F runtime locations; leave approved C virtualenv read dependency.
- [x] Explicit F project temporary directories in generation/selective editing, independent of OS temp defaults.
- [x] Reject Windows non-F destinations for MIDI repositories, editor state, render folders, and standalone renderer output/lock.
- [x] Require F runtime root in launcher and pass RIFF_TEMP_DIR.
- [x] Regression tests: 27 editor/delete/render/save/review tests passed; 3 F-output guard tests passed. Publication recorded by commit.
These application checks are not an OS sandbox and cannot constrain unrelated agents or vendor process caches. Existing running services require a controlled restart to load changed Python code; copying files does not hot-reload it.
