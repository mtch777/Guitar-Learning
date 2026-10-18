# Pedal call/response breadth explorer

Private interactive explorer: http://127.0.0.1:5189/ while the local server runs.
16examples across15candidate song families, unchanged source GPs and32previews.
All13script-selection categories found eligible sources;3earlier human-reviewed
outside-rule contrasts added. Scope is the captured corpus, not all music genres.

## Acceptance checklist

- [x] Regular repetition, varying answers, interval anchors, long/short replies,
  changing response rhythm, polyphony, semitone dyads, held overlap, nonbinary
  subdivisions, mixed attacks, sparse returns and interrupted/unclosed exchanges.
- [x] Add outside contrasts: chord arpeggio, chord playing and insufficient returns.
- [x] Non-AI/non-junk metadata, detailed GP roundtrip pass, temporal eligibility,
  unique source-bar playback visits,4–25second selected excerpts.
- [x] Limit overlapping excerpts and cap two selections per candidate family;
  choose rare categories first rather than exhaust their sources on common cases.
- [x] Preserve source bytes, exact timing/roles, source/track/bars and model caveats.
- [x] Color full continuing region within the excerpt; table focuses on selected
  exchanges. Mixed groups distinct; no polyphonic melody invented.
- [x] Synchronized playhead, sounding-note outline, clickable inspection/seek,
  exchange playback jumps, group filters, exact musical measurements and GP links.
- [x] Verify16sourceGPs against actual corpus bytes;32audio files valid;
 26newrendered hashes verified and6contrast clips copied from prior studies.
- [x] Commit/push and remote CI: delivery evidence in MUSICAL_FIELDS_PROGRESS.md.

## Selected example categories

Regular returns; same call/different answer; interval anchor; short call/long
answer; long call/short answer; changing answer rhythm; polyphonic answer;
close-interval color; call sustain overlap; uneven subdivisions; mixed attacks;
minimal returns; interrupted/unclosed exchange. These are exact scripted properties,
not claims that a musician would agree an example is clear, classic or borderline.

The user asked to understand the widest scope. This is selective coverage rather
than a randomized evaluation. No musical quality ratings are inferred. Prior
accepted identification remains accepted. Edges expose limitations, not new rules
hard-coded from the examples. No source scores/audio are published.

## Reproduce in a NEW private folder

```text
python composition-lab/songsterr_automation/songsterr_api/build_dialogue_explorer.py composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json composition-lab/local-artifacts/pedal-dialogue-v1/dialogue.json composition-lab/local-artifacts/invent-animate-corpus-v1/songs NEW_LOCAL_ARTIFACTS_FOLDER
node composition-lab/render_source_passages.mjs ALPHATAB_MODULE SONIVOX_SF2 NEW_LOCAL_ARTIFACTS_FOLDER/render-jobs.json
```

Copies of prior contrast sources are required locally. Browser page loads only
private same-origin cases.json and media; all source text uses textContent.
Detailed note values and score identity remain in local-artifacts, never Git.

Verification:225Python tests(224pass/1optionalskip),21JS/build pass. Browser checks:
exchange jump advances audio/playhead; edge filter stops previous audio; outside
filter clears the exchange table and shows exclusion explanation. Note inspection
and full-source/media accounting checked. Screenshot kept privately.

Release d1409b0 pushed; Composition CI39101712323 success: https://github.com/mtch777/Guitar-Learning/actions/runs/39101712323 . No public website changes; source examples remain private.
