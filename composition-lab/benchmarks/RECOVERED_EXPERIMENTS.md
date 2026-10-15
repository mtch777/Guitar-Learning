# Recovered source-conditioned experiment results (2026-10-15)

The original GP scores and their MusicXML transcriptions are copyrighted source-derived material; they are not in this public repository. Private bundle supplied separately.

## Cloud Cascade
Source: 111 bars, 6 tracks (two lead guitars, two rhythm guitars, bass, drums). Baseline V2 (seed 17) and source-conditioned prototype (seed 23) each generated 16 bars. Baseline 137 notes, 3 distinct rhythm patterns, 11 unique bar signatures. Conditioned 222 notes, 6 patterns, 14 signatures. Both GP7 ZIP archives passed CRC and GPIF parse; no exact full-bar source-track signatures. These metrics do not establish quality, originality, or correct playback.

## Sweet Child O' Mine
Source: 185 bars, 9 tracks. Baseline 137 notes, 3 patterns, 11 bar signatures, 7 pitch classes. Conditioned 235 notes, 5 patterns, 15 bar signatures, 11 pitch classes. Source model sampled 177 rhythm templates and 19 root transitions from Izzy Stradlin rhythm guitar. Both exports 16 bars and 8-string, not native 6-string: they used the Cloud Cascade GP7 shell. No lead/bass/phrase interaction or listening validation. User judged conditioned result discordant, chord-heavy, and lacking melodic phrases; Cloud V2 baseline sounded better.

## Reproduction and unresolved gaps
Prototype scripts and private binary artifacts are in the separate recovered-input ZIP. Legacy scripts reference local machine paths. The public runner `composition-lab/benchmarks/analysisgnn_preflight.py` does not perform GP-to-MusicXML conversion. Previous local converter reported 5314/5314 Cloud notes and 10138/10138 Sweet notes, but 18 Sweet duration discrepancies; validate against source before trusting it. Pretrained AnalysisGNN inference has NOT run. Do not mark Step 1 complete.

All generated baseline and conditioned GP artifacts must be auditioned, compared against held-out sources, and tested for role/phrase coherence. Avoid hardcoded D Aeolian and eight-string shell assumptions.
