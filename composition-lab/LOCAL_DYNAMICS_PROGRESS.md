# T2-10 local written dynamics — active execution

Start:2026-10-29, main `fe521a1`. User explicitly renewed autonomous execution
and the approximately-ten-working-step efficiency review with ProjectPlanner3000.
A verified commit is a checkpoint, not a reason to await another user prompt.

## Intended result

One source-supported audible dynamic change, using the existing nested source
facts, musical owners and SAME inverse. Change an existing known declaration and
account for its complete influence region. Keep pitches, timing, accents and all
other techniques fixed. No arbitrary MIDI offsets, added reset fields, guessed
loudness or artist-fit claim. Recurring phrase accent patterns remain Tier3.

## Acceptance checklist

- [x] Read handoff/current context; inspect main, source/tests/workflow; refresh
  main without modifying unrelated work or private baselines.
- [x] Planner START and cheap opportunity check: actual saved captures contain
  beat-level markings, no note overrides. Sweet Child part3 has50 declarations:
  f22, ff18, mp8, mf2. Queen lead has onlyf: do not force an alternative there.
- [x] Agree the owned dynamic relationship, influence scope, proposal support,
  missingness, zero/50/100 semantics and independent checker contract.
- [x] Implement source-only shared forward/inverse relationships; preserve
  complete declared-source identity at zero and existing default owners.
- [x] Implement one named local dynamic operation. Count each donor declaration
  once; retain no-choice and unknown-boundary cases; exclude target from support.
- [x] Independently verify original source, full influence and outside effective
  state, raw field locks, actual stripped zero/changed workers and corruptions.
- [x] Freeze one new random capture before analysis; unchanged logic; no reroll.
- [x] Verify actual GP import and native note velocities, unaffected note/tempo/
  technique identities and nonzero audio; preserve existing audio baselines.
- [x] Self-QA actual review artifact with clear source/part/bars and what changed.
- [ ] Planner MID/END; relevant/full tests, source delivery and exact-commit CI.
- [ ] Continue to the next independent required capability when feasible;
  only human musical judgment itself waits for the user.

## Efficiency decisions and evidence

START: T2-10 is already a declared gateway in PROJECT_COMPLETION_PLAN.md. Written
dynamic-state analysis and conversion exist; no new harmony model is needed.
Use an explicit marking's complete influence region. Beat dynamics inherit across
rests/bars; note overrides do not mutate state. Raw field equality alone cannot
prove surrounding expression stayed fixed. Unspecified remains unknown despite
the converter's defaultf; unsupported boundaries must not become permission.

## Development results and retained failures

`python -m unittest test_local_dynamics test_check_local_dynamics test_source_dynamics -q`:
27 tests passed (2.353s). Actual source-denied workers cover 0/50/100 in authored
cases. Source-level marking changes use the existing sole categorical owner;
approved detectors and default reconstruction are unchanged.

`run_local_dynamics_qa.py` on frozen development Sweet Child O' Mine: exact
10,138 notes / 102,106 source facts, 204 declaration influence regions, 743 source
options (546 changed); 203 declarations have alternatives. Complete independent
inventory/options match. Actual inverse runs cover exact zero and selected change;
the other source options are inventories/sampler tests, not 743 full inverse runs.
Fixed 32 seeds × 204 declarations: 0% released0/changed0 of6528; 50% released3264,
changed2144; 100% released6528, changed4267. Coincidence is not forced difference.

First selected pitched short-region change: part4, bar7, p→mp, six notes; other
source fields and effective states remain exact. Standalone GP export correctly
FAILED on pre-existing bend curves; original failure retained. Planner agreed
before fresh freeze to separately test the EXISTING GP+hash-bound bend companion,
without modifying the codec or the strict standalone default. Every checked
pre-export model field matches restored playback for source/zero/changed; no
universal model-fidelity claim. Independent native auditor passed: two GP Dynamic
leaves; six NoteOn velocities plus their six library-coupled NoteOff velocities;
source/zero PCM exact; focused/full-band PCM delta; no clipping. 10,118 known
source refs checked; 20 grace refs unverified, all outside the six affected notes.

Already-inspected All The Small Things: exact6,513notes/60,358facts; 14 markings,
three source alternatives, all percussion; no pitched review choice. Retained,
not used as a fresh benchmark replacement. No extra note or dynamic was invented.

Planner MID: no extra stored copy of the influence graph. Its recomputable
relationship drives proposal, inverse effects and outside-state audit from T2's
sole owner. This proves written dynamic-level control, not phrase intent, artist
preference, accent patterns or full T2-10 completion.

## Fresh gate and final verification

`freeze_local_dynamics.py freeze .../frozen-v1 ...` then `capture` selected exactly
one new song before analysis: Disposable Heroes / Metallica, song23389,8tracks,
seed5714360100019622303. Original first100-letter-search sampling limitation and
all source/selection/code/native hashes are retained. No replacement occurred.

`run_local_dynamics_qa.py .../fresh/capture .../fresh-qa .../freeze.json`:
17,428notes/183,893facts exact;26declarations;55options,38changed;21declarations
allow alternatives. Actual stripped source-zero, pair, explicit dynamic-zero
and selected changed workers passed. 832draws each:0% released0/changed0;
50% released416/changed213;100% released832/changed447.

`build_dynamic_preview.mjs ... gp_with_exact_model_bends` also passed on this
fresh song. Here all three standalone GP checked-field comparisons pass too.
Two source notes (one played attack) on the source-labeled lead-vocal guide track,
bars85-87, change mp→f. One GP Dynamic leaf and its coupled MIDI On/Off velocities
change. Source/zero PCM exact in both mixes; new PCM differs without clipping.
17,355known source refs verified;73grace refs remain unverified, all outside the
changed region. No singing quality or acoustic artist judgment is claimed.

Stable tests: `python -m unittest discover -s . -p 'test_*.py' -q`:
1,405run,1,404passed,1optional skip,210.636s. Targeted44passed/4.060s.
The four workflow Node suites:21passed. `node node_modules/vite/bin/vite.js build`
passed. Accepted detectors, bend codec and existing voicing auditors unchanged.

Actual desktop browser QA: play/cursor advance, seek-to-zero, source/changed
switch, focused/full-band switch, clickable notes and0/0.1/0.5/1speed verified.
Caught/fixed UTF8 display, zero-speed behavior, unsupported0.05browser rate,
standalone-versus-companion wording and source-note versus played-attack counts.
No new browser errors after the final zero+mix/version and rapid seek/switch
checks. Screenshot/evidence remain private. Mobile layout is not claimed tested.
The only post-freeze Python change is display-only `write_dynamic_review.py`
(explicit fresh-failure guard and factual native/attack labels); no analysis,
inverse or musical/native selection dependency changed. Display hashes are sealed
separately from the executed frozen analysis. HTML fixes do not alter scored data.

LAN serving was rejected by automatic approval review. The working server is
strictly localhost127.0.0.1:5276; it exposes no artifacts on the LAN. Human listening
approval is still pending. These mechanical checks do not close fullT2-10.

## Next independent musical improvement

Planner's preregistered private source-context census found55SweetChild targets
with >=2next levels from dependency-disjoint donor regions, conditioned on exact
incoming marking/meter/rational position. All55differ from broad voice palettes.
AllSmallThings and Queen have none, retained. Source/dependency hashes and a target
marking mutation check pass. First pitched opportunity: bassbar17, incomingf,
4/4,offset1q; contextual votesmf2/mp17. Do not hand-selectmf or expand features.
Next: same-inverse context-conditioned development test with fixed seeds0..31,
independent locks and retained coincidences. This improves choice context without
another slider, new model or invented artist rule.

Planner END: independently replayed fresh seed/candidate pool/exclusions, all26
declarations/55options/2,496draws, first demonstration,17,428pair equations and
183,893facts; actual workers and native/PCM report match. Final desktop display
hash/screenshot review approved the bounded core/UI scope. Human fit remains
pending; mobile untested; completeT2-10/artist acceptance staysOPEN.

Delivery: source commit/CI pending at this log checkpoint; continue the next
bounded context test after this verified checkpoint.
