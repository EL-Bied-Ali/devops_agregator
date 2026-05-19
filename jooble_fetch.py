"""
Fetch jobs from Jooble API and apply the same filters as Adzuna.
"""

import time

import pandas as pd
import requests
from pandas.errors import EmptyDataError

from adzuna_fetch import configure_market, passes_filters, safe_save_csv
from config import (
    DEFAULT_PAGES,
    JOOBLE_API_KEY,
    RESULTS_PER_PAGE,
    PAGES_PER_TERM,
    SUPPORTED_CH_FOCUS,
    SUPPORTED_FILTER_MODES,
    SUPPORTED_MARKETS,
    get_market_profile,
    get_output_paths,
    require_jooble_credentials,
    resolve_filter_mode,
)

BASE_URL = f"https://jooble.org/api/{JOOBLE_API_KEY}"


def build_filtered_df(all_jobs: list[dict], filter_mode: str) -> pd.DataFrame:
    filtered = []
    resolved_mode = resolve_filter_mode(filter_mode, allow_both=False)
    for job in all_jobs:
        parsed = passes_filters(job, source="jooble", filter_mode=resolved_mode)
        if parsed:
            filtered.append(parsed)

    df_f = pd.DataFrame(filtered)
    before = len(df_f)
    if not df_f.empty:
        df_f = df_f.drop_duplicates(subset=["url", "title", "company"])
    after = len(df_f)
    print(f"[INFO][Jooble][{resolved_mode}] Duplicates removed: {before - after}")
    print(f"[INFO][Jooble][{resolved_mode}] Filtered kept: {len(df_f)}")
    return df_f


def fetch_jooble_page(
    term: str,
    page: int,
    jooble_location: str = "",
    results_per_page: int = RESULTS_PER_PAGE,
):
    payload = {
        "keywords": term,
        "page": page,
        "searchParam": {
            "pageSize": results_per_page,
        },
    }
    if jooble_location:
        payload["location"] = jooble_location
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
        "--market",
        choices=SUPPORTED_MARKETS,
        default="",
        help="Market mode (be|ch). Defaults to JOB_MARKET env var or be.",
    )
    parser.add_argument(
        "--ch-focus",
        choices=SUPPORTED_CH_FOCUS,
        default="",
        help="CH focus mode (all|romandie). Defaults to JOB_CH_FOCUS env var or all.",
    )
    parser.add_argument(
        "--filter-mode",
        choices=SUPPORTED_FILTER_MODES,
        default="",
        help="Filtering strictness (strict|broad|both). Defaults to JOB_FILTER_MODE env var or strict.",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Ne pas appeler l'API, utiliser uniquement le CSV brut existant",
    )
    args = parser.parse_args()

    market = configure_market(args.market, args.ch_focus)
    selected_filter_mode = resolve_filter_mode(args.filter_mode, allow_both=True)
    market_profile = get_market_profile(market, args.ch_focus)
    output_paths = get_output_paths(market)
    jooble_raw_csv = output_paths["jooble_raw_csv"]
    jooble_filtered_csv = output_paths["jooble_filtered_csv"]
    jooble_filtered_strict_csv = output_paths["jooble_filtered_strict_csv"]
    jooble_filtered_broad_csv = output_paths["jooble_filtered_broad_csv"]
    jooble_location = market_profile["jooble_location"]
    search_terms = market_profile["search_terms"]
    print(
        f"[INFO][Jooble] Market={market} location='{jooble_location or 'none'}' "
        f"ch_focus={market_profile['ch_focus']} "
        f"langs={market_profile['allowed_language_codes']} terms={len(search_terms)} "
        f"filter_mode={selected_filter_mode}"
    )

    all_jobs = []

    if args.no_fetch:
        if not os.path.exists(jooble_raw_csv):
            print(f"[ERROR] Fichier brut introuvable: {jooble_raw_csv}")
            return
        print("[INFO] Chargement du fichier brut existant Jooble...")
        try:
            df_raw = pd.read_csv(jooble_raw_csv)
            all_jobs = df_raw.to_dict(orient="records")
        except EmptyDataError:
            print(f"[WARN] Fichier brut vide: {jooble_raw_csv}")
            all_jobs = []
    else:
        if not market_profile.get("supports_jooble", True):
            raise RuntimeError(f"Jooble fetch is not supported for market '{market}'.")
        require_jooble_credentials()
        for term in search_terms:
            page_count = PAGES_PER_TERM.get(term, DEFAULT_PAGES)
            print(f"[INFO][Jooble] Searching '{term}' ({page_count} pages)...")
            for page in range(1, page_count + 1):
                data = fetch_jooble_page(
                    term,
                    page,
                    jooble_location=jooble_location,
                    results_per_page=RESULTS_PER_PAGE,
                )
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
        safe_save_csv(df_raw, jooble_raw_csv)
        print(f"[INFO][Jooble] Raw saved: {len(df_raw)}")

    if selected_filter_mode in ("strict", "both"):
        df_strict = build_filtered_df(all_jobs, filter_mode="strict")
        safe_save_csv(df_strict, jooble_filtered_strict_csv)
        safe_save_csv(df_strict, jooble_filtered_csv)
        print(f"[INFO][Jooble] Strict filtered saved: {len(df_strict)}")

    if selected_filter_mode in ("broad", "both"):
        df_broad = build_filtered_df(all_jobs, filter_mode="broad")
        safe_save_csv(df_broad, jooble_filtered_broad_csv)
        if selected_filter_mode == "broad":
            safe_save_csv(df_broad, jooble_filtered_csv)
        print(f"[INFO][Jooble] Broad filtered saved: {len(df_broad)}")


if __name__ == "__main__":
    main()
