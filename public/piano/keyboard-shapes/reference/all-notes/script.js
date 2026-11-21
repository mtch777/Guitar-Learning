import {buildAllNotesMusicXML} from './score.js';

const root = document.getElementById('notation');
const message = document.getElementById('render-status');
const toggle = document.getElementById('show-labels');
let display = null;
let generation = 0;

async function showScore() {
  const turn = ++generation;
  message.hidden = false;
  message.textContent = 'Loading sheet music…';
  try {
    const Runtime = window.opensheetmusicdisplay?.OpenSheetMusicDisplay;
    if (!Runtime) throw new Error('The sheet-music renderer did not load.');
    if (!display) {
      display = new Runtime(root, {
        backend: 'svg', autoResize: false, followCursor: false,
        drawTitle: false, drawSubtitle: false, drawComposer: false,
        drawLyricist: false, drawPartNames: false, drawPartAbbreviations: false,
        newPageFromXML: false, newSystemFromXML: false,
      });
    }
    await display.load(buildAllNotesMusicXML({showNames: toggle.checked}));
    if (turn !== generation) return;
    const width = Math.max(280, root.clientWidth);
    display.Zoom = width < 420 ? 0.68 : width < 720 ? 0.8 : 0.95;
    display.render();
    if (turn !== generation) return;
    message.textContent = 'A0 → C8 · 88 eighth notes';
    window.PracticeTracker?.recordOpen('keyboard-shapes-all-notes-reference');
  } catch (error) {
    console.error('All Notes sheet music failed:', error);
    message.textContent = 'Sheet music could not render: ' + (error?.message || error);
  }
}

toggle.addEventListener('change', showScore);
window.addEventListener('load', showScore, {once: true});
