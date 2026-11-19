import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve, extname} from 'node:path';
import {createRequire} from 'node:module';

let playwright = null;
if (process.env.PIANO_BROWSER_TEST === '1') {
  try { playwright = createRequire(import.meta.url)('playwright'); } catch (_) {}
}
const root = fileURLToPath(new URL('../public/', import.meta.url));
const helper = await readFile(new URL('../public/piano/learning-songs/musescore-auto-import.user.js', import.meta.url), 'utf8');

test('Upload song saves a token independently, offers both sources, then imports MuseScore MIDI', {skip:!playwright}, async () => {
  const browser = await playwright.chromium.launch({headless:true, executablePath:'/usr/bin/chromium', args:['--no-sandbox']});
  const context = await browser.newContext();
  await context.addInitScript({content:helper});
  const requests = [];
  await context.route('https://mtch777.github.io/Guitar-Learning/**', async route => {
    const url = new URL(route.request().url());
    const pathname = url.pathname.replace(/^\/Guitar-Learning\//, '');
    const path = resolve(root, pathname.endsWith('/') ? `${pathname}index.html` : pathname);
    if (!path.startsWith(`${root}/`)) return route.fulfill({status:404});
    try {
      const body = await readFile(path);
      const mime = {'.html':'text/html', '.js':'text/javascript', '.json':'application/json', '.css':'text/css', '.musicxml':'application/xml'}[extname(path)] || 'application/octet-stream';
      await route.fulfill({status:200, body, contentType:mime});
    } catch (_) { await route.fulfill({status:404}); }
  });
  await context.route('https://musescore.com/user/19750166/scores/6109206/piano-tutorial*', route => route.fulfill({
    status:200, contentType:'text/html', body:`<!doctype html><html><head><title>Fixture on MuseScore</title></head><body>
    <h1>Fixture Score</h1><script>const img = new Image(); img.src='https://s3w.musescore.com/musescore.scoredata/g/fixture/score.mid?X-Amz-Signature=fake';</script>
    </body></html>`,
  }));
  await context.route('https://s3w.musescore.com/**', route => route.fulfill({status:200, contentType:'audio/midi', body:Buffer.from('MThd')}));
  await context.route('https://api.github.com/repos/mtch777/Guitar-Learning/dispatches', async route => {
    requests.push({url:route.request().url(), body:route.request().postDataJSON(), authorization:route.request().headers().authorization});
    await route.fulfill({status:204});
  });
  const page = await context.newPage();
  try {
    await page.goto('https://mtch777.github.io/Guitar-Learning/piano/learning-songs/', {waitUntil:'domcontentloaded'});
    await page.waitForFunction(() => !!window.PianoSongLesson);
    assert.equal(await page.locator('#url-button').count(), 0, 'URL must not be a separate top-level button');
    await page.click('#upload-button');
    assert.equal(await page.locator('#upload-token-stage').isVisible(), true);
    assert.equal(await page.locator('#upload-choose-stage').isVisible(), false);
    await page.locator('#upload-token').fill('browser-test-token');
    await page.click('#save-token');
    assert.equal(await page.locator('#upload-choose-stage').isVisible(), true);
    assert.equal(await page.evaluate(() => localStorage.getItem('piano-song-github-credential-v1')), 'browser-test-token');
    assert.equal(requests.length, 0, 'saving the token alone must not dispatch or upload anything');
    await page.click('#choose-file');
    assert.equal(await page.locator('#upload-file').isVisible(), true);
    await page.click('#upload-back');
    await page.click('#upload-close');
    await page.click('#upload-button');
    assert.equal(await page.locator('#upload-token-stage').isVisible(), false, 'saved token skips setup on later visits');
    assert.equal(await page.locator('#upload-choose-stage').isVisible(), true);
    await page.click('#choose-url');
    await page.locator('#score-url').fill('https://musescore.com/user/19750166/scores/6109206');
    await page.click('#url-submit');
    await page.waitForFunction(() => document.querySelector('#library-message')?.textContent?.includes('Converting MIDI'), {timeout:20000});
    assert.equal(requests.length, 1, 'MIDI import must be dispatched automatically after the MuseScore return');
    assert.equal(requests[0].authorization, 'Bearer browser-test-token');
    assert.equal(requests[0].body.event_type, 'piano-midi-import');
    assert.equal(requests[0].body.client_payload.title, 'Fixture Score');
    assert.match(requests[0].body.client_payload.midi_url, /^https:\/\/s3w\.musescore\.com\/.*score\.mid\?/);
  } finally { await browser.close(); }
});
