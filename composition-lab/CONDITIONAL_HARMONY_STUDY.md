# Source conditional harmony-step study

## Question and frozen scope

Do observed jumps depend on their starting register and requested voicing shape?
This is a source-population relationship test, **not** a comparison against the
historical sampler's chosen-track prior, free generation or artist feel.
No generator integration or GP output is included in this study.

Accepted composer/report data supplies written harmony-minimum transitions.
Starting register is relative to the source instrument's lowest open string.
Voicing span is transposition-invariant and available before the step draw in
the historical consumer: the source pattern/event shape is selected first.
Destination root/absolute pitch is never an input feature. Roles/minima remain
written proxies; there is no inferred functional harmony or emotional meaning.

## Denominators and support

| Selected-model inventory | Count |
|---|---:|
| Adjacent root pairs | 61,030 |
| Rest/gap/invalid-bar discontinuities | 4,895 |
| Changed section instances | 163 |
| Eligible transitions | **55,972** |
| Development families / songs / tracks | 49 / 60 / 122 |
| Exact register/span contexts | 364 |
| Contexts seen in only one family | **170** |

Every selected track's historical step counter reconciles exactly; included
roots, shape, clock and duration reconcile with accepted source events. Other
exclusion categories are explicitly zero **within this already-selected model
layer**. That does not mean the raw corpus has no unknowns or omitted material.
Examined outer held-out songs were not used. Families are work/version groups,
not49independent artists or independent-sample confidence.

## One candidate; two controls

- Population control: global step marginal with equal training-family mass,
  equal songs within family and equal eligible transitions within song.
- Conditional candidate: exact `(origin register, requested voicing span)`
  step counts, with one family-equivalent prior of the population distribution.
- Shuffled control: same conditional method; jointly shuffle the two training
  context fields within family/song, fixed seed41907. Labels/marginal weights
  and context support stay the same.

All use the same255MIDI-valid step vocabulary (-127…127), fixed per-step
population pseudocount1/2000, identical49leave-one-family-out folds and evaluation
rows. All backoffs remain in scoring. The operational screen was frozen before
fit: strictly lower aggregate NLL and Brier than both controls, plus NLL wins
against both on at least60%of all49eligible families; exact ties are not wins.
This is a developer-proposed research screen, not a user musical requirement.
No bins, priors or gate values were tuned after results.

## Results

Lower is better. Averages weight each held family equally and its songs equally.

| Measure | Population marginal | Conditional | Shuffled context |
|---|---:|---:|---:|
| NLL | 1.901904 | **1.592610** | 1.884615 |
| Multiclass Brier | 0.531293 | **0.476466** | 0.519862 |
| Below-open probability | 0.081692 | 0.046649 | 0.082579 |
| Destination-register TV | 0.247929 | 0.216743 | 0.251673 |

**47/49families win on NLL against both controls. The operational gate passes.**
Weighted absent-context/backoff rate is7.5501%for the conditional methods.
Below-open probability is a mechanical-support diagnostic; register TV uses
teacher-forced observed starting states. Neither is a musical-quality score.

Adverse cases remain: two families regress on NLL against controls, and two
other families regress on Brier. Largest NLL increase versus population is
0.037828; largest Brier increase0.024383. One adverse family has29.86%backoff;
another contains only63transitions. Sparse support is not hidden by averaging.

## Reproduction and QA

`source_harmony_transitions.py COMPOSER.json REPORT.json PRIVATE_OUTPUT.json`
recreates the exact source inventory with explicit exclusion categories and
input/code seals. The extractor writes an **object** containing `events`, `inventory` and seals.
The study runner expects the **events array alone**, in a separate file. For the
preserved study, this exact conversion reproduces the frozen input bytes:

```python
import json
from pathlib import Path
root = Path("composition-lab/local-artifacts/source-transition-context-v1")
inventory = json.loads((root / "public-inventory.json").read_text(encoding="utf-8"))
target = root / "reproduced-events.json"
if target.exists():
    raise FileExistsError("Preserve prior input")
target.write_text(json.dumps(inventory["events"], separators=(",", ":")), encoding="utf-8")
```

Pass `reproduced-events.json` as `EVENTS.json`, not `public-inventory.json`. `conditional_harmony_steps.py
EVENTS.json FROZEN_PLAN.json PRIVATE_OUTPUT.json` runs the fixed study. Private
plans/events/models/identities remain under ignored `local-artifacts`.

Public extraction reproduces all55,972original events exactly. All49fold row
counts/aggregate means reconcile. Weighted NLL, full-vector Brier and backoffs
were independently re-scored for all four adverse families × three methods;
fit/distribution helpers were reused, so this is not independent model/source
truth verification. Focused tests cover leakage, weights, support/backoff,
shuffling, serialization, exact rational duplicate identity, counter/duration
joins, partition refusal and a synthetic context signal.

The first serialization test compared integer versus JSON string metadata keys
instead of prediction equality; its assertion was corrected without changing
probabilities. A later input guard normalizes rational duplicate identities.
The original fitted code/results are retained; the sealed replay reproduces
all original numerical results exactly. Neither change retunes the candidate.

## Next boundary

Passing supports a contextual relationship. Before any separate one-core GP
pilot: inspect support at actual historical decision states, preserve the exact
historical baseline/common pattern draws, declare a population-conditional
replacement versus track-marginal baseline honestly, and freeze joint-context,
fit/refit, backoff and adverse-event checks. Melody/bass/rhythm/form remain locked
unless explicitly declared otherwise. Existing failed G6studies stay unchanged.
No default or musical promotion follows from this study.

ProjectPlanner3000 reviewed START, inventory MIDPOINT, results and END. Bounded delivery accepted pending publication/CI; planner inspected code/tests/saved records, without independently rerunning them. Developer owns technical QA.
