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

    return Array.isArray(data[lessonId])
      ? data[lessonId].length
      : 0;
  }

  function total() {
    const data = prune(load());
    save(data);

    return Object.values(data).reduce(
      (sum, events) =>
        sum + (Array.isArray(events) ? events.length : 0),
      0
    );
  }

  function startOfLocalDay(date) {
    return new Date(
      date.getFullYear(),
      date.getMonth(),
      date.getDate()
    ).getTime();
  }

  function getDailyActivity(days) {
    const dayCount = Math.max(1, Number(days) || 7);
    const data = prune(load());
    save(data);

    const timestamps = Object.values(data)
      .flatMap((events) => Array.isArray(events) ? events : [])
      .filter(Number.isFinite);

    const today = new Date();
    const result = [];

    for (let offset = dayCount - 1; offset >= 0; offset--) {
      const date = new Date(
        today.getFullYear(),
        today.getMonth(),
        today.getDate() - offset
      );

      const dayStart = startOfLocalDay(date);

      const nextDay = new Date(
        date.getFullYear(),
        date.getMonth(),
        date.getDate() + 1
      );

      const dayEnd = startOfLocalDay(nextDay);

      const practiced = timestamps.some(
        (timestamp) =>
          timestamp >= dayStart &&
          timestamp < dayEnd
      );

      result.push({
        date,
        practiced
      });
    }

    return result;
  }

  function renderActivityTimeline(element, days) {
    if (!element) return;

    const activity = getDailyActivity(days || 7);

    element.innerHTML = "";

    activity.forEach((day, index) => {
      const item = document.createElement("div");
      item.className = "activity-day";

      const square = document.createElement("div");
      square.className =
        "activity-square" +
        (day.practiced ? " active" : "");

      const isToday =
        index === activity.length - 1;

      const fullDate =
        day.date.toLocaleDateString(
          undefined,
          {
            weekday: "long",
            month: "short",
            day: "numeric"
          }
        );

      square.setAttribute(
        "role",
        "img"
      );

      square.setAttribute(
        "aria-label",
        fullDate +
          ": " +
          (day.practiced
            ? "practiced"
            : "no practice")
      );

      square.title =
        fullDate +
        " · " +
        (day.practiced
          ? "Practiced"
          : "No practice");

      const label =
        document.createElement("span");

      label.className =
        "activity-label";

      label.textContent =
        isToday
          ? "Today"
          : day.date.toLocaleDateString(
              undefined,
              { weekday: "short" }
            );

      item.appendChild(square);
      item.appendChild(label);
      element.appendChild(item);
    });
  }

  function renderCounts(root) {
    const scope = root || document;

    scope.querySelectorAll("[data-lesson-count]").forEach((element) => {
      const lessonId =
        element.getAttribute("data-lesson-count");

      const value =
        count(lessonId);

      element.textContent =
        value +
        (value === 1 ? " open" : " opens") +
        " · last 7 days";
    });

    scope.querySelectorAll("[data-total-count]").forEach((element) => {
      const value = total();

      element.textContent =
        value +
        (value === 1 ? " lesson open" : " lesson opens");
    });
  }

  window.PracticeTracker = {
    recordOpen,
    count,
    total,
    getDailyActivity,
    renderActivityTimeline,
    renderCounts
  };
})();
