const DATABASE = 'piano-song-library-v1';
const STORE = 'scores';
const SELECTION = 'piano-song-last-selection-v1';
const PREFERENCES = 'piano-song-preferences-v1';
export class SongStorage {
  constructor() { this.db = null; this.memory = new Map(); this.persistent = false; }
  async open() {
    if (!globalThis.indexedDB) return this;
    try {
      this.db = await new Promise((resolve, reject) => {
        const request = indexedDB.open(DATABASE, 1);
        request.onupgradeneeded = () => request.result.createObjectStore(STORE, {keyPath:'id'});
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
        request.onblocked = () => reject(new Error('Song storage is open in another window.'));
      });
      this.persistent = true;
    } catch (_) { this.persistent = false; }
    return this;
  }
  async list() {
    if (!this.db) return [...this.memory.values()];
    return new Promise((resolve, reject) => {
      const request = this.db.transaction(STORE, 'readonly').objectStore(STORE).getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  async put(song) {
    if (!this.db) { this.memory.set(song.id, song); return false; }
    await new Promise((resolve, reject) => {
      const transaction = this.db.transaction(STORE, 'readwrite');
      transaction.objectStore(STORE).put(song);
      transaction.oncomplete = resolve;
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error || new Error('Saving this score was interrupted.'));
    });
    return true;
  }
  lastSelection() { try { return localStorage.getItem(SELECTION); } catch (_) { return null; } }
  select(id) { try { localStorage.setItem(SELECTION, id); } catch (_) {} }
  preferences() { try { return JSON.parse(localStorage.getItem(PREFERENCES) || '{}') || {}; } catch (_) { return {}; } }
  savePreferences(value) { try { localStorage.setItem(PREFERENCES, JSON.stringify(value)); } catch (_) {} }
}
export async function scoreIdentity(xml) {
  if (globalThis.crypto?.subtle) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(xml));
    return 'upload-' + Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2,'0')).join('');
  }
  let hash = 2166136261;
  for (let i = 0; i < xml.length; i++) hash = Math.imul(hash ^ xml.charCodeAt(i), 16777619);
  return 'upload-' + (hash >>> 0).toString(16) + '-' + xml.length;
}
