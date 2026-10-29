# Local accents: optional source ownership

## Why this is the next step
Dynamics now has source-local context and a verified changed output. Accents are
a separate required control: a note's attack emphasis, with inherited dynamic
levels kept fixed. Existing accent integer owners cannot add a missing marking.
We must own absence/presence properly, not insert source fields after analysis.

## Acceptance checklist
- [x] Planner START; frozen census on the four fixed sources, no song shopping.
- [x] Native source semantics:24contrasts, including normal/heavy/ghost/clamping.
- [x] Full source census:30,849note objects. Existing scalar-route opportunities0.
  Queen has43potential absent-to-normal locations, only2plain pitched donors.
  This is limited source evidence, not artist understanding. Other interactions
  (including all Knockin accents with staccato/bend) remain out of plain scope.
- [x] Typed optional owner; absent differs from explicit0/1/2; original key order
  preserved. Unknowns retain old owners. No copied note values or raw payload.
- [x] Explicit opt-in connected schema2; default schema1 unchanged. Note-container
  membership and optional accent have one owner. Coverage derives from CURRENT
  relationship state; intervention does not edit the ledger.
- [x] Synthetic exact-zero and changed-parameter inverse in source-denied worker.
- [x] Planner MID review of integration and corrupt ownership cases.
- [x] Whole-source development inverse/raw parity using the new owner.
- [x] Source-context selection using fixed census; every other field locked.
- [x] Full regressions; new frozen random source; actual zero/nonzero inverse.
- [x] Development GP accent symbol, native MIDI and PCM checked independently; written
  dynamics, pitch/time and other techniques unchanged. No clamped fake change.
- [x] Real UI inspection and scoped Planner END; retained fresh native failure.
- [ ] Publish verified source and check the exact-commit CI.

## Actual work
`optional_accent_slots.py`: same registered build/expand relation returns the
note-container metadata with ordered non-accent child refs plus optional integer
state. All other note values stay in their existing owners. Seven owner tests pass.
Fixed-source smoke:30,849groups emit31,312rows exactly equal to original T1 owners.

`connected_tier2.analyze(..., note_accent_slots=True)` opts into schema2 and a
strict conditional ownership ledger. Its inverse expands the same owner before
resolving ordinary note children, then runs existing full-source and musical
consistency checks. Legacy schema/defaults and approved detectors are unchanged.

`python -m unittest test_connected_accent_slots test_optional_accent_slots test_connected_tier2 test_dynamic_context -q`:
32passed,5.270s. This proves ownership/inverse mechanics on synthetic cases;
it is NOT a creative accent pass or a claim of musical fit.

Preceding context delivery: e3caab8, merged/pushed with unrelated main updates as
8f32a28bfbfa45315df0920c077e09fa718c85d7. Frozen context evidence stays attached to
that version; this new optional-owner work changes code and needs its own gates.

## Development result (not fresh-song acceptance)
Queen / Another One Bites the Dust, fixed existing capture371:
37,953facts exactly reconstructed in the actual source-denied worker. Independent
inventory/options match for all4,144note objects;43targets offer changed sound
levels. All397,824fixed draws checked independently:132,608perstrength;
0% releases0/changes0,50% releases66,304/changes55,100% releases132,608/changes141.
Release probability and realized changes are distinct. No-change outcomes remain.
Actual explicit-zero, no-choice100% and changed inverse workers all pass.

First eligible source-order draw: source-labeled vocal part,bar12,note atquarter offset1, duration1/4
quarter (sixteenth note), atwritten mf. Absent accent becomes normal accent,
witnessed in matching source context. Exactly1GP Accent changes0→1, selected
MIDI velocity79→95; Dynamic fields unchanged. Source/zero PCM sample-exact;
actual delta RMS0.0007933in both focused and ensemble renders. All three standalone
GP checked-field comparisons pass; current rendered package uses the explicit
existing GP/model-bend scope. No new bend repair or converter changes.

Native audit reports all3,384non-rest source occurrences:2,071individually mapped
pitched occurrences and1,313percussion references not individually verified by
that mapping. The edited target IS fully mapped. Complete raw outside fields
remain locked; do not extend this to new percussion execution claims.

Commands: `run_local_accents_qa.py .../tonal-meaning-fresh-v1/capture
.../local-accents-v1/development-queen .../development-freeze.json` and
`node build_local_accent_preview.mjs ... gp_with_exact_model_bends`.
Private manifests, full inventories/options, draw hash, actual workers and audio
receipts are under `local-artifacts/local-accents-v1/`.49focused Python tests pass;
10native-artifact corruption tests pass. The21workflow JS tests and Vite build pass.

Next: finish broad regression, freeze unchanged logic/native dependencies, draw
one fresh source without replacement, inspect real compact player, Planner END.
Human source-feel judgment remains pending; this is attack-context support only.

## Frozen new source and retained native failure
Seed14520102763112858847 selected43276 / Leper Messiah / Metallica, revision9052987,
8tracks. No retry, reroll or source-dependent code adjustment.573Python and49native
files pinned before capture. All10,194note objects and94,113facts reconstruct
exactly. Complete independent contexts/options and978,624fixed draws agree.
456targets offer changed sound levels; actual source-denied0%,100%no-choice and
selected changed workers pass. The forward/backward pair is checked in parent;
the folder name`zero-and-pair`does not imply a second isolated pair-worker job.

First supported changed draw: source-labeled bass,bar4,seed1, no accent→normal,
written f. This is a real symbolic source-supported result, NOT a native/audio pass.
The native builder correctly refused15baseline source beat-count differences on
each unchanged/zero/changed file, despite native GP roundtrip passing.

Planner/root compared every affected source/native bar:22source grace beats
(30notes) become regular timed beats. Eight2-note onBeat cases add1/8quarter;
seven consecutive-beforeBeat cases add1/2quarter; total added nominal time9/2quarters.
Affected voices become4.125or4.5quarters rather than4. Pitch/string/cardinality order
matches, but attack positions shift. Four additional grace ghost markings are lost.
This is a REAL existing GP5 bridge limitation; ignoring extra beats would hide it.
Frozen outputs/failure/probes are retained in`frozen-v1/fresh-qa/native-preview-bundle`
and`native-baseline-investigation-v1`. No converter/grace/detector changes made.
Fresh native creative acceptance remains BLOCKED; it was not replaced with a new
song. Full accent lever and T2 remain OPEN.

Full Python:1463run,1462passed,1optional skip,219.132s. Workflow Node21pass;
Vite build passes. Actual desktop player checks passed after fixing UTF-8 text,
stale dynamics-only labels/report link and ambiguous per-song fidelity wording.
Queen player explicitly says Leper Messiah GP playback failed and is withheld.
Source/change playback, cursor, half/zero speed, mix switches, seek0, E_3note click,
QA rows and no browser errors verified. Screenshots/display hashes:`ui-qa.json`.
Localhost5278only; mobile and human musical-fit judgments untested.

Post-freeze presentation only: added`package_accent_review.py`to display the actual
native failure, plus HTML wording/encoding updates. No pinned Python/native file
or compiled analysis/inverse relation changed. Source and native proofs remain
attached to the original frozen versions. New packaging is not a musical policy.

Next after scoped Planner END/publication: one fixed-input opportunity check for
T2-07 repeated-pitch rhythm pairs. New shared timing ownership only if source
alternatives actually exist. Grace bridge repair remains a specific final-output
gap, not an accent loophole or an excuse to stop other independent analysis work.

### UI follow-up correction and retest

Initial UI receipt was superseded, retained as `ui-qa-before-load-fix.json`.
Rapid end/switch/seek/play exposed a real stale-metadata seek race. The shared
player now owns pending seek/resume while loading, rejects stale selection/resource
callbacks, ignores transient load timeupdates, and cancels resume at zero speed.
Actual browser retest: changed playback advanced to 0.53s; rapid switches kept
seek2s; zero-speed stayed stopped on later inspection; prior dynamics data played
to2.18s using the new template in a separate private copy. No baseline overwritten.
Fresh screenshots, AX text and hashes are sealed in `ui-qa.json`. No browser errors.
This fixes player operation only; native Leper failure and musical-fit scope unchanged.

### Planner END

Scoped publication approved after independent hash/ownership/worker/native and
UI review (`planner-final-end-review.json`). Queen is source-labeled vocals using
program71: positive pitched-note accent evidence, not guitar execution or vocal
realism. Leper remains a fresh symbolic positive and native baseline failure.
No human accent-fit acceptance and no full T2-10/Tier2 promotion.

Safely fast-forwarded unrelated upstream UI work to `a49f96b`; no private baseline or WIP reset. Root JavaScript suite:28/28 passed; Vite build passed after the fast-forward. The separate lab workflow suites previously passed21/21. A transient Git index lock cleared on its own; none was deleted.

### Published CI and portability correction
Published `19d4f65413825c2ca9acf416ad31ef22f8e3e70b`. CI40930227857 failed
four artifact tests: the synthetic fixture built its fake worker output from
filesystem enumeration order, unlike the canonical metadata-first extractor.
Reproduced locally by reversing directory enumeration: same binding failure.
Fixed the fixture to use the actual canonical extractor and added that adversarial
order test. Production analysis, inverse, artifact locks and old private outputs
are unchanged. The original frozen test file is retained privately; this is a
disclosed post-freeze test-only revision, not a rerun claim for original573hashes.

Corrected fixture suite:11/11 passed, including reversed enumeration. Whole-capture native follow-up finds53 pitched grace ghost losses; the earlier four were only within the initially inspected failing bars. The original failure is preserved.
