# Pedal call/response analysis

Pedal identification is accepted by the user. This work measures how accepted
anchor hypotheses alternate with surrounding material; it does not reopen the
identification review or request another generic listening round.

## Acceptance checklist

- [x] Define call, response, mixed attacks and scope explicitly.
- [x] Preserve exact occurrences, strings/voices, rational timing and tied sustains.
- [x] Measure call bursts and response pitches/intervals, durations, onset patterns,
  textures, techniques, gaps, overlaps and return periods.
- [x] Compare repeated calls and replies separately; count varying replies to the
  same call; preserve exact and time-scaled rhythmic signatures.
- [x] Run full eligible corpus and audit event/cycle coverage.
- [x] Generate private source-located examples and source-free aggregate results.
- [x] Regression tests/build, commit/push and remote CI verification.

## Measurement contract

- Call: an attack group containing only the anchor pitch or interval constituents.
- Response: subsequent attack groups containing no anchor constituents, ending
  at the next anchor return, mixed/unknown event, next anchor region or source
  section boundary. These are operational labels, not inferred emotional purpose.
- Mixed: anchor and other notes attacked together; retained separately, never
  forced into an invented monophonic response.
- Unknown: an attack contains unpitched/unknown notes; retain occurrences and abstain.
- Scope starts at the anchor region and ends at the next region or source section.
  Final unclosed responses are censored; this is not a claim of phrase endings.
- Ties extend sustains but do not create attacks. Unmarked let-ring and performed
  articulation are not guessed. Pitch intervals describe written pitches.

For each call and response retain exact pitches/pitch sets, anchor-relative
intervals to lowest and each anchor constituent, monophonic melodic steps,
simultaneous intervals, source IDs/string/fret/voice, note durations, tied lengths,
onset offsets, IOIs, span, texture and technique observations. Each exchange adds
call/reply gap or overlap, return period, response/call span ratio and final
response-to-anchor intervals. These are observations, not harmonic resolutions.

Consistency counts use comparable uninterrupted neighboring exchanges. Same-call
families count distinct observed answers and their frequencies. Rhythm signatures
are exact; scaled signatures normalize rational offsets/durations to the first
positive IOI (single attacks use sustain). No perceptual similarity score is invented.

## Reproduction

```text
python composition-lab/songsterr_automation/songsterr_api/analyze_pedal_dialogue.py composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json composition-lab/local-artifacts/pedal-feedback-v2/corpus-regions.json --public composition-lab/songsterr_automation/results/pedal_dialogue.json --private composition-lab/local-artifacts/pedal-dialogue-v1/dialogue.json
```

Private feedback, raw patterns, source pitches and scores stay ignored. Published
corpus counts pool entries, not deduplicated artist estimates. Musical role and
phrase interpretation remain separate from these exact measurements.

## Corpus execution results

1563regions;16814operational exchanges:15295closed by an anchor return,
1519censored.650calls sustain into the following response. Attack groups:
52451call,109824response,11697mixed,1148unknown. Response textures:
14289monophonic,1960polyphonic,565mixed.

Integrity audit passed on all1563regions,255339attack occurrences and16814cycles:
exact expected occurrence coverage, no duplicate cycle assignment, valid temporal
ordering. These checks establish accounting, not musical-function accuracy.

13904uninterrupted neighboring exchange pairs were comparable:
- Call pitch sequence identical:9688/13904.
- Call rhythm identical:8935/13904.
- Response pitch sequence identical:3782/13904.
- Response rhythm identical:5552/13904.
- Response rhythm equal under time scaling:5827/13904.
- Same call pitch/rhythm followed by a changed response:5810/13904 of ALL comparable
  pairs (not a conditional percentage among same-call pairs). Per-call answer
  frequency tables provide the conditional view privately.

These pooled entry counts are not deduplicated artist statistics or perceptual
similarity. Private SOURCE_EXAMPLES.md gives six source-located tables; dialogue.json
contains full event/cycle/family evidence. No new listening verdict or generated GP
is implied by these analysis measurements.

Release211e3fd pushed to origin/main. Composition CI39101152171 success: https://github.com/mtch777/Guitar-Learning/actions/runs/39101152171 .223Python tests(222pass/1optional skip),21JS/build pass. No website changes. Private artifact paths remain untracked.
