// ==UserScript==
// @name         Guitar Learning: automatic MuseScore MIDI import
// @namespace    https://mtch777.github.io/Guitar-Learning/
// @version      1.2.0
// @description  Load MuseScore's MIDI automatically and return it to the Learning Songs lesson.
// @match        https://mtch777.github.io/Guitar-Learning/piano/learning-songs/*
// @match        https://musescore.com/user/*/scores/*
// @match        https://www.musescore.com/user/*/scores/*
// @run-at       document-start
// @grant        none
// @downloadURL  https://mtch777.github.io/Guitar-Learning/piano/learning-songs/musescore-auto-import.user.js
// @updateURL    https://mtch777.github.io/Guitar-Learning/piano/learning-songs/musescore-auto-import.user.js
// ==/UserScript==

// This runs entirely in the user's authorized MuseScore browser session. It never
// reads the GitHub token, makes a background login, or bypasses access checks.
(function () {
  'use strict';
  const LESSON = 'https://mtch777.github.io/Guitar-Learning/piano/learning-songs/';
  const REQUEST_ID = /^gl-[a-f0-9]{32}$/;
  const REQUEST_KEY = 'guitar-learning-import-request';
  const MAX_WAIT_MS = 90000;
  const HELPER_VERSION = '1.2.0';

  if (location.hostname === 'mtch777.github.io') {
    const markReady = () => {
      if (document.documentElement) {
        document.documentElement.dataset.musescoreHelper = 'ready';
        document.documentElement.dataset.musescoreHelperVersion = HELPER_VERSION;
      }
      window.dispatchEvent(new Event('musescore-helper-ready'));
    };
    markReady();
    document.addEventListener('DOMContentLoaded', markReady, {once:true});
    return;
  }
  if (!['musescore.com', 'www.musescore.com'].includes(location.hostname)) return;
  // The main score page starts the hidden tutorial. The tutorial itself needs
  // its own request interceptor: an iframe's jmuse JSON is not in its parent's
  // fetch/XHR responses, and score.mid may never appear in resource timing.
  const inTutorialFrame = window.top !== window;
  const params = new URLSearchParams(location.hash.slice(1));
  let requestId = params.get(inTutorialFrame ? 'guitar-learning-capture' : 'guitar-learning-import');
  if (inTutorialFrame) {
    // Do not observe or relay arbitrary MuseScore tabs/iframes.
    if (!REQUEST_ID.test(requestId || '')) return;
  } else if (REQUEST_ID.test(requestId || '')) {
    try { sessionStorage.setItem(REQUEST_KEY, JSON.stringify({id:requestId, started:Date.now()})); } catch (_) {}
  } else {
    let stored;
    try { stored = JSON.parse(sessionStorage.getItem(REQUEST_KEY) || 'null'); } catch (_) {}
    if (!stored || !REQUEST_ID.test(stored.id) || Date.now() - stored.started > MAX_WAIT_MS) return;
    requestId = stored.id;
  }

  let completed = false;
  let timer;
  let observer;
  let tutorialFrame;
  let status;
  let frameLoaded = false;
  const startedAt = Date.now();
  const log = [];
  const seen = new Set();
  function safeDetail(value) {
    return String(value ?? '').replace(/https?:\/\/[^\s"']+/g, '[URL]').replace(/[\u0000-\u001f\u007f]/g, ' ').slice(0, 180);
  }
  const report = (phase, detail = '', context = inTutorialFrame ? 'tutorial-frame' : 'score-page') => {
    const safe = safeDetail(detail);
    const key = `${context}:${phase}:${safe}`;
    if (seen.has(key)) return;
    seen.add(key);
    const entry = {ms:Date.now() - startedAt, context, phase};
    if (safe) entry.detail = safe;
    if (inTutorialFrame) {
      window.parent.postMessage({source:'guitar-learning-midi-capture', id:requestId, event:entry}, location.origin);
    } else {
      if (log.length < 100) log.push(entry);
      if (status) status.textContent = `Importing MIDI… ${log.slice(-3).map(item => item.phase).join(' → ')}`;
    }
  };
  function resourceSummary(win) {
    try {
      const resources = win.performance.getEntriesByType('resource');
      return {
        total:resources.length,
        jmuse:resources.filter(entry => /\/api\/jmuse\?/.test(entry.name)).length,
        jmuseMidi:resources.filter(entry => /\/api\/jmuse\?/.test(entry.name) && /(?:\?|&)type=midi(?:&|$)/.test(entry.name)).length,
        midiFiles:resources.filter(entry => /\/score\.mid(?:\?|$)/.test(entry.name)).length,
      };
    } catch (error) { return {error:safeDetail(error?.message || error)}; }
  }
  function pageSummary(win) {
    try {
      return {
        path:win.location?.pathname || location.pathname,
        readyState:win.document?.readyState || 'unknown',
        visibility:win.document?.visibilityState || 'unknown',
        bodyCharacters:win.document?.body?.textContent?.length ?? null,
        hasPlayer:!!win.document?.querySelector?.('#jmuse-scroller-component'),
        resources:resourceSummary(win),
      };
    } catch (error) { return {error:safeDetail(error?.message || error)}; }
  }
  function diagnosticSnapshot() {
    return JSON.stringify({
      helper:HELPER_VERSION,
      request:requestId,
      elapsedMs:Date.now() - startedAt,
      browser:window.navigator?.userAgent || 'unknown',
      online:window.navigator?.onLine ?? null,
      viewport:{width:window.innerWidth || null, height:window.innerHeight || null},
      frameLoaded,
      scorePage:pageSummary(window),
      tutorialFrame:tutorialFrame?.contentWindow ? pageSummary(tutorialFrame.contentWindow) : {error:'No iframe window'},
      events:log,
    });
  }
  function finish(payload) {
    if (completed) return;
    completed = true;
    clearInterval(timer);
    observer?.disconnect();
    if (inTutorialFrame) return;
    try { sessionStorage.removeItem(REQUEST_KEY); } catch (_) {}
    const returnParams = new URLSearchParams({'musescore-request':requestId, ...payload});
    location.replace(`${LESSON}#${returnParams}`);
  }
  function isMidiUrl(candidate) {
    try {
      const url = new URL(candidate);
      return url.protocol === 'https:' && url.hostname === 's3w.musescore.com' &&
        /\/score\.mid$/i.test(url.pathname) && !url.username && !url.password;
    } catch (_) { return false; }
  }
  function hasAuthorization(headers) {
    if (!headers) return false;
    if (typeof headers.has === 'function') return headers.has('authorization');
    if (Array.isArray(headers)) return headers.some(entry => /^authorization$/i.test(String(entry?.[0])));
    return Object.keys(headers).some(name => /^authorization$/i.test(name));
  }
  function found(candidate) {
    if (!isMidiUrl(candidate)) return false;
    report('MIDI URL found');
    if (inTutorialFrame) {
      window.parent.postMessage({source:'guitar-learning-midi-capture', id:requestId, url:candidate}, location.origin);
      completed = true;
      return true;
    }
    const title = (document.querySelector('h1')?.textContent || document.title || '')
      .replace(/\s*[-|]\s*MuseScore.*$/i, '').replace(/\s+/g, ' ').trim().slice(0, 100);
    finish({'musescore-midi':candidate, 'musescore-title':title});
    return true;
  }
  function inspectFrame(win) {
    try {
      const resources = win.performance.getEntriesByType('resource');
      for (let i = resources.length - 1; i >= 0; i--) {
        const name = resources[i].name;
        if (/\/api\/jmuse\?/.test(name) && /(?:\?|&)type=midi(?:&|$)/.test(name)) report('MIDI API requested');
        if (found(name)) return true;
      }
      for (const frame of win.document.querySelectorAll('iframe')) {
        if (frame.contentWindow && inspectFrame(frame.contentWindow)) return true;
      }
    } catch (error) { report('Frame resource inspection failed', error?.message || error); }
    return false;
  }
  // Observe resource loading even when the page fetch/XHR hooks miss a call.
  try {
    observer = new PerformanceObserver(() => inspectFrame(window));
    observer.observe({type:'resource', buffered:true});
  } catch (error) { report('Performance observer unavailable', error?.message || error); }

  window.addEventListener('error', event => {
    report('Browser error', event.message || `${event.target?.tagName || 'resource'} load failed`);
  });
  window.addEventListener('unhandledrejection', event => {
    report('Unhandled promise rejection', event.reason?.message || event.reason || 'unknown');
  });

  // Capture successful jmuse MIDI responses as well. This covers cases where
  // the player receives the signed URL before score.mid appears in Performance.
  if (typeof window.fetch === 'function') {
    const nativeFetch = window.fetch;
    window.fetch = function (...args) {
      const target = String(args[0]?.url || args[0]);
      const isMidiCall = /\/api\/jmuse\?/.test(target) && /(?:\?|&)type=midi(?:&|$)/.test(target);
      if (isMidiCall) report('MIDI API requested', `fetch; authorization header: ${hasAuthorization(args[1]?.headers || args[0]?.headers) ? 'present' : 'not visible'}`);
      let result;
      try { result = nativeFetch.apply(this, args); }
      catch (error) {
        if (isMidiCall) report('MIDI API fetch threw', error?.message || error);
        throw error;
      }
      try {
        if (isMidiCall) {
          Promise.resolve(result).then(response => {
            report(`MIDI API HTTP ${response.status}`);
            return response.clone().json();
          }).then(json => {
            if (!found(json?.info?.url)) report('MIDI response had no URL', `${json?.result || 'unknown'}: ${json?.error?.name || json?.error?.message || 'no info.url'}`);
          }).catch(error => report('MIDI response unreadable', error?.message || error));
        }
      } catch (_) {}
      return result;
    };
  }
  if (typeof window.XMLHttpRequest === 'function') {
    const nativeOpen = window.XMLHttpRequest.prototype.open;
    const nativeSend = window.XMLHttpRequest.prototype.send;
    const nativeSetHeader = window.XMLHttpRequest.prototype.setRequestHeader;
    window.XMLHttpRequest.prototype.open = function (method, url, ...other) {
      this.__guitarLearningMidiResponse = /\/api\/jmuse\?/.test(String(url)) &&
        /(?:\?|&)type=midi(?:&|$)/.test(String(url));
      this.__guitarLearningHasAuth = false;
      return nativeOpen.call(this, method, url, ...other);
    };
    if (typeof nativeSetHeader === 'function') {
      window.XMLHttpRequest.prototype.setRequestHeader = function (name, value) {
        if (this.__guitarLearningMidiResponse && /^authorization$/i.test(name)) this.__guitarLearningHasAuth = true;
        return nativeSetHeader.call(this, name, value);
      };
    }
    window.XMLHttpRequest.prototype.send = function (...args) {
      if (this.__guitarLearningMidiResponse) {
        this.addEventListener('load', () => {
          report(`MIDI API HTTP ${this.status}`);
          try {
            const json = JSON.parse(this.responseText);
            if (!found(json?.info?.url)) report('MIDI response had no URL', `${json?.result || 'unknown'}: ${json?.error?.name || json?.error?.message || 'no info.url'}`);
          } catch (error) { report('MIDI response unreadable', error?.message || error); }
        }, {once:true});
        this.addEventListener('error', () => report('MIDI API XHR network error'));
        this.addEventListener('timeout', () => report('MIDI API XHR timeout'));
        this.addEventListener('abort', () => report('MIDI API XHR aborted'));
        report('MIDI API requested', `XHR; authorization header: ${this.__guitarLearningHasAuth ? 'present' : 'not visible'}`);
      }
      return nativeSend.apply(this, args);
    };
  }

  if (inTutorialFrame) {
    report('Frame capture ready');
    timer = setInterval(() => { if (!completed) inspectFrame(window); }, 500);
    inspectFrame(window);
    return;
  }

  // Only accept capture messages from our own same-origin tutorial iframe.
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== tutorialFrame?.contentWindow ||
        event.data?.source !== 'guitar-learning-midi-capture' || event.data.id !== requestId) return;
    if (typeof event.data.event?.phase === 'string') {
      report(safeDetail(event.data.event.phase), event.data.event.detail, 'tutorial-frame');
    }
    if (event.data.url) found(event.data.url);
  });

  // Start on the NORMAL score page, as the original downloader extension does,
  // and load the tutorial in a same-origin iframe. Starting the whole tab on
  // /piano-tutorial caused the blank Quetta page and no captured MIDI.
  function startMidiPlayer() {
    if (completed || tutorialFrame || !document.body) return;
    status = document.createElement('div');
    status.setAttribute('role', 'status');
    status.style.cssText = 'position:fixed;bottom:12px;left:12px;z-index:2147483647;padding:10px 14px;background:#17212e;color:#fff;border:1px solid #ad90ee;border-radius:8px;font:14px sans-serif;max-width:calc(100vw - 48px)';
    document.body.appendChild(status);
    report('Score page opened');
    const tutorial = new URL(location.href);
    tutorial.hash = new URLSearchParams({'guitar-learning-capture':requestId}).toString();
    tutorial.search = '';
    tutorial.pathname = tutorial.pathname.replace(/\/piano-tutorial\/?$/, '').replace(/\/$/, '') + '/piano-tutorial';
    const frame = document.createElement('iframe');
    frame.src = tutorial.href;
    frame.setAttribute('aria-hidden', 'true');
    frame.tabIndex = -1;
    frame.style.cssText = 'position:fixed;left:-2000px;top:0;width:1000px;height:600px;opacity:0;pointer-events:none;border:0';
    frame.addEventListener('load', () => { frameLoaded = true; report('Tutorial frame loaded'); inspectFrame(window); }, {once:true});
    frame.addEventListener('error', () => report('Tutorial frame load error'), {once:true});
    tutorialFrame = frame;
    document.body.appendChild(frame);
    report('Tutorial frame opened');
    inspectFrame(window);
  }

  timer = setInterval(() => {
    if (completed) return;
    if (Date.now() - startedAt >= MAX_WAIT_MS) {
      finish({
        'musescore-error':'MuseScore did not provide MIDI within 90 seconds.',
        'musescore-debug':diagnosticSnapshot(),
      });
    } else inspectFrame(window);
  }, 500);
  inspectFrame(window);
  if (document.body) startMidiPlayer();
  else document.addEventListener('DOMContentLoaded', startMidiPlayer, {once:true});
})();
