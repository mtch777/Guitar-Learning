# Pedal correction acceptance ledger

Baseline: main `33b8136`. Private frozen detector and source-result references:
`local-artifacts/pedal-correction-v1/baseline.json`. Never overwrite prior reviews.

- [x] Pull main safely; inspect current detector, tests and feedback audit.
- [x] Freeze baseline code and identify unchanged corpus results.
- [x] Reconcile all historical judgments, including latest reversals, into private
  occurrence-level regression inputs. Acceptance: every recorded judgment has a
  disposition; positives and negatives both evaluated; ambiguous scope explicit.
- [x] Compare isolated policies for same-onset exclusion, local anchor recurrence,
  temporal connectivity and chord/arpeggio distinction. Acceptance: reproducible
  comparative results, source occurrences unchanged, no song-name detector rules.
- [x] Implement justified correction with exact rational evidence. Acceptance:
  every answer starts strictly after its associated call; repeated exchanges have
  local anchor evidence; unrelated sections cannot supply recurrence.
- [x] Run all labeled passages and full corpus. Acceptance: report all regressions,
  changed roles and boundaries, not only favorable positive-note coverage.
- [x] Self-QA review output, browser rendering and interactions. Acceptance: full
  note range, populated controls, accurate source context, understandable reasons.
- [x] Run relevant Python/JS tests and build; commit/push verified changes; inspect
  CI and Pages if website changes. Acceptance: actual remote success documented.

No claim of perfect musical classification follows from passing software tests.
Do not promote a replacement while known acceptance failures remain unexplained.

## Execution evidence

- Baseline source and media preserved; main safely pulled before edits.
- Sealed detector SHA256: `4ddb8ebaaf574c5177720812a00b8488c81094eecdce0e972fe4547e110126c2`.
- Eight policy configurations plus a rejected identity-first alternative tested.
- 28/28 bounded decisions and 176/176 latest marked notes retained. All 1,854
  source scopes audited; 908 accepted, 266 removed, 609 retained with changed
  highlights; zero newly accepted scopes; 98,737 changed role occurrences.
- Context investigation found recursive register drift; source-measure register
  context now survives recursion. Remaining excerpt/full-scope differences are
  displayed with complete supporting exchanges and closing returns. They do not
  override the bounded negative judgments.
- Final review: 906 entries / 3,820 audio parts / 210,856 source note displays /
  93 byte-identical score copies. 141 parts explicitly lack an automatic audio
  preview because of repeat mapping/duration; source notes and full GP remain
  available. No unavailable preview is passed off as listening evidence.
- UI QA found and fixed UTF-8 decoding, startup readiness, immediate comment
  persistence, viewed-only export entries, source-scope wording and unrelated
  highlights leaking into a selected support-pattern view.
- All 28 recorded cases were opened in the real browser with populated controls,
  correct source titles and complete note displays. Further final browser and
  remote checks below are pending until recorded as completed.

## Acceptance still requiring a human

The corrected method remains opt-in. Software checks cannot establish perceived
musical call/response or meaningful phrase continuity across the new corpus
results. After final engineering/remote checks, use the prepared source review
for that listening gate. Do not claim global precision or musical perfection.

## Final local verification

- `python -m unittest discover -s composition-lab -p test_*.py`: 264 tests run,
  263 passed, one optional skip; no failures.
- `node --test tests/*.test.mjs`: 23 passed.
- `node node_modules/vite/bin/vite.js build`: passed.
- Release source audit: all 210,856 note displays matched exact source identity,
  pitch, onset, duration, bar and tie status; all 93 score copies hash-identical.
- Browser: source audio ready (44.1-kHz renderer checks finite/non-silent PCM),
  playback advanced and cursor moved; note click sought to 0.47244 seconds with
  matching cursor position. This is playback functionality, not a listening verdict.
- Actual JSON download verified: QA=true, one marked original occurrence and the
  complete typed comment; viewed-only empty cases excluded. Human storage remains
  separate. First-case readiness is awaited before enabling the form.
- Final private review: `http://127.0.0.1:5195/` (loopback only; server required).
  Browser file:// interaction is prohibited by browser tooling; file redirect is
  covered by executable JS tests instead of a false browser-verification claim.

Remote publication/check results are recorded after the verified commit is pushed.

## Remote publication

- Implementation `1e78024c532d41160dfa5dae01a9445290ea96e6` committed and pushed
  to `origin/main`, after a fresh `pull --rebase` confirmed no concurrent updates.
- [Composition Lab CI](https://github.com/mtch777/Guitar-Learning/actions/runs/39161919873): success on that exact commit.
- [Existing Pages build/publish workflow](https://github.com/mtch777/Guitar-Learning/actions/runs/39161919886): success on that exact commit. The private source review is not included in Pages.
- No GP source, private feedback, corpus notes, rendered commercial-source audio,
  dependencies, model weights or secrets were staged or published.

Engineering implementation and reproducible checks are complete for this review
candidate. Musical acceptance is intentionally not marked complete. The baseline
remains available/default; the prepared correction is opt-in pending listening.

- Live public site returned HTTP200. Published JS/CSS asset references match the
  tested build; HTML differs only by blank lines/platform formatting. No private
  review data is present in the public build.
- Final browser deliverable is on port5195 without QA mode; human comments and
  marks verified empty. QA export/download data remains isolated. A screenshot
  is preserved privately in `review-release/review-proof.png`.
- GitHub CLI is unavailable on PATH; remote runs were verified through the
  connected GitHub API rather than assumed from a successful push.
