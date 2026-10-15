# Exact graph and controlled-generation prototype

This implementation advances engineering prerequisites. **The five-step roadmap is not complete.** It is not a trained genre-agnostic composition model, a validated harmony/phrase detector, or a musical-quality result.

## Source fidelity and inference

`exact_score.py` loads the checkpoint extractor without accidentally importing the older top-level `extract.py`. Empty GP voice slots now retain their indices, so occurrence editing addresses the correct voice. The canonical output retains raw track, bar, master-bar, rhythm, beat and note XML plus a source hash. Timing stays rational. This is a supported GPIF view; multi-staff track mapping, grace timing, instrument-articulation pitch resolution and source-specific anomalies still require validation. Raw descriptors do not prove that inference consumes them.

From this directory:

```powershell
python musicxml_bridge.py 'SOURCE.gp' 'local-artifacts/source.musicxml'
..\.venv\Scripts\python.exe benchmarks/analysisgnn_preflight.py local-artifacts/source.musicxml --run --out local-artifacts/inference-run-1
```

The MusicXML bridge emits unique occurrence IDs and independently checks note pitch, onset, duration and voice using MusicXML cursor/backup/chord semantics. Rational divisions avoid quantization. Overfull voices are rejected, never stretched or truncated. Underfull voices are reported. Techniques remain in the canonical sidecar rather than becoming model features. A tied written-note occurrence can be merged by a downstream library; compare identities and sustains before comparing note-array counts.

The preflight actually imports dependencies in subprocesses, uses the active Python interpreter for inference, isolates outputs, and requires nonempty prediction CSVs before reporting predictions produced. It exits nonzero when a requested inference is blocked. Predicted agreement with an existing model is not accuracy. Native-package directory presence and CLI exit zero alone are insufficient evidence.

AnalysisGNN upstream inspected at commit `e115182fb29b74bdcb6bf3547ed427d967580947`; default checkpoint is a W&B artifact. Its training data/checkpoint permissions are separate from source code. No checkpoint or copyrighted source is committed here.

## Graph

`relational_graph.build_graph` preserves occurrence observations and separately stores caller-provided root, quality, inversion, bass, NCT, role and phrase hypotheses with their provenance/confidence. Relationships include voice succession, half-open overlap, simultaneous onset, explicitly marked ties, track/beat/bar membership, source sections, exact bar repeats and transposition-equivalent rhythmic motifs. Membership uses group nodes rather than quadratic track cliques. Motif equality is an engineering definition, not perceptual ground truth. Unresolved ties are reported, not invented.

## Generation experiments

```powershell
python controlled_generation.py --demo --seed 17 --out local-artifacts/FRESH-DIRECTORY
# Or --plan explicit-relational-plan.json instead of --demo.
node verify_gp.mjs PATH-TO-ALPHATAB/dist/alphaTab.mjs local-artifacts/FRESH-DIRECTORY/harmony.gp
..\.venv\Scripts\python.exe playback_review.py local-artifacts/FRESH-DIRECTORY
```

The demo is a **new authored engineering fixture**, not Cloud V2 or a learned commercial-song example. Five GP files are authored from scratch: a reference plus harmony, rhythm, melody and phrase-order control experiments. All stages already contain explicit instrument roles; these are **not** the requested four source-trained role ablations. The original V2 generator source is untouched, and the missing V2 GP must not be replaced by this reference.

Plans explicitly supply track roles/tunings, per-bar chord root/quality, per-note chord degree/octave/chromatic alteration, rhythm and named phrase blocks. No automatic role/harmony truth is assigned to arbitrary GP files. Candidate search selects the closest observed difference targets and penalizes melodic motion; it does not learn coherent progression probabilities or non-chord-tone resolution. Phrase-order changes move actual whole blocks. Joint fingering enforces unique strings, 0–24 frets and at most five frets of non-open chord span; these checks do not establish human playability.

Differences are shares of changed plan units: per-bar root/quality, per-role/bar duration sequences, per-role/bar chord-relative note sequences, and named phrase block order. These are discrete, uncalibrated distances, not perceptual percentages. Zero targets enforce equality in these representations; all-zero returns an identical plan. Melody zero locks explicit degree/octave/alteration, allowing pitch to follow changed harmony. Unknown harmonic roles cannot be safely mapped by this prototype. Candidate counts, observed ranges, actual distances and target attainment are reported independently. Structure reordering can conflict with other locks; infeasible requests must be reported, not silently relaxed. For a narrow candidate set the closest result may be identity.

`gp_author.py` creates new pitched GP tracks and exact occurrence tables; it rejects unsupported ties/techniques. It is not a replacement for the occurrence-aware source editor. `verify_gp.mjs` uses independent alphaTab import, checks expected pitch/timing/tuning and writes SMF MIDI. `playback_review.py` renders that MIDI as sine-wave approximation with anonymous filenames and blank human fields. It does not reproduce GP instruments or validate audio quality.

## Validation and remaining work

`generation_validation.py` separates descriptive per-track statistics, exact/transposition-relative copying, and a byte-hash train/held-out leakage guard. Different editions of the same song still require song identity adjudication. Copying checks against one supplied reference do not prove originality. No held-out commercial-song evaluation or listening judgments have been collected in this clone.

Run `python -m unittest discover -s . -p 'test_*.py' -v` here. Historical checkpoint tests run separately from their own directory; many require unavailable private `/mnt/data` fixtures. Do not report those tests as passing or reinterpret fixture absence as successful validation.

Next prerequisites: locate original source scores/MusicXML/V2 baseline; inspect every Sweet Child timing discrepancy against actual GPIF; provide a functioning GraphMuse native build; run the pretrained model; use adjudicated role/harmonic evidence to build source-conditioned plans; then generate the actual controlled role ablations, validate held-out songs, and collect blind listening judgments.
