# F-drive runtime

Canonical runtime: F:\dot-workspaces\Guitar-Learning-rhythm\riff-generator-runtime
Canonical source: F:\dot-workspaces\Guitar-Learning-rhythm\riff-generator-source

Run start-runtime.ps1 only after existing generator/companion processes are stopped. It validates dataset and preset hashes, uses F for app code, datasets, renderer states/worker/lock, editor snapshots, generated MIDI repository, render artifacts, temporary files, caches, and stdout/stderr logs. Python bytecode writes are disabled for inherited processes. The launcher writes logs/launch.json with the exact configured paths and process IDs.

Installed Python, Kontakt plugin, and licensed libraries remain on C as read-only dependencies; legacy project copies on C are preserved but must not be used for development or launching. This does not guarantee that Windows or third-party installed software never writes its own application state or crash diagnostics.

The standalone start-companion.ps1 is retired to avoid incomplete configuration.

Verified preset rollout: 10 of 56 installed Hydra presets currently have independent initialized-state/render verification. Only those entries are exposed. The remaining 46 are not selectable yet.
