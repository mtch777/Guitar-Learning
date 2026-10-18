# Additive pedal phrase continuation

The evidence detector is unchanged (SHA256
`4ddb8ebaaf574c5177720812a00b8488c81094eecdce0e972fe4547e110126c2`).
`pedal_expansion.py` consumes existing supported patterns. It cannot create a new
detection without a seed, remove a seed, shorten its bounds, or change its
original call/response assignments. Inputs are not mutated.

## Method

1. Preserve every supported chain, including closing returns and tied tails.
   Canonicalize pre-existing overlaps before comparing phrase boundaries.
2. At each boundary, follow the exact established pitch or pitch group, not an
   octave equivalent or a different low note. Inspect original track context,
   including across notation section markers; markers alone are not boundaries.
3. Require a strictly later contrasting answer and a return to that same anchor.
   One additional complete exchange can extend AFTER an established pattern.
   BEFORE requires two complete, upward-answer exchanges. These thresholds are
   explicit operational policies, not claims about universal musical rules.
4. A simultaneous upper note never answers its accompanying call. Unknown notes,
   changed anchor coattacks, chord blocks, uniform chord walks and a substantial
   break in the observed attack cadence stop the search. The existing arpeggio
   predicates are reused; the detector itself is not rerun with weaker gates.
5. A rare lower reply is allowed after an established anchor only when the added
   sequence also has upward answers; a repeatedly recurring lower pitch cannot
   supply that exception. Ties lengthen sustain without counting as attacks.
6. Bound the search by four times the observed median return period and silence
   by four times the observed attack cadence after note release. No song names,
   manually chosen pitches, fixed bar crops or per-example overrides are used.
7. An existing neighbor is a barrier unless an actual same-anchor exchange
   connects to its boundary. Connected intervals are unioned once; their original
   seed identities and every original occurrence are retained. Output intervals
   are disjoint, with no duplicate exchange triples.

The pass has a deliberately narrower responsibility than detection. It does not
reassess previously accepted material, infer intent, or claim new musical quality.
It is an explicit downstream stage, not a silent change to existing detector
defaults. The prior review and sealed analysis remain untouched.

## Corpus verification

All 2,239 input support chains remain represented. They initially form 2,018
disjoint groups because some existing chains already overlap. The pass produces
1,902 disjoint phrases: 1,724 unchanged and 178 expanded/combined outputs.

| Exclusive diff category | Output phrases/groups |
| --- | ---: |
| Existing phrase, continuation BEFORE | 20 |
| Existing phrase, continuation AFTER | 71 |
| Existing phrase, continuation BEFORE AND AFTER | 15 |
| Existing phrases, continuation COMBINED them | 72 |

There are 400 additional complete exchanges. Combined outputs absorb 116
boundaries between original disjoint groups. A smaller output count is merging,
not removed detections. Every seed maps to exactly one output containing its full
range, all members, and its original roles. No newly accepted source scopes are
expected: this pass only expands existing patterns.

Evaluation asserts source identity, exact rational bounds, attack-only evidence,
strict answer timing and retained roles. Separate tests cover all four outcomes,
asymmetric thresholds, merging/barriers, coattacks, chord walks, changed anchors,
silences, tied tails, final bursts, rare lower accents and input immutability.

## Private review

`http://127.0.0.1:5196/` serves four exclusive queues, using the existing verified
piano roll and unchanged GP renderer. Original bounds are orange; expanded bounds
are green. All source notes remain visible in both modes; only highlights change.
Source GP files are byte-identical copies. Existing conversion-fidelity flags
remain visible. Note seeking, playback cursor, marking, browser persistence and
feedback export are retained, with separate automated-QA storage.

The review has 178 cases, 426 consecutive audio parts and 19,785 source note
displays across 57 score copies. 42 parts explicitly lack automatic previews
because of existing repeat mapping/duration limitations; the complete source
notes and full GP remain available. Audio is prepared locally on request.

Reproduce from the repository root, with private inputs available:

```powershell
.venv/Scripts/python.exe composition-lab/evaluate_pedal_expansion.py composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json composition-lab/local-artifacts/pedal-correction-v1/evaluation-sealed/corpus-analysis.json composition-lab/local-artifacts/pedal-expansion-v1/FRESH-EVALUATION.json
.venv/Scripts/python.exe composition-lab/songsterr_automation/songsterr_api/build_pedal_expansion_review.py composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json composition-lab/local-artifacts/pedal-expansion-v1/FRESH-EVALUATION.json composition-lab/local-artifacts/invent-animate-corpus-v1/songs composition-lab/local-artifacts/pedal-expansion-v1/FRESH-REVIEW
.venv/Scripts/python.exe composition-lab/verify_pedal_evidence_review.py composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json composition-lab/local-artifacts/pedal-expansion-v1/FRESH-REVIEW composition-lab/local-artifacts/invent-animate-corpus-v1/songs
```

Source scores, private diagnoses, feedback and audio must not enter Git or Pages.
Engineering invariants and recorded source evidence pass; the musical connection
of expanded passages remains for listening review. No human judgments are invented.
