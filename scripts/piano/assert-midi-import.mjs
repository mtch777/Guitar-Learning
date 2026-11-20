import assert from 'node:assert/strict';
import {verifyMidiFidelity} from './verify-midi-fidelity.mjs';
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';

export async function assertMidiImport(filename, root = 'public/piano/learning-songs') {
  assert.match(filename || '', /^midi-[0-9a-f]{64}\.musicxml$/, 'No converted MIDI source filename was emitted.');
  const catalog = JSON.parse(await readFile(join(root, 'song-library.json'), 'utf8'));
  const songs = catalog.songs.filter(song => song.sourceFilename === filename);
  const errors = (catalog.importErrors || []).filter(error => error.sourceFilename === filename);
  assert.equal(errors.length, 0, `MIDI score was rejected by the learning parser: ${JSON.stringify(errors)}`);
  assert.equal(songs.length, 1, `MIDI source ${filename} must occur exactly once in the lesson catalog.`);
  const song = songs[0];
  assert.match(song.id, /^upload-[0-9a-f]{64}$/);
  assert.ok(song.noteCount > 0 && song.attackCount > 0, 'Imported music has no playable piano notes.');
  assert.equal(song.sourceFilename, filename);
  assert.equal(song.sourcePath, `uploads/${filename}`);
  assert.equal(song.scorePath, `scores/${song.id}.musicxml`);
  const original = await readFile(join(root, 'uploads', filename.replace(/\.musicxml$/, '.mid')));
  assert.equal(original.subarray(0, 4).toString('ascii'), 'MThd', 'Saved source MIDI must remain readable.');
  const xml = await readFile(join(root, song.scorePath), 'utf8');
  assert.match(xml, /<score-partwise/);
  const fidelity = await verifyMidiFidelity(
    join(root,'uploads',filename.replace(/\\.musicxml$/, '.mid')),
    join(root,song.scorePath),
  );
  assert.equal(fidelity.attacks, song.attackCount, 'Lesson attack count must match original MIDI.');
  console.log(`Validated imported song: ${song.title}; ${song.attackCount} attacks; max MIDI timing error ${fidelity.maxEndpointErrorQuarters.toFixed(6)} quarter notes.`);
  return song;
}

if (process.argv[1] && import.meta.url === new URL('file://' + process.argv[1].replace(/\\/g,'/')).href) {
  await assertMidiImport(process.argv[2]);
}
