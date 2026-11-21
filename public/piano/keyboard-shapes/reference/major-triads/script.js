import {groupedTriads, BLACK_KEYS} from './triads.js';

const host = document.getElementById('triad-groups');

function keyboardFor(chord) {
  const keyboard = document.createElement('div');
  keyboard.className = 'mini-keyboard';
  keyboard.setAttribute('role', 'img');
  keyboard.setAttribute('aria-label', chord.name + ' major: ' + chord.notes.join(', '));
  const whiteNotes = [];
  for (let midi=60; midi<=79; midi++) if (!BLACK_KEYS.has(midi%12)) whiteNotes.push(midi);
  const targets = new Set([60+chord.root, 64+chord.root, 67+chord.root]);
  const unit = 100 / whiteNotes.length;
  const whiteIndex = new Map(whiteNotes.map((midi,index)=>[midi,index]));
  for (const [index, midi] of whiteNotes.entries()) {
    const key = document.createElement('span');
    key.className = 'mini-key white' + (targets.has(midi) ? ' active' : '');
    key.style.left = (index*unit)+'%';
    key.style.width = unit+'%';
    key.dataset.midi = String(midi);
    keyboard.append(key);
  }
  for (let midi=60; midi<=79; midi++) {
    if (!BLACK_KEYS.has(midi%12)) continue;
    const previous = whiteIndex.get(midi-1);
    if (previous === undefined) continue;
    const key = document.createElement('span');
    key.className = 'mini-key black' + (targets.has(midi) ? ' active' : '');
    key.style.left = ((previous+1)*unit - unit*0.32)+'%';
    key.style.width = (unit*0.64)+'%';
    key.dataset.midi = String(midi);
    keyboard.append(key);
  }
  return keyboard;
}

for (const {count,chords} of groupedTriads()) {
  const section = document.createElement('section');
  section.className = 'lesson-section';
  section.dataset.blackKeys = String(count);
  const heading = document.createElement('h2');
  heading.className = 'lesson-section-title';
  heading.textContent = count + (count===1?' black key':' black keys');
  section.append(heading);
  const grid = document.createElement('div');
  grid.className='triad-grid';
  for (const chord of chords) {
    const card = document.createElement('article');
    card.className='triad-card';
    card.dataset.chord=chord.name;
    const heading = document.createElement('h3');
    heading.textContent=chord.name + ' major';
    const notes = document.createElement('p');
    notes.className='chord-notes';
    notes.textContent=chord.notes.join(' · ');
    card.append(heading,notes,keyboardFor(chord));
    grid.append(card);
  }
  section.append(grid);
  host.append(section);
}
window.PracticeTracker?.recordOpen('keyboard-shapes-major-triads-reference');
