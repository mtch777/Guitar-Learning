# Drop E fretboard efficiency: fixed MIDI inputs

The user-selected `cfa029a2` and `da80eca9` riffs are now regression fixtures for a whole-sequence fingering optimizer. They are frozen copies from the `generated-midi` branch at commit `b86db9f73d1adf8a5552dc81a475437a36b4ae2c`. Their filename hashes are their verified SHA-256 content hashes.

Fixture C uses the latest user upload, `2026-11-15 midi rewrite(2).mid`, frozen as `2026-11-15_midi_rewrite_2.mid` with SHA-256 `5fa3e52d30a27b3568c7303f47011cb5aaa9777ac2a584ea31e7f797d522ca77`. Its stable lesson identifier remains `c5a35486`, so existing lesson links load the revised MIDI. The identifier records the first revision; `source_sha256` identifies the current bytes. The prior `2026-11-15_midi_rewrite.mid` remains as historical source evidence. C's source provenance is the user upload rather than the earlier generated-MIDI commit.

## Review

The primary lesson is integrated into the existing guitar trainer (`index.html`) as **Fretboard Efficiency**. It uses the same Song Player/alphaTab engine, transport, physical fretboard, keyboard controls and speed selector as existing lessons. All three inputs have the original hand-movement optimizer, a **Strum + pick** optimizer, and the greedy comparison. Direct lesson parameters are `?lesson=fretboardEfficiency&riff=cfa029a2&mapping=optimized`, the same with `riff=da80eca9`, and `riff=c5a35486` for the uploaded rewrite. Use `mapping=strumPick` for the separate strumming/picking priorities. The original default remains `optimized`.

The lesson fetches the published `data/fretboard-efficiency-fixtures.json` file and converts its exact assigned occurrences into a native alphaTab score. It never infers new fingerings from pitch alone. The existing Song Player upload accepts the same mapping JSON as well as Guitar Pro files. Default Time Solo selection is preserved when there is no explicit efficiency-lesson URL.

Optimizer string 1 is high E4; alphaTab/native string 1 is low E1. The adapter converts this with `native_string = 9 - optimizer_string`. Displayed string numbers for this lesson use the conventional high-to-low numbering. Active intervals are relative to E. The lesson shows a fixed range from the open-string column through the highest fret used anywhere in the selected mapping. Playback, seeking, pauses and rests do not move or crop the neck; changing the fixture or mapping updates the complete range. C / Strum + pick shows open strings and frets 1–24 from the start.

The synth and display use the same native tick clock. A paused seek previews notes still held at that tick, including both copies of a duplicated pitch. Pause, Stop and natural finish clear active highlights; a delayed player clock callback cannot repopulate a stopped display. Speeds such as 0.75× change real playback speed while source-tick progress and held contacts remain aligned. Lesson switching cancels pending loads and restores the preceding score when applicable.

Native alphaTab 1.8.4 represents written dynamics rather than arbitrary MIDI velocities. A note-scoped registration supplies the exact original velocity for these mapped native notes; unregistered scores retain the original generator behavior. An independent comparison of all 5,472 native events in the existing Time score before/after registration protects that boundary.

The earlier standalone comparison remains available for inspecting optimizer metrics:

Run `npm ci`, then `npm run dev -- --host 127.0.0.1`, and open `riff-builder.html?efficiency=1` under the configured `/Guitar-Learning/` base. The normal riff builder remains available without that query. The review has silent follow/seek controls, fixture and version selection, an interval-labelled cropped fretboard, separate open strings, exact note contacts, hand position, comparison metrics, and note-data export. No sound is played automatically.

To export the same review as one self-contained offline HTML file:

```bash
python composition-lab/export_fretboard_efficiency_review.py --output /absolute/path/drop-e-efficiency-review.html
```

The exported HTML embeds all fixtures and their available mappings and makes no automatic network requests. Its source-MIDI button opens the recorded GitHub source only when clicked. Older two-version mapping files remain supported; the lesson disables choices absent from the loaded fixture.

## Fixed inputs

| Fixture | File prefix | Notes | Attacks | Duration | Diagnostic purpose |
| --- | --- | ---: | ---: | ---: | --- |
| A: low response | `6_review_cfa029a2…mid` | 164 | 124 | 32.25 seconds | Open-string priority, low response, eventual climb to a high minor-second dyad |
| B: high dyads | `6_review_da80eca9…mid` | 191 | 124 | 32.25 seconds | Repeated high dyads interleaved with lower material; rapid longitudinal changes |
| C: MIDI rewrite (2) | `2026-11-15_midi_rewrite_2.mid` | 241 | 172 | 24 seconds | Revised opening, extended middle, held-note overlaps, new ending and a 96-PPQN source clock |

A/B use 120 BPM and 960 ticks per quarter note. The source files live in `tests/fixtures/fretboard-efficiency/`. A/B each start with two one-second G1–D2–G2 chords, followed by a sustained high chord. Each includes E1–B1 two-note power chords and separate two-note intervals. Their high chords at 2, 10, 18 and 26 seconds contain **two distinct B3 note occurrences**. These are preserved, not deduplicated.

C has 96 ticks per quarter note, no embedded tempo, and therefore uses the MIDI default of 120 BPM. All 4,608 source ticks map exactly to 46,080 native ticks. The lesson converts the native playhead back to the source clock before looking up hand positions. Fourteen attack times contain a previously ringing note; its assigned string/fret stays fixed until its original release. All 217 velocity-90 notes and 24 velocity-74 notes are preserved. The edited file is 24 seconds long, compared with the prior revision's 16 seconds.

For edited C, the feasible greedy baseline has 39 rapid-shift flags, 228 frets of hand travel, and a largest position jump of 14. The original hand optimizer has **0 flags and 0 frets of modeled hand-position travel**, while using all **132 feasible open notes**. Picking cost is 872→1024 and shape cost 1052→1064, consistent with their lower priority. All three C versions were regenerated from the replacement MIDI; both complete A/B fixture objects and all six A/B MIDI exports remain unchanged. C's first revision exposed a local greedy choice that stranded a held note; the existing comparison removes only grips with no feasible held-note continuation before applying its local preferences. That reachability check and all optimizer policies are unchanged by this source update.

## Original hand-movement optimizer

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

## Separate strum/pick optimizer

`fretboard_strum_efficiency.py` provides `optimize_strum_fingering(...)`, a separate search policy. It shares the established playable-grip model but does not call the original optimizer or change its accepted mappings. Its three primary costs are compared lexicographically:

1. **Exact-pitch opens:** minimize eligible note occurrences assigned to a fret rather than their matching open string. Each occurrence is counted once, including notes held across attacks. A lower priority cannot sacrifice a feasible open occurrence.
2. **Strummable chords:** minimize unplayed strings inside the string span of notes attacked at the same original MIDI tick. For sorted attacked strings, cost is `highest_string - lowest_string + 1 - attacked_string_count`. Strings 2/3/4 cost zero; strings 2/4 cost one. A note ringing from an earlier onset does not become another strummed attack and does not fill a missing string in the cost.
3. **Rapid single notes:** for two consecutive attack groups each containing one new note, count `max(0, abs(next_string - previous_string) - 1)` when their original onset gap is at most `rapid_max_gap_seconds`. The default is **0.25 seconds**, inclusive. An intervening chord or larger gap resets the run. Same-string repetitions and adjacent-string crossings both cost zero. Holds, rests and original timing are not shortened to create a run.

The winning primary tuple is `(open_misses, chord_skipped_strings, rapid_single_skipped_strings)`. Only ties across all three use fewer direction reversals within rapid runs, then the existing release-aware rapid-shift cost, total hand travel, and fretting effort. Repeated notes on the same string retain the last nonzero crossing direction; chords and long gaps reset it. A deterministic final order resolves remaining ties. This direction preference helps adjacent-string runs continue in one direction, but does not infer the player's actual downstroke/upstroke convention. Chord pick-order annotations use a canonical low-to-high sweep.

The rapid cutoff uses the fixed source tempo. Changing playback speed in the trainer does not recompute the fingering; regenerate with a different cutoff when a different definition of rapid is wanted.

The new version has ID `strumPick`, its own `objective` settings, and separate `metrics.priority_cost` and `metrics.tie_break_cost`. The original top-level `bundle.model` continues to describe the hand-movement strategy; lesson and review explanations use the selected version's objective. Hand movement, shape and older picking scores remain useful diagnostics, not higher priorities for this profile.

All three priorities remain subject to the same hard string-occupancy, reach and contact constraints. Held occurrences cannot change string or fret before release. Same-string repetitions still need repeated pick attacks; zero skips does not guarantee one uninterrupted sweep. Open-string priority and exact source notes can force unavoidable string gaps. More movement along the neck is an intentional possible tradeoff.

Python API:

```python
from fretboard_strum_efficiency import optimize_strum_fingering

version = optimize_strum_fingering(
    notes,  # distinct id, pitch, start_tick and end_tick per source occurrence
    ticks_per_beat=960,
    tempo_bpm=120,
    rapid_max_gap_seconds=0.25,
)
```

## Original hand-movement results

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

## Strum + pick results

These costs are independently recomputed from the original MIDI attacks. A second dynamic program, which imports no optimizer search or scoring helpers and enumerates playable attacked contacts while reserving held strings, independently proves the exact three-priority minima on all three complete fixtures.

| Fixture | Maximum feasible opens retained | Chord skipped strings: hand → strum/pick | Rapid-single skipped strings: hand → strum/pick | Hand travel: hand → strum/pick |
| --- | ---: | ---: | ---: | ---: |
| A · Low response | 82 | 9 → **3** | 84 → **36** | 12 → 246 frets |
| B · High dyads | 73 | 33 → **15** | 72 → **18** | 84 → 168 frets |
| C · MIDI rewrite (2) | 132 | 0 → **0** | 165 → **54** | 0 → 213 frets |

The independent minimum primary tuples are **A `(4, 3, 36)`**, **B `(4, 15, 18)`**, **C `(0, 0, 54)`**. The first components in A/B are the four unavoidable duplicate-open exceptions described above. Compared with the valid greedy baseline, chord skips tie at 3/15/0 and rapid-single skipped strings improve 53→36, 23→18, and 59→54.

The mappings have **27/30, 42/57 and 69/69 contiguous chord attacks** for A/B/C. Rapid pairs are fixed by the source and cutoff: 83/53/75; only 15/9/17 of those pairs skip any string. The skipped-string totals count every intervening string, not merely the number of affected transitions. All note occurrences, timing, velocities, duplicate pitches and held assignments are preserved, and all nine string exports pass the independent raw-MIDI checker.

This is a distinct picking preference, not a claim of globally easier guitar technique. The substantial increase in neck travel is the consequence of putting adjacency and run direction ahead of hand movement. The original hand-movement optimizer remains selectable and unchanged.

## Output files

- `public/data/fretboard-efficiency-fixtures.json`: exact current source occurrences, parameters, assignments, hand positions, shape labels, picking orders, and measured scores for all three strategies. Adding a strategy to an unchanged source preserves its other accepted versions. Replacing C's source regenerates all three C versions together while retaining A/B.
- `public/fretboard-efficiency/*_strings.mid`: nine standard MIDI exports, one per fixture and strategy. MIDI channels 1–8 correspond to guitar strings 1–8, high to low. Pitches, note-on velocity, onset, release and source duration are preserved; source channel routing is intentionally replaced by string routing. These are ordinary MIDI files, not MPE or a specific virtual-instrument articulation preset.

## Reproduce and verify

Install the single parser/export dependency:

```bash
python -m pip install -r composition-lab/requirements-fretboard-efficiency.txt
python composition-lab/run_fretboard_efficiency.py
python composition-lab/check_fretboard_efficiency.py
```

To regenerate C while keeping the already verified A/B mappings unchanged, use `python composition-lab/run_fretboard_efficiency.py --fixture c5a35486`.

To add or recompute only the separate strum/pick strategy without rerunning or modifying accepted original versions:

```bash
python composition-lab/run_fretboard_efficiency.py --strategy strumPick
```

The source hashes, notes, tempo and ticks must still match the existing bundle. A stale source is rejected rather than combining old and new mappings from different music. Add `--rapid-max-gap-seconds 0.125` to change the rapid-single cutoff, or combine `--fixture c5a35486 --strategy strumPick` to update only C's new strategy.

Run focused tests from `composition-lab`:

```bash
python -m unittest discover -s . -p 'test_fretboard_*.py' -v
```

Native lesson checks use the same pinned alphaTab package as the Pages deployment:

```bash
npm install --prefix .local/qa --no-save @coderline/alphatab@1.8.4
node --test tests/fretboard-efficiency-lesson.test.mjs
```

These checks compare actual native MIDI-generation events against a separate raw-MIDI parser and verify exact string contacts, held-note seeks, partial final bars and existing-score preservation. They fail rather than skip when the required native package is missing. The current lesson-delivery status, live browser checks and deployment receipt are recorded in `FRETBOARD_EFFICIENCY_PROGRESS.md`.

The independent checker parses raw MIDI using only the Python standard library; it does not trust the runner's parsed note list or reported scores. It checks hashes, duplicate multiplicity, exact ticks and velocities, physical string occupancy, hand windows, timing metrics, and every exported MIDI file. Separate strum/pick oracles compute co-attack and rapid-single costs directly from raw occurrences and placements. The tests include held-string conflicts, same-tick retriggers, range failures, an unavoidable earlier-open sacrifice, a zero-shift high-dyad alternative, a held-chord timing counterexample, and a real tradeoff where improving rapid-single adjacency would worsen higher-priority chord adjacency. Tampered source clocks, hashes, deleted duplicates, forged metrics and incorrect exported channels are rejected.

Automated verification for all three strategies: **173 JavaScript tests passed with zero skips; 73 focused fingering Python tests passed; independent source/export check and production build passed.** Twenty existing browser-analysis Python checks also pass, with one pre-existing optional-fixture skip. Forty-two native lesson tests execute the same pinned `alphaTab.js` browser distribution used by the deployed player, preserving exact events for all nine mappings. Sixteen focused selector/review tests cover all three fixtures, all three mappings, legacy uploads, objective labels, missing metrics and source-clock conversion. Live browser playback is recorded separately in the progress document.

Both original A/B optimized riffs were played through in the published trainer, each finishing at exactly 61,920 ticks / 32.25 seconds with no remaining active contacts. Live checks cover sustained-note seeks, both B3 occurrences, the lowest open E1/B1, the B4/C5 high dyad, Pause, Stop, native 0.75x timing, and full-neck/follow controls. The exact mapping JSON was uploaded through the existing Song Player file chooser and played successfully; the original Time lesson then restored normally. An independent join of the retained live DOM observations against the frozen occurrences/assignments verifies all 23 captured active-contact snapshots. See `fretboard-efficiency-live-validation.json` for that receipt and `../FRETBOARD_EFFICIENCY_PROGRESS.md` for current C deployment and playback status. Desktop rendering was inspected; phone rendering is not claimed.

## Limits and next refinement

This establishes exact optimization within the stated reach/contact/position/picking model. It does not certify human comfort, finger independence or real picking technique. Four-contact feasibility and a four-fret span are constraints, not a complete biomechanics model.

Shape support includes drop-power shapes, adjacent-string power shapes, all five major CAGED templates, common E/A/D minor templates, and E/A minor-pentatonic fragments. **Complete 2/3-notes-per-string and arpeggio phrase recognition is not implemented.** These can be added at Tier 5 without overriding higher priorities.

The parser/export pilot handles fixed-tempo note MIDI. It refuses tempo changes and bend/controller messages rather than silently discarding them. A/B have no notes held across later attacks; C supplies real overlap evidence in addition to the authored held-note counterexamples.
