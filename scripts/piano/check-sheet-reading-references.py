"""Verify compact 88-note sheet and distinct major-triad references in real Chrome."""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOTS=Path('piano-reference-screenshots')
SCREENSHOTS.mkdir(exist_ok=True)

BASE=os.environ.get('PIANO_SITE_ROOT','http://127.0.0.1:8765/Guitar-Learning/piano/')

async def verify(browser,width):
    mobile=width<600
    context=await browser.new_context(viewport={'width':width,'height':850},is_mobile=mobile,has_touch=mobile)
    page=await context.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    try:
        response=await page.goto(BASE+'sheet-reading/',wait_until='domcontentloaded',timeout=30000)
        assert response and response.status==200
        cards=await page.locator('section.lesson-section').first.locator('a.lesson-card').all_text_contents()
        assert len(cards)==2 and 'All Notes' in cards[0] and 'Major Triads' in cards[1],cards

        await page.goto(BASE+'sheet-reading/reference/all-notes/',wait_until='load',timeout=30000)
        await page.wait_for_function("""() => document.querySelector('#notation')?.dataset.noteCount === '88'""",timeout=20000)
        summary=await page.evaluate("""() => ({
          rows:document.querySelectorAll('#notation .reference-score-row').length,
          notes:document.querySelectorAll('#notation ellipse.notehead').length,
          names:[...document.querySelectorAll('#notation text.note-name')].map(x=>x.textContent),
          ledger:document.querySelectorAll('#notation line.ledger-line').length,
          clefs:document.querySelectorAll('#notation .clef-path').length,
          sharps:document.querySelectorAll('#notation .accidental-sign').length,
          accidentalAlignment:[...document.querySelectorAll('#notation .accidental-sign')].map(sign=>{
            const head=document.querySelector('#notation ellipse[data-midi="'+sign.dataset.forMidi+'"]');
            const prev=document.querySelector('#notation ellipse[data-midi="'+(Number(sign.dataset.forMidi)-1)+'"]');
            const a=sign.getBoundingClientRect(), n=head?.getBoundingClientRect(), p=prev?.getBoundingClientRect();
            return {midi:Number(sign.dataset.forMidi),left:a.left,right:a.right,
              noteLeft:n?.left,prevRight:p?.right,valid:!!(p&&n&&a.left>p.right+0.05&&a.right<n.left-0.05)};
          }),
          text:document.querySelector('#render-status')?.textContent,
          overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
        })""")
        print(f'ALL NOTES {width}: rows={summary["rows"]} notes={summary["notes"]} names={summary["names"][:8]} ledger={summary["ledger"]} overflow={summary["overflow"]} errors={errors}',flush=True)
        assert summary['rows']==4 and summary['notes']==88 and summary['clefs']==4,summary
        assert summary['sharps']==36,summary
        assert all(a['valid'] for a in summary['accidentalAlignment']),summary['accidentalAlignment']
        assert len(summary['names'])==88 and all(n and not any(c.isdigit() for c in n) for n in summary['names']),summary
        assert summary['overflow']<=3,summary
        await page.screenshot(path=str(SCREENSHOTS/f'all-notes-{width}.png'),full_page=True)
        await page.locator('#show-labels').uncheck()
        assert await page.locator('#notation .note-name').count()==0
        assert await page.locator('#notation ellipse.notehead').count()==88
        await page.locator('#show-labels').check()
        assert await page.locator('#notation .note-name').count()==88

        await page.goto(BASE+'sheet-reading/reference/major-triads/',wait_until='load',timeout=30000)
        await page.wait_for_function("""() => document.querySelectorAll('#triad-groups section[data-ready="true"]').length===4 ||
          document.querySelector('#triad-groups section[data-ready="false"]')""",timeout=30000)
        sections=page.locator('#triad-groups .notation-group')
        assert await sections.count()==4
        groups=[]
        for count in range(4):
            group=page.locator(f'#triad-groups section[data-black-keys="{count}"]')
            label=await group.locator('.chord-labels').inner_text()
            svgs=await group.locator('svg').count()
            paths=await group.locator('svg path').count()
            groups.append((label,svgs,paths))
            assert svgs>=1 and paths>=3,(count,label,svgs,paths)
        print(f'SHEET TRIADS {width}: {groups}; errors={errors}',flush=True)
        await page.screenshot(path=str(SCREENSHOTS/f'sheet-triads-{width}.png'),full_page=True)
        assert await page.locator('#triad-groups .mini-keyboard').count()==0
        assert [g[0].replace(' · ',' ') for g in groups]==[
          'C F G','D E A B♭','B D♭ E♭ A♭','F♯'
        ]

        await page.goto(BASE+'keyboard-shapes/',wait_until='domcontentloaded',timeout=30000)
        assert 'Major Triads' in await page.locator('section.lesson-section').first.inner_text()
        assert 'Scales & Chords Reference' not in await page.locator('section.lesson-section').first.inner_text()
        await page.goto(BASE+'keyboard-shapes/reference/major-triads/',wait_until='load',timeout=30000)
        await page.wait_for_function("""() => document.querySelectorAll('.triad-card').length===12""",timeout=10000)
        await page.screenshot(path=str(SCREENSHOTS/f'keyboard-triads-{width}.png'),full_page=True)
        assert await page.locator('.mini-keyboard').count()==12
        assert await page.locator('.triad-score').count()==0
        print(f'KEYBOARD TRIADS {width}: 12 keyboard diagrams; errors={errors}',flush=True)
        assert not errors,errors
    finally:
        await context.close()

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='chrome',headless=True)
        try:
            await verify(browser,393)
            await verify(browser,1120)
        finally:await browser.close()

if __name__=='__main__':asyncio.run(main())
