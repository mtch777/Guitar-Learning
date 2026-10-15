import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {recordReview,revealReview,mergeFeedback,csvFeedback,storageKey} from '../src/ablation-review-state.mjs';

test('blind judgments remain auditable after reveal and subsequent edits',()=>{
  assert.throws(()=>revealReview({notes:'not rated'}));
  const first=recordReview({}, {coherence:'uncertain',notes:'Could not judge'}, {now:'2026-10-15T10:00:00Z'});
  const revealed=revealReview(first,'2026-10-15T10:01:00Z');
  const edited=recordReview(revealed,{coherence:'3'},{now:'2026-10-15T10:02:00Z'});
  assert.equal(first.revealedAt,undefined);assert.equal(edited.editedAfterReveal,true);
  assert.equal(edited.revealedAt,'2026-10-15T10:01:00Z');assert.equal(edited.reviewedBeforeReveal,true);
});

test('restore rejects other datasets, keeps newer notes and never erases reveal exposure',()=>{
  const manifest={version:'v1',cases:[{id:'a',family:'cloud'}]};
  const local={a:{coherence:'4',notes:'newer',updatedAt:'2026-10-15T12:00:00Z'}};
  const incoming={format:'composition-ablation-feedback-v1',version:'v1',reviews:{a:{coherence:'1',notes:'older',updatedAt:'2026-10-15T11:00:00Z',revealedAt:'2026-10-15T11:01:00Z'}}};
  const merged=mergeFeedback(local,incoming,manifest);
  assert.equal(merged.a.notes,'newer');assert.ok(merged.a.revealedAt);assert.equal(merged.a.editedAfterReveal,true);
  assert.throws(()=>mergeFeedback(local,{...incoming,version:'other'},manifest));
  assert.equal(local.a.revealedAt,undefined);assert.notEqual(storageKey('v1'),'v23_review_60');
});

test('CSV preserves quoted multiline notes, blanks and authoritative case identity',()=>{
  const text=csvFeedback({version:'v1',cases:[{id:'a',family:'cloud'},{id:'b',family:'sweet'}]},
    {a:{coherence:'4',notes:'a "quoted" note\nand another line',case_id:'spoof'}},{cloud:'a'});
  assert.ok(text.includes('"a ""quoted"" note\nand another line"'));
  assert.ok(text.includes('"v1","a","cloud","4"'));
  assert.ok(text.includes('"v1","b","sweet",""'));
  assert.ok(!text.includes('spoof'));
});

test('published review contains exactly ten generated scores and matching media hashes',()=>{
  const root=new URL('../public/composition-ablation-review/',import.meta.url);
  const manifest=JSON.parse(fs.readFileSync(new URL('cases.json',root)));
  assert.equal(manifest.cases.length,10);assert.deepEqual(manifest.judgments,[]);
  for(const family of ['cloud','sweet'])assert.equal(manifest.cases.filter(c=>c.family===family).length,5);
  const forbidden=new Set(['63cfae7762a5ac56b2f0521d8c01cbf6025fac74ea525c7a6b7d260703492f66','17c5ecc0606a6334bf2818ba3f2d1f4a8574f0777cf6750565f644a0ee0b9e7f']);
  for(const c of manifest.cases){
    assert.ok(!forbidden.has(c.gpSha256));
    for(const [file,hash] of [[c.gp,c.gpSha256],[c.audio,c.audioSha256]])assert.equal(crypto.createHash('sha256').update(fs.readFileSync(new URL(file,root))).digest('hex'),hash);
    const roll=JSON.parse(fs.readFileSync(new URL(c.roll,root)));assert.ok(roll.notes.length>0);assert.ok(roll.duration>0);
    assert.ok(roll.notes.every(n=>n.start>=0&&n.end>=n.start&&n.end<=roll.duration+.01));
  }
});
