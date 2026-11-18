const KEY = 'piano-song-github-credential-v1';

/** Optional, device-local persistence. The token is never included in published files. */
export const githubCredentials = Object.freeze({
  get() {
    try { return globalThis.localStorage?.getItem(KEY) || ''; }
    catch (_) { return ''; }
  },
  save(token) {
    if (!String(token || '').trim()) return false;
    try { globalThis.localStorage?.setItem(KEY, String(token).trim()); return true; }
    catch (_) { return false; }
  },
  forget() {
    try { globalThis.localStorage?.removeItem(KEY); }
    catch (_) { /* Private browsing may prohibit persistent storage. */ }
  },
});
