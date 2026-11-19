// ==UserScript==
// @name         Guitar Learning: automatic MuseScore MIDI import
// @namespace    https://mtch777.github.io/Guitar-Learning/
// @version      1.1.0
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
  const HELPER_VERSION = '1.1.0';

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
  // The parent inspects same-origin tutorial-frame resources. Do not run the
  // handoff inside that frame or redirect only the invisible frame to GitHub.
  if (window.top !== window) return;

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
  let tutorialFrame;
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

  // Loading the piano tutorial in a hidden, same-origin frame triggers its MIDI
  // request even when the parent score page is idle. The MuseScore downloader
  // extension uses this same player-loading mechanism. No user click or audio
  // playback is needed. Keep the frame rendered (not display:none) so mobile
  // browsers do not skip player initialization.
  function startMidiPlayer() {
    if (completed || tutorialFrame || !document.body) return;
    const status = document.createElement('div');
    status.textContent = 'Importing MuseScore MIDI… Returning to Learning Songs automatically.';
    status.setAttribute('role', 'status');
    status.style.cssText = 'position:fixed;bottom:12px;left:12px;z-index:2147483647;padding:10px 14px;background:#17212e;color:#fff;border:1px solid #ad90ee;border-radius:8px;font:14px sans-serif;max-width:calc(100vw - 48px)';
    document.body.appendChild(status);
    const tutorial = new URL(location.href);
    tutorial.hash = '';
    tutorial.search = '';
    tutorial.pathname = tutorial.pathname.replace(/\/piano-tutorial\/?$/, '').replace(/\/$/, '') + '/piano-tutorial';
    const frame = document.createElement('iframe');
    frame.src = tutorial.href;
    frame.setAttribute('aria-hidden', 'true');
    frame.tabIndex = -1;
    frame.style.cssText = 'position:fixed;left:-2000px;top:0;width:1000px;height:600px;opacity:0;pointer-events:none;border:0';
    frame.addEventListener('load', () => inspectFrame(window), {once:true});
    tutorialFrame = frame;
    document.body.appendChild(frame);
    inspectFrame(window);
  }

  const startedAt = Date.now();
  timer = setInterval(() => {
    if (completed) return;
    if (Date.now() - startedAt >= MAX_WAIT_MS) {
      finish({'musescore-error':'The piano tutorial did not load a MIDI file within 90 seconds.'});
    } else inspectFrame(window);
  }, 500);
  inspectFrame(window);
  if (document.body) startMidiPlayer();
  else document.addEventListener('DOMContentLoaded', startMidiPlayer, {once:true});
})();
