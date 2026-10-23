# Tonal center: real events versus artificial data boundaries

2026-10-23; research diagnosis, not product inference or a new generation engine.

## Requirements and acceptance

- [x] Preserve delivered source codecs, all accepted technique detectors and
  timed harmonic graph unchanged. Source tiers remain sole note/time authority.
- [x] Freeze selection/model/data/code before inference; first lexicographic
  eligible held-out test piece, not a desired example or replacement.
- [x] Replay saved fixed predictions before perturbation.
- [x] Split observations into exact equal rational halves with identical source
  note support and elapsed span, no new score notes/attacks. Join exactly.
- [x] Compare at declared scopes; retain both half distributions and pooled
  posterior, distinguish mean losses from loss of the mean.
- [x] Separate this observation split/join check from the full-source inverse
  gate and from new-song generalization. No borrowed QA1/QA2 accuracy claim.
- [x] Planner START/MID/END and independent developer review.
- [x] Isolate a surgical correction that ignores artificial subdivision but
  preserves actual repeated attacks, duration, source distinctions and uncertainty.
- [x] Test correction on frozen original plus new source, with explicit refusal
  and adversarial contrasts. No unmeasured guitar/key/mode accuracy claims.
- [ ] Commit/push verified source and record actual CI result.

## Actual frozen result

`diagnose_tonal_subdivision.py`, tests4PASS. Private
`local-artifacts/tonal-subdivision-study-v1/`: K280-1 selected before inference;
1203eligible observations ->2406halves;1280/3quarter notes; exact split/join and
unchanged source note support. Both baseline replays bit-identical, unchangedtrue.

Ordered model baselineNLL0.894492 ->mean-half1.888909, pooledposterior1.870032;
mean total-variation0.147686;144/1203pooledMAP states change.
Marginal baseline0.855437 ->mean-half2.329860, pooled2.305399;
meanTV0.155406;187MAP states change. These are errors against evaluation-only
major/minor labels, not new guitar/modal accuracy measurements.

Subdivision simultaneously changes emission count, predecessor features and
HMM transition count. Marginal model ignores predecessors and still shifts;
changed predecessor context therefore is NOT NECESSARY. Emission/transition
count causality remains unseparated. Current fixed inference applies factors
PER CELL; clocks/durations are validated/reported, not elapsed-time factors.

Planner accepts representation sensitivity, not a proven final fix. Product
deployment remains withheld. No research weights/annotations/scores published.

## Next action under challenge

Compare source-support aware observation ownership against a learned continuous-
time factor. Prefer smallest testable correction. Identical PC sets alone must
NOT collapse genuine attacks, different registers or different physical notes.
Any elapsed-time model must compare at the SAME physical query clock, not
mistake different half-cell centers for invariant observations. No manually
invented cadence weights, new musical notes, guessed modes or retuned test labels.

## Correction and actual verification

`research_observation_cuts.py`: versioned membership/interval/support relation.
Forward canonicalization and inverse restoration use the SAME relationship;
original source boundaries never merge. Only explicitly introduced cuts with
identical support, mask, continuous rational time and no boundary events may
coalesce. Rest/empty-support cells remain explicitly unsplit. Written ties are
preserved as declarations, never asserted to be picked attacks. Four contrast
tests cover reattacks, ties, changed notes, rest/gaps and sequence changes.

`run_research_observation_cuts.py` fixed replay
`local-artifacts/research-cut-invariance-v1`:1203original/2403children,
3explicitly unsplit cells; exact packet/source-support recovery. Both ordered
and marginal predictions bit-identical to original/saved baselines, zero changes.
No parameter updates. This fixes artificial-cut handling, not duration learning
or demonstrated key accuracy.

`source_written_sonority_cells.py` consumes existing pure written/tie extraction,
not a second raw-score parser. Complete source measure and written-note on/off
boundaries; physical occurrence IDs and tie/frame witnesses retained. Explicit
nonpitched declarations excluded, unknown pitched support quarantines intervals,
timing warnings refuse rather than invent repairs. Written base pitch only.

`run_source_cut_qa.py` applies SAME adapter/model relations to frozen randomly
selected Songsterr385798. Initialv1 worker failed because wrapper entrypoint was
named realize rather than harness-required reconstruct; retained. Fixed wrapper
and added actual-worker regression test. v2PASS unchangedtrue:6749occurrences,
1527eligible cells/528quarter notes,3051children/3unsplit cells; exact cut-packet
recovery by actual -I -S Python-audited worker with no raw source/model/expected
packet staged. Both fixed model outputs bit-identical. Python audit is NOT OS
sandbox. No human evaluation labels used or key accuracy claim.

Planner END independently computed ALL1527cells directly from original raw JSON
without producer/parser imports: exact support IDs/PCmasks/rational clocks,
onset/end/tie/frame witnesses and predecessors;1853nonpitched excluded,
zero discrepancies/quarantine/zero-duration cases. APPROVED bounded QA3.
Evidence: `source-cut-qa-v2/planner-independent-raw-cell-audit.json`.

Full final regression963run962pass1optional skip; bare stdlib963run953pass
10optional skips. Private logs `tonal-cut-full-tests-v1.log` and
`tonal-cut-bare-tests-v1.log`. Five source-cell tests include actual isolated
inverse, real boundaries, unknown pitch, percussion invariance and timing refusal.

Project Gate1/complete-source Gate2 remain separately verified on this capture
by chord-overlay-fresh-qa-v1 (71772typedfacts/containers exact). This new research
cut-packet inverse is a different declared boundary and DOES NOT replace that
proof. Musical-center/mode identification and elapsed-time likelihood remain
UNRESOLVED, not certified by representation invariance or exact serialization.
