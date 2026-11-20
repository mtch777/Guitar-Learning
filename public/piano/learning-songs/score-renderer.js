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
const WINDOW_PADDING = 4;
const noteKey = note => JSON.stringify([
  note.partId, note.partIndex, note.staff, String(note.voice), note.measureIndex,
  timeKey(note.measureOnset), note.midi, Boolean(note.isGrace),
]);

// OSMD 2.3.1 can drop noteheads in ANY measure that begins with a
// sound-only tempo direction, not just the first bar. The original model.xml
// retains every tempo change for playback; only the engraving copy omits them.
const engravingXML = xml => xml.replace(
  /<direction\b[^>]*>\s*(?:<offset>[^<]*<\/offset>\s*)?<sound\b[^>]*\btempo="[^"]+"[^>]*\/>\s*<\/direction>/g,
  '',
);

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
    this.systems = [];
    this.systemForMeasure = new Map();
    this.visibleSystem = -1;
    this.cursorStep = 0;
    this.beat = 0;
    this.loadVersion = 0;
    this.resizeTimer = null;
    this.renderedWidth = 0;
    this.renderedHeight = 0;
    this.onResize = () => {
      if (!this.osmd || (Math.abs(this.availableWidth() - this.renderedWidth) < 1
        && Math.abs(this.availableHeight() - this.renderedHeight) < 1)) return;
      this.view.clearTimeout(this.resizeTimer);
      this.resizeTimer = this.view.setTimeout(() => {
        if (this.osmd) this.resize();
      }, 120);
    };
    if (this.view.ResizeObserver) {
      this.resizeObserver = new this.view.ResizeObserver(this.onResize);
      this.resizeObserver.observe(this.container);
      if (this.viewport !== this.container) this.resizeObserver.observe(this.viewport);
    } else this.view.addEventListener('resize', this.onResize);
  }

  availableWidth() {
    const style = this.view.getComputedStyle(this.container);
    const padding = (parseFloat(style.paddingLeft) || 0) + (parseFloat(style.paddingRight) || 0);
    return Math.max(1, Math.floor((this.container.clientWidth || this.viewport.clientWidth || 800) - padding));
  }

  /** Clear the score and note mapping while the next song loads. */
  clear() {
    this.loadVersion++;
    this.view.clearTimeout(this.resizeTimer);
    this.osmd?.dispose?.();
    this.osmd = null;
    this.model = null;
    this.host = null;
    this.frame = null;
    this.container.replaceChildren();
    this.noteMap = new Map();
    this.statuses = new Map();
    this.currentIds = new Set();
    this.appliedColors = new Map();
    this.cursorPositions = [];
    this.systems = [];
    this.systemForMeasure = new Map();
    this.visibleSystem = -1;
    this.renderedWidth = 0;
    this.renderedHeight = 0;
  }

  availableHeight() {
    return Math.max(1, Math.floor(this.viewport.clientHeight || 300));
  }

  indexSystems(display, host) {
    const sources = new Map(display.Sheet.SourceMeasures.map((measure, index) => [measure, index]));
    const svgs = [...host.querySelectorAll('svg')];
    const rows = [];
    let pageTop = 0;
    for (const [pageIndex, page] of display.GraphicSheet.MusicPages.entries()) {
      const svg = svgs[pageIndex];
      const viewWidth = Number(svg?.getAttribute('viewBox')?.split(/\s+/)[2]);
      const pixelsPerUnit = viewWidth > 0 ? Number(svg.getAttribute('width')) / viewWidth : display.Zoom;
      const staffGroups = [...(svg?.querySelectorAll('.osmd-staffline') || [])];
      let staffIndex = 0;
      for (const system of page.MusicSystems) {
        const box = system.PositionAndShape;
        const origin = box.AbsolutePosition.y - page.PositionAndShape.AbsolutePosition.y;
        let top = pageTop + (origin + box.BorderTop) * 10 * display.Zoom;
        let bottom = pageTop + (origin + box.BorderBottom) * 10 * display.Zoom;
        // Native system bounds include labels and expressions. Actual staff SVG
        // bounds also protect ledger notes, stems, slurs and ties in browsers.
        for (const staff of system.StaffLines) {
          const group = staffGroups[staffIndex++];
          if (typeof group?.getBBox !== 'function') continue;
          try {
            const bounds = group.getBBox();
            if (Number.isFinite(bounds.y) && bounds.height > 0) {
              top = Math.min(top, pageTop + bounds.y * pixelsPerUnit);
              bottom = Math.max(bottom, pageTop + (bounds.y + bounds.height) * pixelsPerUnit);
            }
          } catch (_) { /* Native bounds remain available before browser paint. */ }
        }
        const measures = [...new Set(system.GraphicalMeasures.flat().filter(Boolean)
          .map(measure => sources.get(measure.parentSourceMeasure)).filter(Number.isInteger))];
        rows.push({top, bottom, measures});
      }
      pageTop += Number(svg?.getAttribute('height')) || 0;
    }
    return rows;
  }

  renderToViewport(display, host) {
    const width = this.availableWidth();
    const height = this.availableHeight();
    host.style.width = `${width}px`;
    host.style.top = '0px';
    display.Zoom = 1;
    // The web lesson needs a small screen margin, not a printed page's gutters.
    display.EngravingRules.PageLeftMargin = 1.2;
    display.EngravingRules.PageRightMargin = 1.2;
    display.EngravingRules.PageTopMargin = .6;
    display.EngravingRules.PageBottomMargin = .6;
    display.EngravingRules.MinimumDistanceBetweenSystems = 3;
    let systems;
    for (let pass = 0; pass < 8; pass++) {
      display.render();
      systems = this.indexSystems(display, host);
      let requiredWidth = width;
      for (const page of display.GraphicSheet.MusicPages) {
        for (const system of page.MusicSystems) {
          const first = system.GraphicalMeasures[0]?.find(Boolean);
          if (!first) continue;
          const start = first.PositionAndShape.AbsolutePosition.x - page.PositionAndShape.AbsolutePosition.x;
          const measures = system.GraphicalMeasures.reduce((sum, staves) => sum + Math.max(0, ...staves.filter(Boolean).map(measure =>
            measure.beginInstructionsWidth + measure.minimumStaffEntriesWidth + measure.endInstructionsWidth
          ).filter(Number.isFinite)), 0);
          requiredWidth = Math.max(requiredWidth, (start + measures + display.EngravingRules.PageRightMargin) * 10 * display.Zoom);
        }
      }
      // Fit musical measures, not long directions/lyrics in the entire SVG.
      // Only braced multi-staff scores need a negative-origin gutter.
      let braceOverhang = 0;
      for (const svg of host.querySelectorAll('svg')) {
        const braces = [...svg.querySelectorAll('.vf-brace path')];
        if (!braces.length) continue;
        const bounds = braces.map(path => {
          try { return path.getBBox?.(); } catch (_) { return null; }
        }).filter(Boolean);
        if (bounds.length) braceOverhang = Math.max(braceOverhang, ...bounds.map(box => Math.max(0, -box.x)));
        else if (typeof svg.getBBox === 'function') {
          // A jsdom integration fixture exposes the actual brace extents
          // through its SVG bounding box when path.getBBox is unavailable.
          try { braceOverhang = Math.max(braceOverhang, -svg.getBBox().x); } catch (_) { /* no native bounds */ }
        }
      }
      const requiredHeight = Math.max(1, ...systems.map((row, index) =>
        (systems[index + 1] || row).bottom - row.top + WINDOW_PADDING * 2));
      if (braceOverhang <= .01 && requiredWidth <= width + .5 && requiredHeight <= height + .5) break;
      if (pass === 7) throw new Error('The score could not fit the available two-row window.');
      if (braceOverhang > .01) {
        display.EngravingRules.PageLeftMargin += braceOverhang / 10 + .3;
        continue;
      }
      // Re-engrave at a fitting scale instead of cropping/scaling an
      // old SVG. Native cursor positions and notehead mappings stay coherent.
      display.Zoom *= Math.min(width / requiredWidth,
        Math.max(1, height - WINDOW_PADDING * 2) / Math.max(1, requiredHeight - WINDOW_PADDING * 2)) * .99;
    }
    host.style.width = '100%';
    return {width, height, systems};
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
    Object.assign(host.style, {visibility: 'hidden', position: 'absolute', width: `${this.availableWidth()}px`});
    this.container.append(host);
    const display = new Runtime(host, {
      backend: 'svg', autoResize: false, followCursor: false,
      drawTitle: false, drawSubtitle: false, drawComposer: false, drawLyricist: false,
      drawPartNames: false, drawPartAbbreviations: false,
      newSystemFromXML: false, newPageFromXML: false,
      cursorsOptions: [{type: 0, color: COLORS.current, alpha: 0.18, follow: false}],
    });
    display.EngravingRules.CursorIgnoreRepetitions = true;
    let mapping;
    let positions;
    let layout;
    try {
      await display.load(engravingXML(model.xml));
      if (version !== this.loadVersion) throw new Error('This score load was replaced by a newer selection.');
      layout = this.renderToViewport(display, host);
      mapping = this.indexNotes(display, model);
      positions = this.indexCursor(display, model);
    } catch (error) {
      display.dispose?.();
      host.remove();
      throw error;
    }
    this.osmd?.dispose?.();
    const frame = this.container.ownerDocument.createElement('div');
    frame.className = 'lesson-score-window';
    Object.assign(frame.style, {position: 'relative', width: '100%', overflow: 'hidden'});
    frame.append(host);
    this.container.replaceChildren(frame);
    host.style.visibility = '';
    host.style.position = 'absolute';
    host.style.left = '0px';
    host.style.width = '100%';
    this.host = host;
    this.frame = frame;
    this.osmd = display;
    this.renderedWidth = layout.width;
    this.renderedHeight = layout.height;
    this.setSystems(layout.systems);
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
        positions.push({beat, step, measureIndex: iterator.CurrentMeasureIndex});
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
    const position = this.cursorPositions[Math.max(0, low - 1)];
    const target = position.step;
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
    this.showSystem(this.systemForMeasure.get(position.measureIndex) ?? 0);
  }

  setSystems(systems) {
    this.systems = systems;
    this.systemForMeasure = new Map(systems.flatMap((row, index) => row.measures.map(measure => [measure, index])));
    this.visibleSystem = -1;
  }

  showSystem(index) {
    if (!this.systems.length || index === this.visibleSystem) return;
    const row = this.systems[index];
    const next = this.systems[index + 1];
    const previous = this.systems[index - 1];
    const after = this.systems[index + (next ? 2 : 1)];
    // Keep a small edge around this pair without admitting any neighboring row.
    const topPadding = previous ? Math.min(WINDOW_PADDING, Math.max(0, (row.top - previous.bottom) / 2)) : WINDOW_PADDING;
    const last = next || row;
    const bottomPadding = after ? Math.min(WINDOW_PADDING, Math.max(0, (after.top - last.bottom) / 2)) : WINDOW_PADDING;
    const top = Math.max(0, row.top - topPadding);
    const bottom = last.bottom + bottomPadding;
    this.host.style.top = `${-top}px`;
    this.frame.style.height = `${bottom - top}px`;
    this.frame.dataset.visibleSystemStart = String(index + 1);
    this.frame.dataset.visibleSystemCount = next ? '2' : '1';
    this.frame.dataset.systemCount = String(this.systems.length);
    this.visibleSystem = index;
  }

  resize() {
    if (!this.osmd || !this.model) return;
    const beat = this.beat;
    const layout = this.renderToViewport(this.osmd, this.host);
    this.renderedWidth = layout.width;
    this.renderedHeight = layout.height;
    this.setSystems(layout.systems);
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
    this.resizeObserver?.disconnect();
    this.view.clearTimeout(this.resizeTimer);
    this.osmd?.dispose?.();
    this.osmd = null;
    this.model = null;
    this.systems = [];
    this.systemForMeasure.clear();
    this.host = null;
    this.frame = null;
    this.noteMap.clear();
    this.container.replaceChildren();
  }
}
