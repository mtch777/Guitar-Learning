# Tiered music data examples

Start with **tiered-passage.html** for the realistic example; it loads the adjacent
`tiered-passage.example.json`. Serve this directory over HTTP. `tiered-song.html`
and its JSON preserve the older four-note miniature for comparison.

The richer fixture contains an authored eight-bar passage, three tracks, two
lead voices, 80 written note segments, 13 explicit rests and 588 records across
five tiers. A repeated E call receives a higher answer; its return keeps the
rhythm but changes a written pitch and bend/vibrato execution. The four focused
views explain idea development, performance, timing/repeats and statistics.

Included complications: exact triplets/dotted durations, two cross-bar tie chains,
open-string hammer/pull, typed slide endpoints, half-step two-string texture,
power-chord coattacks, cross-track alignment, 3/4 meter change, 100->80 BPM change,
and repeat-expanded playback visits. Eight written bars (31 quarter notes) map
to ten visits (39 quarter notes, exactly 513/20 seconds). No audio.

All data is synthetic and source-free. Tier 0 uses deliberately normalized fixture
notation, not literal GPIF. Section/pattern/call-response groupings are authored,
not detector predictions. Unknown vibrato rate/depth and uncertain tonal quality
remain explicit. These examples do not implement or prove a GP inverse, an artist
profile, full physical playability, variation controls or musical quality.

## Reproduce and check

From repository root:

```
.venv/Scripts/python.exe composition-lab/examples/build_realistic_tier_example.py
.venv/Scripts/python.exe -m unittest discover -s composition-lab -p test_realistic_tier_example.py
```

The deterministic builder writes the JSON. HTML derives geometry, counts, pitch
ranges and curve labels from records. Authored case selections guide inspection;
they are fixture navigation, not hardcoded analysis or reverse-generation rules.
All records remain searchable and downloadable. Timing, source rhythm/pitch,
ties/transitions, classification, membership, pattern reconstruction arithmetic,
statistics, exact playback clocks and adjacent-tier inputs are independently
checked. A successful fixture check is not an implemented bidirectional engine.

## Note names, lower techniques and harmonic coordinates (v3)

Score settings are separate meter, tuning, tempo, repeat and opaque-source-field
records. Note labels use letter_octave, e.g. E_4 note. Display enharmonic spelling
is a convention; string/fret does not prove a particular written letter spelling.

Tier 0 keeps encoded technique parameters; Tier 1 adds explicit resolved
performance parameters, including rational bend-point score positions and
sounding-pitch samples. The selected-note inspector exposes both. Vibrato
rate/depth remain unknown where only a marking is present.

The fixture explicitly declares E natural minor and an E Aeolian chord-scale
hint during written q0-2. These are authored annotations, not a key/mode detector
and not conclusions inferred from root/fifth/octave. Tier 2 resolves contexts.
Tier 3 note_harmonic_view references the SAME Tier 1 note and stores:

- interval_of_note_base_key: tonic-relative signed semitones, mod12, relative
  octave, chromatic interval label, declared mode degree/scale membership.
- interval_of_note_current_chord_mode: exact context segments over each note;
  chord-root coordinates and chord-tone membership can be known while mode is
  unknown. Written accompaniment gaps remain explicit no-chord-support spans.

These fields describe written BASE pitch. A bend's sounding trajectory is a
separate performance representation, not falsely labelled constant degree.
All coordinate forms preserve pitch/register and have independent inverse
arithmetic checks; this does not implement a general inverse GP engine.

Relationship families now include metric location, same-voice successor groups,
same-string movement, simultaneous onsets, chord/key contexts, cross-track and
cross-voice overlaps, exact per-note variation and the original technique,
sustain, membership and call/response relations. Every type has explicit
endpoints/evidence/scope. No newly proposed artist/phrase/role model is claimed.
