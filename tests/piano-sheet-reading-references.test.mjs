import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {DOMParser} from '@xmldom/xmldom';
import {parseMusicXML} from '../public/piano/learning-songs/score-model.js';
import {LOWEST_MIDI,HIGHEST_MIDI,EXPECTED_COUNT,NOTES_PER_MEASURE,noteForMidi,buildAllNotesMusicXML} from '../public/piano/sheet-reading/reference/all-notes/score.js';
import {MAJOR_TRIADS,BLACK_KEYS,blackKeyCount,groupedTriads,triadPitchClasses} from '../public/piano/sheet-reading/reference/major-triads/triads.js';

const root=new URL('../public/piano/',import.meta.url);
const load=async path=>readFile(new URL(path,root),'utf8');

test('All Notes contains A0 through C8 in exactly 88 consecutive eighth notes',()=>{
  assert.equal(LOWEST_MIDI,21);
  assert.equal(HIGHEST_MIDI,108);
  assert.equal(EXPECTED_COUNT,88);
  assert.equal(NOTES_PER_MEASURE,8);
  const xml=buildAllNotesMusicXML();
  const doc=new DOMParser().parseFromString(xml,'application/xml');
  const measures=[...doc.getElementsByTagName('measure')];
  const notes=[...doc.getElementsByTagName('note')];
  assert.equal(measures.length,11);
  assert.equal(notes.length,88);
  assert.ok(notes.every(n=>n.getElementsByTagName('type')[0]?.textContent==='eighth'));
  assert.ok(notes.every(n=>n.getElementsByTagName('duration')[0]?.textContent==='240'));
  assert.ok(notes.every(n=>n.getElementsByTagName('lyric').length===1));
  assert.equal(doc.getElementsByTagName('clef').length,2);
  const model=parseMusicXML(xml,{DOMParser});
  assert.deepEqual(model.attacks.map(n=>n.midi),Array.from({length:88},(_,i)=>i+21));
  assert.equal(model.notes.filter(n=>n.isRest).length,0);
});

test('All Notes labels can be disabled without changing the score',()=>{
  const withoutLabels=buildAllNotesMusicXML({showNames:false});
  assert.ok(!withoutLabels.includes('<lyric'));
  assert.equal(parseMusicXML(withoutLabels,{DOMParser}).attacks.length,88);
  assert.equal(noteForMidi(21).name,'A0');
  assert.equal(noteForMidi(22).name,'A♯0');
  assert.equal(noteForMidi(108).name,'C8');
  assert.throws(()=>noteForMidi(20),RangeError);
});

test('Major triad groups contain every pitch class exactly once',()=>{
  assert.equal(MAJOR_TRIADS.length,12);
  const groups=groupedTriads();
  assert.deepEqual(groups.map(g=>g.chords.length),[3,4,4,1]);
  assert.deepEqual(groups.map(g=>g.chords.map(c=>c.name)),[
    ['C','F','G'],['D','E','A','B♭'],['B','D♭','E♭','A♭'],['F♯'],
  ]);
  assert.equal(new Set(MAJOR_TRIADS.map(c=>c.root)).size,12);
  assert.deepEqual(MAJOR_TRIADS.map(c=>blackKeyCount(c.root)),
    MAJOR_TRIADS.map(c=>triadPitchClasses(c.root).filter(p=>BLACK_KEYS.has(p)).length));
});

test('Only Sheet Reading presents the new learning references',async()=>{
  const sheet=await load('sheet-reading/index.html');
  const keyboard=await load('keyboard-shapes/index.html');
  assert.match(sheet,/reference\/all-notes\//);
  assert.match(sheet,/reference\/major-triads\//);
  assert.doesNotMatch(sheet,/Staff Notes Reference/);
  assert.match(keyboard,/Scales &amp; Chords Reference/);
  assert.doesNotMatch(keyboard,/reference\/all-notes\//);
  assert.doesNotMatch(keyboard,/reference\/major-triads\//);
});

test('Sheet Reading removes random prefixes from cards and lesson headers',async()=>{
  const sheet=await load('sheet-reading/index.html');
  const script=await load('sheet-reading/note-reading/script.js');
  const html=await load('sheet-reading/note-reading/index.html');
  assert.doesNotMatch(sheet,/Random (?:Note|Chord) — /);
  assert.doesNotMatch(script,/'Random (?:Note|Chord) — /);
  assert.match(script,/'Major Triad — '/);
  assert.match(script,/'' \+ clefs\[\$scope.clefFilter\]/);
  assert.doesNotMatch(html,/Random Note \/ Chord/);
  assert.equal((sheet.match(/note-reading\/\?/g)||[]).length,10);
});
