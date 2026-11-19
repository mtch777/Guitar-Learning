// ==UserScript==
// @name         Guitar Learning: automatic MuseScore MIDI import
// @namespace    https://mtch777.github.io/Guitar-Learning/
// @version      1.0.0
// @description  Return a MIDI link to the Learning Songs lesson automatically when its MuseScore piano tutorial loads.
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

  if (location.hostname === 'mtch777.github.io') {
    const markReady = () => {
      if (document.documentElement) document.documentElement.dataset.musescoreHelper = 'ready';
      window.dispatchEvent(new Event('musescore-helper-ready'));
    };
    markReady();
    document.addEventListener('DOMContentLoaded', markReady, {once:true});
    return;
  }
  if (!['musescore.com', 'www.musescore.com'].includes(location.hostname)) return;

  const params = new URLSearchParams(location.hash.slice(1));
  let requestId = params.get('guitar-learning-import');
  if (REQUEST_ID.test(requestId || '')) {
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
  function finish(payload) {
    if (completed) return;
    completed = true;
    clearInterval(timer);
    observer?.disconnect();
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
  function found(candidate) {
    if (!isMidiUrl(candidate)) return false;
    const title = (document.querySelector('h1')?.textContent || document.title || '')
      .replace(/\s*[-|]\s*MuseScore.*$/i, '').replace(/\s+/g, ' ').trim().slice(0, 100);
    finish({'musescore-midi':candidate, 'musescore-title':title});
    return true;
  }
  function inspectFrame(win) {
    try {
      const resources = win.performance.getEntriesByType('resource');
      for (let i = resources.length - 1; i >= 0; i--) if (found(resources[i].name)) return true;
      for (const frame of win.document.querySelectorAll('iframe')) {
        if (frame.contentWindow && inspectFrame(frame.contentWindow)) return true;
      }
    } catch (_) { /* Cross-origin frame: it cannot expose this session's resources. */ }
    return false;
  }
  // The player itself loads score.mid. Observe the same resource the working
  // bookmarklet found, without requiring the user to invoke that bookmarklet.
  try {
    observer = new PerformanceObserver(() => inspectFrame(window));
    observer.observe({type:'resource', buffered:true});
  } catch (_) { /* Polling below is supported even without PerformanceObserver. */ }

  // Capture successful jmuse MIDI responses as well. This covers cases where
  // the player receives the signed URL before score.mid appears in Performance.
  if (typeof window.fetch === 'function') {
    const nativeFetch = window.fetch;
    window.fetch = function (...args) {
      const result = nativeFetch.apply(this, args);
      try {
        const target = String(args[0]?.url || args[0]);
        if (/\/api\/jmuse\?/.test(target) && /(?:\?|&)type=midi(?:&|$)/.test(target)) {
          Promise.resolve(result).then(response => response.clone().json())
            .then(json => found(json?.info?.url)).catch(() => {});
        }
      } catch (_) {}
      return result;
    };
  }
  if (typeof window.XMLHttpRequest === 'function') {
    const nativeOpen = window.XMLHttpRequest.prototype.open;
    const nativeSend = window.XMLHttpRequest.prototype.send;
    window.XMLHttpRequest.prototype.open = function (method, url, ...other) {
      this.__guitarLearningMidiResponse = /\/api\/jmuse\?/.test(String(url)) &&
        /(?:\?|&)type=midi(?:&|$)/.test(String(url));
      return nativeOpen.call(this, method, url, ...other);
    };
    window.XMLHttpRequest.prototype.send = function (...args) {
      if (this.__guitarLearningMidiResponse) {
        this.addEventListener('load', () => {
          try { if (this.status === 200) found(JSON.parse(this.responseText)?.info?.url); } catch (_) {}
        }, {once:true});
      }
      return nativeSend.apply(this, args);
    };
  }

  const startedAt = Date.now();
  timer = setInterval(() => {
    if (completed) return;
    if (Date.now() - startedAt >= MAX_WAIT_MS) {
      finish({'musescore-error':'The piano tutorial did not load a MIDI file within 90 seconds.'});
    } else inspectFrame(window);
  }, 500);
  inspectFrame(window);
})();
