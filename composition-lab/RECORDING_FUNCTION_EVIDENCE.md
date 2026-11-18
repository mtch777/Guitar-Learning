# Optional recording-time function evidence

`analyze_functions(..., recording_evidence=None)` is unchanged by default.
Supply a `recording_function_evidence.recording_evidence(...)` object to attach a separate evidence layer. It does not overwrite score features, hypotheses, labels, weights, or generation behavior. No model/audio dependencies, downloads or inference are added.

Inputs: source-feature SHA256, original-recording SHA256 and duration, exact model revision, chronological nonoverlapping timed candidate distributions. Use actual model distributions, not duration shares or invented confidence. Gaps and truncated tails remain explicit uncovered spans. Alternatives including `bridge`/`inst` remain unchanged; they are not automatically relabeled as breakdown/solo.

Score bars require identity-matched caller-supplied timing attestations (`validation_status='verified'`, nonblank validation method, finite error bound within caller tolerance). The adapter checks the contract, not acoustic correctness. Our exploratory chroma/onset and held-out-attack maps are NOT marked verified and do not populate these bar weights. Recording-time evidence remains useful without a score clock. No links, lyrics, recordings or proprietary captures are committed.

Each output bar remains `label='unknown'`, with uncalibrated candidate weights only where mapping and coverage qualify. Uncertainty intersecting a model boundary at a bar edge causes abstention. Mixed bars use nominal-time duration averaging, NOT uncertainty-integrated probabilities. Full candidate distributions and model provenance are retained. Attach revalidates deserialized content and rejects mutation/inconsistency.

Local pilot: seven recordings processed with unchanged external SongFormer; four first-stage captures also ran the frozen existing classifier. One-song selected-bar agreement improved32/32 versus19/32, but broader provisional reference-interior agreements ranged54-75%. Not broad accuracy, not full-boundary validation, not human listening. No claims about absence from pretrained model training. Currents/ERRA capture inventories exist but corresponding original recordings were not found locally, preventing a fresh paired cross-artist test.
