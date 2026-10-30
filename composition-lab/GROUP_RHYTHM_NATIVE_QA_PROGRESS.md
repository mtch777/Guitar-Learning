# Group rhythm: independent native-output review

Scope: a development-song rhythm change using the source's own three-note grouping and a supported donor rhythm. This review does not certify a fresh random song, human musical approval, or every creative control.

## Acceptance checklist

- [x] Source and 0% exports have identical normalized GP content, complete MIDI events, and rendered samples.
- [x] The changed export alters only the selected rhythm references. Actual GP durations match the chosen rhythm shares; pitch, articulation, other beats, and non-score archive assets stay locked.
- [x] Selected MIDI note start/end times follow the group-duration equation. Unrelated note events and controllers remain unchanged.
- [x] Native center-pitch resets follow their generating selected note. Other notes cannot supply that permission; non-center bends cannot move under this allowance.
- [x] All six render jobs/results bind the expected score, MIDI, capture, track, excerpt, cue, sample count, and audio hash.
- [x] Corruption tests fail for unrelated GP changes, wrong duration, absent capture/dependency proof, wrong/missing/duplicate render receipts, MIDI drift, controller misattribution, and modified worker output.
- [x] Fresh actual GP imports independently regenerate the saved native snapshots and MIDI-origin ledgers exactly.
- [x] Original failed process/report stays preserved; a separate recovery receipt identifies the corrected audit assumptions and current evidence.

## What this review found and fixed

The initial artifact checker did not independently bind every capture/dependency, inspect selected GP duration definitions, verify all render receipts, or compare archive members outside GPIF. Root added those checks. The archive omission was demonstrated by a corruption test that originally passed with an unrelated archive asset changed; it now fails as required.

Two earlier audit assumptions caused retained failures: a successful standalone GP comparison does not produce a recovery comparison file, and AlphaTab emits a center-pitch reset for ordinary note attacks. The revised checker verifies the exact reset value, track/channel/key, actual generating note, and attack time. It does not ignore arbitrary pitch or controller changes.

## Commands and results

From `composition-lab`:

- `..\.venv\Scripts\python.exe -m unittest test_group_rhythm_artifacts -v` — **8 tests pass**, including 19 corruption scenarios and one passing synthetic fixture. Synthetic fixtures contain no copyrighted score material and are not audio-execution evidence.
- Fresh copies of the three private GP exports were re-read using `audit_dynamic_gp.mjs`, then checked using `audit_group_rhythm_origins.mjs`. All three snapshots contain **9,233 notes**; snapshots and complete MIDI-origin ledgers reproduce exactly.
- Actual audio: both focused and ensemble excerpts contain **233,472 samples at 44,100 Hz**. Source/0% samples match exactly. The prefix before the target at **2.647059 seconds** remains identical; the first difference is at **2.755918 seconds**, after the selected group starts.

Private evidence: `local-artifacts/group-rhythm-v1/independent-native-review-v1/recovery-receipt.json`, alongside the fresh snapshots and replay script. The original `native-preview/failure.json` and `native-audio-audit.log` remain unchanged. The original process is still recorded as failed; the subsequent validated recovery has a separate receipt.

## Boundaries and next action

This is the existing development song. The target is bar 39, offset 2 quarter notes; the donor is bar 162. No easier song was substituted. Existing GP fidelity qualifications and the separately bound bend companion remain explicit. Human listening and artist-style approval are not inferred from these checks.

This bounded native review is complete. Root coordinates the shared dependency freeze and subsequent new random-song gate with ProjectPlanner3000. No source converter, approved detector, or unrelated technique was changed by this review.
