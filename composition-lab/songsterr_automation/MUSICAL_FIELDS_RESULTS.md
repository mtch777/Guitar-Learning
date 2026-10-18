# Source technique analysis: measured results, 2026-10-17

This release extends analysis, not validated artist-style generation. See
TECHNIQUE_ANALYSIS_CONTRACT.md for definitions and outstanding semantic gates.

## Findings

- All 98 entries / 495 tracks processed. Guitar/bass scope is 413 tracks after
  catalog vocal/empty exclusions. 339385 regular guitar/bass written segments and
  316030 attacks reconcile with the earlier inventory; scope changes do not delete notes.
- 55 voice/bar overflow observations across 25 tracks remain quarantined from
  temporal candidates. Source observations remain available. No identity, shared
  meter or timeline warnings were observed. Physical notation flags are not claims
  of musician playability.
- Corrected raw bend labels: tone/25 is quarter-tone units; semitones use tone/50.
  The former raw-analysis v1 labels were doubled. Existing GP conversion and audio
  were not doubled by this labeling bug. Private v1 reports remain preserved.
- Precise curve positions use /100 when supplied; coarse positions use /60.
  Captured precise values differ from coarse fractions in 25/216 observed points.
  Point vibrato, curve slopes, excursions and held-neighbor center intervals are
  recorded without asserting physical vibrato rate or emotional purpose.
- Shared meter/pickup layout, explicit rests, bounded nested repeat/ending visits,
  step-tempo and sound-change timelines added: 52660 rest spans, 139 tempo points,
  12 sound changes, 11137 written bars / 11718 playback visits; all 98 repeat maps
  complete. No actual shortened pickup was found under the stated rule.
- 306364 sustained guitar gestures; 94466 technique gestures, 295 with held
  neighbors. All observed technique contexts have step-tempo seconds. Linear
  ramps/conflicting tempo abstain; none were observed. Harmonic sounding pitch and
  unquantified vibrato intervals remain unresolved rather than guessed.
- Brush upStroke overrides raw direction: 451 note-scope observations have raw
  direction down but effective direction up. Beat events and note-scope counts
  must not be confused. Brush duration/shift native API units remain unresolved.

## Independent verification

The new validator imports no production detectors. Raw readback covers all
420119 written/grace occurrences across all instruments: exact occurrence-set
coverage on 495 tracks and raw note, identity, duration and written-pitch checks
on each occurrence. Zero failed checks.

An independently expressed interval/set oracle checks all 190890 eligible attack
groups, including negatives and missing detections: 28187 double stops, 2933 exact
semitone textures, 17683 power chords, 11091 extended power chords. All group-label
comparisons agree. 9707 HP candidate pair invariants pass. These establish rule
conformance, NOT independently labeled musical precision/recall or transcription
truth. 102 tracks are excluded from this group audit by instrument/timing scope.

Private deterministic inspection seeds: 168 source-located samples across 14
positive/negative or marked/unmarked strata. Existing 88 evidence cases / 2904 raw
context-control occurrences were reverified. Sampling is an inspection seed, not
a population accuracy estimate. Human labels remain empty.

Strict observed-field coverage: 218 paths = 114 analyzed at differing depths,
77 retained only, 11 unsupported, 16 outside technique scope; zero unmapped.
Detailed matrix and implementation hashes: API_FIELD_COVERAGE.md and results/.

## Real-source controlled comparison infrastructure

Private source-technique-passages-v5 contains 8 modified full-source GPs and
16 fixed-gain previews across four source passages: brush spread, bend arrival,
tremolo picking, and contextual arm-curve transfer. The last two inspect captured
API mechanics; tremolo picking is not substituted for requested finger vibrato.
Four byte-identical zero-lock baselines are retained privately, not presented.
Unrelated archive/XML data remains locked. Independent GP reopen, MIDI differences,
finite/nonzero/unclipped audio and nonidentical paired audio verified. Earlier
ineffective tied/dead-note candidates were rejected; v1-v4 artifacts preserved.
Source locations, edit descriptions and transfer origin are visible in the review.

Local review: http://127.0.0.1:5183/ while the private server runs. Browser media and
controls were exercised; no musical listening verdict was inferred. GM soundfont
preview does not establish authentic guitar articulation or source feel.

## Reproduction

From repository root, using the existing isolated songsterr Python environment:

```text
python composition-lab/songsterr_automation/songsterr_api/analyze_relationships.py composition-lab/local-artifacts/invent-animate-corpus-v1/songs --out composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json --aggregate composition-lab/songsterr_automation/results/corpus_relationships_v2.json
python composition-lab/songsterr_automation/songsterr_api/build_analysis_evidence.py composition-lab/local-artifacts/invent-animate-corpus-v1 --aggregate composition-lab/songsterr_automation/results/corpus_relationships_v2.json
python composition-lab/songsterr_automation/songsterr_api/validate_technique_analysis.py composition-lab/local-artifacts/invent-animate-corpus-v1/songs --report composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json --public composition-lab/songsterr_automation/results/technique_validation.json --private composition-lab/local-artifacts/invent-animate-corpus-v1/technique-validation.json
```

Strict field audit reproduction is in API_COVERAGE_PROGRESS.md. Source material,
raw evidence, weights and feedback remain ignored. New tests include injected
missing detections and corrupted durations, not only passing examples.

## Remaining acceptance

Independent semantic labels are still needed for pedal function, phrase/role
interpretation, resolution and source-feel preservation. Parser checks cannot
answer these. Notation-only vibrato cannot provide physical speed/depth. The
24 detailed GP roundtrip failures remain flagged, not repaired by this release.
Do not mark step 2 musically validated on the strength of these engineering checks.
