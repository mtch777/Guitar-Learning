# Musical context and voicing choice: next bounded plan

DESIGN ONLY. No inference, fitting, generation, policy change or new source sampling
is authorized by this document. Current frozen trials run unchanged. Existing
failures and development repairs remain separate. Approved detectors stay closed.

## Why the current result is insufficient

Source families now share spacing parameters and exact inverse equations. Fresh
positive choices so far change fingering, not musical spacing. This establishes
physical-choice reuse, not audible voicing creativity or artist understanding.
The pilot locks EACH source member's pitch class, pitch-class multiplicity and
lowest written pitch. Those locks are stricter than preserving a supported chord
identity: they exclude changed doublings and inversions by construction.

Two independent gaps must be addressed, without silently weakening those locks.

| Gap | Smallest next question | What success would establish |
|---|---|---|
| Context-dependent spacing choice | Can source-only local motion/ensemble context predict held-out observed spacing choices better than family frequency? | Predictive evidence for choices already within a declared candidate scope |
| Full voicing meaning and ownership | Can harmonic identity, degree roles, doubling, inversion, bass register and physical realization be distinguished and reversed under explicit alternatives? | A defensible specification for a broader voicing lever; not yet a new policy |

The first cannot solve the second. Better prediction cannot create unseen spacing
support or make prohibited inversions legal. The second cannot justify a preferred
choice merely by giving it a chord label.

## Experiment A: context predicts permitted source spacing

### Fixed scope and preregistration

Use existing inspected development captures 17042/8385538,11714/9188861 and
16453/7421771. Do not draw more songs to obtain a positive result. Freeze capture
hashes, code, complete source-unit/refusal inventory and the proposed dataset
before fitting. All source units remain counted, including no-variety families.
Use the completed support audit as descriptive evidence, not a tuning target.

Keep source-family cardinality, member-PC/bass locks and all timing/expression,
physical witness, open-status, occupancy and incident dependency rules unchanged.
The candidate universe is independently enumerated before model outcomes. Keep
contextually mismatching candidates identifiable as experimental comparisons;
they do not become authorized output choices. Any later choice-policy proposal
requires separate approval of its scope and frozen validation.

### Independent observations and targets

Targets are the observed canonical spacing-definition IDs, joined ONLY after
source features and split assignment are frozen. An observed choice is evidence
of source practice, not the only correct or most beautiful realization.

Use a minimal explicit source-only feature schema: preceding/following written
part pitch-class context, rational onset/duration relationships, metrical position,
nominal ensemble overlap, and known versus unknown execution descriptors. Context
features must exclude the target unit's spacing, frets, selected strings, register
interval vector, target-derived voice-leading distances, detector descriptions
that reveal that spacing, target ID and absolute song position. Neighbor features
may use independently observed neighboring units; do not compute their distance
FROM the target realization and leak the answer. Bass-relative coordinates must
state their gauge. Unknown context stays unknown, never guessed function.

Freeze duplicate/repetition groups from source context with target outcomes
masked. All exact/near repetition members and overlapping context windows belong
to one split group. Split contiguous sections first; remove cross-boundary context
or assign its whole dependency group together. A held-out occurrence's own spacing
and repetitions must not contribute training counts. If grouping leaves too few
independent choices, report INCONCLUSIVE rather than switching to random note folds.
Candidate definitions observed only in test are explicit out-of-support cases.
No test spacing is used to build a train-time choice vocabulary covertly.

### Comparisons and done criteria

Compare a proper family-frequency distribution with a minimal conditional model
using the SAME training targets and candidate support. Fit smoothing/regularization
only on grouped training/validation data, using a small grid frozen before fitting.
No hand-scored cadence, preferred inversion or artist weights. Run one matched
training-context-shuffled control, preserving family and train-only support.
Keep model complexity and total parameter counts visible; do not search a model zoo.

Report coverage, complete eligible/refused denominators, conditional log loss,
Brier score, top-choice agreement and each held-out group/song separately. Report
context help/hurt examples using a deterministic rule fixed before inspecting
outputs. Repeated phrases are not independent significance samples. Source-choice
prediction is not a musical-quality or guitar-domain accuracy benchmark.

PASS_PREDICTIVE_SUPPORT requires better held-out log loss than family frequency
AND the shuffled control, with no hidden support/coverage reduction. Report all
per-song regressions and uncertainty; aggregate improvement alone does not authorize
production. If independent groups or distinct alternatives are insufficient, stop
with INCONCLUSIVE. If the model fails, retain the negative result and do not tune
held-out cases or loosen current safety rules. One frozen study closes this endeavor;
it does not start an unbounded sequence of benchmark variants.

## Experiment B: specify the complete voicing relationship

Prepare the following ownership table and authored/source-backed contrast tests
before implementing any broader musical edit. Do not force a single root or key.

| Variable | Required meaning and evidence |
|---|---|
| Harmonic identity | Explicit source declaration or retained scored/theoretical hypothesis, with vocabulary, missing tones and uncertainty |
| Chord-relative degree | Pinned theory formula including alteration and octave; preserve ambiguous enharmonic/formula alternatives |
| Doubling | Multiplicity of realized degree roles, separate from harmonic template's possible/unplayed tones |
| Inversion | Actual lowest written member relative to the explicit chord-root hypothesis, not a guessed root from bass |
| Bass/register | Independent owned realization coordinates; changing inversion is not automatically an octave-register change |
| Voice correspondence | Source occurrence identity and defensible role mapping; no arbitrary PC-sort correspondence presented as voice-leading |
| Physical execution | String/fret/tuning/capo equations, explicit source joint support and accepted dependencies |

The shared equations remain pitch=root-reference+degree-offset+12*register and
pitch=tuning[string]+capo+fret, with exact original witnesses where the musical
interpretation is ambiguous. A normalized chord-root reference is a coordinate
choice unless independently supported as inferred harmony. Source-observed notes
must never be inserted to fill an unplayed third or erased as a nonchord tone.

Done for this design slice means an exact lock matrix distinguishes: ordinary
spacing change; same chord with changed doubling; inversion with supported root;
bass-register-only change; ambiguous dyad; held nonchord tone; missing third; and
incompatible technique/physical change. Include positive and negative cases.
Each proposed unlocked dimension must state required source/model evidence and
what remains unknown. Existing Tier2 reconstruction and source choices remain the
only inverse authority. No duplicate absolute note stream or late source read.
Broader cardinality/degree reassignment is NOT activated by this document.

## All three QA gates and human boundary

1. Freeze logic and evaluate complete source populations. Future production
   promotion still needs genuinely new random captures, failures retained; existing
   development material is never relabeled fresh.
2. Any implemented relationship must prove exact0 pairwise and complete stripped
   inverse, using the same equations with lower/source/cache access blocked. A
   predictive distribution itself is not claimed to be invertible. Nonzero edits
   separately prove every declared source and relationship lock.
3. Independently verify musical contrast/evidence, ambiguity, support and negative
   cases. A finite schema or correct fret equation cannot certify choice quality.

Only an actual supported audible edit proceeds to GP dependency checks, exact0
render comparison and changed render verification. Listening and human execution
remain genuine later gates; they are not required to run the bounded prediction
or ownership-design work. No claim of artist-wide fit is possible from these few
songs: that requires separately supported multi-song held-out evidence.

Checklist: freeze dataset/features/splits; audit target leakage and support;
run fixed baseline/conditional/shuffle once; publish scoped results; complete the
semantic lock table; independent midpoint/end review; propose any next policy
separately. No implementation or source capture performed for this plan.
