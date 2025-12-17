"""
Merge Adzuna and Jooble jobs, deduplicate (3 levels), then apply final filters.
"""

import re
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from pandas.errors import EmptyDataError
from rapidfuzz import fuzz

from adzuna_fetch import passes_filters, safe_save_csv
from config import (
    ADZUNA_RAW_CSV,
    JOOBLE_RAW_CSV,
    MERGED_CSV,
    MERGED_FILTERED_CSV,
    MERGED_RAW_CSV,
)


def normalize_simple(text: str) -> str:
    """Lowercase, strip accents, remove punctuation and collapse spaces."""
    if not text:
        return ""
    text = str(text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_tokens(text: str) -> str:
    """Remove common tokens that create false duplicates."""
    if not text:
        return ""
    cleaned = str(text).lower()
    cleaned = re.sub(r"\(m[fwhx]/?f?/?x?\)", " ", cleaned)
    for tok in ["m/f/x", "m/f", "m w d", "junior", "senior", "medior"]:
        cleaned = cleaned.replace(tok, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def canonical_key(company: str, title: str, location: str) -> str:
    combo = f"{strip_tokens(company)} {strip_tokens(title)} {strip_tokens(location)}"
    return normalize_simple(combo)


def parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
    except Exception:
        return None


def salary_present(job: Dict) -> bool:
    return bool(job.get("salary_min")) or bool(job.get("salary_max"))


def choose_best(a: Dict, b: Dict) -> Dict:
    """Pick the best job using description length, recency, salary, source preference."""
    desc_a = len((a.get("description") or "").strip())
    desc_b = len((b.get("description") or "").strip())
    if desc_b > desc_a:
        better = b
    elif desc_a > desc_b:
        better = a
    else:
        date_a = parse_date(a.get("created"))
        date_b = parse_date(b.get("created"))
        if date_a and date_b:
            if date_b > date_a:
                better = b
            elif date_a > date_b:
                better = a
            else:
                better = None
        elif date_b and not date_a:
            better = b
        elif date_a and not date_b:
            better = a
        else:
            better = None

        if better is None:
            if salary_present(b) and not salary_present(a):
                better = b
            elif salary_present(a) and not salary_present(b):
                better = a
            else:
                # Source preference
                prefer_order = ["adzuna", "jooble"]
                a_score = prefer_order.index(a.get("source")) if a.get("source") in prefer_order else len(prefer_order)
                b_score = prefer_order.index(b.get("source")) if b.get("source") in prefer_order else len(prefer_order)
                if b_score < a_score:
                    better = b
                else:
                    better = a
    return better


def dedup_by_url(jobs: List[Dict]) -> List[Dict]:
    bucket = {}
    no_url = []
    for job in jobs:
        url = (job.get("url") or "").strip()
        if url:
            if url in bucket:
                bucket[url] = choose_best(bucket[url], job)
            else:
                bucket[url] = job
        else:
            no_url.append(job)
    return list(bucket.values()) + no_url


def dedup_by_canonical(jobs: List[Dict]) -> List[Dict]:
    bucket = {}
    for job in jobs:
        key = canonical_key(job.get("company", ""), job.get("title", ""), job.get("location", ""))
        if not key:
            key = normalize_simple((job.get("title") or "") + " " + (job.get("company") or ""))
        if key in bucket:
            bucket[key] = choose_best(bucket[key], job)
        else:
            bucket[key] = job
    return list(bucket.values())


def location_similar(a: str, b: str) -> bool:
    na = normalize_simple(a)
    nb = normalize_simple(b)
    if not na or not nb:
        return True
    if na == nb:
        return True
    return fuzz.token_set_ratio(na, nb) >= 90


def fuzzy_dedup(jobs: List[Dict]) -> List[Dict]:
    kept = []
    keys = []
    for job in jobs:
        text = f"{normalize_simple(job.get('company', ''))} {normalize_simple(job.get('title', ''))}"
        merged = False
        for idx, existing in enumerate(kept):
            score = fuzz.token_set_ratio(text, keys[idx])
            if score >= 92 and location_similar(job.get("location", ""), existing.get("location", "")):
                kept[idx] = choose_best(existing, job)
                merged = True
                break
        if not merged:
            kept.append(job)
            keys.append(text)
    return kept


def load_raw_jobs(path: str, source: str) -> List[Dict]:
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        print(f"[MERGE] No file for {source}: {path}")
        return []
    except EmptyDataError:
        print(f"[MERGE] Empty file for {source}: {path}")
        return []
    records = df.to_dict(orient="records")
    print(f"[MERGE] Loaded {len(records)} rows from {source}")
    return records


def map_adzuna_row(row: Dict) -> Dict:
    company_val = row.get("company", "")
    if isinstance(company_val, dict):
        company = company_val.get("display_name", "") or company_val.get("name", "")
    else:
        company = company_val
    if not company:
        company = row.get("company.display_name", "")

    return {
        "title": row.get("title", ""),
        "company": company,
        "location": row.get("location.display_name", "") or row.get("location", ""),
        "created": row.get("created", ""),
        "url": row.get("redirect_url", ""),
        "salary_min": row.get("salary_min"),
        "salary_max": row.get("salary_max"),
        "description": row.get("description", "") or "",
        "search_term": row.get("search_term", ""),
        "source": "adzuna",
    }


def map_jooble_row(row: Dict) -> Dict:
    url = row.get("url") or row.get("link", "")
    return {
        "title": row.get("title", ""),
        "company": row.get("company", ""),
        "location": row.get("location", ""),
        "created": row.get("created", "") or row.get("updated", ""),
        "url": url,
        "salary_min": row.get("salary_min"),
        "salary_max": row.get("salary_max"),
        "description": row.get("description", "") or row.get("snippet", "") or "",
        "search_term": row.get("search_term", ""),
        "source": "jooble",
    }


def main():
    adzuna_raw = load_raw_jobs(ADZUNA_RAW_CSV, "Adzuna")
    jooble_raw = load_raw_jobs(JOOBLE_RAW_CSV, "Jooble")

    if not adzuna_raw and not jooble_raw:
        print("[MERGE] Nothing to merge.")
        return

    normalized = [map_adzuna_row(r) for r in adzuna_raw] + [map_jooble_row(r) for r in jooble_raw]

    # Save merged raw (normalized)
    safe_save_csv(pd.DataFrame(normalized), MERGED_RAW_CSV)

    # Dedup levels
    lvl1 = dedup_by_url(normalized)
    lvl2 = dedup_by_canonical(lvl1)
    lvl3 = fuzzy_dedup(lvl2)
    print(f"[MERGE] Dedup level1 -> {len(lvl1)}, level2 -> {len(lvl2)}, level3 -> {len(lvl3)}")

    # Final filtering
    filtered = []
    for job in lvl3:
        parsed = passes_filters(job, source=job.get("source", "merged"))
        if parsed:
            filtered.append(parsed)

    df_filtered = pd.DataFrame(filtered)
    safe_save_csv(df_filtered, MERGED_FILTERED_CSV)
    safe_save_csv(df_filtered, MERGED_CSV)  # legacy path

    print(f"[MERGE] Raw merged: {len(normalized)} rows -> final filtered: {len(df_filtered)}")


if __name__ == "__main__":
    main()
