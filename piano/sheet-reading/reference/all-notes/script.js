import {LOWEST_MIDI, HIGHEST_MIDI, noteForMidi} from './score.js';
import {TREBLE_CLEF,BASS_CLEF} from './clef-paths.js';

const root = document.getElementById('notation');
const NS = 'http://www.w3.org/2000/svg';
const STEPS = Object.freeze({C:0,D:1,E:2,F:3,G:4,A:5,B:6});
const ROW_HEIGHT = 144;
const STAFF_TOP = 29;
const STAFF_LINE_GAP = 9;
const STAFF_BOTTOM = STAFF_TOP + STAFF_LINE_GAP * 4;
const ROW_WIDTH = 380;
const LEFT_MARGIN = 43;
const RIGHT_MARGIN = 7;

export const MOBILE_NOTES_PER_ROW = 24;
export const DESKTOP_NOTES_PER_ROW = 24;

export function rowDefinitions(width) {
  const perRow = width < 650 ? MOBILE_NOTES_PER_ROW : DESKTOP_NOTES_PER_ROW;
  const rows = [];
  for (let first = LOWEST_MIDI; first <= HIGHEST_MIDI; first += perRow) {
    const last = Math.min(HIGHEST_MIDI, first + perRow - 1);
    // Each row fits three complete 4/4 bars. Octave-shifting clefs keep the\n    // written pitches correct without excessive ledger lines.
    const row = first === 21
      ? {clef:'bass', shift:1, octaveMark:'8'}
      : first === 45 ? {clef:'treble', shift:1, octaveMark:'8'}
      : first >= 93 ? {clef:'treble', shift:-2, octaveMark:'15'}
      : {clef:'treble', shift:0, octaveMark:''};
    rows.push({first,last,...row});
  }
  return rows;
}

function element(name, attrs={}, value=null) {
  const el=document.createElementNS(NS,name);
  for (const [k,v] of Object.entries(attrs)) el.setAttribute(k,String(v));
  if (value!==null) el.textContent=String(value);
  return el;
}

export function noteY(note, row) {
  const bottomIndex = row.clef==='bass' ? 2*7+STEPS.G : 4*7+STEPS.E;
  const writtenIndex = (note.octave + row.shift)*7 + STEPS[note.step];
  return STAFF_BOTTOM - (writtenIndex-bottomIndex)*(STAFF_LINE_GAP/2);
}

function ledgerLines(svg, x, y) {
  const minY=STAFF_TOP;
  const maxY=STAFF_BOTTOM;
  if (y<minY) {
    for (let yy=minY-STAFF_LINE_GAP;yy>=y-0.01;yy-=STAFF_LINE_GAP)
      svg.append(element('line',{x1:x-7,x2:x+7,y1:yy,y2:yy,class:'ledger-line'}));
  } else if (y>maxY) {
    for (let yy=maxY+STAFF_LINE_GAP;yy<=y+0.01;yy+=STAFF_LINE_GAP)
      svg.append(element('line',{x1:x-7,x2:x+7,y1:yy,y2:yy,class:'ledger-line'}));
  }
}

function drawRow(row, rowIndex) {
  const svg=element('svg',{viewBox:'0 0 '+ROW_WIDTH+' '+ROW_HEIGHT,role:'img',
    'aria-label':'Ascending chromatic eighth notes, '+(rowIndex+1)+' of '+rowDefinitions(root.clientWidth).length});
  svg.classList.add('reference-staff');
  svg.dataset.firstMidi=String(row.first);
  svg.dataset.lastMidi=String(row.last);
  for (let i=0;i<5;i++) {
    const y=STAFF_TOP+i*STAFF_LINE_GAP;
    svg.append(element('line',{x1:7,y1:y,x2:ROW_WIDTH-6,y2:y,class:'staff-line'}));
  }
  // SVG outlines, not OS/browser-dependent music-font glyphs.
  const clef=element('g',{transform:row.clef==='bass'
    ? 'translate(5 66) scale(0.039 -0.039)' : 'translate(6 61) scale(0.038 -0.038)',
    'data-clef':row.clef});
  clef.append(element('path',{d:row.clef==='bass'?BASS_CLEF:TREBLE_CLEF,class:'clef-path'}));
  svg.append(clef);
  if(row.octaveMark) {
    svg.append(element('text',{x:20,y:row.shift>0?86:16,
      class:'octave-clef-mark'},row.octaveMark));
  }
  const capacity = root.clientWidth < 650 ? MOBILE_NOTES_PER_ROW : DESKTOP_NOTES_PER_ROW;
  // Accidentals are written BEFORE the altered note, not after the natural.
  // Reserve extra horizontal room before sharps so their marks do not touch
  // the preceding natural notehead at compact, 24-notes-per-row phone sizes.
  const notes=Array.from({length:row.last-row.first+1},(_,i)=>noteForMidi(row.first+i));
  const gapWeights=notes.slice(1).map(n=>n.alter ? 18 : 12);
  const weightTotal=gapWeights.reduce((sum,gap)=>sum+gap,0);
  const factor=(ROW_WIDTH-LEFT_MARGIN-RIGHT_MARGIN)/(Math.max(
    weightTotal, (capacity-1)*12
  ));
  const notePositions=[];
  let x=LEFT_MARGIN;
  for(let index=0;index<notes.length;index++) {
    const n=notes[index];
    const midi=n.midi;
    if(index) x+=gapWeights[index-1]*factor;
    const y=noteY(n,row);
    notePositions.push({x,y,midi,alter:n.alter});
    ledgerLines(svg,x,y);
    // Sharp signs remain on the stave; only the printed names lose octave numbers.
    if(n.alter) {
      // Small deterministic vector sharp, centered in the reserved gap
      // immediately to the left of THIS notehead, not the previous natural.
      const sign=element('g',{transform:'translate('+(x-8.8)+' '+y+')',
        class:'accidental-sign','data-for-midi':midi});
      sign.append(element('path',{d:
        'M -1.6 -5.4 L -2.1 5.4 M 1.8 -5.4 L 1.3 5.4 '+
        'M -2.6 -1.7 L 2.6 -2.5 M -2.6 2.5 L 2.6 1.7'}));
      svg.append(sign);
    }
    svg.append(element('ellipse',{cx:x,cy:y,rx:4.8,ry:3.3,
      transform:'rotate(-20 '+x+' '+y+')',class:'notehead'+(n.alter?' accidental-note':''),'data-midi':midi}));
    svg.append(element('text',{x,y:127,
      class:'note-name'+(n.alter?' accidental-label':''),'data-midi':midi},
      n.step+(n.alter?'♯':'')));
    // Each note remains an eighth note. Group their stems in 4-note beams.
  }
  for(let start=0;start<notePositions.length;start+=4) {
    const group=notePositions.slice(start,start+4);
    const up = rowIndex===0;
    const beamY=up ? Math.min(...group.map(n=>n.y))-24 : Math.max(...group.map(n=>n.y))+24;
    for(const n of group) {
      const sx=n.x+(up?4.2:-4.2);
      svg.append(element('line',{x1:sx,y1:n.y,x2:sx,y2:beamY,class:'stem'+(n.alter?' accidental-stem':'')}));
    }
    if(group.length>1) {
      svg.append(element('line',{x1:group[0].x+(up?4.2:-4.2),y1:beamY,
        x2:group[group.length-1].x+(up?4.2:-4.2),y2:beamY,class:'beam'}));
    } else {
      const n=group[0], sx=n.x+(up?4.2:-4.2);
      svg.append(element('path',{d:up
        ? 'M '+sx+' '+beamY+' q 8 3 7 13'
        : 'M '+sx+' '+beamY+' q -8 -3 -7 -13',class:'flag'}));
    }
  }
  // Preserve the original 4/4 measure boundaries: eight eighth notes per bar.
  for(let i=8;i<notePositions.length;i+=8) {
    const between=(notePositions[i-1].x+notePositions[i].x)/2;
    svg.append(element('line',{x1:between,x2:between,y1:STAFF_TOP,y2:STAFF_BOTTOM,class:'bar-line'}));
  }
  return svg;
}

export function renderNotes() {
  const rows=rowDefinitions(root.clientWidth);
  root.replaceChildren();
  for (const [i,row] of rows.entries()) {
    const line=document.createElement('div');
    line.className='reference-score-row';
    line.append(drawRow(row,i));
    root.append(line);
  }
  root.dataset.rowCount=String(rows.length);
  root.dataset.noteCount=String(HIGHEST_MIDI-LOWEST_MIDI+1);
  window.PracticeTracker?.recordOpen('sheet-reading-all-notes-reference');
}

window.addEventListener('resize',()=>{
  const expected=rowDefinitions(root.clientWidth).length;
  if(expected!==Number(root.dataset.rowCount))renderNotes();
});
window.addEventListener('DOMContentLoaded',renderNotes,{once:true});