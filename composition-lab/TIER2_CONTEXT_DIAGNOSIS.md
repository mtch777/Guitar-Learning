# Tier2: where musical interpretation still fails

The reversible interface works for its declared fields. Tonal interpretation
remains unresolved. This diagnosis changes no model, score, parameter or prediction.

## Actual evidence

All three previously frozen, aligned Bach references remain in the evaluation.
Every interval of their common source/reference support is counted exactly once.
The014reference retains its documented edition offset and contradictions; these
are analyst-label comparisons, not universal harmonic truth or guitar-style proof.

| Reference | Evaluated duration | Best possible agreement with one key per measure | Current window4 agreement |
|---|---:|---:|---:|
| 004 | 40quarter notes | 36 | 21 |
| 010 | 52quarter notes | 42 | 36 |
| 014 | 56quarter notes | 54 | 53 |

The middle column is an oracle representability ceiling, not an achievable model
result. Intra-measure key changes are a real limitation, but do not explain all
disagreement. Neighbor smoothing helps010/014and hurts004; no window was tuned.

| Outcome, window4 | 004 | 010 | 014 |
|---|---:|---:|---:|
| Key and chord uniquely agree | 19 | 32 | 38.5 |
| Chord agrees; key differs | 15.5 | 10.5 | 2 |
| Key agrees; chord differs | 1.5 | 0 | 4.5 |
| Both uniquely differ | 0.25 | 0.5 | 0 |
| Ambiguous or unknown | 3.75 | 9 | 8 |
| Reference chord outside vocabulary | 0 | 0 | 3 |

Units are quarter notes. Categories are exclusive, with vocabulary/uncertainty
taking precedence. Consequently, “chord agrees; key differs” is **not all key
disagreement**: uncertain/unsupported intervals may also have tonal disagreement.
All globally optimal harmonic alternatives are retained, not just a display path.

Earliest source-clock examples are selected mechanically for every observed
class/window. Each includes actual XML notes, literal tie tags, all covering
harmonic labels and raw/neighbor tonal contributions. Literal XML ties are
inspection evidence; the current XML adapter does not reconstruct those tags.

## Concrete missing relationship

Opening010: the E7 chord agrees with the analyst reference, while raw local
pitch-duration evidence favors E major over the reference's A-minor context.
Neighbor smoothing selects A minor, but that does not establish that it understood
E7's function. Chord identity and pitch inventory do not determine tonic/function.

The controlled counterexample makes the limitation reproducible:

| Controlled passage | Pitch-duration inventory | Current tonal scores | Ordered harmony |
|---|---|---|---|
| A minor → E7 → C major | Same | Same | Retained |
| C major → E7 → A minor | Same | Same | Different and retained |

Both passages occupy one3/4measure. All48global and24raw/smoothed temporal scores
are identical. Their harmonic alternatives distinguish the order. An independent
harmonic arithmetic oracle and actual stripped-input workers pass for both.
These authored fixtures assert **no true key, preferred order or emotional intent**.
They are not generation rules or training material.

## What this supports—and what it does not

**Supported:** current tonal evidence discards within-measure order. Existing
harmonic analysis retains order, but it is not consumed by the key scorer.

**Not established:** a correct functional interpretation, a replacement scoring
factor, a learned transition distribution, or proof that adding order alone fixes
the reference disagreements. Do not introduce an E7→A-minor rule or combine raw
correlations as if they were calibrated probabilities.

Repeatable scripts: `diagnose_tier2_joint_errors.py` and
`run_tonal_order_challenge.py`. Complete private results, source/producer hashes,
earliest examples and qualified reference details remain in ignored
`local-artifacts/joint-error-diagnosis-v3.json` and `tonal-order-challenge-v1/`.
This is additional diagnosis, not a new random-song gate or a new accuracy claim.
