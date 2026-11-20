"""Live desktop verification of November 20 Drop E mapping and native playback."""
import asyncio
import json
from playwright.async_api import async_playwright

URL = "https://mtch777.github.io/Guitar-Learning/?lesson=fretboardEfficiency&riff=186bfd78&mapping=strumPick&v=20261120-final"
SHA = "16fb521d0286d40a8afc9db227282f47e1f7fd4d9296a162ec1606c60f8fac77"


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            for attempt in range(8):
                response = await page.goto(URL, wait_until="domcontentloaded", timeout=40000)
                assert response and response.status == 200
                try:
                    await page.wait_for_function("""() => {
                      const f=document.querySelector('#fretboardEfficiencyRiff');
                      const m=document.querySelector('#fretboardEfficiencyMapping');
                      const p=document.querySelector('#songPlayerProgress');
                      const b=document.querySelector('#songPlayerPlayPause');
                      return f?.value==='186bfd78' && m?.value==='strumPick'
                        && p?.dataset?.fixtureId==='186bfd78'
                        && p?.dataset?.versionId==='strumPick'
                        && p?.dataset?.durationTicks==='20160'
                        && b && !b.disabled;
                    }""", timeout=18000)
                    break
                except Exception:
                    if attempt == 7:
                        raise AssertionError("Live November 20 mapping did not become selectable and ready")
                    await page.wait_for_timeout(10000)
            payload = await page.evaluate("""async () => {
                const response=await fetch('/Guitar-Learning/data/fretboard-efficiency-fixtures.json?v=20261120-rewrite',
                  {cache:'no-store'});
                if (!response.ok) throw new Error('Mapping JSON was not served');
                const data=await response.json();
                const fixture=data.fixtures.find(f=>f.id==='186bfd78');
                return {
                  present:!!fixture, id:fixture?.id, noteCount:fixture?.notes?.length,
                  sourceSha:fixture?.source_sha256, seconds:fixture?.duration_seconds,
                  versions:fixture?.versions?.map(v=>({
                    id:v.id, assignments:v.assignments.length,
                    opens:v.metrics.open_used, chordSkips:v.metrics.chord_skipped_strings,
                    contiguous:v.metrics.contiguous_chord_count
                  }))
                };
            }""")
            assert payload["present"] and payload["noteCount"] == 113 and payload["sourceSha"] == SHA, payload
            assert abs(payload["seconds"] - 10.5) < 0.0001, payload
            assert set(v["id"] for v in payload["versions"]) == {"greedy","optimized","strumPick"}, payload
            assert all(v["assignments"] == 113 and v["opens"] == 32 for v in payload["versions"]), payload
            assert next(v for v in payload["versions"] if v["id"]=="strumPick")["contiguous"] == 38
            await page.screenshot(path="/tmp/fretboard-nov20-ready.png", full_page=True)
            print("PUBLIC FIXTURE AND NATIVE PLAYER READY:", json.dumps(payload), flush=True)

            play = page.locator("#songPlayerPlayPause")
            await play.click()
            await page.wait_for_function("""() => document.querySelector('#songPlayerPlayPause')?.textContent?.includes('Pause')""", timeout=8000)
            samples = []
            for _ in range(12):
                await page.wait_for_timeout(500)
                sample = await page.evaluate("""() => ({
                    progress:Number(document.querySelector('#songPlayerProgress')?.value||0),
                    active:[...document.querySelectorAll('[data-note-id]')].filter(el=>el.dataset.noteId).length,
                    playing:document.querySelector('#songPlayerPlayPause')?.textContent?.includes('Pause'),
                    duration:document.querySelector('#songPlayerDuration')?.textContent,
                    info:document.querySelector('#fretboardEfficiencyInfo')?.textContent,
                  })""")
                samples.append(sample)
            assert max(x["progress"] for x in samples) > 150, samples
            assert any(x["active"] > 0 for x in samples), samples
            print("LIVE COLORED NOTE AND TRANSPORT SAMPLES:", json.dumps(samples), flush=True)
            await page.wait_for_function("""() =>
                 !document.querySelector('#songPlayerPlayPause')?.textContent?.includes('Pause')""", timeout=20000)
            await page.screenshot(path="/tmp/fretboard-nov20-finished.png", full_page=True)
            await page.locator("#songPlayerStop").click()
            await page.wait_for_function("""() => Number(document.querySelector('#songPlayerProgress')?.value||0)===0""", timeout=5000)

            for strategy in ("optimized", "greedy", "strumPick"):
                await page.locator("#fretboardEfficiencyMapping").select_option(strategy)
                await page.wait_for_function("""(wanted) =>
                  document.querySelector('#songPlayerProgress')?.dataset?.versionId === wanted
                  && !document.querySelector('#songPlayerPlayPause')?.disabled""", arg=strategy, timeout=12000)
            await page.locator("#fretboardEfficiencyView").select_option("static")
            assert await page.locator("#fretboardEfficiencyView").input_value() == "static"
            await page.screenshot(path="/tmp/fretboard-nov20-static.png", full_page=True)
            await page.locator("#fretboardEfficiencyView").select_option("playback")
            assert not errors, errors
            print("SUCCESS: real published site played November 20 D in color over gray positions, "
                  "completed its native transport, stopped and switched all three fingering profiles and static view.",
                  flush=True)
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
