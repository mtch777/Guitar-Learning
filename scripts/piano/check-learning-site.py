"""Verify the REAL published piano score in runner Chrome, including on a phone viewport."""
import asyncio
import os
from playwright.async_api import async_playwright

URL = os.environ.get("PIANO_LESSON_URL", "https://mtch777.github.io/Guitar-Learning/piano/learning-songs/")


async def verify(browser, mobile):
    context = await browser.new_context(viewport={"width": 393 if mobile else 1120, "height": 844 if mobile else 820},
                                        is_mobile=mobile, has_touch=mobile)
    page = await context.new_page()
    await page.add_init_script("""(() => {
      window.__pianoScoreErrors = [];
      const previous = console.warn.bind(console);
      console.warn = (...args) => {
        if (args[0] === 'Score selection failed:') {
          const e = args[1];
          const details = {};
          for (const name of ['name','code','message','stack','cause','innerError','originalError']) {
            try { details[name] = typeof e?.[name] === 'object'
              ? String(e[name]) : e?.[name]; } catch (_) {}
          }
          details.keys = Object.getOwnPropertyNames(e || {});
          window.__pianoScoreErrors.push(details);
        }
        previous(...args);
      };
    })();""")
    errors = []
    page.on("console", lambda msg: errors.append(f"console.{msg.type}: {msg.text}")
            if msg.type in ("error", "warning") or "[PianoRender]" in msg.text else None)
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    try:
        response = await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        assert response and response.status == 200, f"Lesson HTTP {response.status if response else 'unknown'}"
        await page.wait_for_function("""() => [...document.querySelectorAll('#song-select option')]
          .some(o => /Polite Company/i.test(o.textContent))""", timeout=30000)
        song_id = await page.evaluate("""() => [...document.querySelectorAll('#song-select option')]
          .find(o => /Polite Company/i.test(o.textContent)).value""")
        await page.locator("#song-select").select_option(song_id)
        try:
            await page.wait_for_function("""() => {
              const spinner=document.querySelector('#score-loading');
              const ready=spinner?.hidden && document.querySelector('#score svg');
              const failed=spinner?.hidden && !document.querySelector('#empty-score')?.hidden;
              return ready || failed;
            }""", timeout=20000)
        except Exception:
            print('REAL SCORE RENDER TIMEOUT; captured console messages:', flush=True)
            try:
                print('REAL SCORE TIMEOUT DOM:', await page.evaluate("""() => ({
                  status: document.querySelector('#practice-status')?.textContent,
                  loading: !document.querySelector('#score-loading')?.hidden,
                  svg: document.querySelectorAll('#score svg').length,
                  empty: !document.querySelector('#empty-score')?.hidden,
                  notice: document.querySelector('#import-message')?.textContent,
                  selection: document.querySelector('#song-select')?.selectedOptions?.[0]?.textContent,
                })"""), flush=True)
            except Exception as error:
                print('REAL SCORE TIMEOUT DOM UNAVAILABLE:', str(error)[:250], flush=True)
            for msg in errors[-45:]:
                print('REAL SCORE TIMEOUT CONSOLE:', msg[:900], flush=True)
            raise
        await page.wait_for_timeout(1000)
        summary = await page.evaluate("""() => ({
          status: document.querySelector('#practice-status')?.textContent,
          notice: document.querySelector('#import-message')?.textContent,
          library: document.querySelector('#library-message')?.textContent,
          svgCount: document.querySelectorAll('#score svg').length,
          rendered: !!document.querySelector('#score svg .vf-stavenote, #score svg .vf-stave'),
          empty: !document.querySelector('#empty-score')?.hidden,
          scoreUrl: [...performance.getEntriesByType('resource')].filter(x=>/upload-.*\\.musicxml/.test(x.name)).map(x=>x.name),
          capturedErrors: window.__pianoScoreErrors,
        })""")
        print(f"REAL SCORE {'MOBILE' if mobile else 'DESKTOP'}: {summary}", flush=True)
        for item in errors[-25:]:
            print("REAL SCORE BROWSER ERROR:", item[:2500], flush=True)
        assert summary["status"] in ("Ready", "Listening for notes") and summary["svgCount"] > 0 and not summary["empty"], (
            f"Polite Company is listed but DOES NOT LOAD on {'mobile' if mobile else 'desktop'}; "
            f"status={summary['status']}, notice={summary['notice']}"
        )
        # The original Android failure happened in Continuous playback mode.
        await page.locator('input[name="lesson-mode"][value="timed"]').check()
        await page.wait_for_function("""() =>
          document.querySelector('input[name="lesson-mode"][value="timed"]')?.checked
          && document.querySelector('#practice-status')?.textContent === 'Ready'
        """, timeout=10000)
        continuous = await page.evaluate("""() => ({
          mode: document.querySelector('input[name="lesson-mode"]:checked')?.value,
          status: document.querySelector('#practice-status')?.textContent,
          svgCount: document.querySelectorAll('#score svg').length,
          blank: !document.querySelector('#empty-score')?.hidden,
          playEnabled: !document.querySelector('#play-button')?.disabled,
          noteError: document.querySelector('#import-message')?.textContent,
        })""")
        print(f"REAL SCORE CONTINUOUS {'MOBILE' if mobile else 'DESKTOP'}: {continuous}", flush=True)
        assert continuous['mode'] == 'timed' and continuous['status'] == 'Ready' and continuous['svgCount'] > 0
        assert not continuous['blank'] and continuous['playEnabled'] and not continuous['noteError']

    finally:
        await context.close()


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        try:
            await verify(browser, True)
            await verify(browser, False)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
