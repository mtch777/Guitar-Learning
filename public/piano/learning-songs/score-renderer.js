const COLORS = Object.freeze({pending: '#111111', current: '#7653b3', hit: '#16875d', miss: '#d63349'});
const COLOR_OPTIONS = Object.freeze({
  // OSMD's notehead option colors ALL members of the VexFlow chord. Individual
  // heads are selected below by vfnote[1], so one miss cannot repaint a hit.
  applyToNoteheads: false, applyToStem: false, applyToBeams: false,
  applyToFlag: false, applyToLedgerLines: false, applyToModifiers: false,
  applyToLyrics: false, applyToSlurs: false, applyToTies: true, applyToGlissandi: false,
  applyToMultiRestMeasure: false,
});
const beatValue = fraction => Number(fraction?.RealValue ?? 0) * 4;
const timeKey = value => Number(value).toFixed(8);
const noteKey = note => JSON.stringify([
  note.partId, note.partIndex, note.staff, String(note.voice), note.measureIndex,
  timeKey(note.measureOnset), note.midi, Boolean(note.isGrace),
]);

/** Original notation, with attack results painted onto its actual SVG noteheads. */
export class ScoreRenderer {
  constructor(container, viewport = container) {
    if (!container?.ownerDocument || !viewport) throw new TypeError('A score container and viewport are required.');
    this.container = container;
    this.viewport = viewport;
    this.view = container.ownerDocument.defaultView;
    this.osmd = null;
    this.model = null;
    this.noteMap = new Map();
    this.statuses = new Map();
    this.currentIds = new Set();
    this.appliedColors = new Map();
    this.cursorPositions = [];
    this.cursorStep = 0;
    this.beat = 0;
    this.loadVersion = 0;
    this.resizeTimer = null;
    this.onResize = () => {
      this.view.clearTimeout(this.resizeTimer);
      this.resizeTimer = this.view.setTimeout(() => {
        if (this.osmd) this.resize();
      }, 120);
    };
    this.view.addEventListener('resize', this.onResize);
  }

  async load(model) {
    if (!model?.xml || !Array.isArray(model.notes) || !Array.isArray(model.attacks)) {
      throw new TypeError('The score renderer needs a parsed MusicXML model.');
    }
    const Runtime = this.view.opensheetmusicdisplay?.OpenSheetMusicDisplay;
    if (!Runtime) throw new Error('The sheet music renderer has not loaded. Reload the page and try again.');
    const version = ++this.loadVersion;
    const host = this.container.ownerDocument.createElement('div');
    host.className = 'lesson-score-render';
    // Lay out a replacement at the real available width without disturbing the
    // currently usable score. A failed load leaves that score and its grades intact.
    Object.assign(host.style, {visibility: 'hidden', position: 'absolute', width: `${this.container.clientWidth || 800}px`});
    this.container.append(host);
    const display = new Runtime(host, {
      backend: 'svg', autoResize: false, followCursor: false,
      drawTitle: true, newSystemFromXML: false, newPageFromXML: false,
      cursorsOptions: [{type: 0, color: COLORS.current, alpha: 0.18, follow: false}],
    });
    display.EngravingRules.CursorIgnoreRepetitions = true;
    let mapping;
    let positions;
    try {
      await display.load(model.xml);
      if (version !== this.loadVersion) throw new Error('This score load was replaced by a newer selection.');
      display.render();
      mapping = this.indexNotes(display, model);
      positions = this.indexCursor(display, model);
    } catch (error) {
      display.dispose?.();
      host.remove();
      throw error;
    }
    this.osmd?.dispose?.();
    this.container.replaceChildren(host);
    host.style.visibility = '';
    host.style.position = '';
    host.style.width = '100%';
    this.osmd = display;
    this.model = model;
    this.noteMap = mapping.notes;
    this.cursorPositions = positions;
    this.cursorStep = 0;
    this.statuses = new Map();
    this.currentIds = new Set();
    this.appliedColors = new Map();
    this.beat = 0;
    this.color(this.statuses);
    this.cursorAtBeat(0);
    return {mappedNotes: this.noteMap.size, expectedNotes: model.notes.length, warnings: mapping.warnings};
  }

  indexNotes(display, model) {
    const buckets = new Map();
    const instruments = display.Sheet.Instruments;
    const seen = new Set();
    for (const [measureIndex, measure] of display.Sheet.SourceMeasures.entries()) {
      for (const vertical of measure.VerticalSourceStaffEntryContainers) {
        for (const entry of vertical.StaffEntries.filter(Boolean)) {
          for (const voice of entry.VoiceEntries) {
            for (const source of voice.Notes) {
              if (seen.has(source)) continue;
              seen.add(source);
              const staff = source.ParentStaffEntry?.ParentStaff || entry.ParentStaff;
              const instrument = staff.ParentInstrument;
              const descriptor = {
                partId: instrument.IdString, partIndex: instruments.indexOf(instrument),
                staff: staff.Id, voice: voice.ParentVoice.VoiceId, measureIndex,
                measureOnset: beatValue(voice.Timestamp),
                midi: source.isRest() ? null : source.Pitch.getHalfTone() + 12,
                isGrace: source.IsGraceNote,
              };
              const key = noteKey(descriptor);
              if (!buckets.has(key)) buckets.set(key, []);
              buckets.get(key).push({source, graphical: display.EngravingRules.GNote(source)});
            }
          }
        }
      }
    }
    const notes = new Map();
    const missing = [];
    for (const note of model.notes) {
      const match = buckets.get(noteKey(note))?.shift();
      if (match?.graphical) {
        const heads = match.graphical.getNoteheadSVGs();
        const head = heads[match.graphical.vfnote?.[1] ?? 0];
        notes.set(note.id, {...match, note, head});
        if (!head && !note.isRest && !note.isHidden && note.attackId) missing.push(note);
      } else missing.push(note);
    }
    const required = new Set(model.attacks.flatMap(attack => attack.noteIds));
    const missingRequired = missing.filter(note => !note.isHidden && required.has(note.id));
    if (missingRequired.length) {
      const first = missingRequired[0];
      throw new Error(`Cannot match ${missingRequired.length} practice note(s) to the displayed score (first: measure ${first.measureNumber}, staff ${first.staff}). Import another MusicXML export of this score.`);
    }
    const warnings = missing.length
      ? [`${missing.length} non-practice or hidden notation item(s) have no individual color target.`] : [];
    return {notes, warnings};
  }

  indexCursor(display, model) {
    const cursor = display.cursor;
    cursor.hide();
    cursor.reset();
    const positions = [];
    // Written-order iteration is bounded even if a damaged score trips a library
    // repetition bug. Grading and playback must never silently follow other bars.
    const limit = model.notes.length * 3 + model.measures.length * 4 + 100;
    let step = 0;
    while (!cursor.Iterator.EndReached && step <= limit) {
      const iterator = cursor.Iterator;
      const measure = model.measures[iterator.CurrentMeasureIndex];
      if (measure) {
        const beat = measure.onset + beatValue(iterator.CurrentRelativeInMeasureTimestamp);
        if (positions.length && beat < positions.at(-1).beat - 1e-7) {
          throw new Error('The score cursor did not follow written measure order.');
        }
        positions.push({beat, step});
      }
      cursor.next();
      step++;
    }
    if (step > limit) throw new Error('The score cursor could not finish this notation.');
    cursor.reset();
    return positions;
  }

  color(statuses = new Map(), currentAttackIds = []) {
    this.statuses = new Map(statuses);
    this.currentIds = new Set(currentAttackIds);
    for (const [id, {note, graphical, head}] of this.noteMap) {
      const status = this.statuses.get(note.attackId) ?? this.statuses.get(id) ?? 'pending';
      const color = status === 'hit' ? COLORS.hit : status === 'miss' ? COLORS.miss
        : this.currentIds.has(note.attackId) || this.currentIds.has(id) ? COLORS.current : COLORS.pending;
      if (this.appliedColors.get(id) === color) continue;
      graphical.setColor(color, COLOR_OPTIONS);
      if (head) {
        head.setAttribute('fill', color);
        head.setAttribute('data-lesson-note-id', id);
        for (const shape of head.querySelectorAll('path, text, ellipse, polygon')) {
          shape.setAttribute(shape.getAttribute('fill') === 'none' ? 'stroke' : 'fill', color);
        }
      }
      this.appliedColors.set(id, color);
    }
  }

  cursorAtBeat(beat) {
    if (!Number.isFinite(beat)) throw new TypeError('Cursor position must be a finite quarter-note beat.');
    this.beat = Math.max(0, beat);
    if (!this.osmd || !this.cursorPositions.length) return;
    let low = 0;
    let high = this.cursorPositions.length;
    while (low < high) {
      const middle = (low + high) >> 1;
      if (this.cursorPositions[middle].beat <= this.beat + 1e-8) low = middle + 1;
      else high = middle;
    }
    const target = this.cursorPositions[Math.max(0, low - 1)].step;
    const cursor = this.osmd.cursor;
    if (target < this.cursorStep) {
      cursor.reset();
      this.cursorStep = 0;
    }
    if (target !== this.cursorStep) {
      cursor.hide();
      while (this.cursorStep < target && !cursor.Iterator.EndReached) {
        cursor.next();
        this.cursorStep++;
      }
    }
    cursor.show();
    this.scrollCursorIntoViewport();
  }

  scrollCursorIntoViewport() {
    const cursor = this.osmd?.cursor.cursorElement;
    if (!cursor || !this.viewport.clientHeight) return;
    const rect = cursor.getBoundingClientRect();
    const view = this.viewport.getBoundingClientRect();
    const margin = 24;
    if (rect.top < view.top + margin || rect.bottom > view.bottom - margin) {
      const target = this.viewport.scrollTop + rect.top - view.top - margin;
      this.viewport.scrollTop = Math.max(0, Math.min(target, this.viewport.scrollHeight - this.viewport.clientHeight));
    }
    if (rect.left < view.left + margin || rect.right > view.right - margin) {
      const target = this.viewport.scrollLeft + rect.left - view.left - margin;
      this.viewport.scrollLeft = Math.max(0, Math.min(target, this.viewport.scrollWidth - this.viewport.clientWidth));
    }
  }

  resize() {
    if (!this.osmd || !this.model) return;
    const beat = this.beat;
    this.osmd.render();
    const mapping = this.indexNotes(this.osmd, this.model);
    this.noteMap = mapping.notes;
    this.cursorPositions = this.indexCursor(this.osmd, this.model);
    this.cursorStep = 0;
    this.appliedColors.clear();
    this.color(this.statuses, this.currentIds);
    this.cursorAtBeat(beat);
  }

  destroy() {
    this.loadVersion++;
    this.view.removeEventListener('resize', this.onResize);
    this.view.clearTimeout(this.resizeTimer);
    this.osmd?.dispose?.();
    this.osmd = null;
    this.model = null;
    this.noteMap.clear();
    this.container.replaceChildren();
  }
}
