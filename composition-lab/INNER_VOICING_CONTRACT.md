# Source-supported inner voicing

## Purpose and ownership

The current whole-layout donor couples changes to the outer notes with changes
inside the chord. This experiment separates those musical dimensions. It is a
new named scope, not a relaxation of the existing fixed-doubling policy.

The SAME existing chord-degree / octave / tuning / fret relationships remain
authoritative in both directions. No new inverse, handpicked pitch, fixed musical
offset, guessed key, inferred melodic voice or separate generator.

## Allowed change and hard locks

- Protect every occurrence at the target's literal highest and lowest pitch.
  These are observable boundaries, not claims about melody/bass voice identity.
- Only the remaining occurrences can receive a coupled degree/register component
  observed on the same actual string subset inside another source chord.
- Donor: same part, explicit supported root/formula, plain known execution.
  Donor selected strings must also be strictly inside its own pitch boundaries.
  Exclude the complete target neighborhood from donor evidence.
- Root, formula, complete pitch-class set, exact bass/top pitches, all target
  occurrence IDs/times/strings, source spelling/labels, and every outside fact
  stay fixed. Doubling MAY change: that is explicitly part of this voicing scope.
- No reversal of literal pitch order between fixed inner strings (negative
  product of before/after pitch differences). Unisons have no prior ordering.
  This is not melodic voice identity. No new string assignment or extra notes.
- All existing tie, HP, slide, bend, roll, unknown-clock, occupied-string and
  source-execution dependencies remain hard guards. Accepted technique detectors
  and pedal interpretation remain unchanged.

## Physical and contextual evidence

- Require a whole plain source coattack with the same actual strings,
  instrument, tuning and capo, and the same fret geometry up to one uniform
  translation. Open-string status must match exactly; output bounds remain valid.
  No ergonomic claim from a fret-span threshold or a partial handshape.
- Geometry may be from another part with identical physical settings; a donor
  chord may have extra members, provided the entire target inner string subset
  is strictly inside the donor's boundaries. Target and geometry require uniform
  positive durations and no outside same-part event overlapping their nominal
  span. A zero-duration event at the left boundary also counts as overlap.
  This is observed fret-pattern evidence, not human playability verification.
- Source component and geometry evidence must come from outside the changed
  neighborhood. Neither can use the candidate's invented output as evidence.
- Plain fixed-string edge/triple novelty is reported, not equated with musical
  invalidity. Unknown execution on incident paths remains a refusal. The new
  boundary/component contract replaces only the exact copied-triplet demand.
- This does not establish inner melodic roles, emotional intent, artist fit or
  human listening acceptance. Those remain explicitly unverified.

## Three QA gates and deliverables

- [x] Planner START review of this scope and independent-checker design.
- [x] Authored positive/negative tests: same inverse; outer and outside locks;
  changed doubling with complete formula; component/geometry provenance;
  execution refusal; unknown roles retained; 0/50/100 release semantics.
- [x] Planner MID review; independent raw-source oracle agrees on complete
  unit/geometry/component denominators and actual producer output. Fifteen
  targeted tests pass, including indexed versus literal rational overlaps.
- [x] Freeze code and choose a new random capture before running unchanged logic.
  Retain all failures and all eligible/refused candidate counts.
- [x] Run actual source-free whole and removed-degree-pair workers. Authored
  changed-worker positive passes; no real change admitted, so no real changed
  worker is claimed. Independently compare original source and declared scope;
  independently compare original source and declared changed scope.
- [x] QA3 bounded relationship audit: inspect degree/outer-boundary/component relationships, exact
  ownership and coverage. An empty donor pool is not a creative pass.
- [x] Planner END review of v1 and v2, including failures and negative results.
- [x] Source-only commit `4228b84` pushed; CI40651904318 passed.
- [x] No real change admitted: export/playback work not applicable. Audio,
  whole-lever and artist acceptance remain OPEN, not passed.

## Frozen v1 outcomes and retained failure

Private `local-artifacts/inner-voicing-v1`: 504 project / 266 native source files;
new random seed 6689848996157294462, 163 excluded IDs. Selected Texas Flood,
Stevie Ray Vaughan & Double Trouble, song 8709 / revision 8728167 / four tracks.

- Full suite: 1,235 passes, one optional skip (109.409 seconds).
- Queen and Smiths recover 11,951 notes / 107,491 facts in four actual isolated
  whole/pair workers. Independent source denominators agree on all 5,998 raw
  geometry groups and 300 component links (40 changed Queen links).
- Queen: six changed layouts lose required chord tones and are correctly
  refused; four retain the chord and outer pitches but have no independent
  complete geometry witness. None admitted; this is not proof of unplayability.
- Smiths: 188 source component links, all unchanged.
- Texas Flood FAIL retained: one structured trill was unsupported (container,
  integer auxiliaryFret, integer speed). No substitute song or source edits.
- Planner END independently verifies source/native/capture hashes, outputs,
  full denominators and negative claims. No creative/audio acceptance.

V2 repair retains trill fields as typed note-level technique observations and
keeps execution unknown. The observed speed value is 65; its units are NOT
established. The retained third-party converter ignores it and supplies 16;
that conversion limitation is recorded, not repaired or disguised here.
Unknown structures/types still refuse. Empty/partial objects stay distinct;
nonempty and empty trill declarations cannot qualify as plain creative context.
Planner caught an independent root-inventory omission; a regression now checks
the complete technique audit and verifies that deleting the trill owner fails.

V2: 505 project / 266 native files; seed 5690346822287915302, 164 excluded IDs.
New random capture: Linkin Park / A Place For My Head / 3711 / revision 9918577 /
eight tracks. Full suite 1,238 passes / one optional skip (118.090 seconds).
Queen, Smiths, repaired Texas Flood and fresh Linkin Park recover 19,548 notes /
189,565 facts through eight actual isolated whole/pair workers. Planner verifies
every source/native/capture hash, all 11,852 raw geometry keys/eligibility, all
342 component links, complete negative outcomes and technique-root ownership.
Original Texas Flood failure remains retained. No real changed layout admitted.

Next agreed investigation: compile the already-frozen corpus into explicitly
supplied physical-only geometry evidence. Musical component donors remain inside
the current song. Do not add source access to the inverse, invent corpus notes,
weaken physical conditions, or silently inject a model outside the tier contract.
