const ALPHATAB_ROOT = 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/';
const RECIPES = {conversation: {title: 'Fracture Dialogue', tempo: 142}, flow: {title: 'Open Orbit', tempo: 132}, chords: {title: 'Glass Counterweight', tempo: 148}};
const INTERVALS = ['1','♭2','2','♭3','3','4','♭5','5','♭6','6','♭7','7'];
export function fraction(value) { const [a, b = '1'] = String(value).split('/'); return Number(a) / Number(b); }

// Adapt the composer's written score without selecting or changing any notes.
export function toNativeScore(at, source, title = 'Drop E riff') {
  const m = at.model, score = new m.Score();
  score.title = title; score.artist = 'Original Drop E composition';
  const track = new m.Track(); score.addTrack(track); track.name = 'Drop E 8 string';
  track.playbackInfo.program = 30;
  const staff = new m.Staff(); track.addStaff(staff);
  staff.stringTuning.tunings = [...source.tuning_high_to_low];
  staff.showStandardNotation = false; staff.showTablature = true;
  for (const [barIndex, sourceBar] of source.bars.entries()) {
    const master = new m.MasterBar();
    master.timeSignatureNumerator = source.meter[0]; master.timeSignatureDenominator = source.meter[1];
    if (!barIndex) master.tempoAutomations.push(m.Automation.buildTempoAutomation(false, 0, source.tempo, 2));
    score.addMasterBar(master);
    const bar = new m.Bar(); staff.addBar(bar); const voice = new m.Voice(); bar.addVoice(voice);
    for (const sourceBeat of sourceBar) {
      const beat = new m.Beat(); voice.addBeat(beat);
      beat.duration = sourceBeat.type; beat.dots = sourceBeat.dots || 0; beat.isEmpty = false;
      beat.dynamics = m.DynamicValue[(sourceBeat.velocity || 'mf').toUpperCase()];
      for (const sourceNote of sourceBeat.notes) {
        const note = new m.Note();
        note.string = source.tuning_high_to_low.length - sourceNote.string;
        note.fret = sourceNote.fret;
        note.isPalmMute = Boolean(sourceBeat.palmMute);
        note.isHammerPullOrigin = Boolean(sourceNote.hp);
        note.accentuated = sourceNote.accentuated || 0;
        note.dynamics = beat.dynamics;
        beat.addNote(note);
      }
    }
  }
  score.finish(new at.Settings());
  return score;
}

function loadAlphaTab() {
  if (window.alphaTab) return Promise.resolve(window.alphaTab);
  return new Promise((resolve, reject) => {
    const script = document.createElement('script'); script.src = `${ALPHATAB_ROOT}alphaTab.min.js`;
    script.onload = () => window.alphaTab ? resolve(window.alphaTab) : reject(new Error('Player did not initialize.'));
    script.onerror = () => reject(new Error('Could not load the guitar player. Check your connection and Generate again.'));
    document.head.append(script);
  });
}

export function mountBuilder() {
  const $ = id => document.getElementById(id);
  let recipe = 'conversation', version = 'baseline', result = null, api = null, at = null;
  let worker = null, requestId = 0, busy = false, ready = false, playing = false, speed = 1, q = 0, playerPromise = null;
  let timeout = null, changedIds = new Set(), activeCells = new Map(), labelCells = [], scoreLoad = 0;
  const status = (message, error = false) => { $('status').textContent = message; $('status').classList.toggle('error', error); };
  function transport() {
    $('play').disabled = busy || !ready; $('stop').disabled = busy || !ready;
    $('play').textContent = playing ? '❚❚ Pause' : '▶ Play';
    $('download').disabled = busy || !result; $('seek').disabled = busy || !ready;
    for (const button of $('versions').querySelectorAll('button')) button.disabled = busy || !result;
  }
  function setBusy(value) {
    busy = value; document.body.setAttribute('aria-busy', String(value));
    $('generate').disabled = value; $('generate').textContent = value ? 'Generating…' : 'Generate riff';
    $('tempo').disabled = value;
    for (const button of $('recipes').querySelectorAll('button')) button.disabled = value;
    transport();
  }
  function fail(error) {
    clearTimeout(timeout); setBusy(false); ready = false; transport();
    status(error?.message || String(error), true);
  }
  function updatePosition(value) {
    q = Math.max(0, Math.min(32, value)); $('seek').value = String(q);
    $('position').textContent = `Bar ${Math.min(8, Math.floor(q / 4) + 1)} / 8`;
    drawActive();
  }
  function createFretboard() {
    const board = $('fretboard'); board.replaceChildren(); activeCells = new Map(); labelCells = [];
    const blank = document.createElement('div'); board.append(blank);
    for (let fret = 1; fret <= 24; fret++) { const cell = document.createElement('div'); cell.className = 'fret-number'; cell.textContent = fret; board.append(cell); }
    const score = result[version];
    for (let string = 0; string < 8; string++) {
      const label = document.createElement('div'); label.className = 'string-label';
      label.textContent = INTERVALS[(score.tuning_high_to_low[string] - 4 + 120) % 12];
      label.title = 'Open string interval relative to E'; board.append(label); labelCells.push(label);
      for (let fret = 1; fret <= 24; fret++) {
        const cell = document.createElement('div'); cell.className = 'cell';
        const marker = document.createElement('span'); marker.className = 'marker';
        marker.textContent = INTERVALS[(score.tuning_high_to_low[string] + fret - 4 + 120) % 12];
        cell.title = `Fret ${fret} · ${marker.textContent}`; cell.append(marker); board.append(cell); activeCells.set(`${string}:${fret}`, cell);
      }
    }
    for (const note of score.notes) {
      const cell = activeCells.get(`${note.string}:${note.fret}`); if (!cell) continue;
      cell.classList.add('used'); if (version === 'variation' && changedIds.has(note.id)) {cell.classList.add('changed'); cell.dataset.changed = 'true';}
    }
    drawActive();
  }
  function drawActive() {
    if (!result) return;
    for (const cell of activeCells.values()) {cell.classList.remove('active'); cell.classList.toggle('changed', cell.dataset.changed === 'true');}
    for (const cell of labelCells) cell.classList.remove('open');
    for (const note of result[version].notes) {
      const start = fraction(note.onset_q), end = start + fraction(note.duration_q);
      if (q < start || q >= end || q >= 32) continue;
      if (note.fret === 0) labelCells[note.string]?.classList.add('open');
      else {const cell = activeCells.get(`${note.string}:${note.fret}`); if (cell) {cell.classList.add('active'); cell.classList.toggle('changed', version === 'variation' && changedIds.has(note.id));}}
    }
  }
  async function ensurePlayer() {
    if (api) return;
    if (playerPromise) return playerPromise;
    playerPromise = (async () => {
    at = await loadAlphaTab();
    api = new at.AlphaTabApi($('score'), {
      core: {scriptFile: `${ALPHATAB_ROOT}alphaTab.min.js`, fontDirectory: `${ALPHATAB_ROOT}font/`},
      display: {scale: 0.8},
      player: {playerMode: 'enabledSynthesizer', outputMode: 'webAudioScriptProcessor', soundFont: `${ALPHATAB_ROOT}soundfont/sonivox.sf2`, enableCursor: true, enableUserInteraction: false, scrollMode: 'off'}
    });
    api.error.on(fail);
    api.scoreLoaded.on(() => {ready = false; transport();});
    api.playerReady.on(() => {ready = true; api.playbackSpeed = speed; transport(); status('Ready. Press Play.');});
    api.playerStateChanged.on(args => {playing = args.state === 1; transport();});
    api.playerPositionChanged.on(args => updatePosition(Number(args.currentTick || 0) / 960));
    })().catch(error => {playerPromise = null; throw error;});
    return playerPromise;
  }
  async function showVersion() {
    const load = ++scoreLoad;
    ready = false; playing = false; api?.stop(); transport();
    for (const button of $('versions').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.version === version));
    updatePosition(0); createFretboard();
    const changed = result.changes?.changed || {};
    $('changes').textContent = version === 'baseline' ? 'Original composed riff. Switch to Developed return to compare.' : `${(changed.pitch || []).length} pitches · ${(changed.onset_q || []).length} starts · ${(changed.duration_q || []).length} holds changed. Green marks changed notes.`;
    status('Loading guitar sound…');
    try {
      await ensurePlayer(); if (load !== scoreLoad) return;
      api.load(toNativeScore(at, result[version], `${result.title} — ${version === 'baseline' ? 'Original' : 'Developed return'}`));
      api.playbackSpeed = speed;
    } catch (error) {fail(error);}
  }
  function getWorker() {
    if (worker) return worker;
    worker = new Worker(new URL('./riff-builder-worker.js', import.meta.url), {type: 'module'});
    worker.onerror = error => {worker?.terminate(); worker = null; fail(new Error(error.message || 'Composer could not start. Try Generate again.'));};
    worker.onmessage = async ({data}) => {
      if (data.id !== requestId) return;
      if (data.type === 'status') status(data.message);
      if (data.type === 'error') fail(new Error(data.message));
      if (data.type === 'result') {
        clearTimeout(timeout); result = data.result; version = 'baseline';
        changedIds = new Set(Object.values(result.changes?.changed || {}).flat());
        $('result').hidden = false; $('result-title').textContent = `${result.title} · ${result.tempo} BPM`;
        setBusy(false); await showVersion();
      }
    };
    return worker;
  }
  $('recipes').addEventListener('click', event => {
    const button = event.target.closest('[data-recipe]'); if (!button || busy) return;
    recipe = button.dataset.recipe; $('tempo').value = RECIPES[recipe].tempo;
    for (const item of $('recipes').querySelectorAll('button')) item.setAttribute('aria-pressed', String(item === button));
    status('Recipe selected. Generate to apply it.');
  });
  $('generate').addEventListener('click', () => {
    const tempo = Number($('tempo').value);
    if (!Number.isInteger(tempo) || tempo < 80 || tempo > 200) {status('Choose a whole-number tempo from 80 to 200 BPM.', true); $('tempo').focus(); return;}
    api?.stop(); ready = false; playing = false; setBusy(true); requestId++;
    status('Starting composer…');
    timeout = setTimeout(() => {worker?.terminate(); worker = null; requestId++; fail(new Error('Composer took too long to load. Check your connection and try again.'));}, 180000);
    getWorker().postMessage({id: requestId, recipe, tempo, assetBase: new URL('riff-builder/', document.baseURI).href});
  });
  $('versions').addEventListener('click', event => {const button = event.target.closest('[data-version]'); if (!button || busy || !result || version === button.dataset.version) return; version = button.dataset.version; showVersion();});
  $('play').addEventListener('click', () => {if (ready && !busy) api.playPause();});
  $('stop').addEventListener('click', () => {api?.stop(); updatePosition(0);});
  $('speeds').addEventListener('click', event => {const button = event.target.closest('[data-speed]'); if (!button) return; speed = Number(button.dataset.speed); if (api) api.playbackSpeed = speed; for (const item of $('speeds').querySelectorAll('button')) item.setAttribute('aria-pressed', String(item === button));});
  $('seek').addEventListener('input', () => {if (api && ready) {api.tickPosition = Number($('seek').value) * 960; updatePosition(Number($('seek').value));}});
  $('download').addEventListener('click', () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'}), url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = `${result.title.toLowerCase().replaceAll(' ', '-')}-${result.tempo}bpm.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  transport();
}
if (typeof document !== 'undefined') mountBuilder();
