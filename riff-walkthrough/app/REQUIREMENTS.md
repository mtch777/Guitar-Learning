# Riff generator walkthrough requirements

## Purpose
Let Mitch control, hear, and inspect how existing analysis becomes a riff. This is a working interface to the current analytical generator, not a simulated demo or new music algorithm.

## Interaction contract
- Six ordered steps: seed, scaffold, rhythms, opening pitches, remaining pitches, final review/export.
- Each generation step has its real parameters and a Generate button. Final review has render/export parameters only if they really exist.
- Clicking Generate preserves all upstream selections and applied settings exactly. It replaces the selected step and automatically regenerates every dependent downstream step.
- Changing controls only edits a draft; nothing regenerates until Generate is clicked. The UI distinguishes draft settings from settings used for the displayed result.
- Store per-stage RNG seed and result. No global-RNG coupling. Repeated generation creates fresh draws; identical seeds replay identically.
- Immediately invalidate stale downstream results when a generation starts. Errors/blocks cannot leave old audio, downloads or output masquerading as current.
- No concurrent requests may race and overwrite newer runs. Show honest busy state and block conflicting actions.
- Keep a previous completed version for comparison, clearly separate from current state. Do not silently restore it or use it as fallback.
- Actual runtime data is the sole source for selections, scores, labels, counts, notes and blockers. No AI prose, fabricated outcomes or invented labels.

## Stages
1. Seed: randomly select among existing eligible riffs, show first phrase and its real attributes; optional artist selection only if explicitly exposed, default all. Reference audio must say Reference.
2. Scaffold: existing same-known-opening-role similarity-weighted whole scaffold lookup, current approved static field weights, user-adjustable weights. Preserve first seed phrase and existing repeat-length rules. Show phrase order, length, role, texture, repeats. Before rhythm exists, clearly label reference audio.
3. Rhythms: existing exact-length opening lookup followed by independent or contextual method and real weights. Preserve repeat timing relationships. No pitches; preview uses E1 and says Rhythm. Show each source and copy relationship, actual candidate counts and available scores under optional details.
4. Opening pitches: current four pooled tiers (exact order, reordered, contiguous subsequence, gapped subsequence), default weights 1/.75/.5/.25, same reference similarity scoring. No initial tonal filter or transposition. Preserve every rhythm slot, onset and duration. Preview opening notes and unpitched remainder distinctly labeled.
5. Remaining pitches: one at a time; exact note repeats copy pitches, rhythm-only repeats choose new pitches. Use existing relative-key compatibility and refine from actual notes. Strict scale limitation is visible, not silently fixed. Crucially DO NOT redraw any rhythm at this step. Expose specific blockers including carry-in mismatch and no compatible scale. Preserve already completed phrase audio on partial result without presenting it as a complete riff.
6. Final: generated audio and MIDI export from same actual notes, no new musical choices. Do not silently fill missing notes or label partial output complete.

## Non-negotiable existing behavior
- No 50-riff cap, top-N cap, score cutoff, artificial candidate pool, hidden resampling, or newly invented exclusions.
- Exclude unresolved selected seed/reference roles as current logic specifies; retain base CSV unchanged.
- Preserve exact mapped Drop E pitches; do not transpose tonal centers or force E key.
- No seconds field in CSV. No unrelated data repair or key/color-note logic redesign.
- Keep both existing rhythm methods.
- All rhythmic slots including overlaps and carries must be preserved; if a stage cannot handle them, stop clearly, never drop them.

## Clean interface and playback
- Phone-first responsive layout with large labeled controls, minimal text, no marketing or explanatory filler.
- Parameters, Generate, result and Play together in each step. Deeper fields, scoring and provenance tucked under Details.
- Reference vs rhythm-only vs generated/partial audio distinguished; simple synth pitches rather than invented performance expression.
- User gesture unlocks audio; no autoplay. One playback at a time; stopping, regeneration and switching audio halt prior voices.
- Play button directly above visualization; playback cursor and automatic horizontal tracking if timeline overflows.
- Retain previous/current playback comparison without clutter.
- Clear loading, empty, blocked and unavailable states. Errors say what failed; no fake success.
- No unnecessary tuning selector, whole-fretboard setting, playback tempo control, dropdown phrase picker, clear-filters button or fluff.

## QA and iterative gates
Develop in small stages. Share each stage and evidence with independent reviewer acting for Mitch; fix actionable findings and retest before advancing. Check actual backend/state contracts and browser behavior, not screenshots alone. Cover desktop and phone widths, repeated clicks, invalid parameters, missing candidates, blocked later stage, audio switching, refresh, stale results and export parity. Preserve test artifacts and a critique/fix ledger. Stop only on verified completion or specific external blocker; do not claim literal perfection.

## Critique iteration 1 clarifications
- Stage 4 mixed preview is explicitly “Opening pitches + E1 rhythm,” not a completed generated riff.
- Stage 5 partial preview contains only completed pitched phrases, labeled partial; no invented completion.
- Stage 2 source audio is identified as donor reference, not the new scaffold. If only pitch-free source timing is usable, say “Reference rhythm · E1.”
- Upstream Generate applies current drafts for every regenerated downstream step and records each applied snapshot.
- Reachable phone delivery is essential, not optional: unreachable phone/backend is a delivery blocker.
- Backend does not expose arbitrary paths, run files, or secret values. Sessions isolate state; requests validated; no security-setting changes.
