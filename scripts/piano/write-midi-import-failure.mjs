import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = fileURLToPath(new URL('../../public/piano/learning-songs/', import.meta.url));
const REQUEST_ID = /^gl-[a-f0-9]{32}$/;

export function safeImportFailure(log = '') {
  const clean = String(log)
    .replace(/https?:\/\/[^\s"'<>]+/gi, '[download URL hidden]')
    .replace(/[\u0000-\u001f\u007f]/g, ' ');
  const lines = clean.split(/(?=\b(?:Error|Exception|Traceback):)/);
  const candidates = lines.flatMap(line => line.split(/\s{2,}/))
    .filter(line => /(?:Error|Exception|failed|rejected|cannot convert|missing|invalid|HTTP [45]\d\d)/i.test(line));
  const candidate = candidates.at(-1)?.replace(/^(?:Error|Exception):\s*/i, '').trim();
  return (candidate || 'The score could not be converted or validated. Check the GitHub Actions import run.')
    .slice(0, 300);
}

export async function writeFailedMidiReceipt(id, logs = '', {directory = root} = {}) {
  if (!REQUEST_ID.test(id)) throw new Error('Invalid MIDI import request ID.');
  const dir = path.join(directory, 'imports');
  await fs.mkdir(dir, {recursive:true});
  const receipt = {version:1, requestId:id, status:'failed', error:safeImportFailure(logs)};
  await fs.writeFile(path.join(dir, `${id}.json`), JSON.stringify(receipt)+'\n', {flag:'wx'});
  return receipt;
}

if (process.argv[1] && import.meta.url === new URL('file://' + path.resolve(process.argv[1])).href) {
  const logs = await Promise.all(process.argv.slice(3).map(async filename => {
    try { return await fs.readFile(filename, 'utf8'); }
    catch (_) { return ''; }
  }));
  await writeFailedMidiReceipt(process.argv[2], logs.join('\n'));
}
