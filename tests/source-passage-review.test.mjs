import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {Script} from 'node:vm';
const html=fs.readFileSync(new URL('../composition-lab/source_passage_review.html',import.meta.url),'utf8');
test('source passage review script parses before private score data is inserted',()=>{
 const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];assert.doesNotThrow(()=>new Script(script));
 assert.match(script,/STUDY=\/\*STUDY_DATA\*\/\[\]/);
});
test('source review identifies rendered-media fingerprints and keeps source text out of HTML interpolation',()=>{
 assert.match(html,/STUDY\.map\(x=>x\.fingerprint\)/);
 assert.match(html,/n\.textContent=text/);
 assert.match(html,/fingerprint:c\.fingerprint,revision_id:c\.revision_id/);
 assert.doesNotMatch(html,/innerHTML\s*=/);
});
