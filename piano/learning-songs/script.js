const buildVersion = document.querySelector('meta[name="build-version"]')?.content
  || new URL(import.meta.url).searchParams.get('v') || 'dev';
const loadModule = name => import(new URL(`./${name}?v=${encodeURIComponent(buildVersion)}`, import.meta.url).href);
const [scoreModule, engineModule, renderModule, storageModule, repositoryModule, audioModule] = await Promise.all(
  ['score-model.js', 'lesson-engine.js', 'score-renderer.js', 'song-storage.js', 'github-song-storage.js', 'piano-audio.js'].map(loadModule)
);
const {parseMusicXML, secondsAtBeat, beatAtSeconds} = scoreModule;
const {LessonEngine} = engineModule;
const {ScoreRenderer} = renderModule;
const {SongStorage} = storageModule;
const {SONG_LIBRARY, loadSongLibrary, loadSongScore} = repositoryModule;
const {PianoAudio} = audioModule;
if (document.readyState === 'loading') await new Promise(resolve => document.addEventListener('DOMContentLoaded', resolve, {once:true}));

const $ = id => document.getElementById(id);
const DEFAULT_ID = 'phoebe-bridgers-i-know-the-end';
const TEST_ID = 'conversion-test-nwc';
const builtIns = [
  {id:DEFAULT_ID, title:'I Know the End', composer:'Phoebe Bridgers', url:new URL('./scores/phoebe-bridgers-i-know-the-end.musicxml', document.baseURI).href, repositorySaved:true, description:'Piano arrangement by Edgar Roock · converted from MIDI'},
  {id:TEST_ID, title:'Conversion test · 20 notes', composer:'Michael Cuthbert', url:new URL('./scores/conversion-test.musicxml', document.baseURI).href, testScore:true, repositorySaved:true}
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
let busy = false, libraryLoading = false, countIn = 0, lastPaint = '', lastStatus = '';
let librarySource = 'bundled', waitingForUpload = false;
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
  $('refresh-library').disabled = busy || libraryLoading;
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
    option.textContent = `${song.composer ? song.composer + ' — ' : ''}${song.title}${song.localOnly ? ' · only on this device' : ''}`;
    $('song-select').append(option);
  }
  if (selectedId) $('song-select').value = selectedId;
}
function libraryNotice(message = '', error = false) {
  $('library-message').textContent = message;
  $('library-message').hidden = !message;
  $('library-message').classList.toggle('error', error);
}
async function refreshSharedLibrary({announce = false} = {}) {
  if (libraryLoading || busy) return false;
  libraryLoading = true; controls();
  try {
    const catalog = await loadSongLibrary({deployedCatalogUrl:new URL('./song-library.json', document.baseURI).href});
    const localSongs = [...songs.values()].filter(song => song.localOnly);
    const previousSong = songs.get(selectedId);
    songs.clear();
    for (const song of catalog.songs) songs.set(song.id, song);
    for (const song of localSongs) songs.set(song.id, song);
    if (previousSong && !songs.has(previousSong.id)) songs.set(previousSong.id, previousSong);
    librarySource = catalog.source;
    refreshLibrary();
    const messages = [];
    if (catalog.warning) messages.push(catalog.warning);
    if (announce) messages.push(`Song list refreshed · ${catalog.songs.length} songs saved on GitHub. A new upload appears after publishing finishes.`);
    for (const issue of catalog.importErrors || []) messages.push(`${issue.sourceFilename}: ${issue.message}`);
    libraryNotice(messages.join(' '), !!catalog.importErrors?.length);
    return true;
  } catch (error) {
    libraryNotice(error.message, true);
    return false;
  } finally { libraryLoading = false; controls(); }
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
    {
      let xml = song.xml;
      if (!xml) {
        const loaded = await loadSongScore(song);
        xml = loaded.xml;
        if (loaded.warning) notice(loaded.warning);
      }
      const candidate = preparedModel || parseMusicXML(xml);
      $('score').hidden = false; $('empty-score').hidden = true;
      const rendered = await renderer.load(candidate);
      model = candidate;
      configureEngine();
      $('song-title').textContent = song.title;
      $('song-composer').textContent = song.composer || candidate.composer || '';
      $('song-detail').textContent = `${candidate.parts.length} part${candidate.parts.length === 1 ? '' : 's'} · ${candidate.attacks.length} attacks${song.testScore ? ' · NoteWorthy → MusicXML' : ''}`;
      $('song-description').textContent = song.description || '';
      $('song-description').hidden = !song.description;
      $('local-recovery').hidden = !song.localOnly;
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
      $('empty-title').textContent = 'The score could not be loaded';
      $('empty-description').textContent = 'Refresh the song list and try again, or select another song.';
    }
    if (selectedId) $('song-select').value = selectedId;
    notice(error.message || 'This score could not be opened.', true);
    setStatus(engine ? 'The previous score is still available. Press Play to continue.' : 'Choose another score to continue.');
    return false;
  } finally { busy = false; controls(); }
}

function downloadLocalScore() {
  const song = songs.get(selectedId);
  if (!song?.localOnly || !song.xml) return;
  const xml = song.xml.replace(/(<\?xml\b[^?]*\bencoding\s*=\s*["'])[^"']+(["'])/i, '$1UTF-8$2');
  const url = URL.createObjectURL(new Blob([xml], {type:'application/vnd.recordare.musicxml+xml'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = `${song.title.replace(/[^\p{L}\p{N}._ -]/gu, '').trim() || 'recovered-score'}.musicxml`;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  libraryNotice('Downloaded this device-only score. Use Upload to GitHub to add it to your shared song library.');
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

for (const id of ['upload-button', 'empty-upload']) {
  $(id).href = SONG_LIBRARY.uploadUrl;
  $(id).addEventListener('click', () => {
    waitingForUpload = true;
    if (playing || starting) pause();
    libraryNotice('On GitHub, choose your score files and commit the changes to main. Return here and refresh songs after publishing finishes.');
  });
}
$('refresh-library').addEventListener('click', () => refreshSharedLibrary({announce:true}));
$('download-local-score').addEventListener('click', downloadLocalScore);
window.addEventListener('focus', () => {
  if (waitingForUpload && !busy && !playing) { waitingForUpload = false; refreshSharedLibrary({announce:true}); }
});
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
try {
  for (const song of await storage.list()) if (song.id && typeof song.xml === 'string') {
    const localSong = {...song, id:`local-${song.id}`, legacyId:song.id, localOnly:true, repositorySaved:false, needsScore:false};
    songs.set(localSong.id, localSong);
  }
} catch (_) { notice('Earlier device-only scores could not be read. Your GitHub song library is still available.', true); }
await refreshSharedLibrary();
refreshLibrary(); drawKeyboard();
const remembered = storage.lastSelection();
await selectSong(songs.get(remembered) || songs.get(`local-${remembered}`) || songs.get(DEFAULT_ID));
try { window.PracticeTracker?.recordOpen('learning-songs'); } catch (_) {}
try { if (window.PracticeMIDI?.isEnabled()) connectMidi(); } catch (_) {}

// A read-only snapshot makes regressions inspectable without synthesizing MIDI.
window.PianoSongLesson = Object.freeze({
  getSnapshot: () => ({selectedId, mode, playing, elapsed, speed,
    songCount:songs.size, storagePersistent:storage.persistent, librarySource,
    model:model ? {title:model.title, parts:model.parts.length, notes:model.notes.length, attacks:model.attacks.length, duration:model.duration, warnings:[...model.warnings]} : null,
    lesson:engine ? {...engine.snapshot(), statuses:Object.fromEntries(engine.statuses)} : null})
});
