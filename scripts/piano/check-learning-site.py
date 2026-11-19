"""Verify Chrome on a GitHub Actions runner can open the published piano lesson."""
import asyncio
from playwright.async_api import async_playwright

URL = "https://mtch777.github.io/Guitar-Learning/piano/learning-songs/"


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        try:
            page = await browser.new_page()
            response = await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
            status = response.status if response else None
            title = await page.title()
            picker = await page.locator("#song-select").count()
            print(f"URL: {page.url}")
            print(f"HTTP status: {status}")
            print(f"Page title: {title}")
            print(f"Song selector present: {bool(picker)}")
            assert status == 200, f"Lesson returned HTTP {status}"
            assert picker == 1, "Learning Songs UI did not load"
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
