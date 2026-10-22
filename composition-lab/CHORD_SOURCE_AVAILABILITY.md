# Chord availability is not score annotation availability

## Observed result

Rough Boy20985/revision9620672 has `metadata.hasChords=true`, but the seven captured
notation tracks have no chord declaration fields. This is not an extraction defect
in the notation parser and does not establish that the song has no chords.

The public page's actual script chain independently exposes two resources:

| Resource | Observed representation | Scope |
|---|---|---|
| Notation metadata + track JSON | Score revision9620672, seven tracks | Existing frozen score source; unchanged |
| Separate chord metadata | Public GET `/api/chords/{songId}` | Advertises a separate ChordPro resource and chord revision identifier |
| Separate ChordPro | Public referenced resource,645bytes,8bracketed chord tokens | Supplemental chord document; no established note/beat alignment |

The separate response reports `chordsRevisionId=20985`. Its song/artist/title match
the notation metadata. Identifiers alone do not prove alignment between documents.

## Verification

- Followed scripts referenced by the actual public page, rather than guessing an
  endpoint: appClient → vendor/common. Their bytes and hashes retained privately.
- Public separate metadata and its referenced ChordPro both returned200.
- Independently compared all eight original capture files against the preceding
  QA baseline hashes: every file unchanged. No supplemental data merged into them.
- Original urllib request failed on HTTP103 Early Hints; same URL retried with
  existing httpx. Failed attempt retained, no song replacement.
- Chord/lyric contents remain private. No raw score, lyrics or source chord sequence
  is published in this report. No authenticated, editing or detection endpoint used.

## Consequence for analysis and QA

`hasChords` is a capability/availability flag, not a timed harmonic label.
Missing notation chord fields do not imply absence of a separate chord document.
If supplemental resources are retained later, preserve their independent provenance
and explicitly unresolved alignment. Do not silently inject them into score Tier0,
overwrite the captured notation, call them inferred harmony, or use them as beat-level
truth. Current Songsterr annotation-backed harmony evaluation remains inconclusive.

The existing raw source remains authoritative for its own fields. This discovery
does not repair or pass the absent active inverse or meaningful-abstraction gate.

Private repeatable probes and preservation evidence live in the current task's
visualization workspace under `roughboy-acquisition-v2`, outside the Git repository.
