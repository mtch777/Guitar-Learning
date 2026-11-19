#!/usr/bin/env python3
"""Import symbolic MIDI exposed by MuseScore's public piano tutorial player.

Uses the page's ordinary network responses; no token extraction or challenge bypass.
"""
import argparse
import asyncio
import importlib.util
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright


def validate_score_url(value):
    url = urlsplit(value)
    if url.scheme != "https" or url.hostname != "musescore.com":
        raise ValueError("Enter a MuseScore HTTPS score-page URL.")
    parts = url.path.strip("/").split("/")
    if len(parts) < 4 or parts[0] != "user" or parts[2] != "scores" or not parts[3].isdigit():
        raise ValueError("Expected a MuseScore URL like /user/123/scores/456.")
    return f"https://musescore.com/user/{parts[1]}/scores/{parts[3]}"


async def retrieve_url(score_page):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        page = await browser.new_page()
        found = asyncio.get_running_loop().create_future()

        async def examine(response):
            if "/api/jmuse?" not in response.url or "type=midi" not in response.url:
                return
            try:
                data = await response.json()
                url = (data.get("info") or {}).get("url")
                if data.get("status") == 200 and url and not found.done():
                    found.set_result(url)
            except Exception:
                pass

        page.on("response", examine)
        try:
            await page.goto(score_page + "/piano-tutorial", wait_until="domcontentloaded", timeout=30000)
            body = (await page.locator("body").inner_text(timeout=15000)).lower()
            if any(term in body for term in ("verify you are human", "checking your browser", "captcha")):
                raise RuntimeError("MuseScore requires human verification; automated import stopped.")
            return await asyncio.wait_for(found, timeout=35)
        finally:
            await browser.close()


def load_converter():
    path = Path(__file__).with_name("import-midi-url.py")
    spec = importlib.util.spec_from_file_location("piano_midi_importer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-url", required=True)
    parser.add_argument("--library", type=Path, default=Path("public/piano/learning-songs"))
    args = parser.parse_args()
    score_page = validate_score_url(args.score_url)
    midi_url = asyncio.run(retrieve_url(score_page))
    load_converter().import_midi(midi_url, args.library)


if __name__ == "__main__":
    main()
