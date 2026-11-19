import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = fileURLToPath(new URL('../../public/piano/learning-songs/', import.meta.url));
const REQUEST_ID = /^gl-[a-f0-9]{32}$/;
const SOURCE_FILE = /^midi-[a-f0-9]{64}\.musicxml$/;

export async function writeImportReceipt(id, filename, {root = defaultRoot} = {}) {
  if (!REQUEST_ID.test(id) || !SOURCE_FILE.test(filename)) throw new Error('Invalid MIDI import receipt arguments.');
  const catalog = JSON.parse(await fs.readFile(path.join(root, 'song-library.json'), 'utf8'));
  const song = catalog.songs.find(song => song.sourceFilename === filename);
  if (!song?.id || !/^upload-[a-f0-9]{64}$/.test(song.id)) {
    throw new Error(`Converted MIDI score ${filename} is missing from the song library.`);
  }
  const dir = path.join(root, 'imports');
  await fs.mkdir(dir, {recursive:true});
  const receipt = {version:1, requestId:id, songId:song.id, sourceFilename:filename};
  await fs.writeFile(path.join(dir, `${id}.json`), JSON.stringify(receipt) + '\n', {flag:'wx'});
  return receipt;
}

if (process.argv[1] && import.meta.url === new URL(`file://${path.resolve(process.argv[1])}`).href) {
  await writeImportReceipt(process.argv[2], process.argv[3]);
}
