# Voicing semantic ownership and lock contract

2026-10-26 — Experiment B contract. Companion to
MUSICAL_CONTEXT_CHOICE_PLAN.md. No production changes or broader creative scope
are activated here. Current family-policy locks and sealed trials remain intact.
The bounded checked interface is now implemented in `voicing_semantics.py`;
production pitch ownership and creative policies are unchanged. Actual results
and remaining implementation gates live in `CONTEXT_PREDICTION_PROGRESS.md`.

## Requirement and present limit

The goal is a source-supported musical choice realized backward through the SAME
relationships, not an assistant-selected offset or a second note generator.
Current families own bass-relative spacing, with complete exact0 reconstruction.
They preserve every member PC, multiplicity and lowest written pitch. Positive
fresh choices to date are fingering changes, not audible spacing changes.
A full voicing lever needs explicit harmonic and realization ownership beyond
those conservative locks. Experiment A may establish contextual prediction within
an allowed scope; it cannot supply these missing semantics or authorize them.

In the current interface, `harmonic_hypotheses` locks only the declared assumption
set. `observed_formula_support` separately locks which hypothesized chord tones
are present; `formula_membership` locks each occurrence's member/nonmember status.
None establishes that a theory-compatible chord is the actual intended harmony.

## One authority for each quantity

| Quantity | Owner and evidence | What it does not establish |
|---|---|---|
| Harmonic hypothesis | Source declaration or existing scored/theoretical context node, exact scope/time and provenance; alternatives retained | True root, key, intention or function merely from a template fit |
| Harmonic template | Pinned theory definition: root PC, formula degree/alteration, expected template PCs | That every template tone was played, or that an incomplete subset identifies a unique chord |
| Realized degree assignment | Per original occurrence, a conditional degree/formula slot under a named hypothesis; unmapped notes explicit | Authored enharmonic spelling or chord membership for every note |
| Doubling pattern | Multiplicity of REALIZED assigned degrees, including explicitly unmapped notes | Template cardinality; an absent fifth is not a deleted source note |
| Spacing/register | Shared interval/register relation and original occurrence correspondence | Harmonic identity or melodic voice-leading from sorted PC slots |
| Inversion | Derived lowest written pitch's degree under the named root hypothesis; ambiguous/unknown as needed | Root inferred from lowest pitch; a unique inversion when bass is nonchord or tied between roles |
| Bass register | Actual lowest-written-pitch coordinate; separate register lock | Performed bass line, tonic or acoustic sustain |
| Physical realization | Owned strings/tuning/capo, shared pitch–fret relation, whole-shape source support and incident dependencies | Human comfort, timbre or optimal fingering |
| Source notation/execution | Existing exact typed owners, ties, declarations and retained detector relationships | Unwritten attack, duration, bend or harmonic sounding pitch |

Harmonic identity is an EXPLICIT contract: named root/formula hypothesis and its
scope, separately from realized degrees, omissions, added/unmapped tones, bass
and spelling. If changing the root/formula is forbidden, no alternate hypothesis
may silently be selected to excuse a result. Template compatibility or completion alone is not grounded harmonic identification; independent source/context evidence and its uncertainty must accompany any such claim. Conditional alternatives can disagree
about inversion or role. Report all retained alternatives or constrain a clearly
named subset; do not claim universal preservation from one convenient witness.

## Shared equations and inverse boundary

For a mapped pitched member i under hypothesis h:

    p_i = root_reference_pc(h) + theory_offset(h, degree_i, alteration_i)
          + 12 * register_i
    p_i = tuning[string_i] + capo + fret_i

Theory offsets retain unwrapped formula distinctions (e.g. diminished seventh
versus sixth, ninth versus second). Fix the formula/register gauge canonically;
do not allow a +12 degree offset and -1 register ambiguity to create dual owners.
The original octave/register witness reconstructs exact pitch, not a guessed tonic
register. Existing bass-relative equation p_i=b+r_i remains the current authority
until a separately tested replacement is adopted; do not retain both as independent
editable pitch stores. A derived coordinate view is checked, not used as a fallback.

Unmapped, fractional, unknown and nonpitched members retain their existing honest
ownership/refusal. No fabricated degree or hidden raw-pitch residual may bypass
the relationship contract. Exact source observations must survive regardless of
whether a harmonic interpretation is established. Uncertainty cannot mean data loss.

An ownership change must remove the replaced lower parameter, retain only necessary
realization witnesses once, and prove exact pairwise plus composed source recovery.
Higher operations take preceding input only. No raw-file lookup, lower-note cache,
serialized answer, late chord-parser result or separate rendering generator may
repair a failed inverse. Candidate probabilities are evidence for choice, not
claimed invertible meaning. The same algebra realizes zero and supported changes.

## Distinct controls and required dependencies

| Proposed release | Quantities allowed to change | Locks that must be stated explicitly |
|---|---|---|
| Spacing | Member octave placement/relative intervals, within the admitted scope | Harmonic hypothesis, occurrence IDs/cardinality, member role/PC multiplicities, bass register, timing and expression |
| Doubling | Assignment/multiplicity of realized chord degrees | Harmonic hypothesis; occurrence cardinality unless separately unlocked; source voice identity, melody/bass role locks and physical execution |
| Inversion | Which supported chord degree occupies the lowest written position | Root/formula hypothesis, treatment of unmapped bass, bass-register policy, doubling and melody locks |
| Register | Named member/group register coordinates | Melody octave versus function, inversion, bass, physical and cross-part locks independently |
| Fingering | Strings/frets derived from unchanged or explicitly changed pitches | Musical pitch/role locks, tuning/capo, incident execution semantics and overlap occupancy |

These are not five new automatically approved sliders. Current pilot releases only
its existing narrow choices. A request that changes inversion while preserving
literal lowest pitch may be impossible. A held melodic degree/octave lock may
conflict with changed doubling. Return a typed conflict; never apply silent priority.
Original occurrence count stays fixed in the minimum scope: doubling changes
reassign allowed occurrences, not insert/delete note events. Event creation/removal
would require a separate topology and rhythm contract.

## Eight mandatory contrast cases

These are controlled requirements tests, not claims that the alternatives sound
equally good. Match them with actual source witnesses before admitting proposals.

| Case | Positive relationship to verify | Negative/refusal or ambiguity to preserve |
|---|---|---|
| 1 Ordinary spacing | C/E/G and C/G/E in different octave placement can retain the same named C-major hypothesis and degree multiplicities, with fixed bass where requested | No arbitrary transposition or member-PC/voice reassignment under current locks; cannot infer melodic voice continuity from sorting |
| 2 Changed doubling | At fixed event count, C/E/G/C versus C/E/G/G can share the explicit C-major hypothesis but have different degree multiplicities | Current member-PC/multiplicity lock correctly REFUSES; a future doubling release needs role mapping and source support |
| 3 Supported inversion | C/E/G versus E/G/C can have the same named root/template, different inversion and register realization | E/G/C does not prove C is the root; retain alternatives, and refuse if bass register or melodic pitch locks conflict |
| 4 Bass register only | A named bass occurrence can move by an octave through the same degree/pitch equation, with clearly scoped accompaniment locks | If it ceases to be the lowest note, inversion/bass-status may change; recompute or refuse rather than claim unchanged inversion |
| 5 Ambiguous dyad | C/G retains two source notes and its explicit compatible hypotheses, not a fabricated third | No forced major/minor, tonic or function; insufficient evidence can block harmonic-identity edits without blocking exact0 |
| 6 Held nonchord tone | A tied C can remain exact while its membership changes under two compatible harmonic contexts | Preserve actual chain, clocks and joint harmonic paths; do not erase/retune it to complete a chord or assert suspension intent |
| 7 Missing third | A source root/fifth or E/G/D subset lists observed notes and hypothetical missing tones separately | Never add an unplayed B/Bb to distinguish Em7/G6/half-diminished alternatives; template completion is not performance |
| 8 Execution conflict | A supported change to untied members may coexist with a pinned tied/HP/slide endpoint; whole source shape validates string/fret equations | Reject broken links, unresolved-status changes, occupied strings, uncoupled SPN, invalid frets or unsupported open transitions; no source-span anatomy rule |

For every case record hypothesis IDs, source occurrence/time refs, lock vector,
original/changed coordinates, allowed fact paths, uncertain/unmapped observations
and expected result. Positive and negative branches must be exercised independently.
No manually selected real-song example substitutes for frozen population accounting.

## Practical minimum audible scope

Begin with a source-supported SPACING change at fixed cardinality/member PCs and
bass register, with current technique/timing/expression locks. Explicitly condition
any chord-degree view on retained harmonic evidence; do not claim full inversion
or doubling control. Use a whole observed/legitimately translated joint shape and
existing equations, with all physical refusals retained. The software selects
from admitted evidence under frozen logic and seeds; the assistant does not choose
an interval, donor or target for a musical demonstration.

A contextual predictive result may justify proposing a new policy, never activate
one automatically. That policy needs its own scope decision, contrast tests and
freeze. If no supported audible spacing choice exists, report that exact gap.
Fingering-only PCM identity is a successful musical-pitch lock, not audible variation.
Do not sample more songs or drop context solely to force a demo.

## SMART completion gates for this design and its implementation

- [x] Name current limits and distinguish harmonic identity, spacing, doubling,
  inversion, register, occurrence correspondence and physical ownership.
- [x] Define the eight contrast contracts and same-equation/uncertainty boundary.
- [ ] Independent midpoint/end review: identify contradictions and required source
  evidence before expanding any implementation scope.
- [ ] Before code promotion, freeze exact typed schema, sole owners, allowed edit
  dimensions, source/model support, refusal enums, tests and dataset manifests.
- [ ] QA1: frozen new-source trials with failures retained; development, repair and
  fresh evidence separated. No conditional acceptance from zero alternatives.
- [ ] QA2: isolated pairwise and whole-source exact0, lower/source/cache removed;
  actual nonzero inverse and independent source/dimension/dependency checks.
- [ ] QA3: all eight contrasts, complete candidate/refusal denominators, harmonic
  alternative/path consistency and explicit unsupported/unknown cases.
- [ ] One software-selected supported audible change: native GP import/pitch/string/
  notation checks, exact0 render baseline, measurable changed PCM with unaffected
  dimensions exact; then separate human listening/playability/source-feel review.

No production or detector edits were made for this document. Experiment A's
single grouped-heldout prediction study and this ownership review may proceed
independently. Neither closes all Tier2 levers or establishes multi-song artist
style, emotional intent, full GP acoustic fidelity or complete song generation.
