(function () {
  const STORAGE_KEY = "practiceAppMidiEnabledV1";
  const FAILURE_KEY = "practiceAppMidiFailuresV1";
  const MAX_FAILURES = 20;
  let enabledInMemory = false;
  let preferenceUnsaved = false;
  let failures = null;

  function isEnabled() {
    if (!preferenceUnsaved) {
      try {
        enabledInMemory = localStorage.getItem(STORAGE_KEY) === "true";
      } catch (_) {}
    }
    return enabledInMemory;
  }

  function setEnabled(enabled) {
    enabledInMemory = !!enabled;
    try {
      localStorage.setItem(STORAGE_KEY, enabledInMemory ? "true" : "false");
      preferenceUnsaved = false;
    } catch (_) {
      preferenceUnsaved = true;
    }
    window.dispatchEvent(
      new CustomEvent("practice-midi-state", {
        detail: { enabled: enabledInMemory }
      })
    );
  }

  function stringProperty(object, key, fallback = "") {
    try {
      return typeof object?.[key] === "string" ? object[key] : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function withoutUrlQueries(value) {
    return value.replace(/https?:\/\/[^\s<>"']+/gi, url => url.split(/[?#]/)[0]);
  }

  function copyRecord(record) {
    return {
      timestamp: record.timestamp,
      stage: record.stage,
      name: withoutUrlQueries(record.name),
      message: withoutUrlQueries(record.message),
      pathname: record.pathname.split(/[?#]/)[0],
      build: record.build
    };
  }

  function getFailureLog() {
    if (failures === null) {
      failures = [];
      try {
        const saved = JSON.parse(localStorage.getItem(FAILURE_KEY) || "[]");
        if (Array.isArray(saved)) {
          failures = saved.filter(record => record &&
            ["access", "setup"].includes(record.stage) &&
            ["timestamp", "name", "message", "pathname", "build"].every(key => typeof record[key] === "string")
          ).slice(-MAX_FAILURES).map(copyRecord);
        }
      } catch (_) {}
    }
    return failures.map(copyRecord);
  }

  function reportFailure(error, stage = "access") {
    stage = stage === "setup" ? "setup" : "access";
    const name = withoutUrlQueries(stringProperty(error, "name", "Error") || "Error");
    let message = stringProperty(error, "message", null);
    if (message === null) {
      try { message = error == null ? "Unknown error" : String(error); }
      catch (_) { message = "Unknown error"; }
    }
    message = withoutUrlQueries(message);
    let pathname = "";
    let build = "";
    try { pathname = stringProperty(window.location, "pathname").split(/[?#]/)[0]; } catch (_) {}
    try { build = document.querySelector('meta[name="build-version"]')?.getAttribute("content") || ""; } catch (_) {}
    const record = {timestamp: new Date().toISOString(), stage, name, message, pathname, build};
    failures = [...getFailureLog(), record].slice(-MAX_FAILURES);
    try { localStorage.setItem(FAILURE_KEY, JSON.stringify(failures)); } catch (_) {}
    try { console.error("MIDI failure:", copyRecord(record)); } catch (_) {}
    return `MIDI ${stage} failed: ${name}${message ? ` — ${message}` : ""}`;
  }

  window.PracticeMIDI = {
    isEnabled,
    setEnabled,
    reportFailure,
    getFailureLog
  };
})();
