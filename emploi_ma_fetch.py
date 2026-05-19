"""
Fetch Morocco jobs from Emploi.ma, then reuse the common filtering logic.

Why a dedicated provider:
- Emploi.ma serves HTML pages, not a public JSON API we can rely on.
- The existing ranking/filtering logic already lives in adzuna_fetch.py.
- This fetcher only handles extraction + normalization, then delegates the rest.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import time
from datetime import datetime
from urllib.parse import urlencode

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

BASE_URL = "https://www.emploi.ma"
IT_FILTER_VALUE = "im_field_offre_metiers:31"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>")
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def html_to_text(value: str) -> str:
    """Strip tags while preserving coarse block boundaries for job content."""
    raw = str(value or "")
    if not raw:
        return ""
    raw = SCRIPT_STYLE_RE.sub(" ", raw)
    for token in ("</p>", "</div>", "</li>", "</ul>", "</section>", "<br>", "<br/>", "<br />"):
        raw = raw.replace(token, "\n")
    raw = TAG_RE.sub(" ", raw)
    raw = html.unescape(raw)
    raw = raw.replace("\xa0", " ")
    lines = [WHITESPACE_RE.sub(" ", line).strip(" -:\t") for line in raw.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def absolute_url(path_or_url: str) -> str:
    value = str(path_or_url or "").strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("/"):
        return f"{BASE_URL}{value}"
    return f"{BASE_URL}/{value}"


def build_listing_url(page: int = 0) -> str:
    params = {"f[0]": IT_FILTER_VALUE}
    if page > 0:
        params["page"] = str(page)
    return f"{BASE_URL}/recherche-jobs-maroc?{urlencode(params)}"


def fetch_url(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def extract_total_pages(listing_html: str) -> int:
    """
    Emploi.ma uses zero-based `page=N` links.
    If max page link is `page=2`, total pages are 3.
    """
    normalized_html = html.unescape(listing_html)
    page_indexes = [int(match) for match in re.findall(r"[?&]page=(\d+)", normalized_html, flags=re.I)]
    return max(page_indexes) + 1 if page_indexes else 1


def parse_listing_cards(listing_html: str) -> list[dict]:
    """
    Parse search result cards.

    We deliberately keep the parser regex-based and dependency-light because
    the repo already runs fine without BeautifulSoup installed in all envs.
    """
    cards: list[dict] = []
    card_pattern = re.compile(
        r'(<div class="card card-job(?: featured)?".*?<time datetime="[^"]+">.*?</time>\s*</div>\s*</div>)',
        flags=re.I | re.S,
    )

    for block in card_pattern.findall(listing_html):
        href_match = re.search(
            r'<h3>\s*<a href="(?P<href>/offre-emploi-maroc/[^"]+)" title="(?P<title>[^"]+)"',
            block,
            flags=re.I | re.S,
        )
        if not href_match:
            continue

        company_match = re.search(
            r'class="card-job-company company-name">(?P<company>.*?)</a>',
            block,
            flags=re.I | re.S,
        )
        snippet_match = re.search(
            r'<div class="card-job-description">\s*<p>(?P<snippet>.*?)</p>',
            block,
            flags=re.I | re.S,
        )
        created_match = re.search(r'<time datetime="(?P<created>[^"]+)">', block, flags=re.I)
        location_match = re.search(
            r'R[ée]gion de\s*:\s*<strong>(?P<location>.*?)</strong>',
            block,
            flags=re.I | re.S,
        )
        experience_match = re.search(
            r"Niveau d[^<]*exp[ée]rience\s*:\s*<strong>(?P<experience>.*?)</strong>",
            block,
            flags=re.I | re.S,
        )
        contract_match = re.search(
            r'Contrat propos[ée]\s*:\s*<strong>(?P<contract>.*?)</strong>',
            block,
            flags=re.I | re.S,
        )

        cards.append(
            {
                "title": html.unescape(href_match.group("title")).strip(),
                "company": html_to_text(company_match.group("company")) if company_match else "",
                "location": html_to_text(location_match.group("location")) if location_match else "",
                "description": html_to_text(snippet_match.group("snippet")) if snippet_match else "",
                "created": (created_match.group("created") if created_match else "").strip(),
                "url": absolute_url(href_match.group("href")),
                "experience_hint": html_to_text(experience_match.group("experience")) if experience_match else "",
                "contract_type": html_to_text(contract_match.group("contract")) if contract_match else "",
                "source": "emploi_ma",
                "search_term": "emploi_ma_it_category",
            }
        )

    return cards


def _extract_detail_section(detail_html: str, class_name: str) -> str:
    match = re.search(
        rf'<div class="{re.escape(class_name)}">(?P<section>.*?)</div>',
        detail_html,
        flags=re.I | re.S,
    )
    return html_to_text(match.group("section")) if match else ""


def _extract_summary_value(detail_html: str, icon_name: str) -> str:
    match = re.search(
        rf'<li class="withicon {re.escape(icon_name)}"><span>(?P<value>.*?)</span></li>',
        detail_html,
        flags=re.I | re.S,
    )
    return html_to_text(match.group("value")) if match else ""


def parse_detail_page(detail_html: str, detail_url: str) -> dict:
    title_match = re.search(r"<h1[^>]*>(?P<title>.*?)</h1>", detail_html, flags=re.I | re.S)
    company_match = re.search(
        r'<meta property="og:title" content="\[(?P<company>[^\]]+)\]',
        detail_html,
        flags=re.I,
    )
    canonical_match = re.search(r'<link rel="canonical" href="(?P<url>[^"]+)"', detail_html, flags=re.I)
    published_match = re.search(r"Publi[ée]e le\s*(?P<date>\d{2}\.\d{2}\.\d{4})", detail_html, flags=re.I)

    created = ""
    if published_match:
        try:
            created = datetime.strptime(published_match.group("date"), "%d.%m.%Y").date().isoformat()
        except Exception:
            created = ""

    description = _extract_detail_section(detail_html, "job-description")
    qualifications = _extract_detail_section(detail_html, "job-qualifications")
    # Emploi.ma embeds catalog metadata in the criteria block (education bands,
    # experience buckets, region, number of openings). Including that block in the
    # free-text description creates false positives such as ubiquitous "10 ans".
    # We therefore keep the actual job body + qualifications only.
    combined_parts = [part for part in [description, qualifications] if part]
    combined_description = "\n\n".join(combined_parts).strip()

    return {
        "title": html_to_text(title_match.group("title")) if title_match else "",
        "company": html_to_text(company_match.group("company")) if company_match else "",
        "location": _extract_summary_value(detail_html, "location-dot"),
        "created": created,
        "url": absolute_url(canonical_match.group("url")) if canonical_match else detail_url,
        "description": combined_description,
        "experience_hint": _extract_summary_value(detail_html, "chart"),
        "education_level": _extract_summary_value(detail_html, "graduation-cap"),
        "contract_type": _extract_summary_value(detail_html, "file-signature"),
        "source": "emploi_ma",
        "search_term": "emploi_ma_it_category",
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


def enrich_jobs_with_details(jobs: list[dict], sleep_seconds: float = 0.4, timeout: int = 20) -> list[dict]:
    enriched: list[dict] = []
    total = len(jobs)
    for idx, job in enumerate(jobs, start=1):
        url = job.get("url", "")
        merged = dict(job)
        try:
            detail_html = fetch_url(url, timeout=timeout)
            detail = parse_detail_page(detail_html, url)
            for key, value in detail.items():
                if value:
                    merged[key] = value
        except Exception as exc:
            print(f"[WARN][Emploi.ma] detail fetch failed idx={idx}/{total} url={url}: {exc}")
        enriched.append(merged)
        if idx % 10 == 0 or idx == total:
            print(f"[INFO][Emploi.ma] detail progress {idx}/{total}")
        if sleep_seconds > 0 and idx < total:
            time.sleep(sleep_seconds)
    return enriched


def build_filtered_df(all_jobs: list[dict], filter_mode: str) -> pd.DataFrame:
    filtered = []
    resolved_mode = resolve_filter_mode(filter_mode, allow_both=False)
    for job in all_jobs:
        parsed = passes_filters(job, source="emploi_ma", filter_mode=resolved_mode)
        if parsed:
            filtered.append(parsed)

    df_f = pd.DataFrame(filtered)
    before = len(df_f)
    if not df_f.empty:
        df_f = df_f.drop_duplicates(subset=["url", "title", "company"])
    print(f"[INFO][Emploi.ma][{resolved_mode}] Duplicates removed: {before - len(df_f)}")
    print(f"[INFO][Emploi.ma][{resolved_mode}] Filtered kept: {len(df_f)}")
    return df_f


def fetch_all_jobs(max_pages: int = 0, max_jobs: int = 0, sleep_seconds: float = 0.4, timeout: int = 20) -> list[dict]:
    first_page_html = fetch_url(build_listing_url(0), timeout=timeout)
    total_pages = extract_total_pages(first_page_html)
    if max_pages > 0:
        total_pages = min(total_pages, max_pages)

    print(f"[INFO][Emploi.ma] Listing pages to fetch: {total_pages}")
    listing_jobs = parse_listing_cards(first_page_html)
    print(f"[INFO][Emploi.ma] Listing page 1/{total_pages}: {len(listing_jobs)} rows")

    for page_idx in range(1, total_pages):
        page_html = fetch_url(build_listing_url(page_idx), timeout=timeout)
        page_jobs = parse_listing_cards(page_html)
        listing_jobs.extend(page_jobs)
        print(f"[INFO][Emploi.ma] Listing page {page_idx + 1}/{total_pages}: {len(page_jobs)} rows")
        if sleep_seconds > 0 and page_idx + 1 < total_pages:
            time.sleep(sleep_seconds)

    deduped = dedup_jobs(listing_jobs)
    print(f"[INFO][Emploi.ma] Listing deduped rows: {len(deduped)}")

    if max_jobs > 0:
        deduped = deduped[:max_jobs]
        print(f"[INFO][Emploi.ma] Max jobs limit applied: {len(deduped)}")

    return enrich_jobs_with_details(deduped, sleep_seconds=sleep_seconds, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description="Fetch Morocco jobs from Emploi.ma and reuse common filters.")
    parser.add_argument(
        "--market",
        choices=SUPPORTED_MARKETS,
        default="ma",
        help="Market mode. Emploi.ma currently supports ma only.",
    )
    parser.add_argument(
        "--ch-focus",
        choices=SUPPORTED_CH_FOCUS,
        default="",
        help="Unused for ma, kept for CLI consistency.",
    )
    parser.add_argument(
        "--filter-mode",
        choices=SUPPORTED_FILTER_MODES,
        default="",
        help="Filtering strictness (strict|broad|both). Defaults to JOB_FILTER_MODE env var or strict.",
    )
    parser.add_argument("--no-fetch", action="store_true", help="Reuse existing raw CSV instead of fetching Emploi.ma.")
    parser.add_argument("--max-pages", type=int, default=0, help="Limit listing pages (0 = all available pages).")
    parser.add_argument("--max-jobs", type=int, default=0, help="Limit jobs after listing dedup (0 = all).")
    parser.add_argument("--sleep", type=float, default=0.4, help="Sleep between HTTP requests.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    args = parser.parse_args()

    market = configure_market(args.market, args.ch_focus)
    selected_filter_mode = resolve_filter_mode(args.filter_mode, allow_both=True)
    market_profile = get_market_profile(market, args.ch_focus)
    if not market_profile.get("supports_emploi_ma", False):
        raise RuntimeError(f"Emploi.ma fetch is not supported for market '{market}'.")

    output_paths = get_output_paths(market)
    raw_csv = output_paths["emploi_ma_raw_csv"]
    filtered_csv = output_paths["emploi_ma_filtered_csv"]
    filtered_strict_csv = output_paths["emploi_ma_filtered_strict_csv"]
    filtered_broad_csv = output_paths["emploi_ma_filtered_broad_csv"]

    print(
        f"[INFO][Emploi.ma] market={market} langs={market_profile['allowed_language_codes']} "
        f"filter_mode={selected_filter_mode} max_pages={args.max_pages or 'all'} max_jobs={args.max_jobs or 'all'}"
    )

    if args.no_fetch:
        if not os.path.exists(raw_csv):
            print(f"[ERROR][Emploi.ma] Missing raw file: {raw_csv}")
            return
        try:
            df_raw = pd.read_csv(raw_csv)
            all_jobs = df_raw.to_dict(orient="records")
        except EmptyDataError:
            print(f"[WARN][Emploi.ma] Empty raw file: {raw_csv}")
            all_jobs = []
    else:
        all_jobs = fetch_all_jobs(
            max_pages=args.max_pages,
            max_jobs=args.max_jobs,
            sleep_seconds=args.sleep,
            timeout=args.timeout,
        )
        safe_save_csv(pd.DataFrame(all_jobs), raw_csv)
        print(f"[INFO][Emploi.ma] Raw saved: {len(all_jobs)}")

    if selected_filter_mode in ("strict", "both"):
        df_strict = build_filtered_df(all_jobs, filter_mode="strict")
        safe_save_csv(df_strict, filtered_strict_csv)
        safe_save_csv(df_strict, filtered_csv)
        print(f"[INFO][Emploi.ma] Strict filtered saved: {len(df_strict)}")

    if selected_filter_mode in ("broad", "both"):
        df_broad = build_filtered_df(all_jobs, filter_mode="broad")
        safe_save_csv(df_broad, filtered_broad_csv)
        if selected_filter_mode == "broad":
            safe_save_csv(df_broad, filtered_csv)
        print(f"[INFO][Emploi.ma] Broad filtered saved: {len(df_broad)}")


if __name__ == "__main__":
    main()
