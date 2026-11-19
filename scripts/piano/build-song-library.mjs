import fs from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {File} from 'node:buffer';
import {DOMParser} from '@xmldom/xmldom';
import {readScoreFile, SUPPORTED_EXTENSIONS} from '../../public/piano/learning-songs/score-upload.js';
import {parseMusicXML} from '../../public/piano/learning-songs/score-model.js';

const lessonRoot = fileURLToPath(new URL('../../public/piano/learning-songs/', import.meta.url));
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const normalizedXML = xml => xml.replace(/(<\?xml\b[^?]*\bencoding\s*=\s*["'])[^"']+(["'])/i, '$1UTF-8$2');
const safeRelative = value => typeof value === 'string' && value.length > 0 && !value.startsWith('/')
  && !value.includes('\\') && !value.split('/').some(segment => !segment || segment === '.' || segment === '..');

// Use the same pinned ZIP implementation as the browser, without executing any
// uploaded content. Originals are read only and are never rewritten.
async function unzipImplementation() {
  const moduleObject = {exports:{}};
  const code = await fs.readFile(path.join(lessonRoot, 'vendor/fflate-0.8.3.min.js'), 'utf8');
  vm.runInNewContext(code, {
    module:moduleObject, exports:moduleObject.exports, require:createRequire(import.meta.url),
    Uint8Array, Uint16Array, Uint32Array, Int32Array, ArrayBuffer, TextEncoder, TextDecoder,
  });
  return moduleObject.exports.unzipSync;
}

async function filesUnder(directory, prefix = '') {
  let entries;
  try { entries = await fs.readdir(directory, {withFileTypes:true}); }
  catch (error) { if (error.code === 'ENOENT') return []; throw error; }
  const found = [];
  for (const entry of entries.sort((a,b) => a.name.localeCompare(b.name, 'en'))) {
    const relative = prefix + entry.name;
    if (entry.isDirectory()) found.push(...await filesUnder(path.join(directory, entry.name), relative + '/'));
    else if (entry.isFile()) found.push(relative);
    // Symlinks cannot pull files from outside the dedicated uploads directory.
  }
  return found;
}

export async function buildSongLibrary({root = lessonRoot} = {}) {
  const seed = JSON.parse(await fs.readFile(path.join(root, 'song-library.seed.json'), 'utf8'));
  if (seed.version !== 1 || !Array.isArray(seed.songs)) throw new Error('Invalid song-library.seed.json.');
  const testSourceHashes = seed.testSourceSha256 || [];
  if (!Array.isArray(testSourceHashes) || testSourceHashes.some(digest => !/^[a-f0-9]{64}$/.test(digest))) {
    throw new Error('Invalid test-source hashes in song-library.seed.json.');
  }
  const testSources = new Set(testSourceHashes);
  const uploadedLabels = seed.uploadedLabels || {};
  if (!uploadedLabels || typeof uploadedLabels !== 'object' || Array.isArray(uploadedLabels)
    || Object.entries(uploadedLabels).some(([name, label]) =>
      !name || name.includes('/') || name.includes('\\') || !label
      || typeof label.title !== 'string' || !label.title.trim() || label.title.length > 120
      || (label.composer !== undefined && (typeof label.composer !== 'string' || label.composer.length > 120)))) {
    throw new Error('Invalid uploaded song labels in song-library.seed.json.');
  }
  const unzip = await unzipImplementation();
  const previousParser = globalThis.DOMParser;
  globalThis.DOMParser = DOMParser;
  const songs = [], importErrors = [], normalizedHashes = new Set(), generatedPaths = new Set();
  try {
    for (const entry of seed.songs) {
      if (!safeRelative(entry.scorePath) || (entry.sourcePath && !safeRelative(entry.sourcePath))) throw new Error('Unsafe seed score path.');
      const xml = await fs.readFile(path.join(root, entry.scorePath), 'utf8');
      const model = parseMusicXML(xml, {DOMParser});
      const sourcePath = entry.sourcePath || entry.scorePath;
      const source = await fs.readFile(path.join(root, sourcePath));
      const digest = sha256(xml);
      songs.push({...entry, sourcePath, sourceFilename:entry.sourceFilename || path.basename(sourcePath),
        sha256:digest, sourceSha256:sha256(source), noteCount:model.notes.filter(note => !note.isRest).length,
        attackCount:model.attacks.length});
      normalizedHashes.add(sha256(normalizedXML(xml)));
      generatedPaths.add(entry.scorePath);
    }
    for (const filename of await filesUnder(path.join(root, 'uploads'))) {
      const extension = filename.split('.').pop().toLowerCase();
      const sourcePath = 'uploads/' + filename;
      // The MIDI importer retains its exact source bytes beside the MusicXML.
      // They are a supported source for this pipeline, not a failed upload.
      if (/^midi-[a-f0-9]{64}\.mid$/.test(filename)) {
        try {
          await fs.access(path.join(root, 'uploads', filename.replace(/\.mid$/, '.musicxml')));
          continue;
        } catch (error) {
          if (error.code !== 'ENOENT') throw error;
        }
      }
      if (!SUPPORTED_EXTENSIONS.includes(extension)) {
        if (!['README.md', '.gitkeep'].includes(path.basename(filename))) importErrors.push({
          sourcePath, sourceFilename:path.basename(filename),
          message:'Upload a .musicxml, .xml or .mxl score. Export other formats to MusicXML first.',
        });
        continue;
      }
      try {
        const original = await fs.readFile(path.join(root, sourcePath));
        const xml = normalizedXML(await readScoreFile(new File([original], filename), {unzip}));
        const model = parseMusicXML(xml, {DOMParser});
        const digest = sha256(xml);
        if (normalizedHashes.has(digest)) continue;
        const scorePath = `scores/upload-${digest}.musicxml`;
        await fs.mkdir(path.join(root, 'scores'), {recursive:true});
        await fs.writeFile(path.join(root, scorePath), xml, 'utf8');
        generatedPaths.add(scorePath);
        const uploadedLabel = uploadedLabels[path.basename(filename)];
        const title = uploadedLabel?.title || (model.title && model.title !== 'Untitled score' ? model.title : path.basename(filename).replace(/\.(musicxml|xml|mxl)$/i, ''));
        const sourceDigest = sha256(original);
        songs.push({id:`upload-${digest}`, title, composer:uploadedLabel?.composer ?? model.composer ?? '', scorePath, sourcePath,
          sourceFilename:path.basename(filename), sha256:digest, sourceSha256:sourceDigest,
          ...(testSources.has(sourceDigest) ? {testScore:true} : {}),
          noteCount:model.notes.filter(note => !note.isRest).length, attackCount:model.attacks.length});
        normalizedHashes.add(digest);
      } catch (error) {
        importErrors.push({sourcePath, sourceFilename:path.basename(filename), message:(error.message || 'This score could not be read.').slice(0, 500)});
      }
    }
  } finally {
    if (previousParser === undefined) delete globalThis.DOMParser;
    else globalThis.DOMParser = previousParser;
  }
  if (songs.length && !songs.some(song => song.id === seed.defaultSongId)) {
    // A deleted default may leave uploaded songs as the only remaining choices.
    seed.defaultSongId = songs[0].id;
  }
  // Remove only this generator's stale derived files, never originals or other scores.
  for (const filename of await filesUnder(path.join(root, 'scores'))) {
    if (/^upload-[a-f0-9]{64}\.musicxml$/.test(filename) && !generatedPaths.has('scores/' + filename)) {
      await fs.unlink(path.join(root, 'scores', filename));
    }
  }
  const catalog = {version:1, defaultSongId:songs.length ? seed.defaultSongId : null, songs, importErrors};
  await fs.writeFile(path.join(root, 'song-library.json'), JSON.stringify(catalog, null, 2) + '\n');
  // Re-conversion changes the MusicXML digest and therefore the song ID. Keep
  // older successful MuseScore handoff receipts pointing to the live song.
  const songBySource = new Map(songs.map(song => [song.sourceFilename, song]));
  for (const filename of await filesUnder(path.join(root, 'imports'))) {
    if (!/^gl-[a-f0-9]{32}\.json$/.test(filename)) continue;
    const receiptPath = path.join(root, 'imports', filename);
    const receipt = JSON.parse(await fs.readFile(receiptPath, 'utf8'));
    const song = songBySource.get(receipt.sourceFilename);
    if (receipt.version === 1 && receipt.requestId === filename.slice(0, -5)
      && /^midi-[a-f0-9]{64}\.musicxml$/.test(receipt.sourceFilename || '')
      && song && receipt.songId !== song.id) {
      await fs.writeFile(receiptPath, JSON.stringify({...receipt, songId:song.id}) + '\n');
    }
  }
  return catalog;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const catalog = await buildSongLibrary();
  console.log(`Piano library: ${catalog.songs.length} shared songs; ${catalog.importErrors.length} unreadable uploads.`);
  for (const failure of catalog.importErrors) console.warn(`${failure.sourceFilename}: ${failure.message}`);
}
