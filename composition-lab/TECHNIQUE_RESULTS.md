# Guitar technique controls — execution results

2026-10-16. Current implementation supersedes the earlier endpoint-only milestone. This is an analysis/control experiment system, **not a trained artist-style composer**. Human musical acceptance is pending.

## Delivered and measured

| Work | Actual evidence | Acceptance limit |
|---|---|---|
| Fretted/open-string hammer-ons and pull-offs | Directed analysis; exact source locks; two scripted methods; 0–100 integer freedom | Existing same-string notes only; unsupported shared note definitions rejected |
| Finger vibrato | Separate Slight/Wide methods; marker-only edits; open strings excluded from new proposals | Generic GP notation does not contain a physical rate/width; synth interpretation is separate |
| Arm vibrato | Explicit beat marker preserved and independently checked on Time | Arm generation not substituted for finger vibrato |
| Pedal, close dyads, power/extended power, double stops | Occurrence-cloned construction with explicit pitch AND voicing permission; rhythm locked | Generic bounded shape/anchor rules, no inferred artist intent or validated phrase model |
| Intermediate freedom | Nested deterministic release of eligible relationships/events; whole measures released for pedals | Percentage is reference release, not measured musical difference or a probability |
| Real-score construction transfer | 30 nonempty variants across three scores; all independent stringed-note imports agree | Written pitch/string/fret checked; harmonic sounding pitch/percussion excluded from this independent pitch comparison |
| Authored controlled probes | 80 actual GP files; 80 independent imports; 80 finite, nonzero, unclipped instrument WAVs | Diagnostic material, not new full compositions or style-transfer evidence |
| Review | Ten technique families, 35 distinct A/B pairs; two rolls, strength selection, loop, synchronized switching, GP download, versioned feedback | One empty-strength pair and four identical-audio pairs withheld; no original/no-technique control offered |
| Human musical results | Zero new judgments | No musical quality, artist fidelity, originality certification, or authentic legato claim |

Full-score guitar-only construction modifies 104 eligible events per Time case (track 4), 706 per Cloud case (track 2), and 505 per Sweet case (track 3). Ten cases per source: five families × two methods. Unsupported/tied/technique-bearing events remain untouched. Original definition tables remain immutable; cloned ancestor paths isolate occurrences. All other archive assets remain byte-identical. Source GP files stay private.

0% copies source bytes. At 100%, performance proposals ignore original selected annotations; construction proposals ignore original event pitch values, while still using locked tuning, timing, safety eligibility and track context. Tests perturb those reference values. No forced difference is imposed. Intermediate controls deliberately retain the unreleased reference subset. Rule method and freedom are independent controls.

HOPO previews use alphaTab internal MIDI and Sonivox sampled guitar. This engine primarily changes destination dynamics; **authentic hammer/pull attack is not certified**. Vibrato has independently observed pitch events. The browser now receives byte-range audio responses so A/B switching retains playback position. Hearing a working audio file is not a listening verdict.

## Reproduce

- `python composition-lab/technique_report.py INPUT.gp [INPUT2.gp ...] --out PRIVATE/report.json`
- `python composition-lab/technique_edits.py INPUT.gp --out PRIVATE/new.gp --track 0 --family hammer_on_fretted --strength 50 --method short_intervals`
- `python composition-lab/pattern_edits.py INPUT.gp --out PRIVATE/new.gp --track 0 --family power_chord --strength 100 --unlock-pitch --unlock-voicing`
- `python composition-lab/benchmarks/pattern_edit_benchmark.py INPUT1.gp INPUT2.gp INPUT3.gp --out NEW_PRIVATE_DIRECTORY`
- `python composition-lab/build_technique_review.py --out NEW_PRIVATE_DIRECTORY`
- `node composition-lab/render_gp_instrument.mjs ALPHATAB_MODULE SONIVOX_SF2 VARIANT.gp ...` (exclude diagnostic reference from listening)
- `node composition-lab/verify_pattern_import.mjs ALPHATAB_MODULE VARIANT.gp ...`
- `python composition-lab/finalize_technique_review.py NEW_PRIVATE_DIRECTORY`
- `python composition-lab/serve_private_review.py NEW_PRIVATE_DIRECTORY --port 5180`

Final private outputs: `local-artifacts/technique-review-v6/`, `local-artifacts/pattern-edits-v3/`, and `local-artifacts/technique-multiscale-v1/`. All earlier artifacts and bend baselines retained. Loopback review URL: http://127.0.0.1:5180/ (requires the local server). Public aggregate: `benchmarks/technique_construction_results.json`. No public website assets changed, so no Pages deployment was needed.

Multiscale reports retain counts/denominators, track and source-section coverage, HOPO interval/fret/duration relationships, simultaneous group duration/co-attack/overlap/effect uncertainty, pedal candidates and threshold sensitivity, and staff property inventories. Missing validated phrase boundaries and artist corpus identity remain explicitly unknown. The three different artists are not pooled into an invented artist model.

## Remaining acceptance gates

- Human review of placement/function and physically credible performance; authentic HOPO tone cannot be certified with this renderer.
- Pedal/motif/phrase function and transformations require labeled evidence; deterministic candidates are available, not verified musical roles.
- Full ergonomic validation goes beyond distinct strings and a four-fret stopped span. No universally playable fingering claim.
- Unmodeled staff/effect semantics, sounding intervals under bends/harmonics, and phrase-conditioned learned proposals remain explicit limitations. Source metadata is preserved rather than silently rewritten.
- Current experiments deliberately retain much source material under locks. They do not establish originality of a new composition or multi-song artist learning.

Verification at this milestone: 169 Python tests, 16 JS tests and Vite build pass. Implementation commit `96fcbd1` is on origin/main; [GitHub CI run 39004239874](https://github.com/mtch777/Guitar-Learning/actions/runs/39004239874) succeeded. QA-only feedback is labeled and isolated from the blank human review.
