"""Headless Chrome QA for sheet-reading references in mobile and desktop."""
import asyncio
import os
from playwright.async_api import async_playwright

BASE=os.environ.get("PIANO_SITE_ROOT","http://127.0.0.1:8765/Guitar-Learning/piano/")

async def verify(browser, width):
    context=await browser.new_context(viewport={"width":width,"height":860}, is_mobile=width<600, has_touch=width<600)
    page=await context.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    try:
        response=await page.goto(BASE+"sheet-reading/",wait_until="domcontentloaded",timeout=25000)
        assert response and response.status==200
        cards=await page.locator('section.lesson-section').first.locator('a.lesson-card').all_text_contents()
        assert len(cards)==2 and "All Notes" in cards[0] and "Major Triads" in cards[1],cards
        assert not any(s.startswith(('Random Note','Random Chord')) for s in await page.locator('a.lesson-card strong').all_text_contents())
        await page.goto(BASE+"sheet-reading/reference/all-notes/",wait_until="load",timeout=30000)
        await page.wait_for_function("""() => document.querySelectorAll('#notation svg').length>0 ||
          document.querySelector('#render-status')?.textContent?.includes('could not render')""",timeout=30000)
        status=await page.locator('#render-status').inner_text()
        svg=await page.locator('#notation svg').count()
        shapes=await page.locator('#notation svg path').count()
        print(f'ALL NOTES {width}: status={status!r}, svg={svg}, paths={shapes}, errors={errors}',flush=True)
        assert svg>0 and shapes>50 and '88 eighth notes' in status, (status,svg,shapes)
        await page.locator('#show-labels').uncheck()
        await page.wait_for_function("""() => document.querySelector('#render-status')?.textContent?.includes('88 eighth notes')""",timeout=15000)
        assert await page.locator('#notation svg').count()>0
        await page.goto(BASE+"sheet-reading/reference/major-triads/",wait_until="load",timeout=30000)
        await page.wait_for_function("""() => document.querySelectorAll('.triad-card').length===12""",timeout=10000)
        actual=[]
        for group in range(4):
            names=await page.locator(f'section[data-black-keys="{group}"] .triad-card h3').all_text_contents()
            actual.append([n.replace(' major','') for n in names])
        expected=[['C','F','G'],['D','E','A','B♭'],['B','D♭','E♭','A♭'],['F♯']]
        print(f'TRIADS {width}: {actual}; errors={errors}',flush=True)
        assert actual==expected,(actual,expected)
        assert len(errors)==0,errors
    finally:
        await context.close()

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='chrome',headless=True)
        try:
            await verify(browser,393)
            await verify(browser,1120)
        finally:
            await browser.close()

if __name__=='__main__':asyncio.run(main())
