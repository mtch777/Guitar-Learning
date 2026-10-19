# Conditional harmony: first generation feasibility test

**Failed before export. No candidate GP, listening result or default change.**

The source prediction study passed its own frozen gate; this separate experiment
tested its use in generation. It replaced the historical chosen-track prior with
the population conditional prior, so it changes both prior and conditioning.
Source-pattern voicings, rhythm, recurrence, form and common random uniforms were
fixed. Melody, bass, performance and all other musical dimensions were locked.

## Acceptance checklist and observed results

| Requirement | Result |
|---|---|
| Recover every historical draw and original harmony | **Pass:** all 658 draws; entire unarranged harmony including fingering exact |
| Audit real baseline context support | 261/658 exact contexts absent (39.7%); 503 reused attacks counted separately |
| Preserve exported chronological history | Baseline preflight passes: 618 active decisions, 557 copied attacks; 40 sampled decisions not exported |
| Unknown initial/post-gap context uses marginal | Frozen amendment before candidate; implemented separately from missing-key backoff |
| Generate without rerolling or widening fit rules | **Fail:** decision 540 cannot fit; aborted, no candidate export |
| Target-hidden equivalence, complete candidate history, GP/native locks | **Not reached**; unit-level redaction is not the complete experiment proof |
| H-distribution improvement and D-distribution nonregression | **Not reached**; no complete score to measure |
| Below-open/refit guardrails, copy audit, equal-renderer playback | **Not reached**; no successful candidate |

At bar 108, local onset 7/4, previous root 60 and voicing [0,1], missing context
(register 28, span 1) triggered the frozen marginal fallback. Common uniform
0.999725460039629 selected step +101: target 161. None of the unchanged octave
shifts from -5 through +5 could fit it. The diagnostic replay changed no policy
or draw and preserved all 539 completed decisions plus the failed decision.

Step +101 occurs **zero times** in the 55,972 observed transitions. The frozen
255-category smoothing floor assigned it probability 0.000010177599104370268.
Exhaustive step checks at this one failed state found total infeasible mass
0.0009465167167064354. That is a state-specific probability, **not** a whole-run
failure rate. Previous fingering affects motion preference, not whether any
fingering exists under these constraints.

## What this establishes

The historical reconstruction is exact. The prediction distribution contains
actions that a generator cannot realize under its fixed mechanical constraints.
This failure does not invalidate the source-held-family prediction results,
establish artist fidelity, identify the best remedy, or justify silently
renormalizing the failed experiment. Any feasibility-conditioned sampler needs
its own frozen experiment, explicit changed-distribution accounting and review.

Private evidence: `local-artifacts/source-transition-context-v1/actual-context-support-v1/`.
No commercial scores, source rows or generated audio are published here.
