const REPO = 'mtch777/Guitar-Learning';
const ALLOWED_HOSTS = new Set(['s3w.musescore.com', 'raw.githubusercontent.com']);
const REQUEST_KEY = 'piano-musescore-import-request-v1';
const REQUEST_ID = /^gl-[a-f0-9]{32}$/;
const HANDOFF_KEY = 'musescore-midi';

export function newImportId(cryptoImpl = globalThis.crypto) {
  if (!cryptoImpl?.randomUUID) throw new Error('A secure browser is needed to import a score.');
  return `gl-${cryptoImpl.randomUUID().replace(/-/g, '').toLowerCase()}`;
}

export function scorePageUrl(value) {
  const input = String(value ?? '').trim();
  // MuseScore redirects /user/0/scores/{id} to the correct uploader's page.
  if (/^\d{1,12}$/.test(input)) return 'https://musescore.com/user/0/scores/' + input;
  let url;
  try { url = new URL(input); } catch (_) { throw new Error('Enter a MuseScore score ID or URL.'); }
  if (url.protocol !== 'https:' || !['musescore.com', 'www.musescore.com'].includes(url.hostname) || url.username || url.password ||
      !/^\/(?:user\/\d+|[a-zA-Z0-9_-]+)\/scores\/\d+(?:\/piano-tutorial)?\/?$/.test(url.pathname)) {
    throw new Error('Enter a MuseScore score URL (musescore.com/user/…/scores/…).');
  }
  return `https://musescore.com${url.pathname.replace(/\/piano-tutorial\/?$|\/$/, '')}`;
}

export function beginMuseScoreImport(value, {storage = globalThis.sessionStorage, id = newImportId()} = {}) {
  if (!REQUEST_ID.test(id)) throw new Error('Invalid import request.');
  const scorePage = scorePageUrl(value);
  try { storage.setItem(REQUEST_KEY, id); }
  catch (_) { throw new Error('Enable browser session storage to import songs.'); }
  return `${scorePage}#${new URLSearchParams({'guitar-learning-import':id})}`;
}

/** Only accept a MIDI link after this tab initiated the matching MuseScore visit. */
export function consumeMidiHandoff(locationLike, historyLike, {storage = globalThis.sessionStorage} = {}) {
  const params = new URLSearchParams(String(locationLike.hash || '').replace(/^#/, ''));
  if (!params.has(HANDOFF_KEY) && !params.has('musescore-error')) return null;
  historyLike.replaceState(null, '', locationLike.pathname + locationLike.search);
  const id = params.get('musescore-request');
  // Old manually obtained MIDI links still open the import dialog, but do not
  // automatically spend the saved GitHub credential on an unsolicited link.
  if (!id && params.has(HANDOFF_KEY)) {
    return {id:newImportId(), url:validateMidiUrl(params.get(HANDOFF_KEY)), title:'', legacy:true};
  }
  if (!id || !REQUEST_ID.test(id) || storage.getItem(REQUEST_KEY) !== id) {
    throw new Error('This MIDI return was not started by this lesson tab. Try Import again.');
  }
  storage.removeItem(REQUEST_KEY);
  if (params.has('musescore-error')) {
    const error = String(params.get('musescore-error') || 'MuseScore MIDI could not be found.').slice(0, 250);
    // The fragment never reaches the server. Preserve the entire on-device
    // trace (rather than truncating the JSON and losing its failure details).
    const debug = String(params.get('musescore-debug') || '').replace(/[\u0000-\u001f\u007f]/g, ' ').slice(0, 50000);
    return debug ? {id, error, debug} : {id, error};
  }
  return {id, url:validateMidiUrl(params.get(HANDOFF_KEY)), title:cleanTitle(params.get('musescore-title'))};
}

export function cleanTitle(value) {
  return String(value || '').replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 100);
}

export function validateMidiUrl(value) {
  let url;
  try { url = new URL(value); } catch (_) { throw new Error('Enter a valid direct MIDI download URL.'); }
  if (url.protocol !== 'https:' || !ALLOWED_HOSTS.has(url.hostname) || url.username || url.password || url.hash ||
      !/\.mid(?:i)?$/i.test(url.pathname)) {
    throw new Error('Use a direct HTTPS MIDI URL from an allowed host, not a MuseScore score-page URL.');
  }
  return url.href;
}

export async function dispatchMidiImport(url, token, {id = newImportId(), title = '', fetchImpl = globalThis.fetch} = {}) {
  const validated = validateMidiUrl(url);
  if (!REQUEST_ID.test(id)) throw new Error('Invalid import request.');
  if (!String(token || '').trim()) throw new Error('Enter your saved GitHub token (Contents: read and write).');
  let response;
  try {
    response = await fetchImpl(`https://api.github.com/repos/${REPO}/dispatches`, {
      method:'POST', credentials:'omit', cache:'no-store',
      headers:{
        Accept:'application/vnd.github+json',
        Authorization:`Bearer ${String(token).trim()}`,
        'Content-Type':'application/json',
        'X-GitHub-Api-Version':'2022-11-28',
      },
      body:JSON.stringify({event_type:'piano-midi-import', client_payload:{midi_url:validated, request_id:id, title:cleanTitle(title)}}),
    });
  } catch (_) { throw new Error('GitHub could not be reached.'); }
  if (response.status === 204) return {queued:true, id};
  if (response.status === 401 || response.status === 403) throw new Error('GitHub rejected the request. Your token needs Contents: write permission.');
  if (response.status === 404) throw new Error('The GitHub import repository was not found or is inaccessible.');
  throw new Error(`Could not start MIDI import (HTTP ${response.status}).`);
}
