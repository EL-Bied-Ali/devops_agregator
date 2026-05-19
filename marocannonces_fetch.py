"""
Fetch Morocco IT jobs from MarocAnnonces, then reuse the common filtering logic.

Why this provider works for the current repo:
- listing pages are server-rendered HTML with stable pagination
- detail pages expose a JobPosting JSON-LD block with rich metadata
- common filtering/ranking remains centralized in adzuna_fetch.py
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from pandas.errors import EmptyDataError

from adzuna_fetch import configure_market, passes_filters, safe_save_csv
from config import (
    SUPPORTED_CH_FOCUS,
    SUPPORTED_FILTER_MODES,
    SUPPORTED_MARKETS,
    get_market_profile,
    get_output_paths,
    resolve_filter_mode,
)

BASE_URL = "https://www.marocannonces.com"
LISTING_URL = (
    f"{BASE_URL}/maroc/offres-emploi-domaine-informatique-multimedia-internet-b309.html"
    "?f_3=Informatique+%2F+Multim%C3%A9dia+%2F+Internet"
)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>")
LISTING_ITEM_RE = re.compile(
    r"<li[^>]*>\s*"
    r"<a[^>]+title=\"(?P<title>[^\"]+)\" href=\"(?P<href>[^\"]+)\"[^>]*>"
    r".*?<div class=\"holder\">.*?<h3>\s*(?P<title_html>.*?)\s*</h3>"
    r".*?<span class=\"location\">(?P<location>.*?)</span>.*?</a>"
    r".*?<div class=\"time\">(?P<time_block>.*?)</div>\s*</li>",
    flags=re.I | re.S,
)


def clean_text(value: str) -> str:
    raw = str(value or "")
    if not raw:
        return ""
    raw = SCRIPT_STYLE_RE.sub(" ", raw)
    raw = TAG_RE.sub(" ", raw)
    raw = html.unescape(raw).replace("\xa0", " ")
    return WHITESPACE_RE.sub(" ", raw).strip(" -:\t\r\n")


def absolute_url(path_or_url: str) -> str:
    value = str(path_or_url or "").strip()
    if not value:
        return ""
    return urljoin(f"{BASE_URL}/", value)


def build_listing_url(page: int = 0) -> str:
    if page <= 0:
        return LISTING_URL
    return f"{LISTING_URL}&pge={page}"


def fetch_html(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def extract_total_pages(listing_html: str) -> int:
    page_indexes = [int(match) for match in re.findall(r"[?&]pge=(\d+)", listing_html, flags=re.I)]
    return max(page_indexes) + 1 if page_indexes else 1


def extract_page_urls(listing_html: str) -> list[str]:
    """
    MarocAnnonces keeps the first page at the base URL and duplicates it with `pge=1`.
    We therefore build the crawl list from discovered links and skip `pge=1`.
    """
    urls = [LISTING_URL]
    seen = {LISTING_URL}
    for href in re.findall(r'href="([^"]*pge=\d+[^"]*)"', listing_html, flags=re.I):
        abs_url = absolute_url(href)
        if re.search(r"[?&]pge=1(?:&|$)", abs_url):
            continue
        if abs_url not in seen:
            urls.append(abs_url)
            seen.add(abs_url)
    return urls


def parse_listing_page(page_html: str) -> list[dict]:
    jobs: list[dict] = []
    for match in LISTING_ITEM_RE.finditer(page_html):
        href = match.group("href").strip()
        if "/annonce/" not in href:
            continue
        title = clean_text(match.group("title_html")) or clean_text(match.group("title"))
        location = clean_text(match.group("location"))
        time_block = clean_text(match.group("time_block"))
        jobs.append(
            {
                "title": title,
                "company": "",
                "location": location,
                "created": "",
                "url": absolute_url(href),
                "description": "",
                "listing_time_hint": time_block,
                "source": "marocannonces",
                "search_term": "marocannonces_informatique_category",
            }
        )
    return jobs


def _extract_json_ld_jobposting(detail_html: str) -> dict:
    blocks = re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>(?P<body>.*?)</script>',
        detail_html,
        flags=re.I | re.S,
    )
    for raw_block in blocks:
        block = html.unescape(raw_block).strip()
        if not block:
            continue
        try:
            payload = json.loads(block)
        except Exception:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("@type") == "JobPosting":
                return candidate
    return {}


def _extract_extra_question_value(detail_html: str, label: str) -> str:
    match = re.search(
        rf"<li>\s*{re.escape(label)}\s*:\s*(?P<value>.*?)</li>",
        detail_html,
        flags=re.I | re.S,
    )
    return clean_text(match.group("value")) if match else ""


def _extract_detail_body(detail_html: str) -> str:
    """
    Fallback body extraction for pages without valid JSON-LD.
    MarocAnnonces keeps the main text between the first content block and the
    parameter sidebar.
    """
    match = re.search(
        r"<h1>.*?</h1>.*?<div class=\"block\">\s*<div class=\"box1\">.*?</div>\s*(?P<body>.*?)</div>\s*<!-- block -->",
        detail_html,
        flags=re.I | re.S,
    )
    if not match:
        return ""
    return clean_text(match.group("body"))


def parse_detail_page(detail_html: str, detail_url: str) -> dict:
    payload = _extract_json_ld_jobposting(detail_html)

    title = clean_text(payload.get("title", "")) if payload else ""
    description = clean_text(payload.get("description", "")) if payload else ""
    created = ""
    if payload:
        date_posted = str(payload.get("datePosted", "") or "").strip()
        created = date_posted[:10] if len(date_posted) >= 10 else date_posted

    company = ""
    if payload:
        org = payload.get("hiringOrganization", {})
        if isinstance(org, dict):
            company = clean_text(org.get("name", ""))

    employment_type = clean_text(payload.get("employmentType", "")) if payload else ""
    industry = clean_text(payload.get("industry", "")) if payload else ""

    location = ""
    if payload:
        address = ((payload.get("jobLocation") or {}).get("address") or {})
        if isinstance(address, dict):
            location = clean_text(address.get("addressLocality", "")) or clean_text(address.get("addressRegion", ""))

    if not title:
        title_match = re.search(r"<h1>(?P<title>.*?)</h1>", detail_html, flags=re.I | re.S)
        title = clean_text(title_match.group("title")) if title_match else ""
    if not description:
        description = _extract_detail_body(detail_html)
    if not location:
        city_match = re.search(r"<li>\s*Ville\s*:\s*(?P<city>.*?)</li>", detail_html, flags=re.I | re.S)
        location = clean_text(city_match.group("city")) if city_match else ""
    if not company:
        company_match = re.search(r"<li>\s*Entreprise\s*:\s*<a[^>]*>(?P<company>.*?)</a></li>", detail_html, flags=re.I | re.S)
        company = clean_text(company_match.group("company")) if company_match else ""
    if not company:
        company = _extract_extra_question_value(detail_html, "Entreprise")
    if not employment_type:
        employment_type = _extract_extra_question_value(detail_html, "Contrat")
    if not industry:
        industry = _extract_extra_question_value(detail_html, "Domaine")

    canonical_url = detail_url
    if payload and payload.get("url"):
        canonical_url = absolute_url(str(payload.get("url")))

    return {
        "title": title,
        "company": company,
        "location": location,
        "created": created,
        "url": canonical_url,
        "description": description,
        "contract_type": employment_type,
        "industry": industry,
        "source": "marocannonces",
        "search_term": "marocannonces_informatique_category",
    }


def dedup_jobs(jobs: list[dict]) -> list[dict]:
    bucket: dict[str, dict] = {}
    for job in jobs:
        url = (job.get("url") or "").strip()
        if not url:
            continue
        existing = bucket.get(url)
        if not existing or len((job.get("description") or "").strip()) > len((existing.get("description") or "").strip()):
            bucket[url] = job
    return list(bucket.values())


def enrich_with_details(jobs: list[dict], sleep_seconds: float = 0.25, timeout: int = 20) -> list[dict]:
    enriched: list[dict] = []
    total = len(jobs)
    for idx, job in enumerate(jobs, start=1):
        merged = dict(job)
        try:
            detail = parse_detail_page(fetch_html(job["url"], timeout=timeout), job["url"])
            for key, value in detail.items():
                if value:
                    merged[key] = value
        except Exception as exc:
            print(f"[WARN][MarocAnnonces] detail fetch failed idx={idx}/{total} url={job.get('url','')}: {exc}")
        enriched.append(merged)
        if idx % 10 == 0 or idx == total:
            print(f"[INFO][MarocAnnonces] detail progress {idx}/{total}")
        if sleep_seconds > 0 and idx < total:
            time.sleep(sleep_seconds)
    return enriched


def fetch_all_jobs(max_pages: int = 0, max_jobs: int = 0, sleep_seconds: float = 0.25, timeout: int = 20) -> list[dict]:
    first_page = fetch_html(build_listing_url(0), timeout=timeout)
    page_urls = extract_page_urls(first_page)
    total_pages = len(page_urls)
    if max_pages and max_pages > 0:
        page_urls = page_urls[:max_pages]
        total_pages = len(page_urls)

    jobs = parse_listing_page(first_page)
    print(f"[INFO][MarocAnnonces] Listing page 1/{total_pages}: {len(jobs)} rows")

    for idx, page_url in enumerate(page_urls[1:], start=2):
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
        page_html = fetch_html(page_url, timeout=timeout)
        page_jobs = parse_listing_page(page_html)
        jobs.extend(page_jobs)
        print(f"[INFO][MarocAnnonces] Listing page {idx}/{total_pages}: {len(page_jobs)} rows")
        if not page_jobs:
            print(f"[INFO][MarocAnnonces] Early stop on empty listing page: {page_url}")
            break

    deduped = dedup_jobs(jobs)
    print(f"[INFO][MarocAnnonces] Listing deduped rows: {len(deduped)}")
    if max_jobs > 0:
        deduped = deduped[:max_jobs]
        print(f"[INFO][MarocAnnonces] Max jobs limit applied: {len(deduped)}")
    return enrich_with_details(deduped, sleep_seconds=sleep_seconds, timeout=timeout)


def build_filtered_df(all_jobs: list[dict], filter_mode: str) -> pd.DataFrame:
    filtered = []
    resolved_mode = resolve_filter_mode(filter_mode, allow_both=False)
    for job in all_jobs:
        parsed = passes_filters(job, source="marocannonces", filter_mode=resolved_mode)
        if parsed:
            filtered.append(parsed)

    df = pd.DataFrame(filtered)
    before = len(df)
    if not df.empty:
        if "canonical_url" not in df.columns:
            df["canonical_url"] = df.get("url", "")
        df = df.drop_duplicates(subset=["canonical_url", "title", "company"])
        sort_cols = [c for c in ["hiring_likelihood_score", "priority_score", "junior_score", "created"] if c in df.columns]
        if sort_cols:
            df = df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
    print(f"[INFO][MarocAnnonces][{resolved_mode}] Duplicates removed: {before - len(df)}")
    print(f"[INFO][MarocAnnonces][{resolved_mode}] Filtered kept: {len(df)}")
    return df


def safe_read_raw(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    try:
        return pd.read_csv(path).to_dict(orient="records")
    except EmptyDataError:
        return []


def main():
    parser = argparse.ArgumentParser(description="Fetch Morocco IT jobs from MarocAnnonces.")
    parser.add_argument(
        "--market",
        choices=SUPPORTED_MARKETS,
        default="",
        help="Market mode. Defaults to JOB_MARKET env var or be.",
    )
    parser.add_argument(
        "--ch-focus",
        choices=SUPPORTED_CH_FOCUS,
        default="",
        help="CH focus mode. Defaults to JOB_CH_FOCUS env var or all.",
    )
    parser.add_argument(
        "--filter-mode",
        choices=SUPPORTED_FILTER_MODES,
        default="",
        help="Filtering strictness (strict|broad|both). Defaults to JOB_FILTER_MODE env var or strict.",
    )
    parser.add_argument("--no-fetch", action="store_true", help="Reuse existing raw CSV instead of fetching.")
    parser.add_argument("--max-pages", type=int, default=0, help="Limit listing pages (0 = all).")
    parser.add_argument("--max-jobs", type=int, default=0, help="Limit detail pages (0 = all).")
    parser.add_argument("--sleep", type=float, default=0.25, help="Sleep seconds between requests.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    args = parser.parse_args()

    market = configure_market(args.market, args.ch_focus)
    profile = get_market_profile(market, args.ch_focus)
    selected_filter_mode = resolve_filter_mode(args.filter_mode, allow_both=True)
    paths = get_output_paths(market)
    raw_csv = paths["marocannonces_raw_csv"]
    filtered_csv = paths["marocannonces_filtered_csv"]
    strict_csv = paths["marocannonces_filtered_strict_csv"]
    broad_csv = paths["marocannonces_filtered_broad_csv"]

    print(
        f"[INFO][MarocAnnonces] market={market} langs={profile['allowed_language_codes']} "
        f"filter_mode={selected_filter_mode} max_pages={args.max_pages or 'all'} max_jobs={args.max_jobs or 'all'}"
    )

    if args.no_fetch:
        all_jobs = safe_read_raw(raw_csv)
    else:
        all_jobs = fetch_all_jobs(
            max_pages=args.max_pages,
            max_jobs=args.max_jobs,
            sleep_seconds=args.sleep,
            timeout=args.timeout,
        )
        safe_save_csv(pd.DataFrame(all_jobs), raw_csv)

    if selected_filter_mode in ("strict", "both"):
        strict_df = build_filtered_df(all_jobs, "strict")
        safe_save_csv(strict_df, strict_csv)
        safe_save_csv(strict_df, filtered_csv)
        print(f"[INFO][MarocAnnonces] Strict filtered saved: {len(strict_df)}")

    if selected_filter_mode in ("broad", "both"):
        broad_df = build_filtered_df(all_jobs, "broad")
        safe_save_csv(broad_df, broad_csv)
        if selected_filter_mode == "broad":
            safe_save_csv(broad_df, filtered_csv)
        print(f"[INFO][MarocAnnonces] Broad filtered saved: {len(broad_df)}")


if __name__ == "__main__":
    main()
