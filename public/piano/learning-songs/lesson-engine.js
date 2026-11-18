const MODES = new Set(['wait', 'timed']);
const EPSILON_SECONDS = 1e-9;

function validateMode(mode) {
  if (!MODES.has(mode)) throw new RangeError('Practice mode must be "wait" or "timed".');
}

function validateTime(time) {
  if (!Number.isFinite(time)) throw new TypeError('Elapsed lesson time must be a finite number of seconds.');
}

function isMidiPitch(pitch) {
  return Number.isInteger(pitch) && pitch >= 0 && pitch <= 127;
}

function copyGroups(groups) {
  if (!Array.isArray(groups)) throw new TypeError('Lesson groups must be an array.');
  const ids = new Set();
  const attackTimes = new Set();
  let previousTime = -Infinity;
  return Object.freeze(groups.map((group, index) => {
    if (!group || !Number.isFinite(group.time) || group.time < 0) {
      throw new TypeError(`Group ${index} needs a nonnegative time in seconds.`);
    }
    if (group.time < previousTime) throw new RangeError('Lesson groups must be ordered by time.');
    previousTime = group.time;
    if (!Array.isArray(group.notes)) throw new TypeError(`Group ${index} needs a notes array.`);
    if (group.endTime != null && (!Number.isFinite(group.endTime) || group.endTime < group.time)) {
      throw new RangeError(`Group ${index} endTime must be at or after its time.`);
    }
    if (group.notes.length && attackTimes.has(group.time)) {
      throw new RangeError('Simultaneous attacks must belong to the same lesson group.');
    }
    if (group.notes.length) attackTimes.add(group.time);
    const notes = group.notes.map(note => {
      if (!note || !((typeof note.id === 'string' && note.id.length > 0)
          || (typeof note.id === 'number' && Number.isFinite(note.id)))) {
        throw new TypeError(`Every note in group ${index} needs a stable id.`);
      }
      if (ids.has(note.id)) throw new RangeError(`Duplicate attack id: ${note.id}`);
      if (!isMidiPitch(note.midi)) throw new RangeError(`Invalid MIDI pitch for attack ${note.id}.`);
      ids.add(note.id);
      return Object.freeze({...note});
    });
    return Object.freeze({...group, notes: Object.freeze(notes),
      requiredPitches: Object.freeze([...new Set(notes.map(note => note.midi))])});
  }));
}

/**
 * Grade pitch/onset attacks independently of audio, rendering and wall clocks.
 *
 * Input: ordered groups {time, endTime?, notes:[{id, midi, ...}]} in elapsed
 * musical seconds, with one group per simultaneous onset. The score adapter
 * resolves ties and tempo changes before constructing this engine. Durations
 * and note-off messages are deliberately not graded.
 *
 * grade() represents ONE fresh key strike. Input adapters must suppress held-key
 * auto-repeat. A simultaneous unison strike grades all its source attack IDs;
 * it never grades a second onset. Counts refer to source attack IDs.
 *
 * Root owns the elapsed clock and freezes it while paused. Negative elapsed
 * times are allowed for count-in; stale updates are ignored. start() resumes,
 * setMode() pauses without clearing, and only reset() clears prior grades.
 */
export class LessonEngine {
  #groups;
  #mode;
  #window;
  #statuses = new Map();
  #running = false;
  #elapsed = 0;
  #currentIndex = 0;
  #hits = 0;
  #misses = 0;
  #wrong = 0;

  constructor(groups, {mode = 'wait', timingWindowMs = 180} = {}) {
    validateMode(mode);
    if (!Number.isFinite(timingWindowMs) || timingWindowMs < 0) {
      throw new RangeError('The timing window must be a nonnegative number of milliseconds.');
    }
    this.#groups = copyGroups(groups);
    this.#mode = mode;
    this.#window = timingWindowMs / 1000;
    this.reset();
  }

  get groups() { return this.#groups; }
  get mode() { return this.#mode; }
  get running() { return this.#running; }
  get elapsed() { return this.#elapsed; }
  get currentIndex() { return this.#currentIndex; }
  get hits() { return this.#hits; }
  get misses() { return this.#misses; }
  get wrong() { return this.#wrong; }
  get total() { return this.#statuses.size; }
  get complete() { return this.#currentIndex === this.#groups.length; }
  get statuses() { return new Map(this.#statuses); }

  snapshot() {
    const currentGroup = this.#groups[this.#currentIndex] ?? null;
    return {
      mode: this.#mode, running: this.#running, elapsed: this.#elapsed,
      timingWindowMs: this.#window * 1000,
      currentIndex: this.#currentIndex, currentGroup,
      requiredPitches: currentGroup
        ? [...new Set(currentGroup.notes.filter(note => this.#statuses.get(note.id) === 'pending')
          .map(note => note.midi))] : [],
      statuses: this.statuses,
      hits: this.#hits, misses: this.#misses, wrong: this.#wrong,
      total: this.total, pending: this.total - this.#hits - this.#misses,
      complete: this.complete,
    };
  }

  start(elapsed = this.#elapsed) {
    validateTime(elapsed);
    // A fresh session may begin with a count-in. Resuming never rewinds grades.
    if (elapsed < this.#elapsed - EPSILON_SECONDS
        && (this.#elapsed !== 0 || this.#hits || this.#misses || this.#wrong)) {
      throw new RangeError('Elapsed time cannot rewind an active lesson; reset first.');
    }
    this.#elapsed = elapsed;
    this.#running = !this.complete;
    return this.update(elapsed);
  }

  pause() {
    this.#running = false;
    return this.snapshot();
  }

  reset() {
    this.#statuses = new Map(this.#groups.flatMap(group => group.notes.map(note => [note.id, 'pending'])));
    this.#running = false;
    this.#elapsed = 0;
    this.#hits = this.#misses = this.#wrong = 0;
    this.#currentIndex = 0;
    this.#advanceIndex();
    return this.snapshot();
  }

  setMode(mode) {
    validateMode(mode);
    if (mode !== this.#mode) {
      this.#mode = mode;
      this.#running = false;
    }
    return this.snapshot();
  }

  update(elapsed = this.#elapsed) {
    validateTime(elapsed);
    if (!this.#running || elapsed < this.#elapsed - EPSILON_SECONDS) return this.snapshot();
    this.#elapsed = Math.max(this.#elapsed, elapsed);
    const missIds = this.#expire();
    return {...this.snapshot(), missIds};
  }

  grade(midi, elapsed = this.#elapsed) {
    validateTime(elapsed);
    const result = (outcome, extra = {}) => ({...this.snapshot(), outcome, hitIds: [], missIds: [], ...extra});
    if (!isMidiPitch(midi)) return result('ignored', {reason: 'invalid-pitch'});
    if (!this.#running) return result('ignored', {reason: this.complete ? 'complete' : 'paused'});
    if (elapsed < this.#elapsed - EPSILON_SECONDS) return result('ignored', {reason: 'stale-time'});
    this.#elapsed = Math.max(this.#elapsed, elapsed);
    const missIds = this.#expire();
    if (this.complete) return result('ignored', {reason: 'complete', missIds});

    let selectedIndex = -1;
    if (this.#mode === 'wait') {
      if (this.#groups[this.#currentIndex].notes.some(note =>
        note.midi === midi && this.#statuses.get(note.id) === 'pending')) {
        selectedIndex = this.#currentIndex;
      }
    } else {
      let closest = Infinity;
      for (let index = this.#currentIndex; index < this.#groups.length; index++) {
        const group = this.#groups[index];
        if (group.time > elapsed + this.#window + EPSILON_SECONDS) break;
        const distance = Math.abs(group.time - elapsed);
        if (distance <= this.#window + EPSILON_SECONDS && distance < closest - EPSILON_SECONDS
            && group.notes.some(note => note.midi === midi && this.#statuses.get(note.id) === 'pending')) {
          selectedIndex = index;
          closest = distance;
        }
      }
    }

    if (selectedIndex < 0) {
      const duplicate = this.#mode === 'wait'
        ? this.#groups[this.#currentIndex].notes.some(note => note.midi === midi && this.#statuses.get(note.id) === 'hit')
        : this.#groups.some(group => Math.abs(group.time - elapsed) <= this.#window + EPSILON_SECONDS
          && group.notes.some(note => note.midi === midi && this.#statuses.get(note.id) === 'hit'));
      if (!duplicate) this.#wrong++;
      return result(duplicate ? 'duplicate' : 'wrong', {missIds});
    }

    const group = this.#groups[selectedIndex];
    const hitIds = group.notes.filter(note => note.midi === midi && this.#statuses.get(note.id) === 'pending')
      .map(note => note.id);
    for (const id of hitIds) this.#statuses.set(id, 'hit');
    this.#hits += hitIds.length;
    const before = this.#currentIndex;
    this.#advanceIndex();
    return result('hit', {hitIds, missIds, groupIndex: selectedIndex,
      advanced: this.#currentIndex !== before,
      timingErrorMs: this.#mode === 'timed' ? (elapsed - group.time) * 1000 : null});
  }

  #expire() {
    const missIds = [];
    if (this.#mode !== 'timed') return missIds;
    for (let index = this.#currentIndex; index < this.#groups.length; index++) {
      const group = this.#groups[index];
      if (this.#elapsed <= group.time + this.#window + EPSILON_SECONDS) break;
      for (const note of group.notes) {
        if (this.#statuses.get(note.id) !== 'pending') continue;
        this.#statuses.set(note.id, 'miss');
        missIds.push(note.id);
      }
    }
    this.#misses += missIds.length;
    this.#advanceIndex();
    return missIds;
  }

  #advanceIndex() {
    while (this.#currentIndex < this.#groups.length
      && this.#groups[this.#currentIndex].notes.every(note => this.#statuses.get(note.id) !== 'pending')) {
      this.#currentIndex++;
    }
    if (this.complete) this.#running = false;
  }
}
