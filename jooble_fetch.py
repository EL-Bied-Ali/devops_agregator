"""
Fetch jobs from Jooble API and apply the same filters as Adzuna.
"""

import time

import pandas as pd
import requests

from adzuna_fetch import passes_filters, safe_save_csv
from config import (
    DEFAULT_PAGES,
    JOOBLE_API_KEY,
    JOOBLE_LOCATION,
    JOOBLE_FILTERED_CSV,
    JOOBLE_RAW_CSV,
    RESULTS_PER_PAGE,
    SEARCH_TERMS,
    PAGES_PER_TERM,
)

BASE_URL = f"https://jooble.org/api/{JOOBLE_API_KEY}"


def fetch_jooble_page(term: str, page: int, results_per_page: int = RESULTS_PER_PAGE):
    payload = {
        "keywords": term,
        "page": page,
        "searchParam": {
            "pageSize": results_per_page,
        },
    }
    if JOOBLE_LOCATION:
        payload["location"] = JOOBLE_LOCATION
    try:
        resp = requests.post(BASE_URL, json=payload, timeout=12)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[WARN] Jooble error term='{term}' page={page}: {e}")
        return None


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Ne pas appeler l'API, utiliser uniquement le CSV brut existant",
    )
    args = parser.parse_args()

    all_jobs = []

    if args.no_fetch:
        if not os.path.exists(JOOBLE_RAW_CSV):
            print(f"[ERROR] Fichier brut introuvable: {JOOBLE_RAW_CSV}")
            return
        print("[INFO] Chargement du fichier brut existant Jooble...")
        df_raw = pd.read_csv(JOOBLE_RAW_CSV)
        all_jobs = df_raw.to_dict(orient="records")
    else:
        for term in SEARCH_TERMS:
            page_count = PAGES_PER_TERM.get(term, DEFAULT_PAGES)
            print(f"[INFO][Jooble] Searching '{term}' ({page_count} pages)...")
            for page in range(1, page_count + 1):
                data = fetch_jooble_page(term, page, RESULTS_PER_PAGE)
                if not data:
                    continue
                results = data.get("jobs", [])
                if not results:
                    break

                for job in results:
                    job["search_term"] = term
                    # Jooble fields harmonisation
                    if not job.get("description") and job.get("snippet"):
                        job["description"] = job.get("snippet", "")
                    if not job.get("created") and job.get("updated"):
                        job["created"] = job.get("updated")

                all_jobs.extend(results)
                time.sleep(1)

        df_raw = pd.DataFrame(all_jobs)
        safe_save_csv(df_raw, JOOBLE_RAW_CSV)
        print(f"[INFO][Jooble] Raw saved: {len(df_raw)}")

    filtered = []
    for job in all_jobs:
        parsed = passes_filters(job, source="jooble")
        if parsed:
            filtered.append(parsed)

    df_f = pd.DataFrame(filtered)
    before = len(df_f)
    df_f = df_f.drop_duplicates(subset=["url", "title", "company"])
    after = len(df_f)
    print(f"[INFO][Jooble] Duplicates removed: {before - after}")

    safe_save_csv(df_f, JOOBLE_FILTERED_CSV)
    print(f"[INFO][Jooble] Filtered saved: {len(df_f)}")


if __name__ == "__main__":
    main()
