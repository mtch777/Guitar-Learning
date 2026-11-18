/**
 * MusicXML -> one shared written-score / attack model for piano practice.
 * Times are quarter-note units. Exact fractions are retained alongside numbers.
 * Repeats/navigation are intentionally followed in written order once, with an
 * explicit warning. This module does not schedule audio or grade MIDI input.
 */

export class ScoreModelError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'ScoreModelError';
    this.code = code;
  }
}

const fail = (code, message) => { throw new ScoreModelError(code, message); };
const localName = node => node.localName || node.nodeName?.split(':').pop();
const elements = (node, name) => Array.from(node?.childNodes || [])
  .filter(child => child.nodeType === 1 && (!name || localName(child) === name));
const child = (node, name) => elements(node, name)[0];
const value = (node, name) => child(node, name)?.textContent?.trim() ?? '';
const attr = (node, name) => node?.getAttribute?.(name) || '';
function descendants(node, name) {
  const found = [];
  for (const element of elements(node)) {
    if (localName(element) === name) found.push(element);
    found.push(...descendants(element, name));
  }
  return found;
}

const abs = n => n < 0n ? -n : n;
function gcd(a, b) {
  a = abs(a); b = abs(b);
  while (b) [a, b] = [b, a % b];
  return a || 1n;
}
function fraction(n, d = 1n) {
  n = BigInt(n); d = BigInt(d);
  if (!d) fail('INVALID_NUMBER', 'A musical duration has a zero denominator.');
  if (d < 0n) { n = -n; d = -d; }
  const divisor = gcd(n, d);
  return { n: n / divisor, d: d / divisor };
}
function decimal(text, label = 'number') {
  const match = String(text).trim().match(/^([+-]?)(\d+)(?:\.(\d+))?$/);
  if (!match) fail('INVALID_NUMBER', `Invalid ${label}: ${text || '(missing)'}.`);
  const digits = match[3] || '';
  return fraction(BigInt((match[1] === '-' ? '-' : '') + match[2] + digits), 10n ** BigInt(digits.length));
}
const ZERO = fraction(0);
const ONE = fraction(1);
const add = (a, b) => fraction(a.n * b.d + b.n * a.d, a.d * b.d);
const subtract = (a, b) => fraction(a.n * b.d - b.n * a.d, a.d * b.d);
const multiply = (a, b) => fraction(a.n * b.n, a.d * b.d);
const divide = (a, b) => fraction(a.n * b.d, a.d * b.n);
const compare = (a, b) => a.n * b.d < b.n * a.d ? -1 : a.n * b.d > b.n * a.d ? 1 : 0;
const maximum = (a, b) => compare(a, b) > 0 ? a : b;
function number(a) {
  const result = Number(a.n) / Number(a.d);
  if (!Number.isFinite(result) || (a.n !== 0n && result === 0)) fail('NUMBER_RANGE', 'A musical time value is outside the supported numeric range.');
  return result;
}
const key = a => a.d === 1n ? String(a.n) : `${a.n}/${a.d}`;

const STEP = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const BEAT_UNITS = {
  maxima: 32, long: 16, breve: 8, whole: 4, half: 2, quarter: 1,
  eighth: 0.5, '16th': 0.25, '32nd': 0.125, '64th': 0.0625,
  '128th': 0.03125, '256th': 0.015625,
};

function readMeter(time) {
  if (!time || child(time, 'senza-misura')) return null;
  const items = elements(time);
  let beats = null;
  let total = ZERO;
  for (const item of items) {
    if (localName(item) === 'beats') {
      beats = item.textContent.trim().split('+').reduce((sum, text) => add(sum, decimal(text, 'time signature')), ZERO);
    } else if (localName(item) === 'beat-type' && beats) {
      const denominator = decimal(item.textContent.trim(), 'time signature denominator');
      if (denominator.n <= 0n) fail('INVALID_METER', 'The time signature denominator must be positive.');
      total = add(total, divide(multiply(beats, fraction(4)), denominator));
      beats = null;
    }
  }
  return total.n > 0n ? total : null;
}

function readPitch(note, where) {
  if (child(note, 'unpitched')) {
    fail('UNPITCHED_SCORE', `${where} contains unpitched percussion. Import a pitched piano or melody part for this lesson.`);
  }
  const pitch = child(note, 'pitch');
  if (!pitch) fail('MISSING_PITCH', `${where} has neither a pitch nor a rest.`);
  const step = value(pitch, 'step');
  const octave = Number(value(pitch, 'octave'));
  const alterText = value(pitch, 'alter') || '0';
  const alter = Number(alterText);
  if (!Number.isFinite(alter) || !Number.isInteger(alter)) {
    fail('MICROTONAL_SCORE', `${where} has a microtonal pitch that a standard piano keyboard cannot match.`);
  }
  if (!(step in STEP) || !Number.isInteger(octave) || value(pitch, 'octave') === '') {
    fail('INVALID_PITCH', `${where} has an invalid pitch.`);
  }
  const midi = 12 * (octave + 1) + STEP[step] + alter;
  if (!Number.isInteger(midi) || midi < 0 || midi > 127) fail('PITCH_RANGE', `${where} is outside the MIDI note range.`);
  return { midi, step, alter, octave };
}

function tieFlags(note) {
  const types = new Set(elements(note, 'tie').map(element => attr(element, 'type')));
  // Some exporters omit playback <tie> but retain the written <tied> element.
  const written = descendants(child(note, 'notations'), 'tied');
  for (const tie of written) {
    const type = attr(tie, 'type');
    if (type === 'continue') { types.add('start'); types.add('stop'); }
    else if (type === 'start' || type === 'stop') types.add(type);
  }
  return {
    tieStart: types.has('start'), tieStop: types.has('stop'),
    tieNumber: attr(written[0], 'number') || '1',
  };
}

function makeId(element, fallback, used) {
  let id = attr(element, 'id');
  if (!/^[A-Za-z_][\w.-]*$/.test(id) || used.has(id)) id = fallback;
  while (used.has(id)) id += '-n';
  used.add(id);
  element.setAttribute('id', id);
  return id;
}

function readTempo(direction, cursor, divisions, measureIndex, partIndex, tempos, warn) {
  let onset = cursor;
  const offset = value(direction, 'offset');
  if (offset) {
    if (!divisions) fail('MISSING_DIVISIONS', 'A tempo offset appears before MusicXML divisions are defined.');
    onset = add(onset, divide(decimal(offset, 'tempo offset'), divisions));
  }
  const sounds = localName(direction) === 'sound' ? [direction] : descendants(direction, 'sound');
  const soundTempos = sounds.filter(sound => attr(sound, 'tempo') !== '');
  for (const sound of soundTempos) {
    const bpm = Number(attr(sound, 'tempo'));
    if (!Number.isFinite(bpm) || bpm <= 0) fail('INVALID_TEMPO', 'Playback tempo must be a positive number.');
    tempos.push({ localOnset: onset, measureIndex, partIndex, bpm, priority: 2 });
  }
  if (soundTempos.length) return;
  for (const metronome of descendants(direction, 'metronome')) {
    const perMinuteText = value(metronome, 'per-minute');
    const perMinute = Number(perMinuteText);
    const beatUnit = BEAT_UNITS[value(metronome, 'beat-unit')];
    if (!perMinuteText || !Number.isFinite(perMinute) || perMinute <= 0 || !beatUnit) {
      warn('A tempo instruction has no exact numeric playback tempo; the previous tempo continues.');
      continue;
    }
    const dots = elements(metronome, 'beat-unit-dot').length;
    const multiplier = 2 - 2 ** -dots;
    tempos.push({ localOnset: onset, measureIndex, partIndex, bpm: perMinute * beatUnit * multiplier, priority: 1 });
  }
}

function parsePart(part, partIndex, metadata, state) {
  const partId = attr(part, 'id') || `part-${partIndex + 1}`;
  const notes = [];
  const measures = [];
  let divisions = null;
  let meter = null;
  for (const [measureIndex, measure] of elements(part, 'measure').entries()) {
    let cursor = ZERO;
    let extent = ZERO;
    let chordAnchor = null;
    let noteIndex = 0;
    const label = attr(measure, 'number') || String(measureIndex + 1);
    for (const item of elements(measure)) {
      const tag = localName(item);
      if (tag === 'attributes') {
        const divisionText = value(item, 'divisions');
        if (divisionText) {
          divisions = decimal(divisionText, 'divisions');
          if (divisions.n <= 0n) fail('INVALID_DIVISIONS', 'MusicXML divisions must be positive.');
        }
        const time = child(item, 'time');
        if (time) meter = readMeter(time);
        for (const transpose of elements(item, 'transpose')) {
          if (Number(value(transpose, 'chromatic') || 0) !== 0 || Number(value(transpose, 'octave-change') || 0) !== 0 || Number(value(transpose, 'diatonic') || 0) !== 0 || child(transpose, 'double')) {
            fail('TRANSPOSED_INSTRUMENT', `${metadata.name} uses instrument transposition. Export it at concert pitch for this piano lesson.`);
          }
        }
      } else if (tag === 'backup' || tag === 'forward') {
        if (!divisions) fail('MISSING_DIVISIONS', 'Musical timing appears before MusicXML divisions are defined.');
        const duration = divide(decimal(value(item, 'duration'), `${tag} duration`), divisions);
        if (duration.n < 0n) fail('INVALID_DURATION', 'Backup and forward durations cannot be negative.');
        cursor = tag === 'backup' ? subtract(cursor, duration) : add(cursor, duration);
        if (cursor.n < 0n) fail('INVALID_BACKUP', `Measure ${label} moves before its own start.`);
        extent = maximum(extent, cursor);
        chordAnchor = null;
      } else if (tag === 'direction' || tag === 'sound') {
        readTempo(item, cursor, divisions, measureIndex, partIndex, state.tempos, state.warn);
      } else if (tag === 'note') {
        const where = `${metadata.name}, measure ${label}`;
        const isRest = Boolean(child(item, 'rest'));
        const isGrace = Boolean(child(item, 'grace'));
        const isCue = Boolean(child(item, 'cue'));
        const isChord = Boolean(child(item, 'chord'));
        const isHidden = attr(item, 'print-object') === 'no';
        if (elements(item, 'pitch').length + elements(item, 'rest').length + elements(item, 'unpitched').length !== 1) {
          fail('INVALID_NOTE', `${where} must contain exactly one pitch, rest or unpitched note.`);
        }
        if (isChord && (!chordAnchor || isRest)) fail('INVALID_CHORD', `${where} has a chord note without a preceding pitched note.`);
        if (!isGrace && !divisions) fail('MISSING_DIVISIONS', `${where} has notes before MusicXML divisions are defined.`);
        const duration = isGrace ? ZERO : divide(decimal(value(item, 'duration'), 'note duration'), divisions);
        if (!isGrace && duration.n <= 0n) fail('INVALID_DURATION', `${where} has a note or rest without a positive duration.`);
        const onset = isChord ? chordAnchor.onset : cursor;
        const staffText = value(item, 'staff') || (isChord ? chordAnchor.staff : '1');
        const staff = Number(staffText);
        if (!Number.isInteger(staff) || staff < 1) fail('INVALID_STAFF', `${where} has an invalid staff number.`);
        const voice = value(item, 'voice') || (isChord ? chordAnchor.voice : '1');
        const pitch = isRest ? { midi: null } : readPitch(item, where);
        const ties = tieFlags(item);
        const sourceId = attr(item, 'id') || null;
        const id = makeId(item, `ls-p${partIndex}-m${measureIndex}-n${noteIndex}`, state.ids);
        notes.push({
          id, sourceId, partId, partIndex, staff, voice, measureIndex, measureNumber: label,
          sourceNoteIndex: noteIndex++, ...pitch, isRest, isGrace, isCue, isHidden,
          ...ties, attackId: null, localOnset: onset, length: duration,
        });
        extent = maximum(extent, add(onset, duration));
        if (!isChord) {
          chordAnchor = isRest ? null : { onset, staff, voice };
          cursor = add(cursor, duration);
        }
        if (isGrace) state.warn('Grace notes remain visible in the score; this lesson does not play or score their unspecified timing.');
        if (isCue) state.warn('Cue notes remain visible in the score and are excluded from practice.');
      }
    }
    measures.push({ index: measureIndex, number: label, extent, meter, partIndex });
  }
  return { notes, measures, part: { id: partId, name: metadata.name, partIndex } };
}

function buildAttacks(rawNotes, warn) {
  const chains = [];
  const open = new Map();
  const ordered = rawNotes.filter(note => !note.isRest && !note.isGrace && !note.isCue)
    .sort((a, b) => compare(a.start, b.start) || a.partIndex - b.partIndex || a.sourceNoteIndex - b.sourceNoteIndex);
  for (const note of ordered) {
    const tieKey = JSON.stringify([note.partId, note.voice, note.midi, note.tieNumber]);
    let chain;
    if (note.tieStop) {
      chain = open.get(tieKey);
      if (!chain || compare(chain.end, note.start) !== 0) {
        fail('UNMATCHED_TIE', `A tie into ${note.measureNumber} has no matching contiguous start. Import a complete or explicitly untied excerpt.`);
      }
      open.delete(tieKey);
      chain.notes.push(note);
      chain.end = add(note.start, note.length);
    } else {
      chain = { start: note.start, end: add(note.start, note.length), midi: note.midi, notes: [note] };
      chains.push(chain);
    }
    if (note.tieStart) {
      if (open.has(tieKey)) fail('AMBIGUOUS_TIE', 'Two simultaneous ties share a pitch and voice without distinct tie numbers.');
      open.set(tieKey, chain);
    }
  }
  if (open.size) fail('UNFINISHED_TIE', 'The score ends with an unfinished tie. Import the complete score or finish the tie in the source file.');

  // A physical piano key is pressed once even when several voices/parts write
  // the same pitch at the same moment. Keep all notation IDs and the longest hold.
  const merged = new Map();
  for (const chain of chains) {
    const mergeKey = `${key(chain.start)}:${chain.midi}`;
    let attack = merged.get(mergeKey);
    if (!attack) {
      attack = { id: `attack-${chain.notes[0].id}`, start: chain.start, end: chain.end, midi: chain.midi, rawNotes: [], hasVisibleStart: false };
      merged.set(mergeKey, attack);
    }
    attack.end = maximum(attack.end, chain.end);
    attack.rawNotes.push(...chain.notes);
    attack.hasVisibleStart ||= !chain.notes[0].isHidden;
  }
  const attacks = [];
  for (const mergedAttack of merged.values()) {
    if (!mergedAttack.hasVisibleStart) {
      warn('Notes hidden by the source file are preserved in score data and excluded from practice.');
      continue;
    }
    const noteIds = mergedAttack.rawNotes.map(note => note.id);
    const first = mergedAttack.rawNotes[0];
    const attack = {
      id: mergedAttack.id, midi: mergedAttack.midi,
      onset: number(mergedAttack.start), duration: number(subtract(mergedAttack.end, mergedAttack.start)),
      onsetFraction: key(mergedAttack.start), durationFraction: key(subtract(mergedAttack.end, mergedAttack.start)),
      noteIds, notationIds: noteIds, partIds: [...new Set(mergedAttack.rawNotes.map(note => note.partId))],
      measureIndex: first.measureIndex, staff: first.staff, voice: first.voice,
      partId: first.partId, partIndex: first.partIndex,
    };
    for (const note of mergedAttack.rawNotes) note.attackId = attack.id;
    attacks.push(attack);
  }
  return attacks.sort((a, b) => a.onset - b.onset || a.midi - b.midi);
}

/**
 * Parse score-partwise MusicXML. Inject DOMParser (and optionally XMLSerializer)
 * for Node tests; browsers use their native implementations. MXL decompression
 * belongs to the upload layer and should pass its actual score XML here.
 */
export function parseMusicXML(text, options = {}) {
  if (typeof text !== 'string' || !text.trim()) fail('EMPTY_INPUT', 'Choose a MusicXML score.');
  const Parser = options.DOMParser || globalThis.DOMParser;
  if (!Parser) fail('DOM_UNAVAILABLE', 'A DOMParser implementation is required.');
  let document;
  try {
    const parser = new Parser({ onError: (level, message) => { if (level !== 'warning') throw new Error(message); } });
    document = parser.parseFromString(text, 'application/xml');
  } catch (error) {
    fail('INVALID_XML', `The score is not valid XML: ${error.message}`);
  }
  const root = document?.documentElement;
  if (!root || localName(root) === 'parsererror' || descendants(root, 'parsererror').length) fail('INVALID_XML', 'The score contains malformed XML.');
  if (localName(root) !== 'score-partwise') fail('UNSUPPORTED_XML', 'Import a score-partwise MusicXML file; this XML is a different format.');
  const warningSet = new Set();
  const warn = message => warningSet.add(message);
  const state = { ids: new Set(), tempos: [], warn };
  const repeats = descendants(root, 'repeat').length || descendants(root, 'ending').length;
  const sounds = descendants(root, 'sound');
  const navigation = sounds.some(sound => ['dacapo', 'dalsegno', 'tocoda', 'fine', 'coda', 'segno', 'forward-repeat'].some(name => attr(sound, name)))
    || descendants(root, 'segno').length || descendants(root, 'coda').length
    || descendants(root, 'words').some(element => /\b(?:D\s*\.?\s*[CS]\s*\.?|Da\s+Capo|Dal\s+Segno|to\s+coda|al\s+fine)\b/i.test(element.textContent));
  if (repeats || navigation) warn('Repeats, endings and navigation are shown as written. Playback and both practice modes follow each written measure once; repeat jumps are not performed.');
  if (descendants(root, 'ornaments').length || descendants(root, 'bend').length || descendants(root, 'glissando').length || descendants(root, 'slide').length) {
    warn('Ornaments and performance techniques remain visible; playback and practice use the written note pitches.');
  }
  const partNames = new Map(elements(child(root, 'part-list'), 'score-part').map(part => [attr(part, 'id'), value(part, 'part-name')]));
  const parsedParts = elements(root, 'part').map((part, index) => parsePart(part, index, { name: partNames.get(attr(part, 'id')) || `Part ${index + 1}` }, state));
  if (!parsedParts.length) fail('EMPTY_SCORE', 'The score has no musical parts.');
  const partIds = parsedParts.map(part => part.part.id);
  if (new Set(partIds).size !== partIds.length) fail('DUPLICATE_PART', 'The score uses the same ID for multiple parts.');

  const measureCount = Math.max(...parsedParts.map(part => part.measures.length));
  const measureStarts = [];
  const measures = [];
  let duration = ZERO;
  for (let index = 0; index < measureCount; index++) {
    const sourceMeasures = parsedParts.map(part => part.measures[index]).filter(Boolean);
    const extent = sourceMeasures.reduce((max, measure) => maximum(max, measure.extent), ZERO);
    const nominal = sourceMeasures.reduce((max, measure) => maximum(max, measure.meter || ZERO), ZERO);
    const width = extent.n > 0n ? extent : nominal;
    if (width.n <= 0n) fail('EMPTY_MEASURE_TIMING', `Measure ${index + 1} has no notes, rests, forward duration or time signature to define its length.`);
    measureStarts.push(duration);
    measures.push({ index, number: sourceMeasures[0].number, onset: number(duration), duration: number(width), onsetFraction: key(duration), durationFraction: key(width) });
    duration = add(duration, width);
  }
  const rawNotes = parsedParts.flatMap(part => part.notes);
  for (const note of rawNotes) note.start = add(measureStarts[note.measureIndex], note.localOnset);
  const attacks = buildAttacks(rawNotes, warn);
  if (!attacks.length) fail('EMPTY_SCORE', 'This score has no playable pitched notes for the piano lesson.');
  const groupsByOnset = new Map();
  for (const attack of attacks) {
    let group = groupsByOnset.get(attack.onsetFraction);
    if (!group) {
      group = { id: `group-${attack.id}`, onset: attack.onset, onsetFraction: attack.onsetFraction, measureIndex: attack.measureIndex, notes: [], midis: [], noteIds: [] };
      groupsByOnset.set(attack.onsetFraction, group);
    }
    group.notes.push(attack);
    group.midis.push(attack.midi);
    group.noteIds.push(...attack.noteIds);
  }

  const tempoByOnset = new Map();
  for (const tempo of state.tempos) {
    const onset = add(measureStarts[tempo.measureIndex], tempo.localOnset);
    if (onset.n < 0n) fail('INVALID_TEMPO_OFFSET', 'A tempo change occurs before the score begins.');
    const onsetKey = key(onset);
    const previous = tempoByOnset.get(onsetKey);
    if (previous && previous.priority === tempo.priority && Math.abs(previous.bpm - tempo.bpm) > 1e-8) fail('CONFLICTING_TEMPO', 'Different parts specify conflicting tempos at the same moment.');
    if (!previous || tempo.priority >= previous.priority) tempoByOnset.set(onsetKey, { onset: number(onset), onsetFraction: onsetKey, bpm: tempo.bpm, priority: tempo.priority });
  }
  if (!tempoByOnset.has('0')) {
    warn('No initial numeric tempo is specified. Playback starts at 120 BPM; change the tempo control if needed.');
    tempoByOnset.set('0', { onset: 0, onsetFraction: '0', bpm: 120, priority: 0 });
  }
  const tempos = [...tempoByOnset.values()].sort((a, b) => a.onset - b.onset).map(({ priority, ...tempo }) => tempo);
  const notes = rawNotes.map(({ start, length, localOnset, tieNumber, ...note }) => ({
    ...note, onset: number(start), duration: number(length),
    onsetFraction: key(start), durationFraction: key(length), measureOnset: number(localOnset),
  }));
  const Serializer = options.XMLSerializer || globalThis.XMLSerializer;
  let xml;
  if (Serializer) xml = new Serializer().serializeToString(document);
  else if (root.outerHTML) xml = root.outerHTML;
  else xml = document.toString();
  if (!xml.trim().startsWith('<')) fail('XML_SERIALIZER', 'This environment cannot serialize the score with stable note IDs.');
  const creators = elements(child(root, 'identification'), 'creator').filter(element => attr(element, 'type') === 'composer').map(element => element.textContent.trim());
  return {
    xml, title: value(child(root, 'work'), 'work-title') || value(root, 'movement-title') || 'Untitled score',
    composer: creators.join(', '), parts: parsedParts.map(part => part.part),
    notes, attacks, groups: [...groupsByOnset.values()], measures, tempos,
    duration: number(duration), durationFraction: key(duration),
    warnings: [...warningSet], playbackOrder: 'written', hasRepeatsOrNavigation: Boolean(repeats || navigation),
  };
}

function validScale(scale) {
  if (!Number.isFinite(scale) || scale <= 0) fail('INVALID_TEMPO_SCALE', 'Tempo scale must be positive.');
}

/** Convert a written-order quarter-note position to elapsed seconds. */
export function secondsAtBeat(model, beat, tempoScale = 1) {
  validScale(tempoScale);
  if (!Number.isFinite(beat)) fail('INVALID_POSITION', 'The beat position must be finite.');
  beat = Math.max(0, beat);
  let seconds = 0;
  for (let i = 0; i < model.tempos.length; i++) {
    const tempo = model.tempos[i];
    if (beat <= tempo.onset) break;
    const end = Math.min(beat, model.tempos[i + 1]?.onset ?? beat);
    seconds += (end - tempo.onset) * 60 / (tempo.bpm * tempoScale);
  }
  return seconds;
}

/** Inverse of secondsAtBeat, including tempo changes and speed scaling. */
export function beatAtSeconds(model, seconds, tempoScale = 1) {
  validScale(tempoScale);
  if (!Number.isFinite(seconds)) fail('INVALID_POSITION', 'Elapsed time must be finite.');
  let remaining = Math.max(0, seconds);
  for (let i = 0; i < model.tempos.length; i++) {
    const tempo = model.tempos[i];
    const next = model.tempos[i + 1];
    const secondsPerBeat = 60 / (tempo.bpm * tempoScale);
    const span = next ? (next.onset - tempo.onset) * secondsPerBeat : Infinity;
    if (remaining <= span) return tempo.onset + remaining / secondsPerBeat;
    remaining -= span;
  }
  return 0;
}
