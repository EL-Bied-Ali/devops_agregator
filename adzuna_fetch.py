# ===== adzuna_fetch.py – version optimisée =====

import time
import requests
import pandas as pd
import unicodedata
from datetime import datetime, timedelta, timezone
from langdetect import detect, LangDetectException

from config import (
    ADZUNA_APP_ID, ADZUNA_APP_KEY, COUNTRY,
    SEARCH_TERMS, PRIORITY_TERMS, MAX_DAYS_OLD,
    ALLOWED_LOCATIONS_KEYWORDS, EXCLUDE_KEYWORDS,
    ROLE_REQUIRED_KEYWORDS, ROLE_FORBIDDEN_KEYWORDS,
    ADZUNA_RAW_CSV, ADZUNA_FILTERED_CSV,
)

BASE_URL = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search"


def normalize(text: str) -> str:
    """Enleve les accents et met en minuscules pour comparer proprement."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower()


def fetch_adzuna_page(page: int = 1, term: str = "devops", results_per_page: int = 50):
    """Appelle l'API Adzuna pour un terme et une page donnés."""
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
    """Retourne True si l'offre est plus recente que max_days (en UTC)."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        dt = dt.astimezone(timezone.utc)
    except Exception:
        return False

    limit = datetime.now(timezone.utc) - timedelta(days=max_days)
    return dt > limit


def location_ok(loc: str) -> bool:
    """Pour l'instant on accepte toutes les localisations (filtrage par langue et seniorite)."""
    return True
    # Si plus tard tu veux filtrer:
    # norm_loc = normalize(loc)
    # return any(normalize(k) in norm_loc for k in ALLOWED_LOCATIONS_KEYWORDS)


def no_excluded_keywords(text: str) -> bool:
    """Retourne False si un des mots-cles exclus apparait dans le texte."""
    norm = normalize(text)
    return not any(normalize(kw) in norm for kw in EXCLUDE_KEYWORDS)


def is_dutch(text: str) -> bool:
    """Retourne True si la langue detectee est le neerlandais (ou gros indice NL)."""
    try:
        snippet = (text or "")[:800]
        if not snippet.strip():
            return False

        # petit heuristique avant langdetect
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
    """
    Filtre sur le type de role :
    - exclut les jobs non-tech / data / ML / dev pur / automation industrielle
    - garde seulement les roles infra / cloud / devops / security / telecom pertinents
    """
    text = normalize((title or "") + " " + (desc or ""))

    # 1) Exclure immediatement si le role contient un mot "forbidden"
    for bad in ROLE_FORBIDDEN_KEYWORDS:
        if bad in text:
            return False

    # 2) Garder seulement si au moins un mot-cle "required" est present
    return any(good in text for good in ROLE_REQUIRED_KEYWORDS)




def compute_junior_score(title: str, desc: str) -> int:
    """
    Score "junior-friendliness" de l'annonce.
    > 0 : plutot adapte junior
    0 : neutre
    < 0 : tendance senior
    """
    text = normalize((title or "") + " " + (desc or ""))

    score = 0

    # Signaux positifs (plutot junior)
    positive_patterns = [
        "junior",
        "young graduate",
        "graduate program",
        "starter",
        "entry level",
        "trainee",
        "training program",
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

    # Signaux negatifs (tendance senior)
    negative_patterns = [
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

        "5 years",
        "5+ years",
        "4 years",
        "4+ years",
        "3+ years",

        "cloud architect",
        "devops architect",
        "senior devops",
        "senior cloud engineer",
        "senior site reliability",
        "team lead",
        "technical lead",
        "tech lead",

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
        "design scalable systems",
        "design cloud solutions",
        "make architectural decisions",
    ]

    for pat in negative_patterns:
        if pat in text:
            score -= 2

    return score


def safe_save_csv(df, path, retry_delay=3):
    """Sauvegarde un CSV, reessaie si le fichier est verrouille (Excel ouvert)."""
    while True:
        try:
            df.to_csv(path, index=False)
            print(f"[INFO] Saved file: {path}")
            break
        except PermissionError:
            print(f"[WARN] Le fichier {path} est ouvert. Ferme Excel et appuie sur Entree...")
            input()


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

    # ============================
    # MODE 1 : PAS DE FETCH (juste filtrer le fichier brut)
    # ============================
    if args.no_fetch:
        if not os.path.exists(ADZUNA_RAW_CSV):
            print(f"[ERROR] Fichier brut introuvable: {ADZUNA_RAW_CSV}")
            return

        print("[INFO] Chargement du fichier brut existant...")
        df_raw = pd.read_csv(ADZUNA_RAW_CSV)
        all_jobs = df_raw.to_dict(orient="records")

    # ============================
    # MODE 2 : FETCH + RAW
    # ============================
    else:
        for term in SEARCH_TERMS:
            print(f"[INFO] Searching for: {term}")
            page_count = PRIORITY_TERMS.get(term, 2)  # 2 pages par défaut

            for page in range(1, page_count + 1):
                data = fetch_adzuna_page(page, term)
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

    # ============================
    # FILTRAGE (avec gestion des doublons)
    # ============================
    filtered = []

    for job in all_jobs:
        created = job.get("created", "")
        loc = job.get("location", {}).get("display_name", "")
        title = job.get("title", "")
        desc = job.get("description", "") or ""
        url = job.get("redirect_url", "")
        
        bad_titles = [
        "senior",
        "medior",
        "principal",
        "expert",
        " l3 ",
        ]
        if any(bt in normalize(title) for bt in bad_titles):
            continue

        full_text = f"{title} {desc}"

        if not is_recent(created, MAX_DAYS_OLD):
            continue

        if not location_ok(loc):
            continue

        if not role_relevant(title, desc):
            continue

        if not no_excluded_keywords(full_text):
            continue

        if is_dutch(full_text):
            continue

        junior_score = compute_junior_score(title, desc)
        if junior_score <= 0:
            continue

        filtered.append({
            "title": title,
            "company": job.get("company", {}).get("display_name", ""),
            "location": loc,
            "created": created,
            "url": url,
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "description": desc[:400],
            "search_term": job.get("search_term", ""),
            "junior_score": junior_score,
            "source": "adzuna",
        })

    # DataFrame + suppression des doublons (meme url / titre / company)
    df_f = pd.DataFrame(filtered)
    before = len(df_f)
    df_f = df_f.drop_duplicates(subset=["url", "title", "company"])
    after = len(df_f)
    print(f"[INFO] Duplicates removed: {before - after}")

    safe_save_csv(df_f, ADZUNA_FILTERED_CSV)
    print(f"[INFO] Filtered saved: {len(df_f)}")



if __name__ == "__main__":
    main()
