import './fretboard-efficiency-view.css';

const INTERVALS = ['1', '♭2', '2', '♭3', '3', '4', '♭5', '5', '♭6', '6', '♭7', '7'];
const PITCHES = ['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B'];
const DROP_E = [64, 59, 55, 50, 45, 40, 35, 28];
const EPS = 1e-8;
const interval = pitch => INTERVALS[((pitch - 4) % 12 + 12) % 12];
const pitchName = pitch => `${PITCHES[pitch % 12]}${Math.floor(pitch / 12) - 1}`;
const seconds = value => `${Number(value).toFixed(2)} s`;
const number = value => Number.isFinite(value) ? Number(value.toFixed(2)).toLocaleString() : '—';

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function prepareFixture(fixture) {
  if (!Array.isArray(fixture.notes) || !fixture.notes.length || !Array.isArray(fixture.versions) ||
      !Number.isFinite(fixture.duration_seconds) || fixture.duration_seconds <= 0) {
    throw new Error('This riff has no complete fingering data.');
  }
  const notes = fixture.notes.map(note => ({...note}));
  const ids = new Set(notes.map(note => String(note.id)));
  if (ids.size !== notes.length) throw new Error('This riff contains repeated note identifiers.');
  const versions = fixture.versions.map(version => {
    const assignments = new Map((version.assignments || []).map(a => [String(a.note_id), a]));
    if (assignments.size !== notes.length || version.assignments.length !== notes.length) {
      throw new Error('A fingering version is missing source note occurrences.');
    }
    const mapped = notes.map(note => {
      const assignment = assignments.get(String(note.id));
      if (!assignment || !Number.isInteger(assignment.string_number) || assignment.string_number < 1 ||
          assignment.string_number > 8 || !Number.isInteger(assignment.fret) || assignment.fret < 0 ||
          assignment.fret > 24 || DROP_E[assignment.string_number - 1] + assignment.fret !== note.pitch ||
          !Number.isFinite(note.start_seconds) || !Number.isFinite(note.end_seconds) ||
          note.start_seconds < 0 || note.end_seconds <= note.start_seconds ||
          note.end_seconds > fixture.duration_seconds + EPS) {
        throw new Error('A note does not match its Drop E string, fret, or source timing.');
      }
      return {...note, ...assignment};
    });
    for (let string = 1; string <= 8; string++) {
      const lane = mapped.filter(note => note.string_number === string).sort((a, b) => a.start_seconds - b.start_seconds);
      for (let i = 1; i < lane.length; i++) {
        if (lane[i].start_seconds < lane[i - 1].end_seconds - EPS) {
          throw new Error('Two sounding note occurrences have been assigned to the same string.');
        }
      }
    }
    return {...version, mapped, positions: [...(version.positions || [])].sort((a, b) => a.time_seconds - b.time_seconds)};
  });
  if (!versions.some(v => v.id === 'optimized') || !versions.some(v => v.id === 'greedy')) {
    throw new Error('Both the efficient mapping and greedy comparison are required.');
  }
  return {...fixture, notes, versions, attacks: [...new Set(notes.map(n => n.start_seconds))].sort((a, b) => a - b)};
}

export function efficiencyFrame(fixture, version, time) {
  const active = version.mapped.filter(note => note.start_seconds <= time + EPS && note.end_seconds > time + EPS);
  const currentPosition = version.positions.filter(position => position.time_seconds <= time + EPS).at(-1);
  const positive = active.filter(note => note.fret > 0).map(note => note.fret);
  const position = Number.isFinite(currentPosition?.position) ? currentPosition.position : (positive.length ? Math.min(...positive) : 1);
  const minimum = Math.max(1, Math.min(position, ...positive));
  const maximum = Math.min(24, Math.max(position + 4, ...positive));
  let firstFret = Math.max(1, minimum - 1);
  let lastFret = Math.min(24, Math.max(firstFret + 5, maximum + 1));
  firstFret = Math.max(1, Math.min(firstFret, lastFret - 5));
  const nextAttack = fixture.attacks.find(attack => attack > time + EPS);
  return {active, currentPosition, position, firstFret, lastFret, nextAttack};
}

export async function mountEfficiencyReview({data: providedData} = {}) {
  const $ = id => document.getElementById(id);
  document.body.classList.add('efficiency-review');
  document.title = 'Drop E Fingering · Guitar Learning';
  document.querySelector('h1').textContent = 'Drop E fingering';
  document.querySelector('.subtitle').textContent = 'Saved riffs · Open strings first · Intervals relative to E';
  document.querySelector('.badge').textContent = 'Fingering study';
  document.querySelector('[aria-label="Generate a riff"]').hidden = true;
  $('result').hidden = false;
  $('result').setAttribute('aria-label', 'Compare guitar fingerings');
  const status = $('status');
  $('result').prepend(status);
  status.textContent = 'Loading mappings…';
  $('download-mpe').hidden = true;
  $('download-midi').textContent = 'Source MIDI';
  $('download-midi').title = 'Open the unchanged source MIDI on GitHub';
  $('download').textContent = 'Mapping JSON';
  $('play').title = 'Follow the fretboard silently';
  $('stop').textContent = '↺ Reset';
  $('result').lastElementChild.hidden = true;
  const scoreDetails = $('score').closest('details');
  scoreDetails.querySelector('summary').textContent = 'Current notes';
  const infoDetails = $('pattern-details').closest('details');
  infoDetails.querySelector('summary').textContent = 'Mapping details';
  $('score').className = 'eff-current-notes';
  $('score').removeAttribute('style');
  $('riff-summary').classList.add('eff-summary');
  $('section-playback').setAttribute('aria-label', 'Jump to a musical event');
  $('seek').step = '0.001';
  $('seek').setAttribute('aria-label', 'Time in riff');

  const controls = element('div', 'eff-controls');
  const selectLabel = element('label', 'eff-riff-label', 'Riff');
  const select = element('select', 'eff-riff-select');
  select.id = 'eff-riff'; select.setAttribute('aria-label', 'Choose a test riff');
  selectLabel.append(select);
  const versionButtons = element('div', 'segmented eff-versions');
  versionButtons.setAttribute('role', 'group'); versionButtons.setAttribute('aria-label', 'Fingering version');
  controls.append(selectLabel, versionButtons);
  $('result').querySelector('.transport').before(controls);

  const metrics = element('div', 'eff-metrics'); metrics.id = 'eff-metrics';
  controls.after(metrics);
  const previous = element('button', '', '← Note');
  previous.type = 'button'; previous.id = 'eff-previous'; previous.title = 'Previous attack';
  const next = element('button', '', 'Note →');
  next.type = 'button'; next.id = 'eff-next'; next.title = 'Next attack';
  $('play').before(previous); $('stop').after(next);
  const noteSummary = element('p', 'eff-note-summary'); noteSummary.id = 'eff-note-summary';
  $('current-shape').after(noteSummary);
  const sourceLink = element('a', 'eff-source-link', 'View source MIDI');
  sourceLink.target = '_blank'; sourceLink.rel = 'noopener';

  let bundle, fixtures, fixture, version, time = 0, speed = 1, following = false, lastFrameTime = null;
  let boardKey = '', cells = new Map(), raf = null;

  function stopFollowing() {
    following = false; lastFrameTime = null;
    if (raf !== null) cancelAnimationFrame(raf);
    raf = null; $('play').textContent = '▶ Follow';
  }

  function startFollowing() {
    if (time >= fixture.duration_seconds - EPS) time = 0;
    following = true; lastFrameTime = null; $('play').textContent = '❚❚ Pause';
    raf = requestAnimationFrame(followFrame);
  }

  function followFrame(timestamp) {
    if (!following) return;
    if (lastFrameTime !== null) time = Math.min(fixture.duration_seconds, time + (timestamp - lastFrameTime) / 1000 * speed);
    lastFrameTime = timestamp; draw();
    if (time >= fixture.duration_seconds - EPS) stopFollowing();
    else raf = requestAnimationFrame(followFrame);
  }

  function seek(value) {
    time = Math.max(0, Math.min(fixture.duration_seconds, Number(value)));
    lastFrameTime = null; draw();
  }

  function step(direction) {
    stopFollowing();
    const choices = direction > 0 ? fixture.attacks.filter(t => t > time + EPS) : fixture.attacks.filter(t => t < time - EPS);
    seek(direction > 0 ? (choices[0] ?? fixture.duration_seconds) : (choices.at(-1) ?? 0));
  }

  function makeBoard(frame) {
    const key = `${frame.firstFret}:${frame.lastFret}`;
    if (key === boardKey) return;
    boardKey = key; cells = new Map();
    const board = $('fretboard'); board.replaceChildren();
    const frets = frame.lastFret - frame.firstFret + 1;
    board.style.gridTemplateColumns = `58px repeat(${frets}, minmax(30px, 1fr))`;
    board.style.minWidth = `${58 + frets * 32}px`;
    board.dataset.firstFret = frame.firstFret; board.dataset.lastFret = frame.lastFret;
    board.append(element('div', 'fret-number eff-open-heading', 'Open'));
    for (let fret = frame.firstFret; fret <= frame.lastFret; fret++) board.append(element('div', 'fret-number', fret));
    DROP_E.forEach((open, index) => {
      const string = index + 1;
      const label = element('div', 'string-label eff-string-label');
      label.dataset.string = string; label.dataset.fret = 0;
      label.title = `String ${string} · open ${pitchName(open)} · ${interval(open)} from E`;
      label.append(element('span', 'eff-string-number', string), element('span', 'marker eff-open-marker', interval(open)));
      label.setAttribute('aria-label', `String ${string}, open ${pitchName(open)}`);
      board.append(label); cells.set(`${string}:0`, label);
      for (let fret = frame.firstFret; fret <= frame.lastFret; fret++) {
        const cell = element('div', 'cell'); cell.dataset.string = string; cell.dataset.fret = fret;
        cell.append(element('span', 'marker', interval(open + fret)));
        cell.title = `String ${string} · fret ${fret} · ${pitchName(open + fret)} · ${interval(open + fret)} from E`;
        cell.setAttribute('aria-label', cell.title); board.append(cell); cells.set(`${string}:${fret}`, cell);
      }
    });
  }

  function drawNotes(frame) {
    const container = $('score'); container.replaceChildren();
    if (!frame.active.length) {
      container.append(element('p', 'small', time >= fixture.duration_seconds - EPS ? 'End of riff.' : 'No notes sounding.'));
      return;
    }
    const table = element('table', 'eff-note-table');
    const head = element('thead'), header = element('tr');
    for (const title of ['String', 'Fret', 'Interval', 'Release']) header.append(element('th', '', title));
    head.append(header); table.append(head);
    const body = element('tbody');
    for (const note of [...frame.active].sort((a, b) => a.string_number - b.string_number)) {
      const row = element('tr'); row.dataset.noteId = note.id;
      row.title = `Source note ${note.id} · ${pitchName(note.pitch)} · begins ${seconds(note.start_seconds)}`;
      for (const value of [note.string_number, note.fret === 0 ? 'Open' : note.fret, interval(note.pitch), seconds(note.end_seconds)]) row.append(element('td', '', value));
      body.append(row);
    }
    table.append(body); container.append(table);
  }

  function draw() {
    if (!fixture || !version) return;
    const frame = efficiencyFrame(fixture, version, time);
    makeBoard(frame);
    for (const [key, cell] of cells) {
      cell.classList.remove('active', 'open', 'eff-hand-window');
      cell.removeAttribute('data-note-id');
      const fret = Number(key.split(':')[1]);
      if (fret > 0 && fret >= frame.position && fret <= frame.position + 4) cell.classList.add('eff-hand-window');
    }
    for (const note of frame.active) {
      const cell = cells.get(`${note.string_number}:${note.fret}`);
      if (cell) {cell.classList.add(note.fret === 0 ? 'open' : 'active');cell.dataset.noteId = note.id;}
    }
    $('seek').value = String(time);
    $('position').textContent = `${seconds(time)} / ${seconds(fixture.duration_seconds)}`;
    const shapeLabels = frame.currentPosition?.shape_labels || [];
    const shape = shapeLabels.length ? ` · ${shapeLabels.map(s => String(s).replaceAll('_', ' ')).join(' · ')}` : '';
    $('current-shape').textContent = `Hand window ${number(frame.position)}–${number(Math.min(24, frame.position + 4))}${shape}`;
    $('current-shape').dataset.position = frame.position;
    const openCount = frame.active.filter(n => n.fret === 0).length;
    noteSummary.textContent = frame.active.length ? `${frame.active.length} sounding ${frame.active.length === 1 ? 'note' : 'notes'} · ${openCount} open` : 'No notes sounding';
    noteSummary.dataset.activeCount = frame.active.length;
    previous.disabled = time <= EPS; next.disabled = time >= fixture.attacks.at(-1) - EPS;
    drawNotes(frame);
    for (const button of $('section-playback').querySelectorAll('button')) button.setAttribute('aria-pressed', String(Math.abs(Number(button.dataset.time) - time) < EPS));
  }

  function showMetrics() {
    const m = version.metrics || {};
    const baseline = fixture.versions.find(v => v.id === 'greedy')?.metrics || {};
    const optimized = fixture.versions.find(v => v.id === 'optimized')?.metrics || {};
    metrics.replaceChildren();
    const openNotes = ['Open notes', `${number(m.open_used)} / ${number(m.open_eligible)}`, `${number(m.open_exceptions)} exceptions`];
    const values = version.id === 'strumPick' ? [
      openNotes,
      ['Chord string skips', number(m.chord_skipped_strings), `${number(m.contiguous_chord_count)} / ${number(m.chord_attack_count)} chord attacks adjacent`],
      ['Rapid single-note string skips', number(m.rapid_single_skipped_strings), `${number(m.rapid_single_skip_transition_count)} / ${number(m.rapid_single_pair_count)} pairs skip strings · ≤ ${number(version.objective?.rapid_max_gap_seconds * 1000)} ms`],
      ['Hand travel', `${number(m.hand_travel_frets)} frets`, `Optimized: ${number(optimized.hand_travel_frets)} frets`]
    ] : [
      openNotes,
      ['Rapid shifts', number(m.rapid_shift_count), `Greedy: ${number(baseline.rapid_shift_count)}`],
      ['Hand travel', `${number(m.hand_travel_frets)} frets`, `Greedy: ${number(baseline.hand_travel_frets)} frets`],
      ['Largest shift', `${number(m.max_shift_frets)} frets`, `Greedy: ${number(baseline.max_shift_frets)} frets`]
    ];
    for (const [label, value, detail] of values) {
      const card = element('div', 'eff-stat');
      card.append(element('span', 'eff-stat-label', label), element('strong', '', value), element('span', 'eff-stat-detail', detail)); metrics.append(card);
    }
  }

  function showJumpButtons() {
    $('section-playback').replaceChildren();
    const groups = fixture.attacks.map(t => ({time: t, notes: fixture.notes.filter(n => Math.abs(n.start_seconds - t) < EPS)}));
    const lowPower = groups.find(g => g.notes.length === 2 && g.notes.map(n => n.pitch).sort((a, b) => a - b).join(',') === '28,35');
    const dyad = groups.find(g => {
      const active = fixture.notes.filter(n => n.start_seconds <= g.time + EPS && n.end_seconds > g.time + EPS);
      return g.notes.length === 2 && active.length === 2 && Math.abs(g.notes[0].pitch - g.notes[1].pitch) % 12 !== 7 && g.notes[0].pitch !== g.notes[1].pitch;
    });
    for (const target of [{label: 'Opening', time: 0}, lowPower && {label: 'Open E power chord', time: lowPower.time}, dyad && {label: 'Other dyad', time: dyad.time}].filter(Boolean)) {
      const button = element('button', '', `${target.label} · ${seconds(target.time)}`);
      button.type = 'button'; button.dataset.time = target.time;
      button.addEventListener('click', () => {stopFollowing(); seek(target.time);}); $('section-playback').append(button);
    }
  }

  function showDetails() {
    const details = $('pattern-details'); details.replaceChildren();
    details.append(element('p', 'small', 'All mappings preserve every source note, including simultaneous duplicates, and keep the original pitch, octave, onset and release. Greedy comparison assigns fingering attack by attack. The source MIDI contains no original guitar fingering.'));
    for (const warning of fixture.warnings || []) details.append(element('p', 'eff-warning', warning));
    const selectedModel = version.objective || bundle.model;
    if (selectedModel) {
      const model = element('details');
      model.append(element('summary', '', version.objective ? 'Selected mapping priorities' : 'Movement and reach model'));
      if (version.objective) {
        const priorities = element('ol', 'small');
        for (const label of selectedModel.priority_labels || selectedModel.priority_order || []) {
          priorities.append(element('li', '', label));
        }
        model.append(priorities);
        const rapidGap = number(selectedModel.rapid_max_gap_seconds * 1000) + ' ms';
        model.append(element('p', 'small', `Rapid pairs use the source timing, at most ${rapidGap} between attacks. Playback speed does not recompute the fingering.`));
        for (const definition of [selectedModel.chord_skip_definition,
          selectedModel.rapid_skip_definition, selectedModel.repeated_shape_definition]) {
          if (definition) model.append(element('p', 'small', definition.replaceAll('rapid_max_gap_seconds', rapidGap)));
        }
        const tieLabels = {
          rapid_run_direction_reversals: 'Fewer picking direction reversals',
          repeated_shape_remaps: 'Keep repeated fretted shapes on the same strings/frets',
          rapid_shift_cost: 'Fewer rapid neck shifts',
          hand_travel_frets: 'Less hand travel',
          fretting_effort: 'Less fretting effort'
        };
        if (selectedModel.tie_break_order?.length) {
          model.append(element('p', 'small', 'When the first three priorities tie: ' +
            selectedModel.tie_break_order.map(key => tieLabels[key] || key.replaceAll('_', ' ')).join(' → ') + '.'));
        }
      } else {
        model.append(element('pre', 'eff-model', JSON.stringify(selectedModel, null, 2)));
      }
      details.append(model);
    }
    sourceLink.href = fixture.source_url; details.append(sourceLink);
  }

  function chooseVersion(id) {
    version = fixture.versions.find(v => v.id === id) || fixture.versions.find(v => v.id === 'optimized');
    for (const button of versionButtons.children) button.setAttribute('aria-pressed', String(button.dataset.version === version.id));
    status.textContent = version.description || 'Only the fingering changes; the music stays the same.';
    boardKey = ''; showMetrics(); showDetails(); draw();
  }

  function chooseFixture(id) {
    stopFollowing(); time = 0;
    fixture = fixtures.find(f => f.id === id) || fixtures[0];
    select.value = fixture.id;
    $('result-title').textContent = fixture.label;
    $('riff-summary').textContent = `${fixture.notes.length} note occurrences · ${seconds(fixture.duration_seconds)} · ${number(fixture.tempo_bpm)} BPM`;
    $('seek').max = String(fixture.duration_seconds);
    versionButtons.replaceChildren();
    for (const v of [...fixture.versions].sort((a, b) => Number(b.id === 'optimized') - Number(a.id === 'optimized'))) {
      const label = v.id === 'optimized' ? 'Efficient mapping' :
        v.id === 'greedy' ? 'Greedy comparison' : (v.label || v.id);
      const button = element('button', '', label);
      button.type = 'button'; button.dataset.version = v.id;
      button.addEventListener('click', () => chooseVersion(v.id)); versionButtons.append(button);
    }
    showJumpButtons(); chooseVersion('optimized');
  }

  try {
    const embedded = document.getElementById('fretboard-efficiency-data');
    if (providedData !== undefined) bundle = providedData;
    else if (embedded) bundle = JSON.parse(embedded.textContent);
    else {
      const base = import.meta.env?.BASE_URL || './';
      const dataUrl = new URL('data/fretboard-efficiency-fixtures.json?v=20261119-shapes',
        new URL(base, document.baseURI));
      const response = await fetch(dataUrl, { cache: 'no-store' });
      if (!response.ok) throw new Error(`Could not load the mapping results (${response.status}).`);
      bundle = await response.json();
    }
    if (bundle.schema !== 'drop-e-fretboard-efficiency/1' || !Array.isArray(bundle.fixtures) ||
        JSON.stringify(bundle.tuning_high_to_low) !== JSON.stringify(DROP_E)) throw new Error('The mapping file does not declare the expected Drop E tuning.');
    fixtures = bundle.fixtures.map(prepareFixture);
    if (!fixtures.length) throw new Error('No test riffs are available.');
    document.querySelector('.subtitle').textContent = `${fixtures.length} saved ${fixtures.length === 1 ? 'riff' : 'riffs'} · Open strings first · Intervals relative to E`;
    for (const f of fixtures) {const option = element('option', '', f.label);option.value = f.id;select.append(option);}
    select.addEventListener('change', () => chooseFixture(select.value));
    previous.addEventListener('click', () => step(-1)); next.addEventListener('click', () => step(1));
    $('play').addEventListener('click', () => following ? stopFollowing() : startFollowing());
    $('stop').addEventListener('click', () => {stopFollowing(); seek(0);});
    $('seek').addEventListener('input', () => seek($('seek').value));
    $('speeds').addEventListener('click', event => {
      const button = event.target.closest('[data-speed]'); if (!button) return;
      speed = Number(button.dataset.speed);
      for (const b of $('speeds').querySelectorAll('button')) b.setAttribute('aria-pressed', String(b === button));
    });
    $('download-midi').addEventListener('click', () => window.open(fixture.source_url, '_blank', 'noopener'));
    $('download').addEventListener('click', () => {
      const url = URL.createObjectURL(new Blob([JSON.stringify({schema: bundle.schema, tuning_high_to_low: DROP_E, fixture, selected_version: version.id}, null, 2)], {type: 'application/json'}));
      const link = element('a'); link.href = url; link.download = `drop-e-${fixture.id}-${version.id}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    document.addEventListener('keydown', event => {
      if (event.target.closest('input, select, textarea, button, a')) return;
      if (event.code === 'Space') {event.preventDefault();following ? stopFollowing() : startFollowing();}
      else if (event.key === 'ArrowLeft') {event.preventDefault();step(-1);}
      else if (event.key === 'ArrowRight') {event.preventDefault();step(1);}
    });
    for (const id of ['play', 'stop', 'seek', 'download-midi', 'download']) $(id).disabled = false;
    $('shape-legend').textContent = 'Filled circles: sounding notes · gray: open strings · shaded frets: current hand window. Numbers inside circles are intervals from E. Rows run from string 1 (highest) to string 8 (lowest). Follow is silent.';
    chooseFixture('cfa029a2');
    document.body.dataset.efficiencyReady = 'true';
  } catch (error) {
    stopFollowing(); status.textContent = error.message || String(error); status.classList.add('error');
    for (const id of ['play', 'stop', 'seek', 'download-midi', 'download', 'eff-previous', 'eff-next']) $(id).disabled = true;
    document.body.dataset.efficiencyReady = 'error';
  }
}
