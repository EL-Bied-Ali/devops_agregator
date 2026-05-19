"""
Fetch Morocco IT jobs from ReKrute, then reuse the common filtering logic.

The site serves server-rendered HTML, so we can keep this provider lightweight:
- listing pages are parsed directly
- detail pages are fetched only once per listing row
- common scoring/filtering remains in adzuna_fetch.py
"""

from __future__ import annotations

import argparse
import html
import os
import re
import time
from datetime import datetime
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

BASE_URL = "https://www.rekrute.com"
START_URL = (
    f"{BASE_URL}/offres.html?"
    "p=1&s=1&o=1&positionId%5B0%5D=13&positionId%5B1%5D=19&positionId%5B2%5D=23"
)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


def clean_text(value: str) -> str:
    raw = html.unescape(str(value or "")).replace("\xa0", " ")
    return re.sub(r"\s+", " ", raw).strip()


def clean_location(value: str) -> str:
    text = clean_text(value)
    text = re.sub(r"^\d+\s*poste\(s\)\s*(?:sur\s+)?", "", text, flags=re.I)
    return text


def fetch_html(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_listing_page(page_html: str, page_url: str) -> tuple[list[dict], str]:
    jobs: list[dict] = []

    block_pattern = re.compile(r'(<li class="post-id" id="\d+".*?</li>)', flags=re.I | re.S)
    for block in block_pattern.findall(page_html):
        title_match = re.search(
            r"<a class=['\"]titreJob['\"] href=\"(?P<href>[^\"]+)\"[^>]*>(?P<title>.*?)</a>",
            block,
            flags=re.I | re.S,
        )
        if not title_match:
            continue
        detail_url = urljoin(BASE_URL, title_match.group("href"))
        title = clean_text(re.sub(r"<[^>]+>", " ", title_match.group("title")))

        company_match = re.search(r'<img[^>]+class="photo"[^>]+(?:title|alt)="(?P<company>[^"]+)"', block, flags=re.I)
        company = clean_text(company_match.group("company")) if company_match else ""

        snippet_match = re.search(r'<div class="info"[^>]*>.*?<span[^>]*>(?P<snippet>.*?)</span>', block, flags=re.I | re.S)
        snippet = clean_text(re.sub(r"<[^>]+>", " ", snippet_match.group("snippet"))) if snippet_match else ""

        date_match = re.search(r"<em class=\"date\".*?<span>(?P<date>\d{2}/\d{2}/\d{4})</span>", block, flags=re.I | re.S)
        created = ""
        if date_match:
            try:
                created = datetime.strptime(clean_text(date_match.group("date")), "%d/%m/%Y").date().isoformat()
            except Exception:
                created = ""

        info_blocks = re.findall(r'<div class="info"[^>]*>(.*?)</div>', block, flags=re.I | re.S)
        tail_text = clean_text(re.sub(r"<[^>]+>", " ", info_blocks[-1])) if len(info_blocks) >= 2 else ""

        location = ""
        location_match = re.search(r"\b([A-Za-zÀ-ÿ'() /-]+?)\s*-\s*Maroc\b", tail_text)
        if location_match:
            location = clean_location(location_match.group(1)) + " - Maroc"

        experience_hint = ""
        exp_match = re.search(
            r"Expérience requise\s*:\s*(.*?)(?:Niveau d'étude|Type de contrat proposé|Télétravail|$)",
            tail_text,
            flags=re.I,
        )
        if exp_match:
            experience_hint = clean_text(exp_match.group(1))

        jobs.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "description": snippet,
                "created": created,
                "url": detail_url,
                "experience_hint": experience_hint,
                "source": "rekrute",
                "search_term": "rekrute_it_category",
            }
        )

    next_match = re.search(
        r'<a(?=[^>]*class="next")(?=[^>]*href="(?P<href>[^"]+)")[^>]*>',
        page_html,
        flags=re.I,
    )
    next_url = urljoin(page_url, next_match.group("href")) if next_match else ""
    return jobs, next_url


def parse_detail_page(detail_html: str, detail_url: str) -> dict:
    title_match = re.search(r"<h1[^>]*>(?P<title>.*?)</h1>", detail_html, flags=re.I | re.S)
    title = clean_text(re.sub(r"<[^>]+>", " ", title_match.group("title"))) if title_match else ""

    meta_title = re.search(r'<meta property="og:title" content="(?P<content>[^"]+)"', detail_html, flags=re.I)
    company = ""
    if meta_title:
        content = meta_title.group("content")
        match = re.search(r"\[(.*?)\]", content)
        if match:
            company = clean_text(match.group(1))

    meta_url = re.search(r'<meta property="og:url" content="(?P<url>[^"]+)"', detail_html, flags=re.I)
    canonical_url = clean_text(meta_url.group("url")) if meta_url else detail_url

    location = ""
    experience_hint = ""
    for li_match in re.finditer(r"<li[^>]+title=\"(?P<title>[^\"]+)\"[^>]*>(?P<body>.*?)</li>", detail_html, flags=re.I | re.S):
        title_attr = clean_text(li_match.group("title"))
        text = clean_text(re.sub(r"<[^>]+>", " ", li_match.group("body")))
        if "Expérience requise" in title_attr:
            experience_hint = text
        elif "Région" in title_attr:
            location = clean_location(text)

    contract_type = ""
    for span_match in re.finditer(r"<span[^>]+class=\"tagContrat\"[^>]+title=\"(?P<title>[^\"]+)\"[^>]*>(?P<body>.*?)</span>", detail_html, flags=re.I | re.S):
        title_attr = clean_text(span_match.group("title"))
        text = clean_text(re.sub(r"<[^>]+>", " ", span_match.group("body")))
        if "Type de contrat" in title_attr:
            contract_type = text

    sections: list[str] = []
    for block_match in re.finditer(r"<div class=\"col-md-12 blc\".*?>(?P<body>.*?)</div>", detail_html, flags=re.I | re.S):
        block_html = block_match.group("body")
        heading_match = re.search(r"<h2[^>]*>(?P<heading>.*?)</h2>", block_html, flags=re.I | re.S)
        heading = clean_text(re.sub(r"<[^>]+>", " ", heading_match.group("heading"))) if heading_match else ""
        if heading and "adresse" in heading.lower():
            continue
        body = clean_text(re.sub(r"<br\s*/?>", "\n", re.sub(r"</p>|</li>|</ul>|</h2>", "\n", block_html, flags=re.I), flags=re.I))
        body = clean_text(re.sub(r"<[^>]+>", " ", body))
        if body:
            sections.append(body)

    meta_desc = re.search(r'<meta property="og:description" content="(?P<content>.*?)"\s*/?>', detail_html, flags=re.I | re.S)
    if meta_desc:
        sections.insert(0, clean_text(meta_desc.group("content")))

    seen = set()
    deduped_sections = []
    for section in sections:
        if section and section not in seen:
            seen.add(section)
            deduped_sections.append(section)

    return {
        "title": title,
        "company": company,
        "location": location,
        "created": "",
        "url": canonical_url,
        "description": "\n\n".join(deduped_sections).strip(),
        "experience_hint": experience_hint,
        "contract_type": contract_type,
        "source": "rekrute",
        "search_term": "rekrute_it_category",
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


def enrich_with_details(jobs: list[dict], sleep_seconds: float = 0.3, timeout: int = 20) -> list[dict]:
    enriched: list[dict] = []
    total = len(jobs)
    for idx, job in enumerate(jobs, start=1):
        merged = dict(job)
        try:
            detail = parse_detail_page(fetch_html(job["url"], timeout=timeout), job["url"])
            for key, value in detail.items():
                if value:
                    merged[key] = value
            if not merged.get("created"):
                merged["created"] = job.get("created", "")
        except Exception as exc:
            print(f"[WARN][ReKrute] detail fetch failed idx={idx}/{total} url={job.get('url','')}: {exc}")
        enriched.append(merged)
        if idx % 10 == 0 or idx == total:
            print(f"[INFO][ReKrute] detail progress {idx}/{total}")
        if sleep_seconds > 0 and idx < total:
            time.sleep(sleep_seconds)
    return enriched


def fetch_all_jobs(max_pages: int = 0, max_jobs: int = 0, sleep_seconds: float = 0.3, timeout: int = 20) -> list[dict]:
    jobs: list[dict] = []
    visited = set()
    page_url = START_URL
    page_no = 0

    while page_url and page_url not in visited:
        visited.add(page_url)
        page_no += 1
        page_html = fetch_html(page_url, timeout=timeout)
        page_jobs, next_url = parse_listing_page(page_html, page_url)
        jobs.extend(page_jobs)
        print(f"[INFO][ReKrute] Listing page {page_no}: {len(page_jobs)} rows")
        if max_pages and page_no >= max_pages:
            break
        page_url = next_url
        if sleep_seconds > 0 and page_url:
            time.sleep(sleep_seconds)

    deduped = dedup_jobs(jobs)
    print(f"[INFO][ReKrute] Listing deduped rows: {len(deduped)}")
    if max_jobs > 0:
        deduped = deduped[:max_jobs]
        print(f"[INFO][ReKrute] Max jobs limit applied: {len(deduped)}")
    return enrich_with_details(deduped, sleep_seconds=sleep_seconds, timeout=timeout)


def build_filtered_df(all_jobs: list[dict], filter_mode: str) -> pd.DataFrame:
    filtered = []
    resolved_mode = resolve_filter_mode(filter_mode, allow_both=False)
    for job in all_jobs:
        parsed = passes_filters(job, source="rekrute", filter_mode=resolved_mode)
        if parsed:
            filtered.append(parsed)

    df_f = pd.DataFrame(filtered)
    before = len(df_f)
    if not df_f.empty:
        df_f = df_f.drop_duplicates(subset=["url", "title", "company"])
    print(f"[INFO][ReKrute][{resolved_mode}] Duplicates removed: {before - len(df_f)}")
    print(f"[INFO][ReKrute][{resolved_mode}] Filtered kept: {len(df_f)}")
    return df_f


def main():
    parser = argparse.ArgumentParser(description="Fetch Morocco IT jobs from ReKrute and reuse common filters.")
    parser.add_argument("--market", choices=SUPPORTED_MARKETS, default="ma")
    parser.add_argument("--ch-focus", choices=SUPPORTED_CH_FOCUS, default="")
    parser.add_argument("--filter-mode", choices=SUPPORTED_FILTER_MODES, default="")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--max-jobs", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    market = configure_market(args.market, args.ch_focus)
    selected_filter_mode = resolve_filter_mode(args.filter_mode, allow_both=True)
    market_profile = get_market_profile(market, args.ch_focus)
    if not market_profile.get("supports_rekrute", False):
        raise RuntimeError(f"ReKrute fetch is not supported for market '{market}'.")

    output_paths = get_output_paths(market)
    raw_csv = output_paths["rekrute_raw_csv"]
    filtered_csv = output_paths["rekrute_filtered_csv"]
    filtered_strict_csv = output_paths["rekrute_filtered_strict_csv"]
    filtered_broad_csv = output_paths["rekrute_filtered_broad_csv"]

    print(
        f"[INFO][ReKrute] market={market} langs={market_profile['allowed_language_codes']} "
        f"filter_mode={selected_filter_mode} max_pages={args.max_pages or 'all'} max_jobs={args.max_jobs or 'all'}"
    )

    if args.no_fetch:
        if not os.path.exists(raw_csv):
            print(f"[ERROR][ReKrute] Missing raw file: {raw_csv}")
            return
        try:
            df_raw = pd.read_csv(raw_csv)
            all_jobs = df_raw.to_dict(orient="records")
        except EmptyDataError:
            print(f"[WARN][ReKrute] Empty raw file: {raw_csv}")
            all_jobs = []
    else:
        all_jobs = fetch_all_jobs(
            max_pages=args.max_pages,
            max_jobs=args.max_jobs,
            sleep_seconds=args.sleep,
            timeout=args.timeout,
        )
        safe_save_csv(pd.DataFrame(all_jobs), raw_csv)
        print(f"[INFO][ReKrute] Raw saved: {len(all_jobs)}")

    if selected_filter_mode in ("strict", "both"):
        df_strict = build_filtered_df(all_jobs, filter_mode="strict")
        safe_save_csv(df_strict, filtered_strict_csv)
        safe_save_csv(df_strict, filtered_csv)
        print(f"[INFO][ReKrute] Strict filtered saved: {len(df_strict)}")

    if selected_filter_mode in ("broad", "both"):
        df_broad = build_filtered_df(all_jobs, filter_mode="broad")
        safe_save_csv(df_broad, filtered_broad_csv)
        if selected_filter_mode == "broad":
            safe_save_csv(df_broad, filtered_csv)
        print(f"[INFO][ReKrute] Broad filtered saved: {len(df_broad)}")


if __name__ == "__main__":
    main()
