(function () {
  'use strict';

  // GitHub is the shared source of truth. Local storage queues offline visits.
  const API = 'https://api.github.com/repos/mtch777/Guitar-Learning/contents/public/piano/shared/practice-activity.json';
  const TOKEN_KEY = 'piano-song-github-credential-v1';
  const EVENT_KEY = 'practiceAppEventsV2';
  const OLD_KEY = 'practiceAppLessonOpensV1';
  const MIGRATION_KEY = 'practiceAppLegacyMigratedV2';
  const WINDOW_DAYS = 7;
  let remote = {version:1, confirmedDays:[], events:[]};
  let localEvents = [];
  let request = null;
  let writing = null;
  let loaded = false;
  let status = 'Loading GitHub activity…';
  const timelines = new Map();
  const counters = new Set();

  function read(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key) || '') || fallback; }
    catch (_) { return fallback; }
  }
  function persist() {
    try { localStorage.setItem(EVENT_KEY, JSON.stringify(localEvents)); } catch (_) {}
  }
  function dateKey(date) {
    return date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2,'0') +
      '-' + String(date.getDate()).padStart(2,'0');
  }
  function validEvent(value) {
    return value && typeof value.id === 'string' && value.id.length <= 160 &&
      typeof value.lesson === 'string' && value.lesson.length <= 120 &&
      /^\d{4}-\d{2}-\d{2}$/.test(value.day);
  }
  function normalize(value) {
    return {
      version:1,
      confirmedDays:Array.isArray(value && value.confirmedDays)
        ? [...new Set(value.confirmedDays.filter(v => /^\d{4}-\d{2}-\d{2}$/.test(v)))].sort() : [],
      events:Array.isArray(value && value.events) ? value.events.filter(validEvent) : [],
    };
  }
  function merge(first, second) {
    const a = normalize(first), b = normalize(second);
    const events = new Map();
    for (const entry of a.events.concat(b.events)) events.set(entry.id, entry);
    return {
      version:1,
      confirmedDays:[...new Set(a.confirmedDays.concat(b.confirmedDays))].sort(),
      events:[...events.values()].sort((x,y) => x.day.localeCompare(y.day) || x.id.localeCompare(y.id)),
    };
  }
  function migrateOldHistory() {
    const stored = normalize({events:read(EVENT_KEY, [])}).events;
    let migrated = false;
    try { migrated = localStorage.getItem(MIGRATION_KEY) === '1'; } catch (_) {}
    if (migrated) return stored;
    const old = read(OLD_KEY, {});
    const cutoff = Date.now() - WINDOW_DAYS * 86400000;
    const migratedEvents = [];
    for (const [lesson, timestamps] of Object.entries(old)) {
      if (!Array.isArray(timestamps)) continue;
      timestamps.forEach((time, index) => {
        if (!Number.isFinite(time) || time < cutoff) return;
        migratedEvents.push({
          id:'legacy-' + encodeURIComponent(lesson).slice(0,100) + '-' + time + '-' + index,
          day:dateKey(new Date(time)), lesson,
        });
      });
    }
    const result = merge({events:stored}, {events:migratedEvents}).events;
    try { localStorage.setItem(MIGRATION_KEY, '1'); } catch (_) {}
    return result;
  }
  localEvents = migrateOldHistory();
  persist();

  function events() { return merge(remote, {events:localEvents}).events; }
  function practicedDays() {
    return new Set(remote.confirmedDays.concat(events().map(event => event.day)));
  }
  function getDailyActivity(days = WINDOW_DAYS) {
    const count = Math.max(1, Number(days) || WINDOW_DAYS);
    const present = practicedDays(), today = new Date(), result = [];
    for (let offset = count - 1; offset >= 0; offset--) {
      const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() - offset);
      result.push({date, practiced:present.has(dateKey(date))});
    }
    return result;
  }
  function weekEvents() {
    const today = new Date();
    const first = new Date(today.getFullYear(), today.getMonth(), today.getDate() - WINDOW_DAYS + 1);
    return events().filter(event => event.day >= dateKey(first));
  }
  function count(lesson) { return weekEvents().filter(event => event.lesson === lesson).length; }
  function total() { return weekEvents().length; }
  function setStatus(message) {
    status = message;
    const element = document.getElementById('activitySyncStatus');
    if (element) element.textContent = message;
  }
  function paintTimeline(element, days) {
    const activity = getDailyActivity(days);
    element.replaceChildren();
    activity.forEach((day, index) => {
      const item = document.createElement('div');
      item.className = 'activity-day';
      const square = document.createElement('div');
      square.className = 'activity-square' + (day.practiced ? ' active' : '');
      const full = day.date.toLocaleDateString(undefined,{weekday:'long',month:'short',day:'numeric'});
      square.setAttribute('role','img');
      square.setAttribute('aria-label',full + ': ' + (day.practiced ? 'practiced' : 'no practice'));
      square.title = full + ' · ' + (day.practiced ? 'Practiced' : 'No practice');
      const label = document.createElement('span');
      label.className = 'activity-label';
      label.textContent = index === activity.length - 1 ? 'Today' :
        day.date.toLocaleDateString(undefined,{weekday:'short'});
      item.append(square,label);
      element.append(item);
    });
  }
  function paintCounts(root) {
    const scope = root || document;
    scope.querySelectorAll('[data-lesson-count]').forEach(element => {
      const value = count(element.getAttribute('data-lesson-count'));
      element.textContent = value + (value === 1 ? ' open' : ' opens') + ' · last 7 days';
    });
    scope.querySelectorAll('[data-total-count]').forEach(element => {
      const value = total();
      element.textContent = value + (value === 1 ? ' lesson open' : ' lesson opens');
    });
  }
  function render() {
    for (const [element, days] of timelines) paintTimeline(element, days);
    for (const root of counters) paintCounts(root);
  }
  function authToken() {
    try { return localStorage.getItem(TOKEN_KEY) || ''; } catch (_) { return ''; }
  }
  function fromBase64(value) {
    const bytes = Uint8Array.from(atob(String(value || '').replace(/\s/g,'')), ch => ch.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  }
  function toBase64(value) {
    const bytes = new TextEncoder().encode(value);
    let data = '';
    for (let i = 0; i < bytes.length; i += 8192) data += String.fromCharCode(...bytes.subarray(i, i+8192));
    return btoa(data);
  }
  async function getRemote() {
    const response = await fetch(API + '?ref=main&time=' + Date.now(), {
      cache:'no-store', credentials:'omit', headers:{Accept:'application/vnd.github+json'},
    });
    if (!response.ok) throw new Error('GitHub history read HTTP ' + response.status);
    const file = await response.json();
    if (!file.sha || !file.content) throw new Error('GitHub history is unavailable.');
    return {sha:file.sha, data:normalize(JSON.parse(fromBase64(file.content)))};
  }
  function unsaved() {
    return localEvents.some(event => !remote.events.some(saved => saved.id === event.id));
  }
  function refresh() {
    if (request) return request;
    request = getRemote().then(latest => {
      remote = latest.data;
      loaded = true;
      render();
      setStatus(unsaved() ? 'Activity loaded · saving local changes…' : 'Activity loaded from GitHub');
      return latest;
    }).catch(error => {
      console.warn('Practice tracker: GitHub read failed', error);
      setStatus('GitHub unavailable · showing queued activity');
      return null;
    }).finally(() => { request = null; });
    return request;
  }
  function sync() {
    if (writing) return writing.then(() => unsaved() ? sync() : true);
    const credential = authToken();
    if (!credential) return refresh().then(() => {
      if (unsaved()) setStatus('Practice not saved · save GitHub token in Upload song');
      return !unsaved();
    });
    writing = (async () => {
      setStatus('Saving practice to GitHub…');
      for (let attempt = 0; attempt < 4; attempt++) {
        const latest = await getRemote();
        const next = merge(latest.data, {events:localEvents});
        if (next.events.length === latest.data.events.length &&
            next.confirmedDays.length === latest.data.confirmedDays.length) {
          remote = next; loaded = true; render();
          setStatus('Practice saved on GitHub');
          return true;
        }
        const response = await fetch(API, {
          method:'PUT', cache:'no-store', credentials:'omit',
          headers:{
            Accept:'application/vnd.github+json',
            Authorization:'Bearer ' + credential,
            'Content-Type':'application/json',
            'X-GitHub-Api-Version':'2022-11-28',
          },
          body:JSON.stringify({
            message:'Save piano practice activity',
            content:toBase64(JSON.stringify(next,null,2) + '\n'),
            sha:latest.sha, branch:'main',
          }),
        });
        if (response.ok) {
          remote = next; loaded = true; render();
          setStatus('Practice saved on GitHub');
          return true;
        }
        if (![409,422].includes(response.status)) throw new Error('GitHub history write HTTP ' + response.status);
      }
      throw new Error('Practice history changed while saving. Please retry.');
    })().catch(error => {
      console.warn('Practice tracker: GitHub save failed', error);
      setStatus('GitHub save failed · practice queued on this device');
      return false;
    }).finally(() => { writing = null; });
    return writing;
  }
  function recordOpen(lesson) {
    if (typeof lesson !== 'string' || !lesson) return;
    const id = typeof globalThis.crypto?.randomUUID === 'function' ?
      globalThis.crypto.randomUUID() : Date.now() + '-' + Math.random().toString(36).slice(2);
    localEvents = merge({events:localEvents}, {events:[{id,day:dateKey(new Date()),lesson}]}).events;
    persist(); render();
    void sync();
  }
  function renderActivityTimeline(element, days = WINDOW_DAYS) {
    if (!element) return;
    timelines.set(element,days);
    paintTimeline(element,days);
    setStatus(status);
    void refresh().then(() => { if (authToken()) void sync(); });
  }
  function renderCounts(root) {
    counters.add(root || document);
    paintCounts(root || document);
    void refresh().then(() => { if (authToken()) void sync(); });
  }
  window.PracticeTracker = Object.freeze({
    recordOpen,count,total,getDailyActivity,renderActivityTimeline,renderCounts,refresh,sync,
    getStatus:() => ({
      loaded,status,
      days:getDailyActivity(WINDOW_DAYS).map(day => ({day:dateKey(day.date),practiced:day.practiced})),
    }),
  });
})();