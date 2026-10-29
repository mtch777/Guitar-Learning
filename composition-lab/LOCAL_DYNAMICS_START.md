# Local written-dynamics level — bounded START

This T2-10 operation changes one existing known velocity declaration and its
complete written influence region. It adds audible expression control, not a
new predictor, phrase model, artist preference, acoustic loudness law or generator.
Accent flags remain locked; full dynamics/accents acceptance remains open.

## Ownership and shared relation

Use the existing sole categorical velocity owner. No baseline/offset migration,
new note fields, inserted reset marks, duplicate values or arbitrary MIDI offsets.
The explicit relationship is source declaration -> inherited per-note marking,
with independent note overrides and exact track/voice source provenance.

Beat markings carry through bars/rests until a subsequent nonnull beat marking;
note overrides affect only that note. Missing/null keys do not reset state. An
unknown nonnull marking remains unknown, not converter-default f. The renderer's
fixed eight-name MIDI mapping is an export convention, not equal loudness steps.

## Population and choices

Inventory every present beat/note velocity field, including unknown/null, and
every original nonrest note's effective marking/provenance. Keep raw source values.
Known targets need a nonempty influence set and no unsupported boundary. Unknown
nonnull beat boundaries and note overrides that the converter handles differently
refuse the affected beat region; unrelated unknowns do not disqualify note targets.

Donors are other eligible explicit markings in the same part, voice and note/beat
scope. Count each original declaration once, not each inherited note or chord tone.
Exclude the edited declaration; retain source context and original donor IDs.
Aggregate equal markings without adding votes for aliases. A coincidence is valid.
No artist-fit or optimal-expression interpretation follows from source frequency.

Controls: dynamics 0/50/100 use the existing release sampler; 50 is release
probability, not half loudness, and 100 does not force a different marking.
Source release counts and realized changes are reported separately.

## Independent checks and gates

check_local_dynamics.py owns a raw state scanner independent of source_dynamics
and producer inventory/options. APIs inventory(T1), choices(T1,target_ref),
check(before,after,target_ref,donor_refs,decision=None). Canonical inventory schema
source-local-dynamics/1; declarations sort by fact_ref, states by occurrence_ref.
State marking is a recognized name or null; declaration marking retains raw JSON.

Only the chosen existing velocity fact may change. Every other source fact and
outside effective state/provenance must remain exact. Every affected note must
resolve to the new source marking through the same inheritance relation. Explicit
note overrides, other voices, accent flags, notes/timing and techniques stay fixed.

Contrasts: note override isolation; carry across rests/bars; known reset; unknown
beat/note boundary; null versus absent; unrelated unknown voice; no influenced
notes; source-weight deduplication; same-level coincidence; raw/outside/decision
corruptions; actual source-denied zero/change inverse; 0/50/100 fixed-seed behavior.

Before substantial implementation, retain a cheap fixed-source opportunity census.
Then freeze stable code, test one new preregistered random capture with failures
and no-choice retained, and independently audit every selected scope/source option.
Keep source/zero/changed GP baselines. Native checks must verify actual note
velocities/markings and unchanged other properties; PCM must demonstrate the real
change. Changed-note decay may extend beyond its last attack: no guessed acoustic
cutoff or linear-dB claim. Human musical-fit review remains separate when a genuinely
new audible artifact is delivered. Do not ask for a repeat judgment on identical audio.

Efficiency stop: complete this local operation and report its limits. Do not expand
into phrase accents, implicit performance, owner redesign or model shopping.

## Explicit playback-bundle scope revision (before fresh freeze)

Strict standalone-GP roundtrip remains the default. Sweet Child's standalone
bend-curve failure is retained; it is not repaired or marked passed. The accepted
existing hash-bound bend companion may be tested under a separately named
`gp_with_exact_model_bends` scope in a new output directory. Its restored playback
model must match EVERY field in the untouched pre-export checked-model snapshot;
GP/reference/companion/extractor/module hashes and full note counts are bound.
This is exact checked-field restoration, not universal source/standalone fidelity.
The old checked model omits dynamics, so the new direct source/native dynamic and
MIDI tests remain required. A paired pass never changes roundtripPass=false.

Pinned alphaTab mirrors each emitted attack velocity into its corresponding
NoteOff record. Only those exactly coupled velocity leaves may differ; on/off
clocks, track/channel/key/duration and every other MIDI event remain fixed. Its
current synth ignores NoteOff velocity. This is not a new release-expression
control or a claim about other playback applications.

Regular mapped known dynamics are checked against actual GP/native notes. Baseline
grace/percussion mapping limits are disclosed; any affected unmapped note refuses.
Exactly six fixed-gain render receipts and their MIDI/GP/WAV hashes are required.
Native audit and PCM change are computational evidence; musical fit and the full
T2-10 creative gateway remain separate.
