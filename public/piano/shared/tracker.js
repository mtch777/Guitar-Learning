(function () {
  const STORAGE_KEY = "practiceAppLessonOpensV1";
  const WINDOW_MS = 7 * 24 * 60 * 60 * 1000;

  function load() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      return value && typeof value === "object" ? value : {};
    } catch (error) {
      return {};
    }
  }

  function save(data) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
      // Keep the app usable if browser storage is unavailable.
    }
  }

  function prune(data) {
    const cutoff = Date.now() - WINDOW_MS;

    Object.keys(data).forEach((lessonId) => {
      const events = Array.isArray(data[lessonId]) ? data[lessonId] : [];
      data[lessonId] = events.filter(
        (timestamp) => Number.isFinite(timestamp) && timestamp >= cutoff
      );

      if (data[lessonId].length === 0) {
        delete data[lessonId];
      }
    });

    return data;
  }

  function recordOpen(lessonId) {
    const data = prune(load());

    if (!Array.isArray(data[lessonId])) {
      data[lessonId] = [];
    }

    data[lessonId].push(Date.now());
    save(data);
  }

  function count(lessonId) {
    const data = prune(load());
    save(data);
    return Array.isArray(data[lessonId]) ? data[lessonId].length : 0;
  }

  function total() {
    const data = prune(load());
    save(data);

    return Object.values(data).reduce(
      (sum, events) => sum + (Array.isArray(events) ? events.length : 0),
      0
    );
  }

  function renderCounts(root) {
    const scope = root || document;

    scope.querySelectorAll("[data-lesson-count]").forEach((element) => {
      const lessonId = element.getAttribute("data-lesson-count");
      const value = count(lessonId);
      element.textContent = value + (value === 1 ? " open" : " opens") + " · last 7 days";
    });

    scope.querySelectorAll("[data-total-count]").forEach((element) => {
      const value = total();
      element.textContent = value + (value === 1 ? " lesson open" : " lesson opens");
    });
  }

  window.PracticeTracker = {
    recordOpen,
    count,
    total,
    renderCounts
  };
})();
