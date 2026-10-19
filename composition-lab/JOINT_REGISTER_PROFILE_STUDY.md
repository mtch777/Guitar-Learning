# Does harmony register help predict melody register?

**This frozen source-only model failed its gate. No GP or default changed.**

Predict melody's own written register R from observed harmony's own register A
and tuning offset T. This is a predictive task, not reconstruction of the exact
identity linking vertical distance to those pitches.

## Frozen design

- Same 1,311 known development boundaries, 35 work families, 42 songs;
  953 unknowns retained. Examined development is not a pristine final test.
- 35 leave-one-family-out folds; identical held rows for all methods.
- Family mass 1, equal songs within family, equal known rows within song.
- Shared 128-class register vocabulary; floor 1/2000 per class.
- Independent baseline: `P(R|T)` with one family-equivalent global prior.
- Paired model: `P(R|A,T)` with one family-equivalent tuning-only prior.
- Control: shuffle R within training family/song/T, seed 41907, same hierarchy.
  Keep A/T fixed and preserve every tuning-only baseline prediction.
- Gate: paired NLL and Brier strictly better than both controls, and strict NLL
  wins against both in at least 60% of all families; ties are not wins.

The inventory has 41 exact A/T contexts, 18 supported by only one family (69
rows). No sparse row is dropped. Register vocabulary is for scoring; it is not
a claim that every register is playable on every source instrument.

## Results

| Lower is better | Independent | Paired | Shuffled |
|---|---:|---:|---:|
| NLL | 3.831865 | 3.800093 | 3.917746 |
| Brier | **0.970336** | 0.985421 | 0.980577 |

Paired NLL wins against both: **12/35 families**, below 60%. Brier worsens
against both controls. 25 families regress on NLL or Brier versus independent;
largest increases are 0.835331 NLL and 0.108630 Brier. This does not establish
that every alternative joint model must fail; this candidate is rejected.

Family-weighted joint-context fallback: 5.033%; tuning-level fallback: 2.857%.
The independent baseline never uses joint context: its unseen-joint-context
diagnostic is not an actual joint backoff. That reporting label was corrected
after the first fit; every NLL/Brier result replays exactly, parameters unchanged.

Across folds, 1,193–1,290 training rows are in strata with both variable A and R.
15–41 rows belong to strata whose joint A/R table remains unchanged by shuffle.
Singleton, constant-A and constant-R strata and actual changed targets are
reported separately. A shuffled target order alone does not prove pairing changed.

## Verification / limits

Three targeted tests cover held-family signal, leakage/duplicates, positive
fallback mass, baseline invariance and constant-A shuffle no-ops. Public CLI
replay reproduces every proper score. Separate song-weighted NLL and full-vector
Brier rescoring verifies all 105 fold/method records within 1e-12; it reuses fit
and distribution functions, so it is not independent source-truth validation.

Heuristic roles, selected known boundaries and source coverage limit the claim.
No emotional interpretation, artist fidelity, full-song coherence, playability
or musical acceptance follows. Earlier failed generation gates remain failed.

Private frozen plan, inventory, folds, adverse cases and replay:
`local-artifacts/source-transition-context-v1/actual-context-support-v1/joint-register-profile-v1/`.
