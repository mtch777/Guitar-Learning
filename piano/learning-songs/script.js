const buildVersion = document.querySelector('meta[name="build-version"]')?.content
  || new URL(import.meta.url).searchParams.get('v') || 'dev';
const loadModule = name => import(new URL(`./${name}?v=${encodeURIComponent(buildVersion)}`, import.meta.url).href);
const [scoreModule, engineModule, renderModule, storageModule, repositoryModule, audioModule, keyboardModule, transposeModule, uploadModule, scoreUploadModule, deleteModule, credentialModule] = await Promise.all(
  ['score-model.js', 'lesson-engine.js', 'score-renderer.js', 'song-storage.js', 'github-song-storage.js', 'piano-audio.js', 'keyboard-model.js', 'score-transpose.js', 'github-song-upload.js', 'score-upload.js', 'github-song-delete.js', 'github-credentials.js'].map(loadModule)
);
const {parseMusicXML, secondsAtBeat, beatAtSeconds} = scoreModule;
const {LessonEngine} = engineModule;
const {ScoreRenderer} = renderModule;
const {SongStorage} = storageModule;
const {SONG_LIBRARY, loadSongLibrary, loadSongScore, visibleSongChoices} = repositoryModule;
const {PianoAudio} = audioModule;
const {keyboardLayout, playingPitchesAt} = keyboardModule;
const {transposeScore, transposeLimits} = transposeModule;
const {uploadScoreToGitHub} = uploadModule;
const {readScoreFile} = scoreUploadModule;
const {deleteSongFromGitHub} = deleteModule;
const {githubCredentials} = credentialModule;
if (document.readyState === 'loading') await new Promise(resolve => document.addEventListener('DOMContentLoaded', resolve, {once:true}));

const $ = id => document.getElementById(id);
const DEFAULT_ID = 'phoebe-bridgers-i-know-the-end';
const songs = new Map();
let songChoices = [], songAliases = new Map();
const storage = await new SongStorage().open();
const audio = new PianoAudio();
const renderer = new ScoreRenderer($('score'), $('score-viewport'));
const preferences = storage.preferences();
let mode = preferences.mode === 'timed' ? 'timed' : 'wait';
let speed = Math.max(.25, Math.min(1.5, Number(preferences.speed) || 1));
let selectedId = null, model = null, engine = null, timedGroups = [], audioNotes = [];
let sourceModel = null, transposeOffset = 0;
let playing = false, elapsed = 0, anchor = 0, animation = 0, nextAudio = 0, totalSeconds = 0;
let busy = false, libraryLoading = false, countIn = 0, lastPaint = '', lastStatus = '';
let librarySource = 'bundled', uploading = false, pendingUploadTimer;
let deleting = false;
const pendingDeleteTimers = new Map();
const PENDING_DELETE_KEY = 'piano-pending-github-deletions-v1';
const pendingDeletes = new Set((() => {
  try { const value = JSON.parse(sessionStorage.getItem(PENDING_DELETE_KEY) || '[]'); return Array.isArray(value) ? value.filter(id => typeof id === 'string') : []; }
  catch (_) { return []; }
})());
function rememberPendingDeletes() {
  try { sessionStorage.setItem(PENDING_DELETE_KEY, JSON.stringify([...pendingDeletes])); } catch (_) {}
}
let libraryNoticeTimer;
let starting = false, startGeneration = 0;
let midiAccess = null;
let keyboardVisible = preferences.keyboardVisible !== false, lastKeyboardPaint = '';
const pressed = new Map();
const noteNames = ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'];
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
function savePreferences() { storage.savePreferences({mode, speed, sound:audio.enabled, keyboardVisible}); }
function controls() {
  $('play-button').disabled = busy || !engine || starting;
  $('restart-button').disabled = busy || !engine;
  $('song-select').disabled = busy || libraryLoading;
  $('refresh-library').disabled = busy || libraryLoading;
  $('upload-button').disabled = uploading;
  $('url-button').disabled = uploading;
  $('delete-song').disabled = busy || libraryLoading || deleting || uploading || !songChoice(selectedId) || !!songChoice(selectedId)?.pendingPublication;
  $('tempo').disabled = busy || playing;
  const limits = sourceModel ? transposeLimits(sourceModel) : {min:0, max:0};
  $('transpose-down').disabled = busy || libraryLoading || !sourceModel || transposeOffset <= limits.min;
  $('transpose-up').disabled = busy || libraryLoading || !sourceModel || transposeOffset >= limits.max;
  const offsetLabel = `${transposeOffset > 0 ? '+' : ''}${transposeOffset}`;
  $('transpose-value').value = offsetLabel;
  $('transpose-value').title = `${offsetLabel} semitones`;
  $('transpose-value').setAttribute('aria-label', `Transpose: ${offsetLabel} semitones`);
  const finished = engine?.complete && (mode === 'wait' || elapsed >= totalSeconds + .2);
  const playLabel = starting ? 'Starting…' : playing ? 'Pause' : finished ? 'Play again' : 'Play';
  const playIcon = starting ? '…' : playing ? 'Ⅱ' : '▶';
  $('play-button').innerHTML = `<span class="button-icon" aria-hidden="true">${playIcon}</span><span class="button-label">${playLabel}</span>`;
  $('play-button').setAttribute('aria-label', playLabel);
  $('play-button').title = playLabel;
}
function songChoice(id) {
  return songChoices.find(song => song.id === (songAliases.get(id) || id));
}
async function refreshLibrary() {
  const choices = await visibleSongChoices(songs.values());
  songChoices = choices.songs;
  songAliases = choices.aliases;
  $('song-select').replaceChildren();
  const labelFor = song => `${song.composer ? song.composer + ' — ' : ''}${song.title}`;
  const labelCounts = new Map();
  for (const song of songChoices) labelCounts.set(labelFor(song), (labelCounts.get(labelFor(song)) || 0) + 1);
  const uploadNumbers = new Map();
  for (const song of songChoices) {
    const option = document.createElement('option');
    option.value = song.id;
    const baseLabel = labelFor(song);
    const isDuplicate = labelCounts.get(baseLabel) > 1;
    if (song.id !== DEFAULT_ID) uploadNumbers.set(baseLabel, (uploadNumbers.get(baseLabel) || 0) + 1);
    const version = song.id === DEFAULT_ID ? 'Piano' : `Upload ${uploadNumbers.get(baseLabel)}`;
    option.textContent = `${baseLabel}${isDuplicate ? ` · ${version}` : ''}${song.pendingPublication ? ' · Publishing…' : song.localOnly ? ' · Device-only copy' : ''}`;
    $('song-select').append(option);
  }
  const selected = songChoice(selectedId);
  if (selected) {
    // A newly published copy replaces its local selector entry without resetting practice.
    if (selected.id !== selectedId) {
      selectedId = selected.id;
      storage.select(selectedId);
      $('local-recovery').hidden = !selected.localOnly;
    }
    $('song-select').value = selectedId;
  } else if (!songChoices.length) {
    selectedId = null;
    $('song-select').replaceChildren(new Option('No songs', ''));
  }
}
function showEmptyLibrary() {
  pause('No songs');
  model = sourceModel = engine = null;
  selectedId = null;
  renderer.osmd?.dispose?.();
  renderer.osmd = null;
  renderer.container.replaceChildren();
  renderer.systems = [];
  $('score').hidden = true;
  $('empty-score').hidden = false;
  $('empty-title').textContent = 'No songs';
  $('empty-description').textContent = 'Upload a score to start.';
  $('hit-count').textContent = '0'; $('miss-count').textContent = '0'; $('progress-count').textContent = '0 / 0';
  $('progress-fill').style.width = '0%';
  drawKeyboard(); controls();
}
function libraryNotice(message = '', error = false, {temporary = false} = {}) {
  clearTimeout(libraryNoticeTimer);
  $('library-message').textContent = message;
  $('library-message').hidden = !message;
  $('library-message').classList.toggle('error', error);
  if (temporary && message) libraryNoticeTimer = setTimeout(() => libraryNotice(), 2500);
}
async function refreshSharedLibrary({announce = false} = {}) {
  if (libraryLoading || busy) return false;
  libraryLoading = true; controls();
  try {
    const catalog = await loadSongLibrary({deployedCatalogUrl:new URL('./song-library.json', document.baseURI).href});
    const localSongs = [...songs.values()].filter(song => song.localOnly || song.pendingPublication);
    const previousSong = songs.get(selectedId);
    songs.clear();
    for (const song of catalog.songs) if (!pendingDeletes.has(song.id)) songs.set(song.id, song);
    for (const song of localSongs) songs.set(song.id, song);
    if (previousSong && !pendingDeletes.has(previousSong.id) && !songs.has(previousSong.id)) songs.set(previousSong.id, previousSong);
    librarySource = catalog.source;
    await refreshLibrary();
    if (selectedId && !songChoice(selectedId)) await selectSong(songChoice(catalog.defaultSongId) || songChoices[0]);
    if (!songChoices.length) showEmptyLibrary();
    if (catalog.importErrors?.length) {
      console.warn('Song upload errors:', catalog.importErrors);
      const filenames = catalog.importErrors.slice(0, 3).map(issue => issue.sourceFilename).join(', ');
      const remaining = catalog.importErrors.length > 3 ? ` and ${catalog.importErrors.length - 3} more` : '';
      libraryNotice(`Could not import ${filenames}${remaining}. Check the files and try again.`, true);
    } else libraryNotice(announce ? 'Refreshed.' : '', false, {temporary:announce});
    return true;
  } catch (error) {
    console.warn('Song library refresh failed:', error);
    libraryNotice('Songs could not be refreshed. Check your connection and try again.', true);
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
  // Releases can fall between score onsets, so keyboard feedback updates every frame.
  highlightKeys(state);
}
function completionText() {
  const state = engine.snapshot();
  return `Finished${state.wrong ? ` · ${state.wrong} extra note${state.wrong === 1 ? '' : 's'}` : ''}`;
}
function pause(message = 'Paused') {
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
  paint(true); controls();
  setStatus('Ready');
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
    setStatus(String(remaining));
  } else if (elapsed >= totalSeconds + .2) {
    pause(completionText());
    return;
  } else {
    setStatus('Playing');
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
  try { await audio.unlock(); } catch (error) {
    console.warn('Piano audio could not start:', error);
    notice('Sound unavailable. Practice can continue silently.');
  }
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
    setStatus('Playing');
    paint();
  }
  controls();
}

function scoreErrorMessage(error) {
  if (error.code === 'TRANSPOSED_INSTRUMENT') return 'Export this score at concert pitch and try again.';
  if (error.code === 'UNPITCHED_SCORE') return 'Choose a piano or melody part with pitched notes.';
  if (error.code === 'MICROTONAL_SCORE') return 'This score uses pitches a standard piano cannot play.';
  if (error.code === 'EMPTY_SCORE') return 'This score has no playable notes.';
  if (['UNMATCHED_TIE', 'AMBIGUOUS_TIE', 'UNFINISHED_TIE'].includes(error.code)) return 'This score has incomplete or ambiguous ties. Try another MusicXML export.';
  if (error.code === 'PITCH_RANGE') return 'This score includes notes outside the MIDI range.';
  if (error.code) return 'This score could not be read. Try another MusicXML export.';
  if (error.message?.includes('could not fit')) return 'This score could not fit the sheet music window on this screen.';
  if (error.message?.includes('Cannot match')) return 'This score has notes the display could not match.';
  if (error.cause?.some?.(reason => /timed out/i.test(reason))) return 'The score download timed out. Check your connection and try selecting it again.';
  if (error.cause?.some?.(reason => /does not yet match/i.test(reason))) return 'The uploaded score is still publishing. Refresh the song list in a moment.';
  if (error.message?.includes('renderer has not loaded')) return 'The sheet music renderer did not load. Reload this page.';
  return 'The score could not be opened. Try selecting it again.';
}
async function selectSong(song, {preparedModel = null, remember = true} = {}) {
  if (!song || busy) return false;
  busy = true;
  const previous = {model, sourceModel, transposeOffset, engine, selectedId};
  pause('Loading score…'); controls(); notice(); libraryNotice();
  try {
    {
      let xml = song.xml;
      if (!xml) {
        const loaded = await loadSongScore(song);
        xml = loaded.xml;
      }
      const candidate = preparedModel || parseMusicXML(xml);
      $('score').hidden = false; $('empty-score').hidden = true;
      const rendered = await renderer.load(candidate);
      model = candidate;
      sourceModel = candidate;
      transposeOffset = 0;
      pressed.clear();
      configureEngine();
      drawKeyboard();
      $('local-recovery').hidden = !song.localOnly;
      if (rendered.warnings?.length) console.warn('Score rendering details:', rendered.warnings);
      paint(true);
      setStatus('Ready');
    }
    selectedId = song.id;
    $('song-select').value = selectedId;
    if (remember) storage.select(selectedId);
    return true;
  } catch (error) {
    console.warn('Score selection failed:', error);
    model = previous.model; sourceModel = previous.sourceModel; transposeOffset = previous.transposeOffset;
    engine = previous.engine; selectedId = previous.selectedId;
    if (model) {
      try { await renderer.load(model); paint(true); } catch (_) { engine = null; }
    } else {
      $('score').hidden = true; $('empty-score').hidden = false;
      $('empty-title').textContent = 'Score unavailable';
      $('empty-description').textContent = 'Refresh or choose another song.';
    }
    if (selectedId) $('song-select').value = selectedId;
    const message = scoreErrorMessage(error);
    const attempted = song.sourceFilename || song.title || 'Selected song';
    libraryNotice(`${attempted} did not load: ${message}${engine ? ' The previous score is still displayed.' : ''}`, true);
    notice(message, true);
    setStatus(engine ? 'Previous score kept' : 'Score unavailable');
    return false;
  } finally { busy = false; controls(); highlightKeys(); }
}

async function transposeBy(semitones) {
  if (busy || libraryLoading || !sourceModel || !engine) return false;
  const nextOffset = transposeOffset + semitones;
  const limits = transposeLimits(sourceModel);
  if (!Number.isInteger(nextOffset) || nextOffset < limits.min || nextOffset > limits.max) return false;
  busy = true;
  pause('Changing pitch…'); controls(); notice();
  try {
    // Always derive from the original score, so repeated arrows never accumulate
    // altered spellings or modify the repository/local-recovery source.
    const candidate = transposeScore(sourceModel, nextOffset);
    const rendered = await renderer.load(candidate);
    model = candidate;
    transposeOffset = nextOffset;
    pressed.clear();
    configureEngine();
    drawKeyboard();
    resetSession();
    if (rendered.warnings?.length) console.warn('Score rendering details:', rendered.warnings);
    return true;
  } catch (error) {
    console.warn('Score transposition failed:', error);
    // Renderer.load keeps its previous score intact when the candidate cannot
    // be engraved. The offset/model are committed only after that succeeds.
    setStatus(error.message || 'Pitch could not be changed');
    return false;
  } finally { busy = false; controls(); paint(true); }
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
  libraryNotice('Downloaded.', false, {temporary:true});
}

function strike(midi, source, sound = false) {
  if (pressed.has(source)) return;
  pressed.set(source, midi);
  highlightKeys();
  if (sound && audio.enabled) {
    // Grade the input immediately; resuming an audio device must not add latency.
    const generation = startGeneration;
    const requestedModel = model;
    audio.unlock().then(() => {
      if (generation === startGeneration && requestedModel === model) audio.note(midi);
    }).catch(() => {});
  }
  if (!playing || !engine || busy) return;
  const position = mode === 'timed' ? audio.time - anchor : 0;
  const result = engine.grade(midi, position);
  paint();
  if (mode === 'wait') {
    if (result.complete) pause(completionText());
    else if (result.outcome === 'wrong') setStatus('Wrong note');
    else if (result.outcome === 'hit') setStatus(result.advanced ? 'Playing' : 'Complete the chord');
  }
}
function release(source) { pressed.delete(source); highlightKeys(); }
function highlightKeys(state = engine?.snapshot()) {
  const down = new Set(pressed.values());
  const sounding = playing && mode === 'timed' && !busy ? playingPitchesAt(audioNotes, elapsed) : new Set();
  const targets = mode === 'wait' && !busy ? new Set(state?.requiredPitches || []) : new Set();
  const signature = `${[...down].sort().join(',')}|${[...sounding].sort().join(',')}|${[...targets].sort().join(',')}`;
  if (signature === lastKeyboardPaint) return;
  lastKeyboardPaint = signature;
  $('keyboard').querySelectorAll('[data-midi]').forEach(key => {
    const midi = Number(key.dataset.midi);
    key.classList.toggle('active', down.has(midi));
    key.classList.toggle('playing', sounding.has(midi));
    key.classList.toggle('current', targets.has(midi));
  });
}
function drawKeyboard() {
  $('keyboard').replaceChildren();
  const layout = keyboardLayout(model?.attacks);
  $('keyboard').style.setProperty('--keyboard-units', layout.units || 1);
  $('keyboard').dataset.whiteCount = layout.whiteCount;
  $('keyboard').classList.toggle('dense', layout.whiteCount > 21);
  for (const {midi, black, left, width} of layout.keys) {
    const key = document.createElement('button');
    key.type = 'button'; key.className = `piano-key ${black ? 'black' : 'white'}`;
    key.dataset.midi = midi; key.setAttribute('aria-label', `Play ${midiName(midi)}`);
    key.style.left = `${left * 100}%`;
    key.style.width = `${width * 100}%`;
    const label = document.createElement('span'); label.className = 'note-name'; label.textContent = midiName(midi);
    label.classList.toggle('octave-label', midi % 12 === 0);
    label.classList.toggle('range-label', midi === layout.min || midi === layout.max);
    key.append(label);
    key.title = midiName(midi);
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
  lastKeyboardPaint = '';
  highlightKeys();
}
function showKeyboard(visible) {
  keyboardVisible = visible;
  $('keyboard-panel').hidden = !visible;
  $('keyboard-toggle').textContent = visible ? 'Hide keyboard' : 'Show keyboard';
  $('keyboard-toggle').setAttribute('aria-expanded', String(visible));
  if (visible) highlightKeys();
}
async function connectMidi() {
  if (!navigator.requestMIDIAccess) {
    $('midi-status').textContent = 'MIDI unavailable in this browser.';
    return;
  }
  let midiStage = 'access';
  try {
    $('midi-status').textContent = 'Requesting MIDI access…';
    midiAccess = await navigator.requestMIDIAccess({sysex:false});
    midiStage = 'setup';
    midiAccess.onstatechange = refreshMidi;
    refreshMidi();
  } catch (error) {
    $('midi-dot').classList.remove('connected');
    $('midi-status').textContent = window.PracticeMIDI?.reportFailure?.(error, midiStage) ||
      `MIDI ${midiStage} failed: ${error?.message || error}`;
  }
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
  $('midi-status').textContent = devices.length ? `Connected: ${devices.map(device => device.name || 'MIDI keyboard').join(', ')}` : 'No MIDI keyboard connected.';
  if (devices.length) { try { window.PracticeMIDI?.setEnabled(true); } catch (_) {} }
}

const PENDING_UPLOAD_KEY = 'piano-pending-github-upload-v1';
function pendingUpload() { try { return sessionStorage.getItem(PENDING_UPLOAD_KEY); } catch (_) { return null; } }
function savePendingUpload(digest) { try { if (digest) sessionStorage.setItem(PENDING_UPLOAD_KEY, digest); else sessionStorage.removeItem(PENDING_UPLOAD_KEY); } catch (_) {} }
function watchPublishedUpload(digest, attempts = 0) {
  clearTimeout(pendingUploadTimer);
  if (!digest) return;
  libraryNotice('Saved to GitHub. Publishing to the song list…');
  pendingUploadTimer = setTimeout(async () => {
    if (busy || libraryLoading) return watchPublishedUpload(digest, attempts);
    await refreshSharedLibrary();
    const published = songChoices.find(song => song.repositorySaved && song.sourceSha256 === digest);
    if (published) {
      savePendingUpload(null);
      songs.delete(`pending-${digest}`);
      await refreshLibrary();
      libraryNotice('Upload ready.', false, {temporary:true});
      await selectSong(published);
      return;
    }
    if (attempts >= 23) {
      libraryNotice('Saved to GitHub. Publishing is taking longer than expected; use Refresh later.');
      return;
    }
    watchPublishedUpload(digest, attempts + 1);
  }, 10000);
}
function uploadStatus(message = '', error = false) {
  $('upload-status').textContent = message;
  $('upload-status').classList.toggle('error', error);
}
function fillCredential(dialog) {
  const saved = githubCredentials.get();
  $(`${dialog}-token`).value = saved;
  $(`${dialog}-remember`).checked = !!saved;
  const section = $(`${dialog}-credentials`);
  if (section) section.open = !saved;
}
function commitCredential(dialog, token) {
  if ($(`${dialog}-remember`).checked) {
    if (!githubCredentials.save(token)) libraryNotice('Could not remember credentials on this device.', true);
  } else githubCredentials.forget();
}
document.querySelectorAll('.credential-forget').forEach(button => button.addEventListener('click', () => {
  githubCredentials.forget();
  for (const dialog of ['upload', 'url', 'delete']) {
    $(`${dialog}-token`).value = '';
    $(`${dialog}-remember`).checked = false;
    const section = $(`${dialog}-credentials`);
    if (section) section.open = true;
  }
}));
async function saveScore(file, dialog, reportStatus) {
  reportStatus('Checking score…');
  const xml = await readScoreFile(file);
  const parsed = parseMusicXML(xml);
  reportStatus('Saving original file to GitHub…');
  const token = $(`${dialog}-token`).value;
  const uploaded = await uploadScoreToGitHub(file, token);
  commitCredential(dialog, token);
  $(`${dialog}-token`).value = '';
  savePendingUpload(uploaded.digest);
  $(`${dialog}-dialog`).close();
  const pendingSong = {
    id:`pending-${uploaded.digest}`, title:parsed.title || file.name,
    composer:parsed.composer || '', sourceFilename:file.name, sourceSha256:uploaded.digest,
    xml, repositorySaved:false, pendingPublication:true,
  };
  songs.set(pendingSong.id, pendingSong);
  await refreshLibrary();
  await selectSong(pendingSong, {preparedModel:parsed});
  watchPublishedUpload(uploaded.digest);
}
function closeUploadDialog() {
  if (uploading) return;
  $('upload-token').value = '';
  $('upload-dialog').close();
}
for (const id of ['upload-button', 'empty-upload']) {
  $(id).addEventListener('click', () => {
    if (playing || starting) pause();
    uploadStatus();
    fillCredential('upload');
    $('upload-dialog').showModal();
  });
}
$('upload-close').addEventListener('click', closeUploadDialog);
$('upload-cancel').addEventListener('click', closeUploadDialog);
$('upload-dialog').addEventListener('cancel', event => {
  if (uploading) event.preventDefault();
  else $('upload-token').value = '';
});
$('upload-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (uploading) return;
  const file = $('upload-file').files?.[0];
  if (!file) return uploadStatus('Choose a score file.', true);
  uploading = true;
  $('upload-submit').disabled = true;
  $('upload-cancel').disabled = true;
  $('upload-close').disabled = true;
  controls();
  try {
    await saveScore(file, 'upload', uploadStatus);
    $('upload-file').value = '';
  } catch (error) {
    uploadStatus(error.message || 'Upload failed.', true);
  } finally {
    uploading = false;
    $('upload-submit').disabled = false;
    $('upload-cancel').disabled = false;
    $('upload-close').disabled = false;
    controls();
  }
});
const urlStatus = (message = '', error = false) => {
  $('url-status').textContent = message;
  $('url-status').classList.toggle('error', error);
};
function closeUrlDialog() {
  if (uploading) return;
  $('url-token').value = '';
  $('url-dialog').close();
}
$('url-button').addEventListener('click', () => {
  if (playing || starting) pause();
  urlStatus();
  fillCredential('url');
  $('url-dialog').showModal();
});
$('url-close').addEventListener('click', closeUrlDialog);
$('url-cancel').addEventListener('click', closeUrlDialog);
$('url-dialog').addEventListener('cancel', event => {
  if (uploading) event.preventDefault();
  else $('url-token').value = '';
});
$('url-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (uploading) return;
  let url;
  try { url = new URL($('score-url').value.trim()); }
  catch (_) { return urlStatus('Enter a valid score URL.', true); }
  if (url.protocol !== 'https:') return urlStatus('Use an HTTPS score URL.', true);
  if (/(^|\.)musescore\.com$/i.test(url.hostname)) {
    return urlStatus('MuseScore page links cannot be imported directly. Download MusicXML from MuseScore, then use Upload.', true);
  }
  const extension = url.pathname.match(/\.(musicxml|xml|mxl)$/i)?.[1]?.toLowerCase();
  if (!extension) return urlStatus('The URL must point directly to a .musicxml, .xml or .mxl file.', true);
  uploading = true;
  for (const id of ['url-submit', 'url-close', 'url-cancel']) $(id).disabled = true;
  controls();
  try {
    urlStatus('Downloading score…');
    const response = await fetch(url.href, {credentials:'omit', cache:'no-store'});
    if (!response.ok) throw new Error(`The score server returned HTTP ${response.status}.`);
    if (Number(response.headers.get('content-length')) > 20 * 1024 * 1024) throw new Error('The score exceeds 20 MB.');
    const blob = await response.blob();
    if (!blob.size || blob.size > 20 * 1024 * 1024) throw new Error('The score must be between 1 byte and 20 MB.');
    const file = new File([blob], decodeURIComponent(url.pathname.split('/').pop()), {type:blob.type});
    await saveScore(file, 'url', urlStatus);
    $('score-url').value = '';
  } catch (error) {
    urlStatus(error instanceof TypeError ? 'The source blocked direct downloading. Download the file there, then use Upload.' : error.message || 'Import failed.', true);
  } finally {
    uploading = false;
    for (const id of ['url-submit', 'url-close', 'url-cancel']) $(id).disabled = false;
    controls();
  }
});
const deleteStatus = (message = '', error = false) => {
  $('delete-status').textContent = message;
  $('delete-status').classList.toggle('error', error);
};
function watchPublishedDeletion(id, attempts = 0) {
  clearTimeout(pendingDeleteTimers.get(id));
  pendingDeleteTimers.set(id, setTimeout(async () => {
    if (busy || libraryLoading || deleting) return watchPublishedDeletion(id, attempts);
    try {
      const catalog = await loadSongLibrary({deployedCatalogUrl:new URL('./song-library.json', document.baseURI).href});
      if (!catalog.songs.some(song => song.id === id)) {
        pendingDeletes.delete(id);
        rememberPendingDeletes();
        libraryNotice('Song deleted.', false, {temporary:true});
        await refreshSharedLibrary();
        return;
      }
    } catch (_) { /* The publish may still be in progress. */ }
    if (attempts >= 29) return libraryNotice('Deleted in GitHub. The song list is still publishing; refresh later.');
    watchPublishedDeletion(id, attempts + 1);
  }, 10000));
}
$('delete-song').addEventListener('click', () => {
  const song = songChoice(selectedId);
  if (!song || busy || deleting || song.pendingPublication) return;
  if (playing || starting) pause();
  const label = [...$('song-select').options].find(option => option.value === song.id)?.textContent || song.title;
  $('delete-description').textContent = song.localOnly
    ? `Delete “${label}” from this device?`
    : `Delete “${label}” from the song list?`;
  fillCredential('delete');
  $('delete-credentials').hidden = !!song.localOnly;
  $('delete-token').required = !song.localOnly;
  deleteStatus();
  $('delete-dialog').showModal();
});
$('delete-cancel').addEventListener('click', () => {
  if (deleting) return;
  $('delete-token').value = '';
  $('delete-dialog').close();
});
$('delete-dialog').addEventListener('cancel', event => {
  if (deleting) event.preventDefault();
  else $('delete-token').value = '';
});
$('delete-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (deleting) return;
  const song = songChoice(selectedId);
  if (!song) return deleteStatus('Select a song first.', true);
  deleting = true;
  $('delete-confirm').disabled = $('delete-cancel').disabled = true;
  controls();
  try {
    deleteStatus('Deleting…');
    if (song.localOnly) await storage.delete(song.legacyId);
    else {
      const token = $('delete-token').value;
      await deleteSongFromGitHub(song, token);
      commitCredential('delete', token);
    }
    $('delete-token').value = '';
    $('delete-dialog').close();
    if (!song.localOnly) { pendingDeletes.add(song.id); rememberPendingDeletes(); }
    songs.delete(song.id);
    await refreshLibrary();
    if (selectedId === song.id) {
      const replacement = songChoices[0];
      if (replacement) await selectSong(replacement);
      else showEmptyLibrary();
    }
    libraryNotice(song.localOnly ? 'Song deleted.' : 'Deleted in GitHub. Updating song list…');
    if (!song.localOnly) watchPublishedDeletion(song.id);
  } catch (error) {
    deleteStatus(error.message || 'Deletion failed.', true);
  } finally {
    deleting = false;
    $('delete-confirm').disabled = $('delete-cancel').disabled = false;
    controls();
  }
});
$('refresh-library').addEventListener('click', () => refreshSharedLibrary({announce:true}));
$('download-local-score').addEventListener('click', downloadLocalScore);
$('song-select').addEventListener('change', event => selectSong(songChoice(event.target.value)));
$('play-button').addEventListener('click', () => playing ? pause() : start());
$('restart-button').addEventListener('click', () => { const resume = playing; resetSession(); if (resume) start(); });
$('transpose-down').addEventListener('click', () => transposeBy(-1));
$('transpose-up').addEventListener('click', () => transposeBy(1));
$('midi-button').addEventListener('click', connectMidi);
$('keyboard-toggle').addEventListener('click', () => { showKeyboard(!keyboardVisible); savePreferences(); });
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
window.addEventListener('blur', () => { pressed.clear(); highlightKeys(); if (playing || starting) pause('Paused — window inactive'); });
document.addEventListener('visibilitychange', () => { if (document.hidden && (playing || starting)) pause('Paused — page hidden'); });

document.querySelector(`input[name="lesson-mode"][value="${mode}"]`).checked = true;
$('tempo').value = Math.round(speed * 100); $('tempo-label').textContent = `${Math.round(speed * 100)}%`;
$('sound-enabled').checked = preferences.sound !== false; audio.setEnabled($('sound-enabled').checked);
showKeyboard(keyboardVisible);
let localRecoveryFailed = false;
try {
  for (const song of await storage.list()) if (song.id && typeof song.xml === 'string') {
    const localSong = {...song, id:`local-${song.id}`, legacyId:song.id, localOnly:true, repositorySaved:false, needsScore:false};
    songs.set(localSong.id, localSong);
  }
} catch (error) {
  console.warn('Local score recovery failed:', error);
  localRecoveryFailed = true;
}
await refreshSharedLibrary();
await refreshLibrary(); drawKeyboard();
const remembered = storage.lastSelection();
await selectSong(songChoice(remembered) || songChoice(`local-${remembered}`) || songChoice(DEFAULT_ID) || songChoices[0]);
if (!songChoices.length) showEmptyLibrary();
if (pendingUpload()) watchPublishedUpload(pendingUpload());
for (const id of pendingDeletes) watchPublishedDeletion(id);
if (localRecoveryFailed && $('import-message').hidden) notice('Device-only scores could not be read.', true);
try { window.PracticeTracker?.recordOpen('learning-songs'); } catch (_) {}
try { if (window.PracticeMIDI?.isEnabled()) connectMidi(); } catch (_) {}

// A read-only snapshot makes regressions inspectable without synthesizing MIDI.
window.PianoSongLesson = Object.freeze({
  getSnapshot: () => ({selectedId, mode, playing, elapsed, speed, keyboardVisible, transpose:transposeOffset,
    songCount:songChoices.length, storagePersistent:storage.persistent, librarySource,
    model:model ? {title:model.title, parts:model.parts.length, notes:model.notes.length, attacks:model.attacks.length, duration:model.duration, warnings:[...model.warnings]} : null,
    lesson:engine ? {...engine.snapshot(), statuses:Object.fromEntries(engine.statuses)} : null})
});
