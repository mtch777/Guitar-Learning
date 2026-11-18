# Phoebe Bridgers — I Know the End

Playable default: [phoebe-bridgers-i-know-the-end.musicxml](./phoebe-bridgers-i-know-the-end.musicxml).

This is **Edgar Roock's piano arrangement**, converted from the existing MIDI
that he links in his [original-key video](https://www.youtube.com/watch?v=qjnUrgG_hv4).
It is not a transcription of the studio recording. No scanning, PDF recognition,
audio transcription or newly invented notes were used.

## Preserved source and conversion

| File | Purpose |
| --- | --- |
| [Original MIDI](./phoebe-bridgers-i-know-the-end.mid) | Unmodified author download; all original events and timings |
| [MusicXML](./phoebe-bridgers-i-know-the-end.musicxml) | Readable two-staff piano score for both lesson modes |
| [Source events](./phoebe-bridgers-i-know-the-end-events.json) | Exact note ticks, MIDI pitches, channels, velocities and controllers; derived notation timing alongside each note |
| [Provenance](./phoebe-bridgers-i-know-the-end.provenance.json) | Source URLs, hashes, conversion decisions and measured timing differences |
| [Validation](./phoebe-score-validation.json) | Actual lesson parser, renderer, cursor and grading-color results |

All **1,396 original note occurrences and pitches** appear in the lesson.
The notation has 1,426 pitched segments because some held notes are split and
tied, plus 196 rests. There are 128 measures, 510 quarter-note beats and
323.957052 seconds of music at source tempo. Playback changes from 75 BPM to
112.00005973336519 BPM at beat 192, matching the MIDI tempo events.

This preserves the MIDI source losslessly, but the **derived notation is not an
exact timing round trip**. Note starts and releases snap to the nearest 1/32 note:

| Timing | Changed notes | Largest shift | Mean absolute shift across all notes |
| --- | ---: | ---: | ---: |
| Note start | 9 / 1,396 | 1 tick / 1.667 ms | 0.0096 ms |
| Note release | 115 / 1,396 | 29 ticks / 36.667 ms | 0.6814 ms |

Original track 1 becomes the treble staff and track 2 the bass staff. Overlapping
notes receive separate voices. D-flat major spelling is enharmonic to the
author's stated C-sharp major; the MIDI's inconsistent C-major key tag is not
copied into the notation. Short notes are beamed by beat. These are notation
decisions, not information that MIDI authored.

The last source note ends at tick 244800. Later metadata extends to tick
34122495; it remains in the original MIDI but does not create hours of empty
practice measures. Original sustain/controller events remain in the source and
event JSON; the current lesson synth plays written note lengths, and grades
pitch and note starts rather than pedal or hold duration.

The author's public MIDI download did not include an explicit redistribution
license. These files are attributed to the arranger and stored here at the
user's explicit request; no public-domain or permissive-license claim is made.

## Reproduce

Install `mido==1.3.3` in a Python environment, then from the repository root:

```sh
python scripts/piano/convert_phoebe_midi.py
```

The converter checks the preserved MIDI SHA-256 before proceeding and rewrites
the same MusicXML, events and provenance deterministically. The expected source
hash is `5339cdf536ad2af95d720f82ce3304547f3b97a9f3f4eee2f3cabf4291dc0364`.

For the actual browser-renderer check, install `jsdom@31.0.1` and
`@napi-rs/canvas@1.1.1` in a temporary dependency prefix, then run:

```sh
node scripts/piano/validate_phoebe_score.mjs /path/to/dependency-prefix/package.json
```

## Acceptance evidence

- [x] Preserved original MIDI bytes and hash.
- [x] Matched all 1,396 note tuples against the independent earlier source extraction: track, channel, pitch, start, end, duration, velocity and release velocity.
- [x] Matched all 1,396 practice attacks and every tied segment against the derived notation timing.
- [x] Validated against the released MusicXML 4.0 XSD, with its local XML and XLink dependencies.
- [x] Actual vendored OSMD rendered and mapped all 1,622 note/rest elements, with no mapping warnings.
- [x] Actual score displayed green hits, red misses and the current-note color; 1,018 ordered cursor positions and restart passed.
- [x] Inspected the rendered opening to confirm title, piano staves, key, beaming and readable note placement.
- [x] Re-running the converter reproduced the same score, event JSON and provenance hashes.

These are technical and visual checks. No audible playback or human musical
acceptance is claimed.
