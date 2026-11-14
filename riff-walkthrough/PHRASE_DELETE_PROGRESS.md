# Phrase deletion and exact matching

- [x] Plan/regen group only current exact length, onset/end and pitch matches.
- [x] No hidden rhythm-only edits; modes preserve unedited dimensions.
- [x] Delete endpoint validates revision and atomically stores new Review plus prior revision copy.
- [x] Deleted windows close, retained contiguous holds preserved, gap-crossing holds clipped.
- [x] Remaining phrase indices and scaffold references remapped; subsequent regeneration tested.
- [x] Delete all yields an empty Review and valid empty MIDI.
- [x] 74 backend tests passed (`python -m unittest discover -p test_*.py`).
- [x] Independent QA found/fixed metadata-only frozen timing comparison; permanent regression test added.
- [ ] Integration/deployment and live endpoint validation owned by coordinating UI agent.

Deletion is a new endpoint; no previous delete action existed in current source. Original generator stages are unchanged; only revisioned Review is edited. Prior editor revisions are retained as local recoverable copies.
