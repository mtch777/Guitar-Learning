# Tiered music data examples

Start with **tiered-passage.html** for the realistic example; it loads the adjacent
`tiered-passage.example.json`. Serve this directory over HTTP. `tiered-song.html`
and its JSON preserve the older four-note miniature for comparison.

The richer fixture contains an authored eight-bar passage, three tracks, two
lead voices, 80 written note segments, 13 explicit rests and 267 records across
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
