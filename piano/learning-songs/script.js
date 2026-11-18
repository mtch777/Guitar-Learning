const buildVersion = document.querySelector('meta[name="build-version"]')?.content
  || new URL(import.meta.url).searchParams.get('v') || 'dev';
const loadModule = name => import(new URL(`./${name}?v=${encodeURIComponent(buildVersion)}`, import.meta.url).href);
const [scoreModule, engineModule, renderModule, storageModule, uploadModule, audioModule] = await Promise.all(
  ['score-model.js', 'lesson-engine.js', 'score-renderer.js', 'song-storage.js', 'score-upload.js', 'piano-audio.js'].map(loadModule)
);
const {parseMusicXML, secondsAtBeat, beatAtSeconds} = scoreModule;
const {LessonEngine} = engineModule;
const {ScoreRenderer} = renderModule;
const {SongStorage, scoreIdentity} = storageModule;
const {readScoreFile} = uploadModule;
const {PianoAudio} = audioModule;
if (document.readyState === 'loading') await new Promise(resolve => document.addEventListener('DOMContentLoaded', resolve, {once:true}));

const $ = id => document.getElementById(id);
const DEFAULT_ID = 'phoebe-bridgers-i-know-the-end';
const TEST_ID = 'conversion-test-nwc';
const builtIns = [
  {id:DEFAULT_ID, title:'I Know the End', composer:'Phoebe Bridgers', needsScore:true},
  {id:TEST_ID, title:'Conversion test · 20 notes', composer:'Michael Cuthbert', url:'./scores/conversion-test.musicxml', testScore:true}
];
const songs = new Map(builtIns.map(song => [song.id, song]));
const storage = await new SongStorage().open();
const audio = new PianoAudio();
const renderer = new ScoreRenderer($('score'), $('score-viewport'));
const preferences = storage.preferences();
let mode = preferences.mode === 'timed' ? 'timed' : 'wait';
let speed = Math.max(.25, Math.min(1.5, Number(preferences.speed) || 1));
let selectedId = null, model = null, engine = null, timedGroups = [], audioNotes = [];
let playing = false, elapsed = 0, anchor = 0, animation = 0, nextAudio = 0, totalSeconds = 0;
let busy = false, uploadForDefault = false, countIn = 0, lastPaint = '', lastStatus = '';
let starting = false, startGeneration = 0;
let octave = 4, midiAccess = null;
const pressed = new Map();
const noteNames = ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'];
const shortcuts = ['a','w','s','e','d','f','t','g','y','h','u','j','k'];
const midiName = midi => noteNames[((midi % 12) + 12) % 12] + (Math.floor(midi / 12) - 1);

function setStatus(text) {
  if (text === lastStatus) return;
  lastStatus = text;
  $('practice-status').textContent = text;
}
function notice(message = '', error = false) {
  $('import-message').textContent = message;
  $('import-message').hidden = !message;
  $('import-message').classList.toggle('error', error);
}
function savePreferences() { storage.savePreferences({mode, speed, sound:audio.enabled}); }
function controls() {
  $('play-button').disabled = busy || !engine || starting;
  $('restart-button').disabled = busy || !engine;
  $('song-select').disabled = busy;
  $('upload-button').disabled = busy;
  $('empty-upload').disabled = busy;
  $('test-score-button').disabled = busy;
  $('tempo').disabled = busy || playing;
  const finished = engine?.complete && (mode === 'wait' || elapsed >= totalSeconds + .2);
  $('play-button').textContent = starting ? 'Starting…' : playing ? 'Ⅱ Pause' : finished ? '▶ Play again' : '▶ Play';
}
function refreshLibrary() {
  $('song-select').replaceChildren();
  for (const song of songs.values()) {
    const option = document.createElement('option');
    option.value = song.id;
    option.textContent = `${song.composer ? song.composer + ' — ' : ''}${song.title}${song.needsScore ? ' · upload score' : ''}`;
    $('song-select').append(option);
  }
  if (selectedId) $('song-select').value = selectedId;
}
function configureEngine() {
  timedGroups = model.groups.map(group => ({...group,
    time:secondsAtBeat(model, group.onset, speed),
    endTime:secondsAtBeat(model, Math.max(group.onset, ...group.notes.map(note => note.onset + note.duration)), speed)
  }));
  engine = new LessonEngine(timedGroups, {mode, timingWindowMs:180});
  audioNotes = model.attacks.map(note => ({...note,
    time:secondsAtBeat(model, note.onset, speed), endTime:secondsAtBeat(model, note.onset + note.duration, speed)
  })).sort((a,b) => a.time - b.time);
  totalSeconds = secondsAtBeat(model, model.duration, speed);
  elapsed = 0; nextAudio = 0; lastPaint = '';
  $('grading-note').textContent = mode === 'timed' ? 'Pitch + onset · ±180 ms · holds are not graded' : 'Hit every highlighted pitch · holds are not graded';
}
function currentVisualGroup(beat) {
  if (mode === 'wait') return engine?.snapshot().currentGroup;
  let lo = 0, hi = model.groups.length - 1, found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (model.groups[mid].onset <= beat + 1e-7) { found = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return found >= 0 ? model.groups[found] : null;
}
function paint(force = false) {
  if (!engine || !model) return;
  const state = engine.snapshot();
  const beat = mode === 'wait' ? (state.currentGroup?.onset ?? model.duration) : Math.max(0, beatAtSeconds(model, elapsed, speed));
  const visual = currentVisualGroup(beat);
  const currentIds = visual?.notes.map(note => note.id) || [];
  const key = `${state.hits}:${state.misses}:${currentIds.join(',')}`;
  if (force || key !== lastPaint) {
    renderer.color(state.statuses, currentIds);
    lastPaint = key;
    $('hit-count').textContent = state.hits;
    $('miss-count').textContent = state.misses;
    $('progress-count').textContent = `${state.hits + state.misses} / ${state.total}`;
    $('progress-fill').style.width = `${state.total ? (state.hits + state.misses) / state.total * 100 : 0}%`;
  }
  renderer.cursorAtBeat(Math.min(beat, model.duration));
}
function completionText() {
  const state = engine.snapshot();
  return `Finished · ${state.hits} hit${state.misses ? `, ${state.misses} missed` : ''}${state.wrong ? `, ${state.wrong} extra key strike${state.wrong === 1 ? '' : 's'}` : ''}. Restart to try again.`;
}
function pause(message = 'Paused. Press Play to continue.') {
  startGeneration++;
  starting = false;
  if (playing && mode === 'timed') {
    elapsed = audio.time - anchor;
    engine?.update(elapsed);
  }
  playing = false;
  cancelAnimationFrame(animation);
  animation = 0;
  engine?.pause();
  audio.stopAll();
  controls();
  if (engine) { paint(); setStatus(message); }
}
function resetSession() {
  pause();
  if (!engine) return;
  engine.reset(); elapsed = 0; nextAudio = 0; lastPaint = '';
  $('score-viewport').scrollTop = 0;
  $('score-viewport').scrollLeft = 0;
  paint(true); controls();
  setStatus(mode === 'wait' ? 'Ready. Press Play, then play the highlighted notes.' : 'Ready. Press Play for a two-beat count-in.');
}
function scheduleAudio() {
  while (nextAudio < audioNotes.length && audioNotes[nextAudio].time <= elapsed + .12) {
    const note = audioNotes[nextAudio++];
    if (note.time < elapsed - .08) continue;
    audio.note(note.midi, note.endTime - note.time, anchor + note.time);
  }
}
function tick() {
  if (!playing || mode !== 'timed') return;
  elapsed = audio.time - anchor;
  scheduleAudio();
  engine.update(elapsed);
  paint();
  if (elapsed < 0) {
    const remaining = Math.max(1, Math.ceil(-elapsed / (countIn / 2)));
    setStatus(`Get ready… ${remaining}`);
  } else if (elapsed >= totalSeconds + .2) {
    pause(completionText());
    return;
  } else {
    setStatus('Keep playing with the score. Green = hit · red = missed.');
  }
  animation = requestAnimationFrame(tick);
}
async function start() {
  if (!engine || busy || playing || starting) return;
  // Finishing the last attack does not finish its sustained sound.
  if (engine.complete && (mode === 'wait' || elapsed >= totalSeconds + .2)) resetSession();
  const generation = ++startGeneration;
  const requestedEngine = engine;
  starting = true;
  controls();
  try { await audio.unlock(); } catch (error) { notice(error.message); }
  if (generation !== startGeneration || requestedEngine !== engine) return;
  starting = false;
  if (mode === 'timed') {
    if (elapsed === 0 && !engine.hits && !engine.misses) {
      countIn = 2 * 60 / ((model.tempos[0]?.bpm || 120) * speed);
      elapsed = -countIn;
    }
    anchor = audio.time - elapsed;
    nextAudio = audioNotes.findIndex(note => note.time >= elapsed - .03);
    if (nextAudio < 0) nextAudio = audioNotes.length;
    for (const note of audioNotes) {
      if (note.time < elapsed && note.endTime > elapsed) audio.note(note.midi, note.endTime - elapsed);
    }
    engine.start(elapsed);
    playing = true;
    tick();
  } else {
    engine.start(0);
    playing = true;
    setStatus('Play the highlighted notes. The score will wait for you.');
    paint();
  }
  controls();
}

async function selectSong(song, {preparedModel = null, remember = true} = {}) {
  if (!song || busy) return false;
  busy = true;
  const previous = {model, engine, selectedId};
  pause('Loading score…'); controls(); notice();
  try {
    if (song.needsScore) {
      renderer.destroy(); model = null; engine = null;
      $('score').hidden = true;
      $('empty-score').hidden = false;
      $('empty-title').textContent = 'I Know the End';
      $('empty-description').textContent = 'Phoebe Bridgers is your first song. Upload a MusicXML score of this song to begin. A verified notation file is still needed; the available performance MIDI cannot preserve the original written score.';
      $('song-title').textContent = song.title;
      $('song-composer').textContent = song.composer;
      $('song-detail').textContent = 'Score needed';
      $('score-warnings').hidden = true;
      $('hit-count').textContent = $('miss-count').textContent = '0';
      $('progress-count').textContent = '0 / 0';
      $('progress-fill').style.width = '0%';
      setStatus('Upload this song, or open the conversion test score.');
    } else {
      let xml = song.xml;
      if (!xml) {
        const response = await fetch(new URL(song.url, import.meta.url));
        if (!response.ok) throw new Error(`The score could not be loaded (${response.status}).`);
        xml = await response.text();
      }
      const candidate = preparedModel || parseMusicXML(xml);
      $('score').hidden = false; $('empty-score').hidden = true;
      const rendered = await renderer.load(candidate);
      model = candidate;
      configureEngine();
      $('song-title').textContent = song.title;
      $('song-composer').textContent = song.composer || candidate.composer || '';
      $('song-detail').textContent = `${candidate.parts.length} part${candidate.parts.length === 1 ? '' : 's'} · ${candidate.attacks.length} attacks${song.testScore ? ' · NoteWorthy → MusicXML' : ''}`;
      const warnings = [...candidate.warnings, ...(rendered.warnings || [])];
      $('score-warnings').textContent = warnings.join(' ');
      $('score-warnings').hidden = !warnings.length;
      paint(true);
      setStatus(mode === 'wait' ? 'Ready. Press Play, then play the highlighted notes.' : 'Ready. Press Play for a two-beat count-in.');
    }
    selectedId = song.id;
    $('song-select').value = selectedId;
    if (remember) storage.select(selectedId);
    $('score-viewport').scrollTop = 0;
    return true;
  } catch (error) {
    model = previous.model; engine = previous.engine; selectedId = previous.selectedId;
    if (model) {
      try { await renderer.load(model); paint(true); } catch (_) { engine = null; }
    } else {
      $('score').hidden = true; $('empty-score').hidden = false;
    }
    if (selectedId) $('song-select').value = selectedId;
    notice(error.message || 'This score could not be opened.', true);
    setStatus(engine ? 'The previous score is still available. Press Play to continue.' : 'Choose another score to continue.');
    return false;
  } finally { busy = false; controls(); }
}

async function uploadFiles(files) {
  const targetDefault = uploadForDefault;
  uploadForDefault = false;
  const results = [], failures = [];
  for (const file of files) {
    try {
      const xml = await readScoreFile(file);
      const candidate = parseMusicXML(xml);
      const title = candidate.title && candidate.title !== 'Untitled score' ? candidate.title : file.name.replace(/\.(musicxml|xml|mxl)$/i,'');
      const matchesDefault = (targetDefault && files.length === 1) || /i\s+know\s+the\s+end/i.test(`${title} ${file.name}`);
      const song = {
        id:matchesDefault ? DEFAULT_ID : await scoreIdentity(xml),
        title:matchesDefault ? 'I Know the End' : title,
        composer:matchesDefault ? 'Phoebe Bridgers' : candidate.composer,
        xml, filename:file.name, uploadedAt:new Date().toISOString(), needsScore:false
      };
      const loaded = await selectSong(song, {preparedModel:candidate, remember:false});
      if (!loaded) { failures.push(`${file.name}: ${$('import-message').textContent}`); continue; }
      let persisted = false;
      try { persisted = await storage.put(song); }
      catch (_) { /* Keep the loaded lesson usable and report the failed save. */ }
      songs.set(song.id, song);
      refreshLibrary();
      storage.select(selectedId || song.id);
      results.push(`${file.name}${persisted ? '' : ' (open for this visit; browser storage is unavailable or full)'}`);
    } catch (error) { failures.push(`${file.name}: ${error.message}`); }
  }
  const messages = [];
  if (results.length) messages.push(`Opened ${results.join(', ')}.`);
  if (failures.length) messages.push(failures.join(' '));
  notice(messages.join(' '), failures.length > 0);
  $('song-upload').value = '';
}

function strike(midi, source, sound = false) {
  if (pressed.has(source)) return;
  pressed.set(source, midi);
  highlightKeys();
  if (sound && audio.enabled) {
    // Grade the input immediately; resuming an audio device must not add latency.
    audio.unlock().then(() => audio.note(midi)).catch(() => {});
  }
  if (!playing || !engine || busy) return;
  const position = mode === 'timed' ? audio.time - anchor : 0;
  const result = engine.grade(midi, position);
  paint();
  if (mode === 'wait') {
    if (result.complete) pause(completionText());
    else if (result.outcome === 'wrong') setStatus('That pitch does not match. Try the highlighted notes.');
    else if (result.outcome === 'hit') setStatus(result.advanced ? 'Correct. Play the next highlighted notes.' : 'Good. Play the other highlighted notes in this chord.');
  }
}
function release(source) { pressed.delete(source); highlightKeys(); }
function highlightKeys() {
  const down = new Set(pressed.values());
  $('keyboard').querySelectorAll('[data-midi]').forEach(key => key.classList.toggle('active', down.has(Number(key.dataset.midi))));
}
function drawKeyboard() {
  $('keyboard').replaceChildren();
  const base = (octave + 1) * 12;
  const white = [0,2,4,5,7,9,11,12];
  const black = new Map([[1,1],[3,2],[6,4],[8,5],[10,6]]);
  for (let semitone = 0; semitone <= 12; semitone++) {
    const midi = base + semitone;
    const key = document.createElement('button');
    key.type = 'button'; key.className = `piano-key ${white.includes(semitone) ? 'white' : 'black'}`;
    key.dataset.midi = midi; key.setAttribute('aria-label', `Play ${midiName(midi)}`);
    if (black.has(semitone)) key.style.left = `${black.get(semitone) / 8 * 100}%`;
    const label = document.createElement('span'); label.className = 'note-name'; label.textContent = midiName(midi);
    const shortcut = document.createElement('span'); shortcut.className = 'shortcut'; shortcut.textContent = shortcuts[semitone].toUpperCase();
    key.append(label, shortcut);
    key.addEventListener('pointerdown', event => {
      event.preventDefault(); key.setPointerCapture?.(event.pointerId);
      strike(midi, `pointer-${event.pointerId}`, true);
    });
    key.addEventListener('pointerup', event => release(`pointer-${event.pointerId}`));
    key.addEventListener('pointercancel', event => release(`pointer-${event.pointerId}`));
    key.addEventListener('lostpointercapture', event => release(`pointer-${event.pointerId}`));
    key.addEventListener('click', event => {
      if (event.detail !== 0) return;
      const source = `accessible-${midi}`;
      strike(midi, source, true); setTimeout(() => release(source), 140);
    });
    $('keyboard').append(key);
  }
  $('keyboard-range').textContent = `${midiName(base)} – ${midiName(base + 12)}`;
  $('octave-down').disabled = octave <= 0; $('octave-up').disabled = octave >= 8;
  highlightKeys();
}
function changeOctave(delta) { octave = Math.max(0, Math.min(8, octave + delta)); drawKeyboard(); }
async function connectMidi() {
  if (!navigator.requestMIDIAccess) {
    $('midi-status').textContent = 'Web MIDI is unavailable in this browser. Use the on-screen keys, or open this page in a Web MIDI browser.';
    return;
  }
  try {
    $('midi-status').textContent = 'Requesting MIDI access…';
    midiAccess = await navigator.requestMIDIAccess({sysex:false});
    midiAccess.onstatechange = refreshMidi;
    refreshMidi();
  } catch (error) { $('midi-status').textContent = `MIDI access was not granted. You can still use the on-screen keys. ${error.message || ''}`; }
}
function refreshMidi() {
  const devices = [...midiAccess.inputs.values()].filter(input => input.state !== 'disconnected');
  for (const source of pressed.keys()) if (source.startsWith('midi-')) pressed.delete(source);
  highlightKeys();
  for (const device of devices) {
    device.onmidimessage = event => {
      const [status, midi, velocity] = event.data;
      const command = status & 0xf0;
      const source = `midi-${device.id}-${status & 0x0f}-${midi}`;
      if (command === 0x90 && velocity > 0) strike(midi, source);
      else if (command === 0x80 || (command === 0x90 && velocity === 0)) release(source);
    };
  }
  $('midi-dot').classList.toggle('connected', devices.length > 0);
  $('midi-status').textContent = devices.length ? `Connected: ${devices.map(device => device.name || 'MIDI keyboard').join(', ')}` : 'MIDI access enabled. Connect your keyboard to begin.';
  if (devices.length) { try { window.PracticeMIDI?.setEnabled(true); } catch (_) {} }
}

$('upload-button').addEventListener('click', () => { uploadForDefault = false; $('song-upload').click(); });
$('empty-upload').addEventListener('click', () => { uploadForDefault = true; $('song-upload').click(); });
$('song-upload').addEventListener('change', event => uploadFiles([...event.target.files]));
$('song-select').addEventListener('change', event => selectSong(songs.get(event.target.value)));
$('test-score-button').addEventListener('click', () => selectSong(songs.get(TEST_ID)));
$('play-button').addEventListener('click', () => playing ? pause() : start());
$('restart-button').addEventListener('click', () => { const resume = playing; resetSession(); if (resume) start(); });
$('midi-button').addEventListener('click', connectMidi);
$('octave-down').addEventListener('click', () => changeOctave(-1));
$('octave-up').addEventListener('click', () => changeOctave(1));
$('lesson-modes').addEventListener('change', event => {
  if (event.target.name !== 'lesson-mode') return;
  pause(); mode = event.target.value;
  if (model) { configureEngine(); resetSession(); }
  savePreferences();
});
$('tempo').addEventListener('input', event => {
  speed = Number(event.target.value) / 100;
  $('tempo-label').textContent = `${event.target.value}%`;
});
$('tempo').addEventListener('change', () => { if (model) { configureEngine(); resetSession(); } savePreferences(); });
$('sound-enabled').addEventListener('change', event => { audio.setEnabled(event.target.checked); savePreferences(); });
document.addEventListener('keydown', event => {
  if (event.repeat || event.altKey || event.ctrlKey || event.metaKey || event.target.closest('input, select, textarea, [contenteditable="true"]')) return;
  const key = event.key.toLowerCase();
  if (key === 'z' || key === 'x') { event.preventDefault(); changeOctave(key === 'z' ? -1 : 1); return; }
  const index = shortcuts.indexOf(key);
  if (index < 0) return;
  event.preventDefault(); strike((octave + 1) * 12 + index, `key-${event.code}`, true);
});
document.addEventListener('keyup', event => release(`key-${event.code}`));
window.addEventListener('blur', () => { pressed.clear(); highlightKeys(); if (playing || starting) pause('Paused while this window was inactive. Press Play to continue.'); });
document.addEventListener('visibilitychange', () => { if (document.hidden && (playing || starting)) pause('Paused while this page was hidden. Press Play to continue.'); });
let resizeTimer;
window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (model) { renderer.resize(); paint(true); } }, 180); });

document.querySelector(`input[name="lesson-mode"][value="${mode}"]`).checked = true;
$('tempo').value = Math.round(speed * 100); $('tempo-label').textContent = `${Math.round(speed * 100)}%`;
$('sound-enabled').checked = preferences.sound !== false; audio.setEnabled($('sound-enabled').checked);
if (!storage.persistent) $('library-note').textContent = 'Browser storage is unavailable. Uploaded scores will remain open for this visit only.';
try { for (const song of await storage.list()) if (song.id && typeof song.xml === 'string') songs.set(song.id, song); }
catch (_) { notice('Saved scores could not be read. You can still upload a score for this visit.', true); }
refreshLibrary(); drawKeyboard();
await selectSong(songs.get(storage.lastSelection()) || songs.get(DEFAULT_ID));
try { window.PracticeTracker?.recordOpen('learning-songs'); } catch (_) {}
try { if (window.PracticeMIDI?.isEnabled()) connectMidi(); } catch (_) {}

// A read-only snapshot makes regressions inspectable without synthesizing MIDI.
window.PianoSongLesson = Object.freeze({
  getSnapshot: () => ({selectedId, mode, playing, elapsed, speed,
    songCount:songs.size, storagePersistent:storage.persistent,
    model:model ? {title:model.title, parts:model.parts.length, notes:model.notes.length, attacks:model.attacks.length, duration:model.duration, warnings:[...model.warnings]} : null,
    lesson:engine ? {...engine.snapshot(), statuses:Object.fromEntries(engine.statuses)} : null})
});
