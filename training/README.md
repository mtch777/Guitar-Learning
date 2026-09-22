# Model training

Current MVP scope:

- 8 physical strings
- frets 0, 5, 7, 12, 17, 19, 24 in the proof-of-concept dataset
- ringing notes only
- soft / normal / hard picking
- muted recordings excluded
- pitch is used to eliminate physically impossible strings
- classifier distinguishes the remaining strings from acoustic/timbral features

The browser feature extractor must match the trained model's feature definition exactly.
