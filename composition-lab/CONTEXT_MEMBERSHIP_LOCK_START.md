# Optional contextual membership lock — bounded START

This adds an executable semantic constraint to existing pitch edits. It does not
choose a true chord/key, identify a melody, rank a voicing or create a generator.
Existing policies, accepted detectors and the approved Queen artifact stay unchanged.

## Relationship and ownership

- Inputs: complete preceding-tier source facts, explicit original edit occurrence
  IDs, and requested same-part-minus-edit-set or ensemble-minus-edit-set scope.
- Exclude the entire edit set before deriving support. Preserve original IDs,
  exact rational half-open spans, source domains and qualification/refusal evidence.
- Reuse existing nominal context and pitch/degree equations. The lock stores only
  the request, cell/support/hypothesis references and expected membership booleans;
  never original target pitches or another note stream.
- Build context once from reconstructed T1 directly. Forward attachment may realize
  the existing owner once; inverse validation must pass its already reconstructed
  T1 into a pure preparation helper, avoiding connected-realize recursion.
- Current exact-fit hypotheses within one population share an identical PC set.
  Membership therefore cannot distinguish their roots/kinds. Mixed results can
  arise across different contexts/cells, not among aliases of one exact PC set.

## Availability and enforcement

Every requested positive-duration occurrence must have complete qualified temporal
coverage. Unknown/fractional/nonpitched focal pitch, missing/crossing geometry,
qualified support, no exact fit or omitted cells makes attachment unavailable.
Missing analysis remains separate; source inversion without an active lock stays exact.

A canonical attached packet preserves its full expected vector, including different
expectations in different contexts. After edits: all comparisons preserved means
SUPPORTED; some preserved means AMBIGUOUS; none preserved means CONTRADICTED relative
to this explicit contract. Unusable evidence means MISSING, never false/nonmember.
An active hard lock permits only SUPPORTED. Invalid/omitted support, hypotheses,
cells or occurrence IDs refuse; no silent partial-denominator success.

## Independent checks and scope

New independent files: check_context_membership.py and test_check_context_membership.py.
The oracle independently scans raw rational intervals and native theory, not the
producer context/packet builder. Proposed API: expected(before_T1, request),
assess(after_T1, packet), check(before_T1, after_T1, packet, reported=None).
Final request/packet field schema must be agreed with the producer before coding.

Contrasts: unchanged exact zero; member-preserving and member-changing pitches;
whole-edit-set exclusion; held focal over two different contexts; conflicting
scope/time comparisons; C6/Am7 identical membership despite root ambiguity; duplicate
source-PC witnesses; missing/unknown/fractional/nonpitched support; incomplete
coverage; corrupted booleans/support/cells/hypothesis inventory; actual stripped
worker acceptance and refusal through the existing inverse.

Existing MusicXML reference extraction emits normalized written events/geometry,
not complete Songsterr T1 or execution facts. Reuse it only for independent
interval/native-membership comparisons against the existing qualified annotations.
Do not fabricate a Songsterr adapter or claim whole-lock/guitar/artist validation
from classical reference agreement. Annotations never enter inference or controls.

After stable focused tests: existing fixed-source comparison, actual stripped
zero/changed-or-refused worker checks, frozen new random input with no replacement,
and independent END accounting. No-choice is retained. Full lever, true harmony,
artist preference and physical/listening acceptance remain separate.
