# V18 — Occurrence-addressed GPIF writer

## Problem
GPIF stores reusable Note, Beat, Voice, and Bar definitions. V17 modified definition IDs only if *every* use wanted the identical change. That prevented most learned melodic substitutions from reaching export.

## Solution
`gp_occurrence_writer.py` accepts `(measure_index, voice_index, beat_index, note_index)` occurrence coordinates and cloned descendants of the MasterBar → Bar → Voice → Beat → Note reference path only for edited occurrences. Unedited definitions/occurrences remain unchanged. The writer preserves track order, voice and beat counts, meter, timing, and original note data.

`gp_similarity_export.py` now plans changes by source occurrence coordinates rather than note-definition IDs. Rhythm changes are applied before cloning to maintain correct rhythm references when pitch and rhythm transforms are combined. Zero-strength controls copy the source byte-identically.

## Checks
- V18 tests: 9/9 pass (`test_gp_similarity_export.py`, `test_gp_occurrence_writer.py`)
- Chet Baker learned melody 100%, chords/rhythm locked: 102 changed note occurrences, GP re-imports; exact timing and other tracks preserved.
- Chet Baker learned chords/melody/rhythm 100%: 321 changed note occurrences, 6 learned rhythm phrase substitutions; GP re-imports.

## Current limitations
- The score's full GPIF reference graph and external native Guitar Pro behavior have not been exhaustively validated.
- Rhythm substitutions still only use existing safe GPIF rhythm definitions, with conservative eligibility rules.
- Learned melodic/rhythmic variations are not calibrated to perceived distance.
- No joint probabilistic harmony interpretation or hierarchical phrase discovery yet.

CLI example:
`python gp_similarity_export.py source.gp --output result.gp --learned --melody 100`