import {SONG_LIBRARY} from './github-song-storage.js';

const repo = `https://api.github.com/repos/${SONG_LIBRARY.repository}`;
const sourceRoot = SONG_LIBRARY.sourcePath;
const safeRelative = path => typeof path === 'string' && /^(?:uploads|scores)\/[\p{L}\p{N}._ /()-]+$/u.test(path)
  && !path.split('/').some(segment => !segment || segment === '.' || segment === '..');

/** Delete the GitHub source and (for a seeded song) its catalog entry atomically. */
export async function deleteSongFromGitHub(song, token, {fetchImpl = globalThis.fetch} = {}) {
  if (!song?.id || !safeRelative(song.sourcePath)) throw new Error('This song has no deletable GitHub source.');
  const authorization = String(token || '').trim();
  if (!authorization) throw new Error('Enter a GitHub token with Contents: read and write access.');
  const headers = {Accept:'application/vnd.github+json', Authorization:`Bearer ${authorization}`,
    'Content-Type':'application/json', 'X-GitHub-Api-Version':'2022-11-28'};
  async function request(path, {method = 'GET', body} = {}) {
    let response;
    try { response = await fetchImpl(`${repo}/${path}`, {method, headers, credentials:'omit', cache:'no-store', ...(body ? {body:JSON.stringify(body)} : {})}); }
    catch (_) { throw new Error('GitHub could not be reached. Check your connection.'); }
    if (response.status === 401 || response.status === 403) throw new Error('GitHub rejected the token. It needs Contents: read and write access.');
    if (!response.ok) throw new Error(response.status === 409 || response.status === 422
      ? 'The GitHub library changed during deletion. Refresh songs and try again.'
      : `GitHub deletion failed (HTTP ${response.status}).`);
    return response.json();
  }
  const branch = SONG_LIBRARY.sourceBranch;
  const ref = await request(`git/ref/heads/${encodeURIComponent(branch)}`);
  const parent = ref.object?.sha;
  if (!/^[a-f0-9]{40}$/i.test(parent || '')) throw new Error('GitHub did not provide a valid branch revision.');
  const commit = await request(`git/commits/${parent}`);
  const baseTree = commit.tree?.sha;
  if (!/^[a-f0-9]{40}$/i.test(baseTree || '')) throw new Error('GitHub did not provide a valid source tree.');

  const changes = [];
  if (song.sourcePath.startsWith('uploads/')) {
    changes.push({path:`${sourceRoot}/${song.sourcePath}`, mode:'100644', type:'blob', sha:null});
  } else {
    const seedPath = `${sourceRoot}/song-library.seed.json`;
    const seedResponse = await request(`contents/${seedPath.split('/').map(encodeURIComponent).join('/')}?ref=${encodeURIComponent(branch)}`);
    if (seedResponse.encoding !== 'base64' || typeof seedResponse.content !== 'string') throw new Error('GitHub returned an invalid song list.');
    const binary = globalThis.atob(seedResponse.content.replace(/\s/g, ''));
    const original = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) original[i] = binary.charCodeAt(i);
    const seed = JSON.parse(new TextDecoder().decode(original));
    const entry = seed.songs?.find(item => item.id === song.id && item.scorePath === song.scorePath);
    if (!entry || !safeRelative(entry.scorePath) || !safeRelative(entry.sourcePath || entry.scorePath)) {
      throw new Error('The song has changed in GitHub. Refresh songs and try again.');
    }
    seed.songs = seed.songs.filter(item => item.id !== song.id);
    if (seed.defaultSongId === song.id) seed.defaultSongId = seed.songs[0]?.id || null;
    const blob = await request('git/blobs', {method:'POST', body:{content:JSON.stringify(seed,null,2)+'\n', encoding:'utf-8'}});
    changes.push({path:seedPath, mode:'100644', type:'blob', sha:blob.sha});
    const stillUsed = new Set(seed.songs.flatMap(item => [item.scorePath, item.sourcePath, item.provenance].filter(Boolean)));
    for (const path of [entry.scorePath, entry.sourcePath, entry.provenance].filter(Boolean)) {
      if (!safeRelative(path) || stillUsed.has(path)) continue;
      changes.push({path:`${sourceRoot}/${path}`, mode:'100644', type:'blob', sha:null});
    }
  }
  const tree = await request('git/trees', {method:'POST', body:{base_tree:baseTree, tree:changes}});
  const next = await request('git/commits', {method:'POST', body:{message:`Delete piano song ${song.id}`, tree:tree.sha, parents:[parent]}});
  await request(`git/refs/heads/${encodeURIComponent(branch)}`, {method:'PATCH', body:{sha:next.sha, force:false}});
  return {id:song.id, commit:next.sha};
}
