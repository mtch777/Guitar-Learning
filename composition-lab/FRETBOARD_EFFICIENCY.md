# Drop E fretboard efficiency: two fixed MIDI inputs

The user-selected `cfa029a2` and `da80eca9` riffs are now regression fixtures for a whole-sequence fingering optimizer. They are frozen copies from the `generated-midi` branch at commit `b86db9f73d1adf8a5552dc81a475437a36b4ae2c`. Their filename hashes are their verified SHA-256 content hashes.

## Review

The primary lesson is now integrated into the existing guitar trainer (`index.html`) as **Fretboard Efficiency**. It uses the same Song Player/alphaTab engine, transport, physical fretboard, keyboard controls and speed selector as existing lessons. Both A/B inputs and optimized/greedy mappings are available. Direct lesson parameters are `?lesson=fretboardEfficiency&riff=cfa029a2&mapping=optimized` and the same with `riff=da80eca9`.

The lesson fetches the published `data/fretboard-efficiency-fixtures.json` file and converts its exact assigned occurrences into a native alphaTab score. It never infers new fingerings from pitch alone. The existing Song Player upload accepts the same mapping JSON as well as Guitar Pro files. Default Time Solo selection is preserved when there is no explicit efficiency-lesson URL.

Optimizer string 1 is high E4; alphaTab/native string 1 is low E1. The adapter converts this with `native_string = 9 - optimizer_string`. Displayed string numbers for this lesson use the conventional high-to-low numbering. Active intervals are relative to E. The Follow hand view retains the open-string column and follows the current hand position/active notes in a seven-fret window; Full neck remains available.

The synth and display use the same native tick clock. A paused seek previews notes still held at that tick, including both copies of a duplicated pitch. Pause, Stop and natural finish clear active highlights; a delayed player clock callback cannot repopulate a stopped display. Speeds such as 0.75× change real playback speed while source-tick progress and held contacts remain aligned. Lesson switching cancels pending loads and restores the preceding score when applicable.

Native alphaTab 1.8.4 represents written dynamics rather than arbitrary MIDI velocities. A note-scoped registration supplies the exact original velocity for these mapped native notes; unregistered scores retain the original generator behavior. An independent comparison of all 5,472 native events in the existing Time score before/after registration protects that boundary.

The earlier standalone comparison remains available for inspecting optimizer metrics:

Run `npm ci`, then `npm run dev -- --host 127.0.0.1`, and open `riff-builder.html?efficiency=1` under the configured `/Guitar-Learning/` base. The normal riff builder remains available without that query. The review has silent follow/seek controls, fixture and version selection, an interval-labelled cropped fretboard, separate open strings, exact note contacts, hand position, comparison metrics, and note-data export. No sound is played automatically.

To export the same review as one self-contained offline HTML file:

```bash
python composition-lab/export_fretboard_efficiency_review.py --output /absolute/path/drop-e-efficiency-review.html
```

The exported HTML embeds both fixtures and both mappings and makes no automatic network requests. Its source-MIDI button opens the pinned GitHub source only when clicked.

## Fixed inputs

| Fixture | File prefix | Notes | Attacks | Duration | Diagnostic purpose |
| --- | --- | ---: | ---: | ---: | --- |
| A: low response | `6_review_cfa029a2…mid` | 164 | 124 | 32.25 seconds | Open-string priority, low response, eventual climb to a high minor-second dyad |
| B: high dyads | `6_review_da80eca9…mid` | 191 | 124 | 32.25 seconds | Repeated high dyads interleaved with lower material; rapid longitudinal changes |

Both use 120 BPM and 960 ticks per quarter note. The source files live in `tests/fixtures/fretboard-efficiency/`. Each starts with two one-second G1–D2–G2 chords, followed by a sustained high chord. Each includes E1–B1 two-note power chords and separate two-note intervals. The high chords at 2, 10, 18 and 26 seconds contain **two distinct B3 note occurrences**. These are preserved, not deduplicated.

## Ordered optimization

Tuning, low to high: **E1 B1 E2 A2 D3 G3 B3 E4**. String 1 is the high E4; string 8 is the low E1. This pilot uses 24 frets.

Candidate paths are compared lexicographically:

1. Minimize missed exact-pitch-and-octave open strings.
2. Minimize rapid longitudinal shift risk, using release-aware time.
3. Minimize total longitudinal distance, then fretting-contact/stretch effort.
4. Minimize a string-travel and skipped-string picking proxy.
5. Prefer explicitly recognized familiar shapes.

A lower tier never compensates for a worse higher tier. The dynamic program exhaustively searches the declared finite model; it does not use a beam search or collapse the tiers into one weighted sum.

Every note occurrence gets its own string/fret assignment. Held assignments remain fixed until note-off. Simultaneous occurrences require distinct strings; positive-fret span is at most four; the existing contact-coverage model admits at most four fretting contacts. Open strings do not force the hand to fret zero. Hand position is a discrete reachable five-fret window.

### Release-aware timing

Time spent holding a fretted chord cannot be treated as freely available travel time. For two successive fretted frames, available time is:

`min(attack spacing, max(0, current onset − prior fretted release) + min(0.125 seconds, attack spacing))`

The provisional threshold is 8 fret positions per second. Excess distance is `max(0, position distance − 8 × available time)`. Tier 2 sums `round(1000 × excess² / max(available time, 0.0625))`. A rapid-shift flag means excess is positive. The 125 ms transition allowance is an explicit modeling choice, not a measured physical capability.

The score penalizes the severity and timing of movement; it is not simply a count of position changes. Open-note and rest windows can provide release time while the previous hand position is retained as the reference.

## Results

The comparison is an admitted open-first, lowest-fret **greedy algorithm**. Source MIDI has no original guitar fingering, so these are not claims about the original player's technique.

| Metric | A: greedy | A: ordered | B: greedy | B: ordered |
| --- | ---: | ---: | ---: | ---: |
| Notes preserved | 164 | 164 | 191 | 191 |
| Open occurrences used | 82 | 82 | 73 | 73 |
| Maximum feasible opens | 82 | 82 | 73 | 73 |
| Rapid-shift flags | 19 | **1** | 34 | **10** |
| Rapid-shift risk | 1,338,667 | **8,000** | 5,454,667 | **152,000** |
| Total hand travel, fret positions | 96 | **12** | 204 | **84** |
| Largest hand-position jump | 14 | **2** | 14 | **5** |
| Count of all nonzero shifts | 34 | 9 | 43 | 45 |
| Maximum positive-fret span | 4 | 4 | 4 | 4 |
| Fretting-effort score | 472 | 472 | 748 | 724 |
| Picking score, lower is better | 433 | 524 | 475 | 686 |
| Shape score, lower is better | 916 | 976 | 892 | 952 |

There are 86/77 raw open-eligible occurrences, but only 82/73 feasible opens. Each duplicated B3 pair has only one matching open string. One B3 must therefore be fretted in each of four chords. The optimized solution uses string 2 open and string 4 fret 9 for those copies.

Less longitudinal movement costs more cross-string travel and some shape preference. This follows the requested tier order. In fixture A, the hand stays near position 5 through roughly 28 seconds before climbing gradually. Its ending B3+C4 dyad uses open string 2 and string 5 fret 15, retaining the high hand position while accepting a wide string skip.

## Output files

- `public/data/fretboard-efficiency-fixtures.json`: unchanged source occurrences, parameters, assignments, hand positions, shape labels, picking orders, and measured scores for both algorithms.
- `public/fretboard-efficiency/*_strings.mid`: four standard MIDI exports, one per fixture and algorithm. MIDI channels 1–8 correspond to guitar strings 1–8, high to low. Pitches, note-on velocity, onset, release and source duration are preserved; source channel routing is intentionally replaced by string routing. These are ordinary MIDI files, not MPE or a specific virtual-instrument articulation preset.

## Reproduce and verify

Install the single parser/export dependency:

```bash
python -m pip install -r composition-lab/requirements-fretboard-efficiency.txt
python composition-lab/run_fretboard_efficiency.py
python composition-lab/check_fretboard_efficiency.py
```

Run focused tests from `composition-lab`:

```bash
python -m unittest -v test_fretboard_efficiency test_fretboard_efficiency_shapes
```

Native lesson checks use the same pinned alphaTab package as the Pages deployment:

```bash
npm install --prefix .local/qa --no-save @coderline/alphatab@1.8.4
node --test tests/fretboard-efficiency-lesson.test.mjs
```

These checks compare actual native MIDI-generation events against a separate raw-MIDI parser and verify exact string contacts, held-note seeks, partial final bars and existing-score preservation. They fail rather than skip when the required native package is missing. The current lesson-delivery status, live browser checks and deployment receipt are recorded in `FRETBOARD_EFFICIENCY_PROGRESS.md`.

The independent checker parses raw MIDI using only the Python standard library; it does not trust the runner's parsed note list or reported scores. It checks hashes, duplicate multiplicity, exact ticks and velocities, physical string occupancy, hand windows, timing metrics, and all four exported MIDI files. The tests include held-string conflicts, same-tick retriggers, range failures, an unavoidable earlier-open sacrifice, a zero-shift high-dyad alternative, and a held-chord timing counterexample. Tampered source clocks, hashes, deleted duplicates, forged metrics and incorrect exported channels are rejected.

Verification completed: **32 focused tests passed, no skips; independent source/export check passed; production build passed.** The existing relevant JavaScript suite passed 49 tests; 38 optional native-alphaTab tests were skipped because that dependency was absent. The new DOM view was exercised at all 496 attack states. Actual desktop/phone visual rendering remains unverified because the available browsers could not render the local server; no audio was played during QA.

## Limits and next refinement

This establishes exact optimization within the stated reach/contact/position/picking model. It does not certify human comfort, finger independence or real picking technique. Four-contact feasibility and a four-fret span are constraints, not a complete biomechanics model.

Shape support includes drop-power shapes, adjacent-string power shapes, all five major CAGED templates, common E/A/D minor templates, and E/A minor-pentatonic fragments. **Complete 2/3-notes-per-string and arpeggio phrase recognition is not implemented.** These can be added at Tier 5 without overriding higher priorities.

The parser/export pilot handles fixed-tempo note MIDI. It refuses tempo changes and bend/controller messages rather than silently discarding them. These two real fixtures have no notes held across later attacks, so overlapping holds are covered separately by adversarial tests.
