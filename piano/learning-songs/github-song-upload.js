import {SONG_LIBRARY} from './github-song-storage.js';

const MAX_BYTES = 20 * 1024 * 1024;
const hex = buffer => Array.from(new Uint8Array(buffer), value => value.toString(16).padStart(2, '0')).join('');

/** GitHub Pages has no server. Commit directly using a user-supplied, transient token. */
export async function uploadScoreToGitHub(file, token, {
  fetchImpl = globalThis.fetch,
  cryptoImpl = globalThis.crypto,
  encodeBase64 = globalThis.btoa,
} = {}) {
  if (!file || !/\.(musicxml|xml|mxl)$/i.test(file.name)) {
    throw new Error('Choose a MusicXML (.musicxml, .xml or .mxl) score.');
  }
  if (!file.size || file.size > MAX_BYTES) throw new Error('Choose a nonempty score smaller than 20 MB.');
  if (!String(token || '').trim()) throw new Error('Enter a GitHub token with Contents: read and write access to this repository.');
  if (!cryptoImpl?.subtle) throw new Error('Secure file hashing is unavailable in this browser.');
  const bytes = new Uint8Array(await file.arrayBuffer());
  const digest = hex(await cryptoImpl.subtle.digest('SHA-256', bytes));
  const extension = file.name.split('.').pop().toLowerCase();
  const originalStem = file.name.slice(0, -(extension.length + 1));
  const stem = originalStem.normalize('NFKC').replace(/[^\p{L}\p{N}._ -]/gu, '_').replace(/^\.+/, '').trim().slice(0, 80) || 'score';
  const filename = `${stem}--${digest}.${extension}`;
  const path = `${SONG_LIBRARY.sourcePath}/uploads/${filename}`;
  const apiPath = path.split('/').map(encodeURIComponent).join('/');
  const url = `https://api.github.com/repos/${SONG_LIBRARY.repository}/contents/${apiPath}`;
  const chunks = [];
  for (let i = 0; i < bytes.length; i += 0x6000) {
    chunks.push(String.fromCharCode(...bytes.subarray(i, i + 0x6000)));
  }
  const content = encodeBase64(chunks.join(''));
  let response;
  try {
    response = await fetchImpl(url, {
      method:'PUT',
      headers:{
        Accept:'application/vnd.github+json',
        Authorization:`Bearer ${String(token).trim()}`,
        'Content-Type':'application/json',
        'X-GitHub-Api-Version':'2022-11-28',
      },
      credentials:'omit',
      cache:'no-store',
      body:JSON.stringify({message:`Add piano score ${filename}`, content, branch:SONG_LIBRARY.sourceBranch}),
    });
  } catch (_) {
    throw new Error('GitHub could not be reached. Check your connection and try again.');
  }
  if (response.status === 201) return {digest, filename, path};
  if (response.status === 401 || response.status === 403) {
    throw new Error('GitHub rejected the token. It needs Contents: read and write permission for mtch777/Guitar-Learning.');
  }
  if (response.status === 422) throw new Error('This file may already be uploaded. Refresh songs to check the library.');
  throw new Error(`GitHub rejected the upload (HTTP ${response.status}).`);
}
