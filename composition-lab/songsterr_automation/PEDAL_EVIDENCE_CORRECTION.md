# Pedal evidence correction — 2026-10-18

## Release status

Implemented and evaluated as a separate method, preserving the frozen register
baseline and all earlier private reviews. Musical acceptance is still a human
listening gate. The baseline remains the default of `rebuild_pedal_review.py`;
`--evidence` explicitly selects the correction. The new evidence-review builder
always uses the correction. No generation, artist profile, source score, audio
performance or public guitar-learning feature was changed.

## Requirements and root causes

A recurring local anchor must have later-starting answers and repeated exchanges.
Notes attacked with the anchor cannot answer that attack. The anchor may ring
under a later answer. Different anchor pitches require their own evidence; merely
returning to a low register is insufficient. Chords in lockstep and routine
uniform chord walks do not establish a pedal. Arpeggio-like movement alone is not
grounds for rejection when a differentiated recurring anchor/answer exists.

The old implementation pooled pitch identity across a broad register, labeled
upper coattacks as answers, borrowed recurrence across scope and treated tied
chord members as absent when judging the written voicing. Intermediate pruning
could also leave orphan highlights. Recursive subscopes changed register
eligibility by losing the rest of a source measure. These are separate failures;
changing one threshold was not a sufficient correction.

## Implemented constraints

- Exact rational attack grouping; immutable original occurrences; tied
  destinations never count as new attacks. Explicit dead strikes retain their
  identity without supplying an invented pitch or answer.
- Call runs retain a common local anchor identity instead of merging unrelated
  low pitches. Repeated identities, independently observed small voicings and
  actual returns are checked before assigning roles.
- Qualifying answers begin strictly after their call. Coattacked upper notes
  remain context unless independently justified as part of an interval anchor;
  they never become simultaneous answers.
- Local source-measure register context is retained through recursive analysis.
  Distant pitch extrema cannot change an exchange's low/middle eligibility.
- Written chord voicings include ties. Repeated full chord blocks cannot
  manufacture standalone root calls through changing attack subsets.
- Whole-scope and local uniform chord-walk exclusions are separate from
  differentiated pedal evidence. Lower answering accents can supplement an
  established pattern; they cannot manufacture its initial acceptance.
- Final roles are revalidated into connected chains of at least two exchanges.
  Invalid units cannot leave isolated calls behind. Inner-pattern role updates
  are atomic at a shared onset, preventing conflicting call/response labels.
- Complete support bounds include the closing anchor burst and its tied sustain.
  Review windows distinguish a self-contained pattern from a closing return or
  continuation whose supporting exchanges lie outside a short excerpt.

The observed-pitch split, midpoint register criterion, recurrence counts, chord
families and four-times-median connectivity policies are operational hypotheses,
not universal musical laws. They remain explicit and testable. No song names,
artist names, track-name exclusions or case-specific detector exceptions exist.

## Experiments and measured results

Private experiment archive: `local-artifacts/pedal-correction-v1/`.
The sealed run is `evaluation-sealed/`; intermediate runs are not release
evidence. In particular, `evaluation-final/` was superseded because code changed
during that run. The evaluator now refuses to seal a mixed-version run.

- Reconciled 21 exported judgments into latest-judgment dispositions and added
  subsequent reported cases: 28 bounded regression excerpts.
- Combined method: 28/28 bounded decisions; all 176 latest marked anchor notes
  retained. These are selected development judgments, not independent accuracy.
- Eight controlled policy configurations were compared. Timing alone matched
  22/28; removing local identity, arpeggio exclusion or local register each
  reduced agreement to 27/28. Other individual removals retained 28/28 on this
  small set; adversarial tests supply separate evidence for those safeguards.
- A separate identity-first comparator lost approved decisions/markings and was
  rejected. Its code/results remain in the private experiment archive.
- Full corpus: 1,854 source scopes; frozen baseline accepted 1,174, corrected
  method accepted 908; 266 lost the label, none newly gained it. Another 609
  scopes retained acceptance with changed highlights. 98,737 occurrence roles
  changed. These numbers describe changes, not musical accuracy.
- All 176 marked notes also survive full-source analysis. Two excluded short
  excerpts contain members of longer supported patterns. The local-register
  sensitivity bug was corrected. The remaining context cases are displayed as
  three complete support patterns, not as new pedals inside the rejected clips.
  Their musical connection requires listening acceptance.
- Every scope was audited for source identity, ties-as-attacks, strict answer
  timing, shared-onset conflicts and consistency between cycle members and roles.

## Review and reproduction

New source templates: `pedal-evidence.html` and `pedal-evidence.js`. Private review
contains all 28 recorded cases, the three complete support patterns, every removed
scope and every retained scope with changed highlights. Source GP files are copied
byte-identically; both modes use the same unchanged synthesized source playback.
This is not generated composition audio.

The roll shows the complete displayed passage and explicit active audio part,
pitch rows, bar markers, playhead and clickable notes. Tied sustains are distinct
from new attacks. Closing returns are identified on inspection. Feedback supports
note marking, plain-language choices, immediate comment saving, reload and JSON
export. QA feedback is stored/exported with `qa: true`, separately from human
feedback; viewed but unanswered cases are not exported as judgments. Startup waits
for the first case before enabling the page. File opens redirect to loopback;
direct browser file access is not claimed as tested.

Reproduction commands, from the clone (private inputs are required):

```powershell
.venv/Scripts/python.exe composition-lab/evaluate_pedal_evidence.py composition-lab/local-artifacts/pedal-correction-v1/fixtures.json composition-lab/local-artifacts/pedal-correction-v1/scopes-with-effects.json composition-lab/local-artifacts/pedal-correction-v1/FRESH-EVALUATION
.venv/Scripts/python.exe composition-lab/songsterr_automation/songsterr_api/build_pedal_evidence_review.py composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json composition-lab/local-artifacts/pedal-correction-v1/fixtures.json composition-lab/local-artifacts/pedal-register-review-v4/corpus-analysis.json composition-lab/local-artifacts/pedal-correction-v1/evaluation-sealed/corpus-analysis.json composition-lab/local-artifacts/invent-animate-corpus-v1/songs composition-lab/local-artifacts/pedal-correction-v1/FRESH-REVIEW
.venv/Scripts/python.exe composition-lab/verify_pedal_evidence_review.py composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json composition-lab/local-artifacts/pedal-correction-v1/review-release composition-lab/local-artifacts/invent-animate-corpus-v1/songs
.venv/Scripts/python.exe -m unittest discover -s composition-lab -p 'test_*.py'
node --test tests/*.test.mjs
node node_modules/vite/bin/vite.js build
```

Never publish the fixtures, source corpus, feedback exports, source GP files,
rendered commercial-source audio or private score-specific diagnoses. Only code,
source-free tests, aggregate measurements and documentation belong in Git.
