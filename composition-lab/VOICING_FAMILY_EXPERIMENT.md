# Preregistered voicing-family experiment

Status: bounded ownership/policy IMPLEMENTED, results in VOICING_FAMILY_PROGRESS.md.
Actual audible spacing and full creative-lever acceptance remain OPEN. The
preregistered protocol below remains the record of the experiment after6359eb4;
failed trials and earlier source-witnessed policies are preserved unchanged.

## Question and fixed development material

Can one shared, transposition-equivariant relationship reuse an observed joint
voicing/fingering at a different written pitch level while preserving the target's
harmonic pitch classes, bass register, source timing and execution dependencies?
This tests reusable musical structure, not artist fidelity or reliable chord naming.

Use ALL source units in these existing, already inspected captures, with no chosen
favorable passage and no new random sampling during development:

| Material | Source identity | Role |
|---|---|---|
| Under Pressure | 17042 / 8385538 (execution-dependency-fresh-v1/case-1) | Negative/support-limited development case |
| Over The Hills And Far Away | 11714 / 9188861 (execution-dependency-fresh-v1/case-2) | Previously observed spacing-family development case |
| Satisfaction | 16453 / 7421771 | Historical audible-change and physical-refusal regression |

Resolve each capture from its existing selection manifest; persist the exact
revision, canonical capture path, complete file inventory and SHA256 values in a
new experiment manifest BEFORE counting candidates. Ambiguous paths or identities
block execution. These sources can never be reported as fresh validation.
The completed joint-fingering-fresh-v2 cases (307 and 2482) remain sealed results;
they are not additional training or selection sources for this experiment.

## Owned representation and equations

One complete Tier1 input and the existing connected Tier2 remain authoritative.
No raw source object, absolute donor note list or second pitch stream is added as
an inverse fallback. A family stores its shared normalized relationship once;
occurrences retain source references, original correspondence and necessary
realization choices. Existing source facts retain exact notation and metadata.

Declare the exact ownership migration before implementation: a shared spacing
definition owns each relative-interval vector; an occurrence owns its definition
reference, bass anchor and reversible member permutation. If those replace current
per-member `voicing_interval` scalars, remove the old owners rather than keeping
both representations authoritative. A derived lookup table alone does not satisfy
this abstraction gate. The stripped inverse must recover the removed interval
owners through these same family equations before reconstructing Tier1.

For an eligible simultaneous unit, define b=min(known member MIDI pitches).
This is the lowest WRITTEN pitch, not a performed bass, chord root or tonic.
Family coordinates are r_i=p_i-b, with multiplicity and relative register retained.
The harmonic condition is the multiset of r_i modulo 12, not merely a set.
The shared musical equation is p_i=b+r_i in BOTH directions.

Correspondence must not sort absolute pitch classes: that breaks at C/B wrap.
Order slots by (relative pitch class modulo 12, relative pitch, original source
address as a tie witness). Equal pitches remain separate occurrences. Preserve
an explicit reversible slot-to-source-occurrence permutation; never infer voice
identity from list order or discard duplicate members. Target and donor slots
correspond by relative class and within-class register rank. This is an explicit
voicing correspondence, not a claim of melodic voice-leading identity.

Initially register is LOCKED: b_target stays exact. Voicing and physical choices
may be released together. A donor's relative spacing supplies r_i; target pitches
are b_target+r_i. Thus the translation Delta=b_target-b_donor is determined by
observations, never selected as a hand-picked offset. No pure transposition of the
whole target or independent melody, duration, rhythm or expression edit is allowed.

## Context is normalized, not dropped

Retain the current incident-policy full/local alternatives and their documented
backoff ordering. Preserve part/instrument, cardinality, durations, actual meter,
metrical position, target refusals and same-part uncertainty veto. Compare exact
normalized descriptors; do not pool unlike contexts after seeing results.

Normalize EVERY pitch-bearing context feature using that unit's b, including
other-part nominal overlap PCs and full-context previous/next units. Use modulo
12 only where the existing descriptor means pitch class; preserve register in
features that originally carry register. Keep overlap rational timing, lengths,
sourcebar boundaries, missingness, uncertainty kinds and multiplicities unchanged.
Identity references authenticate observations but are not equality features.
Do not drop uncertain other parts or convert nominal evidence into sounding truth.
Require an explicit feature-by-feature context schema and independent oracle.

## Transferable physical witness

An admitted donor must be an observed WHOLE simultaneous joint shape, not a
Cartesian combination of individual notes. Require the same instrument identifier,
exact tuning array and capo. Use its complete slot-aligned string assignment.
For each member use the SAME equation p_i=tuning[string_i]+capo+fret_i.
The proposed fret is donor_fret_i+Delta and must equal the pitch equation exactly.
No manual fret patch, anatomy bound or source-observed maximum is a physical law.

Require integral valid strings/frets, nonnegative frets and each explicit positive
integer declared fret limit (both authentic donor validity and target validity).
Unknown bounds stay unknown; they do not certify playability. Preserve source open
status for this first experiment: donor fret zero iff translated fret zero. A
closed-to-open or open-to-closed transfer is rejected explicitly, not silently
claimed to preserve the same execution. This is a conservative declared support
restriction, not a universal prohibition on such playing.

Target incident pins protect pitch AND string. Reject newly occupied same-part
strings using nominal source overlap; recompute the complete accepted tie graph
and global execution-dependency signature after realization. Keep all original
refusals and unresolved states. A direct translated shape witness supports geometry,
not human comfort, acoustic equivalence or suitability in every context.

## Persistent checklist and acceptance gates

- [ ] Freeze the three capture identities, all relevant source/code files, context
  schema, controls, deterministic draw seeds and analysis scope before execution.
- [ ] Implement shared family forward/reverse relationships and exact slot ownership.
  All0 reconstructs complete stripped Tier1 with original typed facts/order, with
  source, lower payloads and derived caches unavailable to the audited worker.
- [ ] Prove equivariance on authored examples across all 12 pitch-class wraps,
  duplicate/unison classes and different valid register shifts; prove inverse
  permutation and exact source reconstruction. Invalid geometry remains a refusal.
- [ ] Independently enumerate ALL units, family memberships, context comparisons,
  donor links, exclusions and translated joint witnesses in each development song.
  Partition pure repetitions, pure source transpositions, distinct spacing choices,
  context rejection, pins, opens, occupancy and declared-bound failures.
- [ ] Freeze 20 seeds 9427..9446 and controls (voicing,register,physical)=(0,0,0),
  (50,0,50),(100,0,100), plus separate-release lock tests. Retain coincidences and
  all no-choice outcomes; do not seek a different seed or target to force change.
- [ ] Independent changed-output audit: only selected fret/string facts may change;
  source occurrence/time/voice, member PC multiplicity, bass anchor, expressions,
  other parts, accepted ties and dependency signatures remain locked. Corresponding
  derived pitch parameters change only through the shared equations.
  Authenticate each mapped target member's original pitch class individually;
  a matching unordered pitch-class multiset cannot excuse swapping note identities.
- [ ] For an actual supported development change, verify GP pitches/strings and
  dependent leaves, exact0 GP/render baseline, and actual rendered consequences.
  Physical-only coincidence need not sound different. Human listening/playability
  remain separate, explicitly unpassed judgments.
- [ ] Only after code and these tests pass, preregister TWO genuinely new random
  captures, exclusion set and code freeze. Run all three bounded QA gates unchanged;
  retain failures and no alternatives. Do not count synthetic or development
  positives as fresh musical validation.

Required negative contrasts: wrong normalized neighboring harmony; wrong meter or
metrical slot; changed other-part uncertainty; duplicate-member permutation loss;
per-note witnesses without a joint shape; changed tuning/capo; fractional/negative/
out-of-range frets; open-status crossing; occupied strings; incoming/outgoing ties,
HP/slide/roll dependencies; scalar/source/cache fallback; register0 bass movement;
physical0 string reassignment; stale cached family/context assertions. A changed
source key declaration alone is not automatically a harmonic mismatch unless the
predeclared context contract explicitly uses that declaration.

## Done and failure meanings

A bounded implementation is complete only with verified ownership, independent
candidate accounting, exact0 and lock proofs, source-backed musical contrasts and
unchanged frozen runs. Positive fresh creative acceptance additionally requires an
actual supported nonzero fresh result; zero alternatives leave that gate OPEN.
If the strict family model still offers no alternatives, report which exact support
stage blocks them and stop this experiment. Do not relax context, open rules or
physical evidence after outcomes. Any next hypothesis needs a separately frozen
comparison. This experiment does not close key/mode/function accuracy, all creative
levers, human playability, artist style or whole-song generation.
