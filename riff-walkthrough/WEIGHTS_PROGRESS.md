# Phrase preference weights

Implemented defaults (editable in each step's Parameters):
- Rhythms: uniform long single notes0.1, triplets2, two-note intervals2.
- Opening and remaining pitches: two-note intervals2, minor2 additional2 (combined4).
- Set every multiplier1 for baseline. Positive multipliers only; extreme combinations that exceed numeric precision give an explicit error, never silent zero/overflow. No new eligibility filter, cap, or gate.

Penalty requires >=4 attacks, one note per attack, identical actual tied durations >=1quarter-note beat, no sounding overlap/carry-in. Triplets use explicit written rhythmic-event labels including rests/ties, not arbitrary fractional onset offsets.

Intervals require exactly2active note events with2different known pitches over positive duration. Any3+active events, unknown sounding note, unison, or mere shared endpoint does not qualify. Minor2 is exactly1semitone, not octave-class13. Sustained overlap counts. Source rhythm groups with unequal holds are unknown when pitch-to-duration identity cannot be established. Pitch selection evaluates only transferred groups on target timing, plus known prior sustains for sequential phrases; discarded source groups cannot boost selection. Each flag multiplies once per candidate, not once per occurrence. Seeds/scaffolds unchanged; selective regeneration uses applied preferences.

Verification
-54Python app tests pass;5frontend suites pass. Frontend artifact fixtures unavailable, so that optional fixture rendering check skipped.
-56analytical tests ran; only blueprint class fixture setup blocked by missing hardcoded csv-current file in isolated checkout; remaining tests passed.
-Independent critic boundary tests and selective preference propagation passed.
-Fixed seed112: weighted generation completed12/12phrases through step5. Neutral settings reproduce old engine's exact rhythm/pitch note SHA256s and identical pre-existing phrase4carry-in blocker after3phrases. Upstream seed/scaffold snapshots unchanged.
-78,628eligible timing phrases,100,000draws/arm, uniform baseline to isolate preference effect (NOT production contextual rates). Exact probability: long-uniform-single1.086127%→0.085850%;triplet3.356311%→6.952473%;interval23.093554%→38.154157%. Same candidate population.

Deployment status: source-only prepared; NOT activated in live server. Original server holds sessions in RAM and must not be restarted without explicit preservation/restart plan. No audible playback or live session mutation performed. Older pitch-only sampling report was superseded by sounding semantics and must not be quoted.

## Parallel activation verified
Updated app http://192.168.0.12:8878/ and companion8879, configured cookie riff_weights_session. Original8768/8769 processes left running with their original start times. LANHTTP200 and cookie isolation verified: an old-cookie request to new app receives only the new cookie; original private QA state unchanged with both cookies present.
FullHTTP generation completed all6steps/12phrases. Both verified Kontakt presets available. Generated stage4 audio rendered37seconds and authenticated Range206WAV verified silently. Initial source-stage1 unavailable preview was correctly rejected; no claim that unavailable source audio was fixed.
Independent MIDI-save checkout configured on generated-midi with dot automation author. No extra QA MIDI published. Browser inventory empty/IAB unavailable: visualUI and physicalAndroid not verified. No firewall/network-security changes, no original restart, no audible playback. Session data remains memory-only in both services; save wanted MIDI before restarting either.
Source commit0fcf729efa1c3b3b8a5a261320712cdda894f384 verified on riff-walkthrough-ui-20261113; this follow-up documents activation.
