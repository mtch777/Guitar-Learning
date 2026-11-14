# Visible manual weights and silence preference

- Phrase preferences were present under collapsed Parameters in steps3/4/5; now always visible above other parameters.
- Review now has editable phrase preferences applied to the next selective regeneration, persisted only on successful edit. Failed lookup/validation leaves output, revision and saved settings unchanged. Earlier generator state is never edited.
- New rhythm preference: mostly_silent default0.1x when at least50% of phrase time has no sounding note. Uses the union of note holds clipped to phrase boundaries, exact rational source length, and includes leading/trailing silence. Overlapping notes are not double-counted; unknown timing or length remains neutral. Threshold inclusive. Factor1 restores neutral behavior; no exclusion.
- Existing defaults unchanged: long uniform singles0.1x; triplets2x; intervals2x; minor second additional2x. Silence preference is rhythm-stage only because pitches do not change fixed timing.
- Older saved preferences gain the new default without rejecting saved parameter dictionaries.

## Verification
- [x]66 Python tests passed.
- [x]7 frontend suites passed; optional private artifact rendering skipped because fixtures unavailable.
- [x]Real isolated HTTP edit imported saved Reviewrevision3, applied silence override0.025, changed actual rhythm/MIDI, committedrevision4 and reopened with exact override/output retained.
- [x]Distinct QA cookie and private storage; source snapshot unchanged.
- [ ]Physical Android/browser screenshot QA unavailable (browser inventory empty).
- [ ]Existing live8878/8879 intentionally not restarted or modified. Backend source publication does not activate this feature there. Localhost-only test copy at8892/8893; LAN exposure awaits authorization.
