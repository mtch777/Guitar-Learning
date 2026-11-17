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

  function syncButton(button) {
    if (!button) return;

    const enabled = isEnabled();
    button.textContent = enabled ? "MIDI enabled" : "Enable MIDI";
    button.disabled = false;
  }

  function watchButton(button) {
    syncButton(button);

    window.addEventListener("practice-midi-state", function () {
      syncButton(button);
    });

    window.addEventListener("storage", function (event) {
      if (event.key === STORAGE_KEY) {
        syncButton(button);
      }
    });
  }

  window.PracticeMIDI = {
    isEnabled,
    setEnabled,
    syncButton,
    watchButton
  };
})();