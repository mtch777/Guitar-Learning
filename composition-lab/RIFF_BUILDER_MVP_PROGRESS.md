# Riff builder — current delivery

The active contract and checklist are in
[PROCEDURAL_RIFF_PROGRESS.md](PROCEDURAL_RIFF_PROGRESS.md); the chosen architecture
and alternatives are in [PROCEDURAL_RIFF_DESIGN.md](PROCEDURAL_RIFF_DESIGN.md).

Only Artist and Mode are generation inputs. The engine selects a complete
source-derived relational program and generates new modal pitches, contours and
Drop E execution. Its phrase order, timing, returns and ending come from that
program; this version does not compose a new whole-riff form.

The local UI removes the length/manual-section workflow, uses phrases, and keeps
the existing player, complete interval fretboard, active shapes, playback speeds
and timestamped JSON downloads. Phrase selection starts playback. These features
are implemented and browser-verified. The verified current library is being
released as a bounded working update while broader source consistency work
continues; release does not certify that every newly analyzed passage is correct.

Large timed hand shifts may occur between independent phrases. Ordinary movement
within a phrase stays cohesive. A dependent accent or local gesture label does
not by itself grant a new phrase boundary or permission for a hand relocation.

Two generated listening comparisons are published through the existing route.
The latest is [comparison 02](https://mtch777.github.io/Guitar-Learning/riff-builder/previews/2026-11-06/ia-lydian-preview-02.mp3).
Generated events, native scheduling, actual rendered onsets and public playback
are verified independently. Human feedback and source annotations remain private;
technical verification does not establish general musical acceptance.

Current remaining work: correct the final source batch's omitted one-configuration
rhythmic return and misplaced connected legato entry, retest shared rules and
integrate any resulting library changes. The current runtime and library pass
150 native-output checks and actual browser playback/download checks. Verify the
exact served version separately. The separate Cloud
composition work remains outside this workstream.

Historical progress and first failed outcomes are retained privately with hashes;
no source/result patches, song-specific cuts, selective rerolls or loss of evidence.
