# Source grace declarations at the GP export boundary

## Why this is the next step
The accent implementation is published as `19d4f65`. The five-source, exact-context
rhythm-pair census found zero supported alternative ratios: no rhythm selector
was built and no constraints were loosened. Planner independently verified all
20,200 adjacent pairs and 1,158 admitted pairs across 91 contexts. The negative
result is retained in `local-artifacts/rhythm-pair-opportunity-v1`.

The fresh Leper Messiah source already passes the complete inverse and accent
change checks. Its GP bridge promotes 22 source grace beats (30 notes) into ordinary
beats in 15 bars, adding 9/2 quarters overall, and loses 53 pitched grace ghost flags.
Independent GP7 synthetic export/reimport proves the target format can represent
both failing group shapes. The upstream one-grace-per-host-note bridge is the limit.

## Acceptance checklist
- [x] Planner START; measured source failure and actual GP7 capability checked.
- [x] Authenticate complete source/native correspondence before any mutation.
- [x] Restore only known grace type and grace ghost flags through a shared helper.
- [x] Native finalization derives clocks; no manual onset or performed-duration patch.
- [x] Unknown, trailing, cross-bar, mixed-type or ambiguous mappings refuse atomically.
- [x] Synthetic multi-note and consecutive grace positives; corrupt-mapping negatives.
- [x] Same frozen Leper source, separate DEVELOPMENT repair output; old failure preserved.
- [x] Every affected bar's regular onset grid and four-quarter total restored; original
      note count, pitch, string and all unrelated fields preserved.
- [x] Actual GP7 export/reimport and independent source checks, including grace flags.
- [x] Rebuild existing accent output from actual isolated inverse; GP/MIDI/audio locks.
- [x] Regression on fixed development inputs; one frozen new random portability input.
      No grace in a random input means no new grace coverage, not a substitute draw.
- [x] All three QA gates scoped honestly; human grace feel remains unproved.
- [x] Planner MID/END and relevant tests.
- [ ] Publication and exact-commit CI (record receipt after publication).

## Scope
Only the JSON-to-GP export boundary. Accepted technique/pedal detectors, bend logic,
source captures, original failed exports and unrelated WIP remain untouched.
A source grace contributes zero nominal metric span. Its written duration is notation;
alphaTab's performed allocation is renderer behavior, not measured source audio.
A one-to-one native/source correspondence is mandatory. General recovery after
collapsed groups or host-string remapping would require a separate authenticated
source-identity ledger; this repair must not guess those correspondences.

## Next action
Publish this bounded one-to-one repair and check exact-commit CI. Next approved
endeavor: source-explicit whole-group timing relationships; keep the new split
grace limitation separate. Preserve all private evidence.

## Full-capture audit correction
The four lost ghost markings were a subset inside the initially failing bars.
The whole Leper capture loses **53 pitched grace-note ghost markings**. The full
audit verifies 894 ordinary durations across available bundles. Native finish
normalizes 179 correctly classified grace glyph durations; that is a distinct,
retained output limitation. Source notation remains exact in T1.

Repair scope is pitched notes only. Two Sweet Child ordinary tied percussion chords
have ambiguous native correspondence. Percussion is counted as unchecked and
unchanged, not silently repaired or promoted. All available pitched grace voices
have exact beat counts and note geometry; Knockin has no existing native bundle.
Evidence: `local-artifacts/local-accents-v1/native-baseline-investigation-v1/all-five-grace-findings.json`.

## Implemented boundary and independent checks
`restore_source_graces.mjs` verifies every beat/member in each affected pitched
voice before applying any change. Source part/voice order, tuning/capo, unique
string/fret members and rational ordinary durations must match. It restores only
known grace modes and ghost flags. The default exporter is unchanged; opt-in is
`--restore-pitched-graces`. Opt-in requires fresh output even if an old report
claims success. Both invalid-byte and valid-GP forged-report tests prove refusal
and byte preservation. Native no-tuplet `-1/-1` means unity; other invalid ratios
remain errors. Native grace glyph normalization is not compared as raw source
duration equality.

Planner's independent `check_source_graces.mjs` imports no repair helper. It checks
complete affected voice correspondence, ordinary source onset grid and nominal
totals, grace classification and ghost flags after real GP7 export/reimport.
Percussion and native performed grace timing are explicitly outside that claim.

## Development result and retained failure
Leper repair: 9,233 native notes, 66 pitched grace voices, 110 grace beats/118
notes; 22 grace classifications and 53 ghost flags restored. Whole-score comparison
finds exactly those 75 changes plus eight native glyph normalizations. All 248
derived clock differences are confined to the 15 repaired voices. All other
compared score fields, including raw bend/whammy arrays, match.

The native accent build used the original actual isolated inverse outputs. Its
first invocation stopped on a Windows locale decode error in the shared JSON
artifact reader, after producing GP/MIDI/PCM. That failure remains saved. The
reader now decodes JSON bytes, with a forced-cp1252 Unicode regression test.
Re-auditing those same untouched artifacts passes: one GP accent 0→1, MIDI95→111
for its paired note-on/off, source/zero sample-exact PCM, changed focused RMS
0.0019815887 and ensemble RMS0.0019816017. Final actual worker/capture binding
passes. `development-recovery-receipt.json` identifies the failed invocation,
recovery checker hashes and independent report; it does not relabel the first
invocation as a successful run. Planner independently reproduced the full report.

## Fixed regressions, tests and fresh protocol
- Queen: no source graces; native roundtrip and regular source fields pass.
- Sweet Child: 11 pitched grace beats; independent grace and regular source fields
  pass, no repair needed. Existing standalone bend loss remains explicit.
- Knockin: 3 pitched grace beats; independent grace and regular source fields
  pass, no repair needed. Existing standalone bend loss remains explicit.
- All Small Things: no source graces; existing dead-tie identity check fails at
  99:0:0. Planner's fresh default-exporter control fails identically from byte-equal
  bridge/source inputs. This is a retained existing limitation, not a grace pass.
- Node: 41/41 pass from repository root, including actual GP7 tests (no skips).
- Python: 1,465 run; 1,464 pass, one optional skip (190.341s).
- Existing published fixture fix `83e9862`: exact-head CI40934630386 succeeds.

New freeze pins 574 Python/53 native dependencies. Seed15173494052321944100
selected Green Day / Boulevard Of Broken Dreams, song92866, nine tracks, before
analysis. Exactly one slot; no substitution for failure/no-grace/no-choice.
`local-artifacts/grace-bridge-v1/frozen-v1/portability-protocol.json` declares
the three QA scopes before capture. The final outcomes follow below.

Commands: `python -m unittest discover -p 'test_*.py' -q`; repository-root
`node --test` on the two grace suites plus the four existing lab workflow suites;
`freeze_local_accents.py freeze ...`, `capture ...`, then
`run_local_accents_qa.py <capture> <fresh-qa> <freeze.json>`.
Actual logs and original errors are private in `local-artifacts/grace-bridge-v1`.

## New random result and Planner END
Green Day: 74,586 facts and every captured field/container/type/order reproduce
exactly. All 10,598 note objects, 74 targets with changed accent choices and
1,017,408 fixed draws were checked. Release counts: 0/339,136 at0%,
169,568/339,136 at50%, 339,136/339,136 at100%. Actual changed levels:0/117/179.
The actual isolated zero, no-choice and changed workers pass. First changed
draw is `event:92866:6:19:0:2:0`, seed12, absent→accent1.

Native source/zero/changed all REFUSE `Grace beat correspondence mismatch at
3:8:0`. Independent inspection finds six source beats but seven bridge beats:
one simultaneous two-note onBeat grace was split into two one-note grace beats
by GP5 import. The ordinary nominal grid is still correct. This is a different,
explicitly unsupported correspondence shape; the new helper refuses before any
writes. No matching by guess, no reroll and no fresh audio claim. The 92 pitched
source grace beats are not claimed verified as a whole native song.

QA1: fresh unchanged analysis/inverse succeeds; native export remains unsupported
for this source. QA2: complete captured-data reconstruction and isolated changed
output pass. QA3: source-declared grace versus metric attack and source-supported
accent context are bounded musical relationships; no artist/phrase intent,
source acoustic grace timing or human fit is claimed. Full T2-10/Tier2 remains OPEN.

Planner independently approved the scoped repair, recovered Leper native/audio
report, unchanged frozen hashes, default-export failure control, and fresh refusal.
Evidence: `planner-fresh-correspondence.json`, `planner-default-control-result.json`,
`planner-final-end-review.json` and the fresh result/native failure. Exact frozen
dependency bytes are privately archived before further development.

### Disclosed post-freeze correspondence hardening
Final review found the exporter selected raw parts by native track count, making
the helper's count comparison unable to catch an extra source track. It now loads
an independently enumerated, contiguous `track-N.json` inventory. A real exporter
test supplies two source tracks but one native track and verifies refusal before
output. The new 21-test grace suite passes with real alphaTab installed. Separate
fresh DEVELOPMENT copies reproduce identical Leper success and Green Day refusal
under the hardened caller; all independent report/count fields match. Original
frozen files/results are unchanged and archived. This is a caller-guard revision,
not a claim that the original fresh run used different code.

## Next musical opportunity (not implemented here)
The five-source pair census had no useful alternatives. A separately preregistered
inventory now finds 6,170 COMPLETE explicit source beam brackets, with lengths2–16;
all boundary/member facts were independently checked. The complete-group test
finds 69 opportunities only in one Leper bass context: three attacks over1quarter,
phase1quarter,4/4,dynamicf, same part/voice. Rational shares [1/2,1/4,1/4] versus
[1/4,1/4,1/2] come from actual source notation groups. The changed vector has ONE
donor in this exact context (bar166); a disjoint ordinary-pattern group supplies
the other witness. This is narrow source support, not robust style inference.
Target pitch/string/fret, attack count and span stay locked; donor and target
absolute registers need not be equal. No fixed-size excerpt window was invented.
No timing owner or rhythm selector exists yet. Native beam-layout fidelity is
also unproved; preserving source markers is not the same as reproducing engraving.
