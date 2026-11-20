import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {safeImportFailure, writeFailedMidiReceipt} from '../scripts/piano/write-midi-import-failure.mjs';

const ID = 'gl-'+'c'.repeat(32);
test('failed importer leaves a useful, sanitized request-scoped receipt', async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), 'piano-failure-receipt-'));
  try {
    const log = 'Traceback: invalid MIDI at https://s3w.musescore.com/score.mid?X-Amz-Signature=private\nError: A tie in measure 22 has no matching start';
    const receipt = await writeFailedMidiReceipt(ID, log, {directory:folder});
    const persisted = JSON.parse(await fs.readFile(path.join(folder,'imports',ID+'.json'),'utf8'));
    assert.deepEqual(persisted, receipt);
    assert.equal(receipt.status,'failed');
    assert.ok(receipt.error.includes('tie'));
    assert.ok(!JSON.stringify(receipt).includes('private'));
    await assert.rejects(() => writeFailedMidiReceipt(ID, log, {directory:folder}), /EEXIST/);
  } finally { await fs.rm(folder,{recursive:true,force:true}); }
});
test('failed receipts reject invalid IDs and bound diagnostic output', async () => {
  assert.ok(safeImportFailure('Z'.repeat(500)).length <= 300);
  await assert.rejects(() => writeFailedMidiReceipt('../attack','bad'), /Invalid/);
});
