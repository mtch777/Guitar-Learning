const REPO = 'mtch777/Guitar-Learning';
const WORKFLOW = 'piano-import-midi.yml';
const ALLOWED_HOSTS = new Set(['s3w.musescore.com', 'raw.githubusercontent.com']);
export const MIDI_HANDOFF_KEY = 'musescore-midi';

export function tutorialUrl(value) {
  let url;
  try { url = new URL(value); } catch (_) { throw new Error('Enter a valid MuseScore score URL.'); }
  if (url.protocol !== 'https:' || url.hostname !== 'musescore.com' || url.username || url.password ||
      !/^\/user\/\d+\/scores\/\d+(?:\/piano-tutorial)?\/?$/.test(url.pathname)) {
    throw new Error('Enter a MuseScore score URL (musescore.com/user/…/scores/…).');
  }
  return `${url.origin}${url.pathname.replace(/\/piano-tutorial\/?$|\/$/, '')}/piano-tutorial`;
}

export function consumeMidiHandoff(locationLike, historyLike) {
  const hash = String(locationLike.hash || '').replace(/^#/, '');
  const params = new URLSearchParams(hash);
  if (!params.has(MIDI_HANDOFF_KEY)) return null;
  // Remove temporary signed links from the visible URL immediately.
  historyLike.replaceState(null, '', locationLike.pathname + locationLike.search);
  return validateMidiUrl(params.get(MIDI_HANDOFF_KEY));
}

export function validateMidiUrl(value) {
  let url;
  try { url = new URL(value); } catch (_) { throw new Error('Enter a valid direct MIDI download URL.'); }
  if (url.protocol !== 'https:' || !ALLOWED_HOSTS.has(url.hostname) || url.username || url.password || url.hash) {
    throw new Error('Use a direct HTTPS MIDI URL from an allowed host, not a MuseScore score-page URL.');
  }
  return url.href;
}

export async function dispatchMidiImport(url, token, {fetchImpl = globalThis.fetch} = {}) {
  const validated = validateMidiUrl(url);
  if (!String(token || '').trim()) throw new Error('Enter your GitHub token. It needs Actions: write access.');
  let response;
  try {
    response = await fetchImpl(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
      method:'POST', credentials:'omit', cache:'no-store',
      headers:{
        Accept:'application/vnd.github+json',
        Authorization:`Bearer ${String(token).trim()}`,
        'Content-Type':'application/json',
        'X-GitHub-Api-Version':'2022-11-28',
      },
      body:JSON.stringify({ref:'main', inputs:{midi_url:validated}}),
    });
  } catch (_) { throw new Error('GitHub could not be reached.'); }
  if (response.status === 204) return {queued:true};
  if (response.status === 401 || response.status === 403) throw new Error('GitHub rejected the request. Your token needs Actions: write permission.');
  if (response.status === 404) throw new Error('The MIDI import workflow is not published on GitHub yet.');
  throw new Error(`Could not start MIDI import (HTTP ${response.status}).`);
}
