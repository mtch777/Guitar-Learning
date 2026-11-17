(function () {
  const STORAGE_KEY = "practiceAppMidiEnabledV1";

  function isEnabled() {
    return localStorage.getItem(STORAGE_KEY) === "true";
  }

  function setEnabled(enabled) {
    localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
    window.dispatchEvent(
      new CustomEvent("practice-midi-state", {
        detail: { enabled: !!enabled }
      })
    );
  }

  window.PracticeMIDI = {
    isEnabled,
    setEnabled
  };
})();