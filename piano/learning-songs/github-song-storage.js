/**
 * Public song library backed by this repository.
 * Originals are committed to main; the build publishes its derived catalog and
 * normalized scores to gh-pages. Browser storage is only for user preferences.
 * Uploads use GitHub's own signed-in upload page: no write credentials live here.
 */
export const SONG_LIBRARY = Object.freeze({
  repository: 'mtch777/Guitar-Learning',
  sourceBranch: 'main',
  publishedBranch: 'gh-pages',
  sourcePath: 'public/piano/learning-songs',
  publishedPath: 'piano/learning-songs',
  catalogFilename: 'song-library.json',
  uploadUrl: 'https://github.com/mtch777/Guitar-Learning/upload/main/public/piano/learning-songs/uploads',
  uploadsUrl: 'https://github.com/mtch777/Guitar-Learning/tree/main/public/piano/learning-songs/uploads',
  deploymentUrl: 'https://github.com/mtch777/Guitar-Learning/actions/workflows/deploy-pages.yml',
});

const RAW_BASE = `https://raw.githubusercontent.com/${SONG_LIBRARY.repository}/${SONG_LIBRARY.publishedBranch}/${SONG_LIBRARY.publishedPath}/`;
const MAX_CATALOG_BYTES = 4 * 1024 * 1024;
const MAX_SCORE_BYTES = 20 * 1024 * 1024;

const normalizedXML = xml => xml.replace(/(<\?xml\b[^?]*\bencoding\s*=\s*["'])[^"']+(["'])/i, '$1UTF-8$2');
const hexDigest = bytes => Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('');
// Exact normalized XML of the three retained regression fixtures. These also
// hide their old device copies when the published catalog cannot be reached.
const TEST_SCORE_SHA256 = new Set([
  '0c28f895ad6061020d48d3ae872a3509664294e2284be01dc70f2796353a54a6',
  '3bd940f45a28e83f4a8065bb0d4e6c4634f5a51afc3874eb22d129ee9ea84c61',
  '734aa2f1e2baa21664a3c34e542730c48bd9c444087544e9b02df32d60a55a72',
]);

/** Display choices only; original catalog entries and device copies stay intact. */
export async function visibleSongChoices(entries) {
  const allSongs = [...entries];
  const repositoryHashes = new Map();
  for (const song of allSongs) {
    if (!song.repositorySaved || song.localOnly) continue;
    for (const digest of [song.sha256, song.sourceSha256].filter(Boolean)) {
      const existing = repositoryHashes.get(digest);
      // A real library entry wins if a test fixture shares its exact bytes.
      if (!existing || (existing.testScore && !song.testScore)) repositoryHashes.set(digest, song);
    }
  }
  const aliases = new Map();
  const choices = await Promise.all(allSongs.map(async song => {
    if (song.testScore) return null;
    if (song.localOnly && typeof song.xml === 'string' && globalThis.crypto?.subtle) {
      try {
        const variants = [...new Set([song.xml, normalizedXML(song.xml)])];
        const digests = await Promise.all(variants.map(async xml => hexDigest(
          await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(xml))
        )));
        const match = digests.map(digest => repositoryHashes.get(digest)).find(Boolean);
        if (match) {
          if (!match.testScore) aliases.set(song.id, match.id);
          return null;
        }
        if (digests.some(digest => TEST_SCORE_SHA256.has(digest))) return null;
      } catch (_) {
        // If hashing is unavailable, keep the recoverable copy visible.
      }
    }
    return song;
  }));
  return {songs: choices.filter(Boolean), aliases};
}

function safePath(value, kind) {
  if (typeof value !== 'string' || value.length > 500 || /[\\\u0000-\u001f\u007f]/.test(value)) return false;
  const segments = value.split('/');
  if (segments.length < 2 || segments.some(segment => !segment || segment === '.' || segment === '..')) return false;
  if (kind === 'score') return segments[0] === 'scores'
    && segments.every(segment => /^[A-Za-z0-9_-][A-Za-z0-9_.-]*$/.test(segment))
    && /\.(musicxml|xml)$/i.test(value);
  return ['scores', 'uploads', 'sources'].includes(segments[0]);
}

function boundedText(value, name, {required = false} = {}) {
  if (value === undefined && !required) return '';
  if (typeof value !== 'string' || value.length > 500 || (required && !value.trim())) {
    throw new Error(`The song catalog contains an invalid ${name}.`);
  }
  return value;
}

/** Reject malformed paths instead of treating catalog entries as arbitrary URLs. */
export function validateSongCatalog(value) {
  if (!value || value.version !== 1 || !Array.isArray(value.songs) || !value.songs.length || value.songs.length > 5000) {
    throw new Error('The published song catalog has an unsupported or empty format.');
  }
  const ids = new Set();
  const songs = value.songs.map(entry => {
    if (!entry || typeof entry.id !== 'string' || !/^[a-z0-9][a-z0-9._-]{0,127}$/.test(entry.id) || ids.has(entry.id)) {
      throw new Error('The song catalog contains an invalid or duplicate song ID.');
    }
    ids.add(entry.id);
    if (!safePath(entry.scorePath, 'score')) throw new Error('The song catalog contains an unsafe score path.');
    if (entry.sourcePath !== undefined && !safePath(entry.sourcePath, 'source')) {
      throw new Error('The song catalog contains an unsafe original-file path.');
    }
    const song = {
      id: entry.id,
      title: boundedText(entry.title, 'title', {required: true}),
      composer: boundedText(entry.composer, 'composer'),
      scorePath: entry.scorePath,
    };
    if (entry.sourcePath !== undefined) song.sourcePath = entry.sourcePath;
    for (const key of ['sourceFilename', 'updatedAt', 'description']) {
      if (entry[key] !== undefined) song[key] = boundedText(entry[key], key);
    }
    for (const key of ['sha256', 'sourceSha256']) {
      if (entry[key] !== undefined) {
        if (typeof entry[key] !== 'string' || !/^[a-f0-9]{64}$/i.test(entry[key])) {
          throw new Error(`The song catalog contains an invalid ${key}.`);
        }
        song[key] = entry[key].toLowerCase();
      }
    }
    if (entry.testScore === true) song.testScore = true;
    // Informational provenance is data only, never a script, URL or fetch target.
    if (entry.provenance && typeof entry.provenance === 'object' && !Array.isArray(entry.provenance)) {
      song.provenance = entry.provenance;
    }
    return song;
  });
  if (typeof value.defaultSongId !== 'string' || !ids.has(value.defaultSongId)) {
    throw new Error('The song catalog does not contain its default song.');
  }
  const importErrors = [];
  if (value.importErrors !== undefined) {
    if (!Array.isArray(value.importErrors) || value.importErrors.length > 5000) {
      throw new Error('The song catalog contains invalid upload diagnostics.');
    }
    for (const issue of value.importErrors) {
      if (!issue || !safePath(issue.sourcePath, 'source')) {
        throw new Error('The song catalog contains an unsafe upload-diagnostic path.');
      }
      importErrors.push({
        sourcePath: issue.sourcePath,
        sourceFilename: boundedText(issue.sourceFilename, 'upload filename', {required: true}),
        message: boundedText(issue.message, 'upload error', {required: true}),
      });
    }
  }
  return {version: 1, defaultSongId: value.defaultSongId, songs, importErrors};
}

async function fetchText(url, {fetchImpl, timeoutMs, maxBytes, cacheKey}) {
  const target = new URL(url);
  if (!['https:', 'http:'].includes(target.protocol)) throw new Error('The song library URL is invalid.');
  if (cacheKey !== undefined) target.searchParams.set('library-refresh', String(cacheKey));
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(target.href, {cache: 'no-store', credentials: 'omit', signal: controller.signal});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (Number(response.headers?.get('content-length')) > maxBytes) throw new Error('The published file exceeds the size limit.');
    const text = await response.text();
    if (new TextEncoder().encode(text).length > maxBytes) throw new Error('The published file exceeds the size limit.');
    return text;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Fetch the deployed catalog first, then the same gh-pages files via GitHub raw.
 * A fallback is explicit; local IndexedDB is never a source of saved songs.
 */
export async function loadSongLibrary({
  fetchImpl = globalThis.fetch,
  deployedCatalogUrl = new URL('./song-library.json', import.meta.url).href,
  timeoutMs = 12000,
  cacheKey = Date.now(),
} = {}) {
  const deployedBase = new URL('./', deployedCatalogUrl).href;
  const locations = [
    {source: 'deployed', url: deployedCatalogUrl, base: deployedBase},
    {source: 'github', url: new URL(SONG_LIBRARY.catalogFilename, RAW_BASE).href, base: RAW_BASE},
  ];
  const errors = [];
  for (let index = 0; index < locations.length; index++) {
    const location = locations[index];
    try {
      const text = await fetchText(location.url, {fetchImpl, timeoutMs, maxBytes: MAX_CATALOG_BYTES, cacheKey});
      const catalog = validateSongCatalog(JSON.parse(text));
      const alternate = locations[1 - index];
      return {
        ...catalog,
        source: location.source,
        warning: '',
        songs: catalog.songs.map(song => ({
          ...song,
          url: new URL(song.scorePath, location.base).href,
          fallbackUrl: new URL(song.scorePath, alternate.base).href,
          librarySource: location.source,
          repositorySaved: true,
          originalUrl: song.sourcePath ? `https://github.com/${SONG_LIBRARY.repository}/blob/${SONG_LIBRARY.sourceBranch}/${SONG_LIBRARY.sourcePath}/${song.sourcePath.split('/').map(encodeURIComponent).join('/')}` : undefined,
        })),
      };
    } catch (error) {
      errors.push(`${location.source}: ${error.name === 'AbortError' ? 'request timed out' : error.message}`);
    }
  }
  throw new Error('Song list unavailable. Check your connection and refresh.', {cause: errors});
}

/** Retrieve a score and verify the catalog digest when Web Crypto is available. */
export async function loadSongScore(song, {fetchImpl = globalThis.fetch, timeoutMs = 12000} = {}) {
  if (!song?.url) throw new Error('This song has no published score.');
  const urls = [...new Set([song.url, song.fallbackUrl].filter(Boolean))];
  const errors = [];
  for (let index = 0; index < urls.length; index++) {
    try {
      const xml = await fetchText(urls[index], {fetchImpl, timeoutMs, maxBytes: MAX_SCORE_BYTES});
      if (song.sha256 && globalThis.crypto?.subtle) {
        const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(xml));
        const actual = hexDigest(digest);
        if (actual !== song.sha256) throw new Error('The score does not yet match the published catalog.');
      }
      return {xml, warning: ''};
    } catch (error) {
      errors.push(error.name === 'AbortError' ? 'request timed out' : error.message);
    }
  }
  throw new Error('Score unavailable. Refresh and try again.', {cause: errors});
}
