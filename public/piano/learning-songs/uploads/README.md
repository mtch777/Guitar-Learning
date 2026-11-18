# Shared piano song uploads

Upload `.musicxml`, `.xml` or `.mxl` files into this directory and commit the
changes to `main`. The normal site build validates each score and adds it to the
Learning Songs dropdown. Originals stay unchanged in this repository. Generated
MusicXML and `song-library.json` are published on the `gh-pages` branch with the site.

Files must be nonempty and at most 20 MiB, including the expanded XML in an MXL.
The lesson supports pitched, non-transposing MusicXML scores. An unreadable score
stays here and is reported in the song library; it does not remove other songs.
Identical normalized scores share one dropdown entry.

After committing, return to the lesson and use **Refresh songs** once publishing
finishes. The selected song is remembered on each device. Repository uploads are
shared across devices; prior browser-only uploads can be downloaded from the
lesson and added here.

## Existing test uploads migrated from the browser

- `Bach-BWV939.musicxml`: Bach BWV 939, converted from the music21
  [ABC fixture](https://github.com/cuthbertLab/music21/blob/86a7dc8a5fb3b1996ac0202d6bb9b4d4b9d19197/documentation/source/usersGuide/files/praludium.abc).
  The source credits Frank Nordberg / Musica Viva. Original encoding attribution
  is retained; no separate license for that encoding is asserted.
- `MusicXML-upload-test.mxl`: unchanged MuseScore
  [testHello.mxl fixture](https://github.com/musescore/MuseScore/blob/4c78b557ffeef1cfce1cc4b96981014d64dfb0b2/src/importexport/musicxml/tests/data/testHello.mxl),
  from its GPL-3.0 repository. The original ZIP/XML contents remain unchanged.
  The GPL-3.0 text is included in `../scores/MuseScore-GPL-3.0.txt`.
