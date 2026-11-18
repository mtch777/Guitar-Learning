import {parseMusicXML, ScoreModelError} from './score-model.js';

const STEPS = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
const NATURAL = [0, 2, 4, 5, 7, 9, 11];
const ACCIDENTALS = ['triple-flat', 'flat-flat', 'flat', 'natural', 'sharp', 'double-sharp', 'triple-sharp'];
const mod = (number, divisor) => ((number % divisor) + divisor) % divisor;
const name = node => node.localName || node.nodeName?.split(':').pop();
const children = (node, tag) => Array.from(node?.childNodes || []).filter(item => item.nodeType === 1 && (!tag || name(item) === tag));
const child = (node, tag) => children(node, tag)[0];
const value = (node, tag) => child(node, tag)?.textContent.trim() || '';
const fail = (code, message) => { throw new ScoreModelError(code, message); };
function descendants(node, tag) {
  return children(node).flatMap(item => [...(name(item) === tag ? [item] : []), ...descendants(item, tag)]);
}
function element(parent, tag) {
  const prefix = parent.prefix ? `${parent.prefix}:` : '';
  return parent.ownerDocument.createElementNS(parent.namespaceURI, prefix + tag);
}
function setAlter(parent, tag, alter, before = null) {
  let node = child(parent, tag);
  if (!node && alter === 0) return;
  if (!node) { node = element(parent, tag); parent.insertBefore(node, before); }
  node.textContent = String(alter);
}

/** Bounds include every engraved pitch, including grace, cue and hidden notes. */
export function transposeLimits(model) {
  const pitches = model.notes.filter(note => !note.isRest && Number.isInteger(note.midi)).map(note => note.midi);
  if (!pitches.length) fail('EMPTY_SCORE', 'This score has no pitches to transpose.');
  return {min: 0 - pitches.reduce((low, pitch) => Math.min(low, pitch), 127), max: 127 - pitches.reduce((high, pitch) => Math.max(high, pitch), 0)};
}

function keyAlter(fifths, step) {
  const order = fifths < 0 ? [6, 2, 5, 1, 4, 0, 3] : [3, 0, 4, 1, 5, 2, 6];
  return order.indexOf(step) < Math.abs(fifths) ? Math.sign(fifths) : 0;
}

// Choose an ordinary enharmonic signature; preserve the original spelling for
// octave shifts and prefer the original sharp/flat direction in an equal tie.
function interval(fifths, semitones) {
  if (!Number.isInteger(fifths) || Math.abs(fifths) > 7) {
    fail('TRANSPOSE_KEY', 'Transposition requires a standard key signature of at most seven sharps or flats.');
  }
  let target = fifths;
  if (mod(semitones, 12) !== 0) {
    const pitchClass = mod(fifths * 7 + semitones, 12);
    target = Array.from({length: 15}, (_, index) => index - 7)
      .filter(candidate => mod(candidate * 7, 12) === pitchClass)
      .sort((a, b) => Math.abs(a) - Math.abs(b) ||
        Number(Math.sign(b) === Math.sign(fifths)) - Number(Math.sign(a) === Math.sign(fifths)) || a - b)[0];
  }
  const fromStep = mod(fifths * 4, 7);
  const toStep = mod(target * 4, 7);
  const fromPitch = 60 + NATURAL[fromStep] + keyAlter(fifths, fromStep);
  const toOctave = (fromPitch + semitones - NATURAL[toStep] - keyAlter(target, toStep)) / 12 - 1;
  return {fifths: target, diatonic: toStep + 7 * toOctave - (fromStep + 28)};
}

function shiftedPitch(stepText, alter, octave, semitones, diatonic) {
  const step = STEPS.indexOf(stepText);
  if (step < 0 || !Number.isInteger(alter) || !Number.isInteger(octave)) {
    fail('TRANSPOSE_PITCH', 'This score contains a pitch or chord symbol that cannot be transposed in semitones.');
  }
  const midi = 12 * (octave + 1) + NATURAL[step] + alter + semitones;
  const position = step + 7 * octave + diatonic;
  const nextStep = mod(position, 7);
  const nextOctave = Math.floor(position / 7);
  const nextAlter = midi - (12 * (nextOctave + 1) + NATURAL[nextStep]);
  if (Math.abs(nextAlter) > 3) {
    fail('TRANSPOSE_PITCH', 'This transposition needs an accidental beyond a triple sharp or flat.');
  }
  return {step: STEPS[nextStep], alter: nextAlter, octave: nextOctave};
}

function shiftHarmony(harmony, semitones, diatonic) {
  for (const [tag, stepTag, alterTag] of [['root', 'root-step', 'root-alter'], ['bass', 'bass-step', 'bass-alter']]) {
    // Multiple groups represent stacked chords. Numeral/function harmony stays
    // relative to its key, but every written root and bass must move.
    for (const pitch of children(harmony, tag)) {
      const step = child(pitch, stepTag);
      if (!step) fail('TRANSPOSE_HARMONY', 'A chord symbol is missing its written root or bass pitch.');
      const shifted = shiftedPitch(step.textContent.trim(), Number(value(pitch, alterTag) || 0), 4, semitones, diatonic);
      step.textContent = shifted.step;
      // A displayed root override is a pitch label, unlike the chord-quality text.
      if (step.hasAttribute('text')) step.setAttribute('text', shifted.step);
      setAlter(pitch, alterTag, shifted.alter);
    }
  }
}

function ensureInitialKey(part) {
  const measure = children(part, 'measure')[0];
  if (!measure) return;
  const items = children(measure);
  const firstNote = items.findIndex(item => ['note', 'backup', 'forward'].includes(name(item)));
  let attributes = items.find((item, index) => name(item) === 'attributes' && (firstNote < 0 || index < firstNote));
  if (!attributes) {
    attributes = element(measure, 'attributes');
    measure.insertBefore(attributes, measure.firstChild);
  }
  if (children(attributes, 'key').some(key => !key.getAttribute('number'))) return;
  const key = element(attributes, 'key');
  const fifths = element(key, 'fifths'); fifths.textContent = '0'; key.appendChild(fifths);
  const before = children(attributes).find(item => name(item) !== 'divisions');
  attributes.insertBefore(key, before || null);
}

/**
 * Derive a transposed score from the supplied immutable original model.
 * The same regenerated MusicXML feeds engraving, playback and MIDI grading.
 * A zero offset returns the original model/notation without respelling it.
 */
export function transposeScore(model, semitones, options = {}) {
  if (!Number.isInteger(semitones)) fail('INVALID_TRANSPOSE', 'Transpose by a whole number of semitones.');
  if (semitones === 0) return model;
  const limits = transposeLimits(model);
  if (semitones < limits.min || semitones > limits.max) {
    fail('TRANSPOSE_RANGE', 'That transposition moves a score note outside the MIDI keyboard range.');
  }
  const Parser = options.DOMParser || globalThis.DOMParser;
  const Serializer = options.XMLSerializer || globalThis.XMLSerializer;
  if (!Parser || !Serializer) fail('DOM_UNAVAILABLE', 'A DOM parser and serializer are required to transpose this score.');
  const document = new Parser().parseFromString(model.xml, 'application/xml');
  const root = document.documentElement;
  if (descendants(root, 'key-step').length || descendants(root, 'key-alter').length) {
    fail('TRANSPOSE_KEY', 'This score uses a nontraditional key signature that cannot be transposed automatically.');
  }
  if (descendants(root, 'accidental-mark').length) {
    fail('TRANSPOSE_ORNAMENT', 'This score has ornamental accidental marks that cannot be transposed automatically.');
  }
  if (descendants(root, 'frame').length) {
    fail('TRANSPOSE_HARMONY', 'This score includes chord diagrams that cannot be transposed automatically.');
  }
  if (descendants(root, 'key-octave').length) {
    fail('TRANSPOSE_KEY', 'This score uses custom key-signature octave positions that cannot be transposed automatically.');
  }
  const byId = new Map(model.notes.map(note => [note.id, note]));
  const noteTasks = [];
  const harmonyTasks = [];
  const defaultInterval = interval(0, semitones);
  for (const part of children(root, 'part')) {
    ensureInitialKey(part);
    const changes = [];
    let divisions = 1;
    const lookup = (time, staff) => {
      let current = defaultInterval;
      for (const change of changes) {
        if (change.time > time + 1e-9) break;
        if (!change.staff || change.staff === staff) current = change.interval;
      }
      return current;
    };
    children(part, 'measure').forEach((measure, measureIndex) => {
      const start = model.measures[measureIndex].onset;
      let cursor = 0;
      for (const item of children(measure)) {
        if (name(item) === 'attributes') {
          if (value(item, 'divisions')) divisions = Number(value(item, 'divisions'));
          for (const key of children(item, 'key')) {
            const fifths = child(key, 'fifths');
            if (!fifths) fail('TRANSPOSE_KEY', 'This score has a key signature without a conventional fifths value.');
            const shifted = interval(Number(fifths.textContent), semitones);
            // An explicitly keyless passage remains keyless; pitches still move.
            if (value(key, 'mode') !== 'none') fifths.textContent = String(shifted.fifths);
            const cancel = child(key, 'cancel');
            if (cancel) cancel.textContent = String(interval(Number(cancel.textContent), semitones).fifths);
            changes.push({time: start + cursor, staff: Number(key.getAttribute('number')) || 0, interval: shifted, order: changes.length});
          }
        } else if (name(item) === 'note') {
          const note = byId.get(item.getAttribute('id'));
          if (!note) fail('TRANSPOSE_PITCH', 'The score contains a note without a stable lesson identity.');
          if (!child(item, 'chord')) cursor = note.measureOnset + note.duration;
          if (!note.isRest) noteTasks.push({element: item, note, lookup});
        } else if (name(item) === 'backup') cursor -= Number(value(item, 'duration')) / divisions;
        else if (name(item) === 'forward') cursor += Number(value(item, 'duration')) / divisions;
        else if (name(item) === 'harmony') {
          harmonyTasks.push({element: item, time: start + cursor + Number(value(item, 'offset') || 0) / divisions, staff: Number(value(item, 'staff')) || 1, lookup});
        }
      }
    });
    changes.sort((a, b) => a.time - b.time || a.order - b.order);
  }
  // A tie crossing a key change keeps the spelling of its initial notehead.
  const ties = new Map();
  noteTasks.sort((a, b) => a.note.onset - b.note.onset || a.note.partIndex - b.note.partIndex || a.note.sourceNoteIndex - b.note.sourceNoteIndex);
  for (const task of noteTasks) {
    const {note, element: written, lookup} = task;
    const pitch = child(written, 'pitch');
    const tieNumber = descendants(child(written, 'notations'), 'tied')[0]?.getAttribute('number') || '1';
    const tieKey = JSON.stringify([note.partId, note.voice, note.midi, tieNumber, note.isGrace, note.isCue]);
    const shifted = note.tieStop && ties.has(tieKey) ? ties.get(tieKey)
      : shiftedPitch(note.step, note.alter, note.octave, semitones, lookup(note.onset, note.staff).diatonic);
    child(pitch, 'step').textContent = shifted.step;
    child(pitch, 'octave').textContent = String(shifted.octave);
    setAlter(pitch, 'alter', shifted.alter, child(pitch, 'octave'));
    const accidental = child(written, 'accidental');
    if (accidental) {
      accidental.textContent = ACCIDENTALS[shifted.alter + 3];
      if (accidental.hasAttribute('smufl')) accidental.removeAttribute('smufl');
    }
    if (note.tieStart) ties.set(tieKey, shifted);
    else if (note.tieStop) ties.delete(tieKey);
  }
  for (const task of harmonyTasks) shiftHarmony(task.element, semitones, task.lookup(task.time, task.staff).diatonic);
  const result = parseMusicXML(new Serializer().serializeToString(document), options);
  // The first parse assigns missing XML IDs. Those generated IDs stay stable,
  // while sourceId continues to describe the uploaded source, not this copy.
  for (const note of result.notes) note.sourceId = byId.get(note.id).sourceId;
  return result;
}
