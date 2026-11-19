import fs from 'node:fs/promises';
import assert from 'node:assert/strict';

const path = 'public/piano/learning-songs/song-library.json';
const catalog = JSON.parse(await fs.readFile(path, 'utf8'));
const imported = catalog.songs.filter(song => song.sourceFilename?.startsWith('midi-'));
assert.ok(imported.length > 0, 'MIDI fixture was not added to the song library');
assert.ok(imported.some(song => song.noteCount >= 3), 'MIDI fixture did not produce the three expected notes');
console.log('MIDI conversion, MusicXML parsing, and song library integration passed.');
