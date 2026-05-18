"""
One-time scraper: fetches all 178 Khayyam ruba'is from ganjoor.net
and saves them to poems.json.

Run once:  python scraper.py
"""

import asyncio
import json
import re
import aiohttp
from bs4 import BeautifulSoup

BASE_URL = "https://ganjoor.net/khayyam/robaee/sh{}"
API_URL = "https://api.ganjoor.net/api/ganjoor/poem/{}"
TOTAL = 178
OUTPUT = "poems.json"


async def fetch(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
        r.raise_for_status()
        return await r.text()


def extract_poem_id(html: str) -> int | None:
    match = re.search(r"countPoemWords\((\d+),", html)
    if match:
        return int(match.group(1))
    match = re.search(r"[?&]p=(\d+)", html)
    if match:
        return int(match.group(1))
    return None


def parse_verses_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    verses = []
    for span in soup.select("p.poem-text span, div.poem span.m"):
        text = span.get_text(strip=True)
        if text:
            verses.append(text)
    return verses


async def fetch_poem(session: aiohttp.ClientSession, index: int) -> dict | None:
    page_url = BASE_URL.format(index)
    try:
        html = await fetch(session, page_url)
    except Exception as e:
        print(f"  [sh{index}] page fetch failed: {e}")
        return None

    poem_id = extract_poem_id(html)

    # Try Ganjoor API for clean data
    summary = None
    verses = []
    if poem_id:
        try:
            api_html = await fetch(session, API_URL.format(poem_id))
            data = json.loads(api_html)
            plain = data.get("plainText", "")
            verses = [line.strip() for line in plain.splitlines() if line.strip()]
            summary = data.get("poemSummary") or None
        except Exception:
            pass

    # Fallback: parse verses from HTML
    if not verses:
        verses = parse_verses_from_html(html)

    if not verses:
        print(f"  [sh{index}] WARNING: no verses found")
        return None

    print(f"  [sh{index}] OK — {len(verses)} lines, summary={'yes' if summary else 'no'}")
    return {
        "index": index,
        "ganjoor_id": poem_id,
        "verses": verses,
        "summary": summary,
    }


async def main() -> None:
    print(f"Fetching {TOTAL} ruba'is from ganjoor.net …\n")
    poems = []

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Fetch in small batches to be polite to the server
        for batch_start in range(1, TOTAL + 1, 10):
            batch = range(batch_start, min(batch_start + 10, TOTAL + 1))
            tasks = [fetch_poem(session, i) for i in batch]
            results = await asyncio.gather(*tasks)
            for poem in results:
                if poem:
                    poems.append(poem)
            await asyncio.sleep(1)

    poems.sort(key=lambda p: p["index"])

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"poems": poems}, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(poems)}/{TOTAL} poems saved to {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
