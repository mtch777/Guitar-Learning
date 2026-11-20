"""Verify the REAL published piano score in runner Chrome, including on a phone viewport."""
import asyncio
import os
from playwright.async_api import async_playwright

URL = os.environ.get("PIANO_LESSON_URL", "https://mtch777.github.io/Guitar-Learning/piano/learning-songs/")


async def verify(browser, mobile):
    context = await browser.new_context(viewport={"width": 393 if mobile else 1120, "height": 844 if mobile else 820},
                                        is_mobile=mobile, has_touch=mobile)
    page = await context.new_page()
    await page.add_init_script("""() => {}""") if False else None
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
              const s=document.querySelector('#practice-status')?.textContent;
              return s==='Ready' || s==='Score unavailable';
            }""", timeout=40000)
        except Exception:
            print('REAL SCORE RENDER TIMEOUT; captured console messages:', flush=True)
            for msg in errors[-40:]:
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
        assert summary["status"] == "Ready" and summary["svgCount"] > 0 and not summary["empty"], (
            f"Polite Company is listed but DOES NOT LOAD on {'mobile' if mobile else 'desktop'}; "
            f"status={summary['status']}, notice={summary['notice']}"
        )
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
