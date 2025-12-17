# ===== adzuna_fetch.py =====
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
from langdetect import LangDetectException, detect

from config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    ADZUNA_FILTERED_CSV,
    ADZUNA_RAW_CSV,
    COUNTRY,
    DEFAULT_PAGES,
    MAX_DAYS_OLD,
    ALLOWED_LOCATIONS_KEYWORDS,
    MIN_DESCRIPTION_CHARS,
    PAGES_PER_TERM,
    REQUIRE_DESCRIPTION,
    RESULTS_PER_PAGE,
    SEARCH_TERMS,
    EXCLUDE_KEYWORDS,
    ROLE_FORBIDDEN_KEYWORDS,
    ROLE_REQUIRED_KEYWORDS,
)

BASE_URL = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search"

# Title patterns to drop immediately
BAD_TITLE_KEYWORDS = [
    "senior",
    "medior",
    "principal",
    "expert",
    " l3 ",
]


def normalize(text: str) -> str:
    """Remove accents and lower-case."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower()


def fetch_adzuna_page(page: int, term: str, results_per_page: int = RESULTS_PER_PAGE):
    """Call Adzuna API for a given term and page."""
    url = f"{BASE_URL}/{page}"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": term,
        "results_per_page": results_per_page,
        "content-type": "application/json",
    }
    print(f"[ADZUNA] Fetch page {page} for '{term}'...")
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[WARN] Error on term='{term}' page={page}: {e}")
        return None


def is_recent(date_str, max_days: int) -> bool:
    """Return True if offer is newer than max_days (UTC)."""
    try:
        dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        dt = dt.astimezone(timezone.utc)
    except Exception:
        return False

    limit = datetime.now(timezone.utc) - timedelta(days=max_days)
    return dt > limit


def location_ok(loc: str) -> bool:
    """Allow only locations that match allowed keywords (if configured)."""
    if not ALLOWED_LOCATIONS_KEYWORDS:
        return True
    norm_loc = normalize(loc)
    if not norm_loc:
        return False
    # Accept any location containing "belg" (Belgium/Belgique) or remote hints
    if "belg" in norm_loc or " remote" in norm_loc or "teletravail" in norm_loc or "telework" in norm_loc:
        return True
    return any(normalize(k) in norm_loc for k in ALLOWED_LOCATIONS_KEYWORDS)


def no_excluded_keywords(text: str) -> bool:
    """Return False if any excluded keyword appears."""
    norm = normalize(text)
    return not any(normalize(kw) in norm for kw in EXCLUDE_KEYWORDS)


def is_dutch(text: str) -> bool:
    """Return True if language looks Dutch."""
    try:
        snippet = (text or "")[:800]
        if not snippet.strip():
            return False

        norm = normalize(snippet)
        if " nederlands " in f" {norm} " or " dutch " in f" {norm} ":
            return True

        lang = detect(snippet)
        return lang == "nl"
    except LangDetectException:
        return False
    except Exception:
        return False


def role_relevant(title: str, desc: str) -> bool:
    """Keep infra / cloud / devops roles, drop forbidden ones."""
    text = normalize((title or "") + " " + (desc or ""))

    for bad in ROLE_FORBIDDEN_KEYWORDS:
        if bad in text:
            return False

    return any(good in text for good in ROLE_REQUIRED_KEYWORDS)


def compute_junior_score(title: str, desc: str) -> int:
    """Score junior-friendliness."""
    text = normalize((title or "") + " " + (desc or ""))
    score = 0

    positive_patterns = [
        "junior",
        "young graduate",
        "graduate program",
        "starter",
        "entry level",
        "trainee",
        "training program",
        "traineeship",
        "apprentice",
        "apprenticeship",
        "alternance",
        "intern",
        "internship",
        "stage",
        "stagiaire",
        "0-2 years",
        "0-3 years",
        "1-2 years experience",
        "1 to 2 years",
        "school leaver",
        "willing to learn",
        "training provided",
        "no experience required",
        "new graduate",
        "young talent",
    ]
    for pat in positive_patterns:
        if pat in text:
            score += 2

    # Heavier senior signals
    severe_negative = [
        "strong experience",
        "solid experience",
        "proven experience",
        "seasoned",
        "track record",
        "in-depth knowledge",
        "deep knowledge",
        "expertise in",
        "hands-on experience in multiple",
        "broad experience",
        "many years of experience",
        "extensive experience",
        "cloud architect",
        "devops architect",
        "senior devops",
        "senior cloud engineer",
        "senior site reliability",
        "team lead",
        "technical lead",
        "tech lead",
        "make architectural decisions",
        "design scalable systems",
        "design cloud solutions",
    ]
    for pat in severe_negative:
        if pat in text:
            score -= 2

    # Mild senior signals
    mild_negative = [
        "5 years",
        "5+ years",
        "4 years",
        "4+ years",
        "3+ years",
        "ability to mentor",
        "mentor junior",
        "coaching",
        "manage stakeholders",
        "ownership",
        "take ownership",
        "autonomous",
        "work autonomously",
        "end-to-end responsibility",
        "strategic",
        "strategic mindset",
        "contractor",
        "consultant",
    ]
    for pat in mild_negative:
        if pat in text:
            score -= 1

    return score


def safe_save_csv(df, path, retry_delay=3, max_retries=3):
    """Save CSV and retry if locked by Excel; fall back to .bak if still locked."""
    attempts = 0
    while attempts < max_retries:
        try:
            df.to_csv(path, index=False)
            print(f"[INFO] Saved file: {path}")
            return
        except PermissionError:
            attempts += 1
            print(f"[WARN] File {path} is open (attempt {attempts}/{max_retries}). Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
    # fallback
    backup = path + ".bak"
    df.to_csv(backup, index=False)
    print(f"[WARN] Could not write {path} after {max_retries} attempts. Saved to {backup} instead.")


def passes_filters(job: dict, source: str = "adzuna") -> dict | None:
    """Apply common filters and return normalized job if it passes."""
    created = job.get("created", "") or job.get("updated", "")

    loc = job.get("location", "")
    if isinstance(loc, dict):
        loc = loc.get("display_name", "")
    if not loc:
        loc = job.get("location.display_name", "")

    title = job.get("title", "") or ""
    desc = job.get("description", "") or ""
    url = job.get("redirect_url", "") or job.get("url", "") or job.get("link", "")
    canonical_url = url.split("?", 1)[0] if url else ""

    company_val = job.get("company", "")
    if isinstance(company_val, dict):
        company = company_val.get("display_name", "") or company_val.get("name", "")
    else:
        company = company_val or job.get("company.display_name", "")

    if REQUIRE_DESCRIPTION and len(desc.strip()) < MIN_DESCRIPTION_CHARS:
        return None

    norm_title = normalize(title)
    if any(bt in norm_title for bt in BAD_TITLE_KEYWORDS):
        return None

    full_text = f"{title} {desc}"

    if not is_recent(created, MAX_DAYS_OLD):
        return None

    if not location_ok(loc):
        return None

    if not role_relevant(title, desc):
        return None

    if not no_excluded_keywords(full_text):
        return None

    if is_dutch(full_text):
        return None

    # Autoriser les offres neutres (score >= 0) pour ne pas filtrer trop agressivement
    junior_score = compute_junior_score(title, desc)
    # Exclure les annonces au score clairement négatif, garder neutre ou positif
    if junior_score < 0:
        return None

    return {
        "title": title,
        "company": company,
        "location": loc,
        "created": created,
        "url": url,
        "canonical_url": canonical_url,
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "description": desc[:400],
        "search_term": job.get("search_term", ""),
        "junior_score": junior_score,
        "source": source,
    }


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
        if not os.path.exists(ADZUNA_RAW_CSV):
            print(f"[ERROR] Fichier brut introuvable: {ADZUNA_RAW_CSV}")
            return
        print("[INFO] Chargement du fichier brut existant...")
        df_raw = pd.read_csv(ADZUNA_RAW_CSV)
        all_jobs = df_raw.to_dict(orient="records")
    else:
        for term in SEARCH_TERMS:
            print(f"[INFO] Searching for: {term}")
            page_count = PAGES_PER_TERM.get(term, DEFAULT_PAGES)

            for page in range(1, page_count + 1):
                data = fetch_adzuna_page(page, term, RESULTS_PER_PAGE)
                if not data:
                    continue

                results = data.get("results", [])
                if not results:
                    break

                for job in results:
                    job["search_term"] = term

                all_jobs.extend(results)
                time.sleep(1)

        df_raw = pd.json_normalize(all_jobs)
        safe_save_csv(df_raw, ADZUNA_RAW_CSV)
        print(f"[INFO] Raw saved: {len(df_raw)}")

    # Filtering
    filtered = []
    for job in all_jobs:
        parsed = passes_filters(job, source="adzuna")
        if parsed:
            filtered.append(parsed)

    df_f = pd.DataFrame(filtered)
    before = len(df_f)
    if "canonical_url" not in df_f.columns:
        df_f["canonical_url"] = df_f["url"].str.split("?", n=1).str[0]
    df_f = df_f.drop_duplicates(subset=["canonical_url", "title", "company"])
    after = len(df_f)
    print(f"[INFO] Duplicates removed: {before - after}")

    safe_save_csv(df_f, ADZUNA_FILTERED_CSV)
    print(f"[INFO] Filtered saved: {len(df_f)}")


if __name__ == "__main__":
    main()
