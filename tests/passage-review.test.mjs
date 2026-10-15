import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';

test('short passage media are hash-matched 8-second PCM clips and generated scores',()=>{
  const root=new URL('../public/composition-passage-review/',import.meta.url);
  const manifest=JSON.parse(fs.readFileSync(new URL('cases.json',root)));
  assert.equal(manifest.passages.length,4);
  assert.equal(Object.keys(manifest.media).length,36);
  for(const [file,hash] of Object.entries(manifest.media)){
    const bytes=fs.readFileSync(new URL(file,root));assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),hash);
    if(file.endsWith('.wav')){
      assert.equal(bytes.toString('ascii',0,4),'RIFF');assert.equal(bytes.readUInt32LE(24),22050);
      assert.equal(bytes.readUInt32LE(40),22050*8*2);
    }
  }
});
