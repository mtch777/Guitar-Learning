# Three required QA gates

Active user requirements. These gates apply together; passing one never substitutes
for another. This document governs future tier work. It does not authorize an engine
or revive the retired architecture. Existing research can continue within its approved
scope, with unimplemented or irrelevant gates explicitly marked NOT RUN.

## The user's musical-abstraction requirement

> we want to balance recreation accuracy, with abstraction in the right direction.
>
> so the question is: how can we capture the previous tier with so much fidelity that it is re-creatable with perfect accuracy? while abstracting it in a way that captures the next level of musical abstraction in a way that is musical and emotional and theory based and taking steps towards a more conceptual musical artist's abstracted theory of mind?

## Gate 1 — New-song portability

**Question:** Does unchanged logic handle genuinely new input?

- Freeze the sampling rule, exclusions, seed and selected capture/revision. Pin
  input, code, model and configuration before inference. Declare novelty limits;
  a new capture is not proof of absence from external model pretraining.
- Run the same code/configuration. Verify source occurrences, exact time,
  identities, track/voice, relationships, techniques, field coverage and unknowns
  against the actual source—not merely another model or a report's row count.
- Preserve every failure and missing-evidence outcome. No replacement song,
  selection after seeing output, song-specific patch or silently invented value.
- If annotations are absent, portability may still be tested, but interpretation
  accuracy is UNTESTED. Missing chord symbols are not a failed song and do not
  justify skipping the rest of its source data.

**Required evidence:** frozen manifest, source coverage/diff, unknown/loss inventory,
failure history and actual commands/results. Existing frozen cases provide regression
tests; a fresh case provides a separate portability test.

## Gate 2 — Same-relationships exact reversal

**Question:** Can the retained higher representation reconstruct the removed lower
representation using the SAME relationships?

- For every tier boundary, declare exactly which source/lower fields must return.
  Test pairwise boundaries and the composed path through all implemented tiers.
- Physically remove lower payloads from the test input. In a separate worker,
  deny access to original files, lower-tier copies, caches, network and hidden
  side channels; retain only the upper input, declared lever/configuration values
  and versioned shared relationship code. Configuration must not hide original
  notes, target outputs or source-derived answers. Pin all variation controls at
  0% for the exactness test; do not rely on an implicit default.
- Solve the same relations used in analysis. No separately authored musical
  reconstruction rules, guessed notes, fallback generator or raw event-stream
  copy disguised as residual parameters.
- Retain explicit realization parameters where an abstraction admits several
  possible lower realizations. Explain each parameter's role; an upper label
  alone cannot magically recover choices it discarded.
- Independently compare identities, rational onset/duration, pitch/fingering,
  tracks/voices, rests/ties, curves/techniques, structure and metadata in the
  declared scope. Preserve missing/null/false distinctions. Unsupported fields
  remain OPEN; a partial pass must name its field/tier limits.
- At 0% variation, locked dimensions must equal the source. Nonzero variation
  does not waive the zero-control exactness check.

**Required evidence:** stripped input, actual I/O-denial tests and read audit,
shared-relation version/hash, reconstruction output and independent field diff.
Describe the isolation actually achieved; a Python read hook is not an OS sandbox.

## Gate 3 — Meaningful musical abstraction

**Question:** Does each analysis tier add musical meaning and relationships while
retaining enough information to recreate its previous tier exactly?

Before implementing a tier, write its musical contract:

| Contract item | Required answer |
|---|---|
| Musical question | What can a musician understand here that the previous tier did not express? |
| Allowed input | Which immediately preceding representation is the sole data input? |
| Relationships | Which musical relations are added, and which source occurrences/times support them? |
| Ownership and abstraction | Which lower fields are removed or transformed; what does each retained anchor/choice parameter mean; how are duplicated lower payloads and replay ruled out? |
| Evidence | Which real source cases support the interpretation; which contradict it or admit alternatives? |
| Exactness | Which shared relations and explicit choices recover every required previous-tier detail? |
| Uncertainty | What is observed, inferred, ambiguous, missing or not observable from notation? |

Review actual data, not just the contract:

- Walk a real occurrence upward through every implemented tier and back down.
  Every higher claim must be traceable to preceding-tier evidence and source time.
- Show a newly expressible musical relationship: e.g. chord versus bass and
  voicing; a note's relation to key/current harmony; a motif's transformation;
  a supported call/response; a context-conditioned relationship across songs.
  A new container, higher-level name, ID lookup, compressed note template or
  algebraic coordinate change alone does not earn an analysis tier.
- Include contrasting and ambiguous cases. A repeated pitch set is not proof of
  identical harmonic function; a changed note is not automatically a chord change.
  Preserve competing interpretations rather than force a convenient label.
- Check interpretations against actual source evidence. Two models agreeing,
  a successful inverse or syntactically valid JSON does not validate meaning.
- Inspect reconstruction parameters for disguised lower-tier copies. Inspect
  abstractions for discarded details or unsupported labels. Both are failures.
- Separate musical function from claims about emotion or artistic intent.
  Do not infer a composer's feelings from notation as fact. Use source/audio/human
  evidence where needed, and mark judgments requiring listening as UNVERIFIED.
- Automated checks can validate references, time alignment, field coverage,
  contradictions and declared musical examples. They cannot certify emotional
  meaning or artist fidelity. Planner must challenge that qualitative claim;
  listening-dependent acceptance remains a separate, explicit human judgment.

T0 is preserved source; T1 is faithful extraction. Do not invent interpretive
meaning in those tiers just to satisfy Gate 3. The increasing-musical-abstraction
requirement applies to analysis tiers above them.

**Required evidence:** musical contract, real source-to-tier-to-source trace,
source-backed contrasts/counterexamples, reconstruction evidence and Planner verdict.

## When the gates run

| Point in the work | Required action |
|---|---|
| Before a new endeavor/tier | Developer and Planner agree the musical question, scope, source cases, inverse obligations and acceptance evidence. Gate 3 is a design gate, not an end-of-project decoration. |
| After each relevant code/schema change | Run affected regression and reversal checks; inspect changed musical output against the contract. Do not wait until the complete system exists. |
| Midpoint; about ten substantive working steps | Planner inspects real intermediate artifacts, scope drift, failures and missing evidence. Check sooner when an assumption or requirement changes. |
| At the first usable end-to-end version and each major revision | Run a fresh frozen song plus the existing regression set; run isolated pairwise/composed reversal for implemented scope; review musical abstraction on real cases. |
| Before calling a tier/feature complete or promoting it into the active design | Developer and Planner report ALL THREE statuses separately, with evidence. Unknown/unimplemented checks are NOT RUN, not PASS. User listening is required only for claims that actually depend on it. |

Do not fetch a new song after every tiny edit. Reuse frozen cases for targeted
regression; use a fresh, preselected case at meaningful end-to-end checkpoints.

## What failure stops

- FAIL or NOT RUN blocks claiming completion of the affected tier/scope and
  promoting it as a verified foundation. Passing old codec tests cannot bypass
  the musical-abstraction gate.
- Diagnose and repair the failing assumption; preserve counterexamples and
  recheck previously working cases. Continue independent authorized work.
- Do not hide a failure by relabeling it PASS, shrinking scope silently, copying
  the removed payload, picking easier examples or adding a song-specific fix.
- A research experiment may finish with an honest negative/inconclusive result.
  That is completion of the experiment, not completion of a musical-analysis tier.

## Review record required at checkpoints

For each gate record: status (PASS / FAIL / NOT RUN / INCONCLUSIVE), exact tier,
fields and song scope, commands, evidence paths, counterexamples, unresolved
questions, Planner verdict and next action. No combined green percentage.

## Current truth

2026-10-22 QA implementation authorization supersedes the earlier documentation-only
scope for QA machinery. See QA_IMPLEMENTATION_PROGRESS.md. Executable source checks
and fail-closed evidence guards now exist; the actual active inverse, full ownership/
forward-isolation adapters and musical adjudication are still missing. The runner
exposes those gaps rather than claiming all three pass. Overnight continue schedule
is active. No new engine or retired-codec foundation is implied.

The new engine remains paused. Historical reversible codecs were retired as an
active foundation; their results do not establish Gate 3. Current external-method
research has source-backed diagnostics but still exhibits missed musical changes.
No new complete tier chain or full inverse is claimed to pass these three gates.
This policy is enforced through work instructions and review; it is not a claim
that all automated gate runners already exist.

## Policy installation checklist

- [x] Define all three gates, evidence, cadence and failure consequences.
- [x] Link active handoff/context/reset and historical QA entry point to this policy.
- [x] Verify four active references, user quote and required sections by script; all assertions passed.
- [x] ProjectPlanner3000 final challenge/review; tightened explicit zero-control/configuration isolation and parameter ownership to prevent hidden source answers or renamed lower payloads.
