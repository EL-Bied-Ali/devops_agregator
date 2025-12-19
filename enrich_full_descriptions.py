"""
Fetch full job descriptions from URLs in the filtered CSV and annotate seniority hits.

Usage:
    python enrich_full_descriptions.py \
        --input data/adzuna_jobs_filtered.csv \
        --output data/adzuna_jobs_enriched.csv \
        --sleep 2

Notes:
    - Low-volume, respectful scraping: small sleep between requests, simple retries.
    - Focused on getting longer descriptions and spotting excluded keywords (senior/lead/...).
"""

import argparse
import time
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from adzuna_fetch import normalize, excluded_hits
from config import EXCLUDE_KEYWORDS

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
]


def fetch_with_retries(
    url: str, session: requests.Session, max_retries: int = 3, timeout: int = 15
) -> Tuple[Optional[str], Optional[str]]:
    """Return HTML text or (None, error). Retries on transient HTTP errors."""
    for attempt in range(max_retries):
        try:
            parsed = urlparse(url)
            referer = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else "https://www.google.com/"
            resp = session.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": USER_AGENTS[attempt % len(USER_AGENTS)],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Connection": "close",
                    "Referer": referer,
                },
            )
            # Retry on 5xx/429
            if resp.status_code >= 500 or resp.status_code == 429:
                raise requests.HTTPError(f"{resp.status_code} {resp.reason}")
            resp.raise_for_status()
            return resp.text, None
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            return None, err
    return None, "unknown_error"


def extract_text(html: str, max_chars: int = 8000) -> str:
    """Crude text extraction from HTML (best-effort, no JS)."""
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(s.strip() for s in soup.stripped_strings)
    text = " ".join(text.split())
    return text[:max_chars]


def matched_excludes(text: str) -> List[str]:
    """Return the list of exclude keywords found in text (normalized), honoring exceptions."""
    return excluded_hits(text)


def playwright_fetch(url: str, timeout_ms: int = 15000) -> Tuple[Optional[str], Optional[str]]:
    """Try to render JS-heavy pages with Playwright headless Chromium."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(timeout_ms)
            page.goto(url, wait_until="domcontentloaded")
            text = page.inner_text("body")
            browser.close()
            return text, None
    except PlaywrightTimeout as e:
        return None, f"PlaywrightTimeout: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def main():
    parser = argparse.ArgumentParser(description="Enrich filtered jobs with full descriptions.")
    parser.add_argument("--input", default="data/adzuna_jobs_filtered.csv", help="Input filtered CSV")
    parser.add_argument("--output", default="data/adzuna_jobs_enriched.csv", help="Output enriched CSV")
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds to sleep between requests")
    parser.add_argument("--max-retries", type=int, default=4, help="Max retries per URL")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout seconds")
    parser.add_argument(
        "--use-browser",
        action="store_true",
        help="Use Playwright headless Chromium as a fallback for pages that fail with requests.",
    )
    parser.add_argument("--browser-timeout", type=int, default=15, help="Playwright timeout seconds")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    rows = []

    session = requests.Session()
    ok = 0
    fail = 0

    for _, row in df.iterrows():
        # Prefer full redirect_url with query params (more likely to work), fallback to canonical
        url = row.get("url") or row.get("canonical_url")
        scraped = ""
        fetch_error = ""
        if url:
            html, err = fetch_with_retries(url, session, max_retries=args.max_retries, timeout=args.timeout)
            if html:
                scraped = extract_text(html)
                ok += 1
            else:
                # Optional browser fallback for JS/blocked pages
                if args.use_browser:
                    text, perr = playwright_fetch(url, timeout_ms=args.browser_timeout * 1000)
                    if text:
                        scraped = " ".join(text.split())[:8000]
                        ok += 1
                        fetch_error = ""
                    else:
                        fetch_error = perr or err or "fetch_failed"
                        fail += 1
                else:
                    fetch_error = err or "fetch_failed"
                    fail += 1
            time.sleep(args.sleep)
        original_desc = row.get("description", "") or ""
        combined_desc = scraped if scraped and len(scraped) > len(original_desc) else original_desc
        exclude_hits = matched_excludes(combined_desc)

        rows.append(
            {
                **row.to_dict(),
                "scraped_description": scraped,
                "scraped_len": len(scraped),
                "original_len": len(original_desc),
                "combined_description": combined_desc,
                "combined_len": len(combined_desc),
                "exclude_hits": ", ".join(exclude_hits),
                "exclude_hit": bool(exclude_hits),
                "fetch_error": fetch_error,
            }
        )

    out_df = pd.DataFrame(rows)
    out_df.to_csv(args.output, index=False)
    print(f"[ENRICH] Saved {len(out_df)} rows to {args.output}")
    print(f"[ENRICH] Fetched OK: {ok}, failed: {fail}")


if __name__ == "__main__":
    main()
