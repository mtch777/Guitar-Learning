# Shared edit contract — G1

This is a verification boundary around existing performance and palm-mute
methods. It does not change generation, technique identification or sampling.

## What is executable

| Boundary | Check |
|---|---|
| Context | Explicit field whitelist; nested target annotations and provenance excluded |
| Request | Integer freedom 0–100; exact representation; conflicting locks refused |
| Support | Known positive rational mass with a named denominator and model seal |
| 0% | Supported representation stays locked; all-zero transaction must be byte identical |
| 100% | Every recorded decision released; coincidental equality is allowed |
| Output | Actual output hash, occurrence identities, retained fields and proposed selection |
| Decision scope | Deterministic release rule, unique units, complete coattacks and directed same-string open-note relationships |
| Preservation | Undeclared GPIF changes, other archive-member changes and comment changes rejected |
| Evidence | GPIF/archive checks distinguished from native playback and musical acceptance |

Representations currently supported: written bend curve, vibrato marker,
directed open-string hammer/pull pair, palm-mute coattack annotation.
Melody function plus relative octave is explicitly unsupported here.

`proposal_context` is an opt-in builder. Existing generators have not all been
rewired through it. Passing an audit does **not** prove that legacy proposal
inputs were isolated from source annotations. Caller-supplied support is not
independently authenticated by the adapter: the real-file experiment separately
verified model-file hashes against the existing pipeline manifest.

## Verification performed

- Six tests: typed target-context perturbation/redaction, refusal cases, disabled
  marker semantics, actual existing-method output with falsified audit claims,
  actual all-zero byte lock, complete coattack/intermediate release mutations.
- Existing private pipeline: 1,225 performance decisions and 911 palm-mute
  decisions checked against their actual stage GP files. Both model hashes
  matched the recorded manifest. Support denominators are explicitly global
  family-weighted eligible mass, **not** conditional-cell counts.
- Expanded read-only check across 12 existing full-freedom cases: 12,799
  performance and 9,635 palm-mute decisions passed the same checks.
- Full local Python discovery: 490 tests run, 489 passed, one optional skip.
  This includes eight previously uncommitted WIP modules/tests; passing discovery
  does not mean those WIP gates have been accepted or delivered.

No new rendering/listening was performed. Presence checks do not verify native
bend curve values, gesture fidelity, HOPO playback or musical quality. Audits
cover reported decisions, not missing-opportunity recall. Private reports and
source-located decisions remain outside Git.

## G1 acceptance

Stakeholder-scope review and developer self-QA passed. Commit b95606b was pushed
to origin/main; CI39255271728 and39255272811 both succeeded.
User retired QABot3000 during this gate; ProjectPlanner3000
remains the sole consulted agent. Historical QABot findings remain actionable,
but no independent engineering acceptance is claimed for this gate. G2 has not started.

Reports include the current method source hash and recorded manifest hash.
They explicitly do not establish that historical execution used that exact code.
Per-decision coverage marks native curve values and directed links pending.

Repeat the private real-file check with `verify_engine_contract.py DIRECTORY
--performance-model MODEL --palm-model MODEL --artist ARTIST --report NEW_PATH`.
It refuses model hashes differing from the recorded manifest and never rewrites
scores or an existing report. Keep source-located reports private.
