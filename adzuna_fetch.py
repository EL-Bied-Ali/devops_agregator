# ===== adzuna_fetch.py =====
import os
import re
import subprocess
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from html import unescape
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import requests
from langdetect import LangDetectException, detect

try:
    import ftfy
except Exception:
    ftfy = None

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

from config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    DEFAULT_FILTER_MODE,
    DEFAULT_PAGES,
    EXPERIENCE_HARD_BLOCK_PHRASES,
    EXPERIENCE_SOFT_BLOCK_PHRASES,
    EXTRA_BAD_TITLE_KEYWORDS,
    JOB_MODE,
    MAX_DAYS_OLD,
    MIN_DESCRIPTION_CHARS,
    PAGES_PER_TERM,
    PRIORITY_TERMS,
    REQUIRE_DESCRIPTION,
    RESULTS_PER_PAGE,
    SEARCH_TERMS,
    EXCLUDE_KEYWORDS,
    ROLE_FORBIDDEN_KEYWORDS,
    ROLE_REQUIRED_KEYWORDS,
    SPEED_ROLE_TARGETS,
    SUPPORTED_CH_FOCUS,
    SUPPORTED_FILTER_MODES,
    SUPPORTED_MARKETS,
    get_market_profile,
    get_output_paths,
    resolve_ch_focus,
    resolve_filter_mode,
    resolve_market,
)

# Title patterns to drop immediately
DEFAULT_BAD_TITLE_KEYWORDS = [
    "senior",
    "medior",
    "principal",
    "expert",
    " l3 ",
]
BAD_TITLE_KEYWORDS = DEFAULT_BAD_TITLE_KEYWORDS + list(EXTRA_BAD_TITLE_KEYWORDS)

# Phrases where senior/lead terms are benign (mentoring/supervision)
EXCLUDE_EXCEPTIONS = [
    "under guidance from senior",
    "under guidance of senior",
    "guidance from senior",
    "under supervision of senior",
    "supervision of senior",
    "mentored by senior",
    "mentored by a senior",
    "supported by senior",
    "working with senior engineers",
    "supporting senior engineers",
    "reporting to senior",
    "reports to senior",
    "managerial team",
    "accountmanager",
    "vergelijkbare vacatures senior",
    "user hardware",
    "hardware and peripherals",
]

# Leadership/seniority words that should only hard-block when present in title.
TITLE_ONLY_EXCLUDE = {
    "manager",
    "lead",
    "director",
    "head",
    "head of",
    "principal",
    "expert",
    "architect",
    "team lead",
    "tech lead",
}

ACTIVE_MARKET = ""
ACTIVE_CH_FOCUS = "all"
ACTIVE_FILTER_MODE = DEFAULT_FILTER_MODE
ACTIVE_JOB_MODE = JOB_MODE
ACTIVE_MARKET_PROFILE = {}
ACTIVE_OUTPUT_PATHS = {}
ACTIVE_PRIORITY_TERMS = {}
BASE_URL = ""

AUTO_CLOSE_EXCEL_ON_LOCK = os.getenv("JOB_AUTO_CLOSE_EXCEL_ON_LOCK", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
FORCE_KILL_EXCEL_ON_LOCK = os.getenv("JOB_FORCE_KILL_EXCEL_ON_LOCK", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}


def configure_market(market: str = "", ch_focus: str = "") -> str:
    """Configure market-specific country/location/language/output settings."""
    global ACTIVE_MARKET, ACTIVE_CH_FOCUS, ACTIVE_MARKET_PROFILE, ACTIVE_OUTPUT_PATHS, ACTIVE_PRIORITY_TERMS, BASE_URL
    global SEARCH_TERMS, EXCLUDE_KEYWORDS, ROLE_FORBIDDEN_KEYWORDS, ROLE_REQUIRED_KEYWORDS, BAD_TITLE_KEYWORDS

    ACTIVE_MARKET = resolve_market(market)
    ACTIVE_CH_FOCUS = resolve_ch_focus(ch_focus) if ACTIVE_MARKET == "ch" else "all"
    ACTIVE_MARKET_PROFILE = get_market_profile(ACTIVE_MARKET, ACTIVE_CH_FOCUS)
    ACTIVE_OUTPUT_PATHS = get_output_paths(ACTIVE_MARKET)
    BASE_URL = f"https://api.adzuna.com/v1/api/jobs/{ACTIVE_MARKET_PROFILE['adzuna_country']}/search"
    SEARCH_TERMS = list(ACTIVE_MARKET_PROFILE.get("search_terms", SEARCH_TERMS))
    EXCLUDE_KEYWORDS = list(ACTIVE_MARKET_PROFILE.get("exclude_keywords", EXCLUDE_KEYWORDS))
    ROLE_FORBIDDEN_KEYWORDS = list(ACTIVE_MARKET_PROFILE.get("role_forbidden_keywords", ROLE_FORBIDDEN_KEYWORDS))
    ROLE_REQUIRED_KEYWORDS = list(ACTIVE_MARKET_PROFILE.get("role_required_keywords", ROLE_REQUIRED_KEYWORDS))
    BAD_TITLE_KEYWORDS = list(DEFAULT_BAD_TITLE_KEYWORDS) + list(
        ACTIVE_MARKET_PROFILE.get("extra_bad_title_keywords", [])
    )
    ACTIVE_PRIORITY_TERMS = dict(PRIORITY_TERMS)
    if ACTIVE_MARKET == "ch":
        ACTIVE_PRIORITY_TERMS.update(
            {
                "it support": 8,
                "support informatique": 8,
                "application support engineer": 8,
                "system administrator": 8,
                "linux system administrator": 8,
                "cloud support": 8,
                "it operations": 7,
                "operations engineer": 7,
                "network operations engineer": 7,
                "security operations engineer": 6,
                "it trainee": 6,
                "it intern": 6,
                "stage informatique": 5,
                "junior": 4,
                "graduate": 3,
            }
        )
    return ACTIVE_MARKET


configure_market()


def clean_text(text: str) -> str:
    """Best-effort fix for common mojibake sequences from source feeds."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    if ftfy is not None:
        try:
            text = ftfy.fix_text(text)
        except Exception:
            pass

    common_replacements = {
        "\xC3\xA9": "\u00e9",
        "\xC3\xA8": "\u00e8",
        "\xC3\xAA": "\u00ea",
        "\xC3\xAB": "\u00eb",
        "\xC3\xA0": "\u00e0",
        "\xC3\xA2": "\u00e2",
        "\xC3\xA7": "\u00e7",
        "\xC3\xB9": "\u00f9",
        "\xC3\xBB": "\u00fb",
        "\xC3\xB4": "\u00f4",
        "\xC3\xAE": "\u00ee",
        "\xC3\xAF": "\u00ef",
        "\xC3\x83\xC2\xA9": "\u00e9",
        "\xC3\x83\xC2\xA8": "\u00e8",
        "\xC3\x83\xC2\xAA": "\u00ea",
        "\xC3\x83\xC2\xAB": "\u00eb",
        "\xE2\x80\x99": "'",
        "\xE2\x80\x93": "-",
        "\xE2\x80\x94": "-",
        "\xE2\x80\x9C": '"',
        "\xE2\x80\x9D": '"',
        "ÃƒÂ©": "\u00e9",
        "ÃƒÂ¨": "\u00e8",
        "ÃƒÂª": "\u00ea",
        "ÃƒÂ«": "\u00eb",
        "ÃƒÂ ": "\u00e0",
        "ÃƒÂ¢": "\u00e2",
        "ÃƒÂ§": "\u00e7",
        "ÃƒÂ¹": "\u00f9",
        "ÃƒÂ»": "\u00fb",
        "ÃƒÂ´": "\u00f4",
        "ÃƒÂ®": "\u00ee",
        "ÃƒÂ¯": "\u00ef",
        "Ã¢â‚¬â„¢": "'",
        "Ã¢â‚¬â€œ": "-",
        "Ã¢â‚¬â€": "-",
        "Ã¢â‚¬Å“": '"',
        "Ã¢â‚¬\x9d": '"',
    }
    for broken, fixed in common_replacements.items():
        text = text.replace(broken, fixed)

    return text


_HTML_SIGNAL_PATTERN = re.compile(r"<\s*(html|body|div|span|p|br|ul|li|section|article|script|style)\b", flags=re.I)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_PATTERN = re.compile(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>")


def looks_like_html(text: str) -> bool:
    raw = str(text or "")
    if not raw:
        return False
    if _HTML_SIGNAL_PATTERN.search(raw):
        return True
    if len(_HTML_TAG_PATTERN.findall(raw)) >= 4:
        return True
    return False


def html_to_plain_text(text: str) -> str:
    raw = unescape(clean_text(text or ""))
    if not raw:
        return ""
    if BeautifulSoup is not None:
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        plain = " ".join(chunk.strip() for chunk in soup.stripped_strings)
    else:
        plain = _SCRIPT_STYLE_PATTERN.sub(" ", raw)
        plain = _HTML_TAG_PATTERN.sub(" ", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain


def rule_plain_text(text: Any) -> str:
    if text is None:
        return ""
    raw = unescape(clean_text(str(text)))
    if not raw:
        return ""
    if looks_like_html(raw):
        return html_to_plain_text(raw)
    if "<" in raw and ">" in raw and _HTML_TAG_PATTERN.search(raw):
        raw = _SCRIPT_STYLE_PATTERN.sub(" ", raw)
        raw = _HTML_TAG_PATTERN.sub(" ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def normalize_text(text: str) -> str:
    """Canonical normalization for filtering and scoring."""
    text = rule_plain_text(text)
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize(text: str) -> str:
    """Backward-compatible alias."""
    return normalize_text(text)


def job_text_for_rules(job: dict | None = None, **overrides) -> tuple[str, str]:
    """
    Build normalized + cleaned plain text for rules from title/description/company/location.
    Returns: (normalized_text, cleaned_text)
    """
    payload = dict(job or {})
    payload.update({k: v for k, v in overrides.items() if v is not None})
    title = rule_plain_text(payload.get("title", ""))
    desc = rule_plain_text(payload.get("description", ""))
    company_val = payload.get("company", "")
    if isinstance(company_val, dict):
        company_val = company_val.get("display_name", "") or company_val.get("name", "")
    company = rule_plain_text(company_val)
    loc = payload.get("location", "") or payload.get("location.display_name", "")
    if isinstance(loc, dict):
        loc = loc.get("display_name", "")
    location = rule_plain_text(loc)
    combined = " ".join(part for part in [title, desc, company, location] if part).strip()
    return normalize_text(combined), combined


def keyword_hit(text: str, keyword: str, boundary_only: bool = True) -> bool:
    """
    Keyword match with safer boundaries to reduce substring false positives.
    Example fixed: expert vs expertise, host vs hosting, coo vs coordinate.
    """
    txt = normalize(text or "")
    kw = normalize(keyword or "").strip()
    if not txt or not kw:
        return False

    if boundary_only and re.fullmatch(r"[a-z0-9 ]+", kw):
        pattern = r"(?<![a-z0-9])" + re.escape(kw).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
        return re.search(pattern, txt) is not None

    return kw in txt


def keyword_match(text: str, kw: str) -> bool:
    """
    Match a keyword with safer semantics for exclude keyword checks:
    - Multi-word / non-word keywords => case-insensitive substring.
    - Single token keywords => whole-word regex match.
    """
    txt_norm = normalize_text(text or "")
    kw_norm = normalize_text(kw or "").strip()
    if not txt_norm or not kw_norm:
        return False

    if " " in kw_norm or re.search(r"\W", kw_norm):
        return kw_norm in txt_norm

    return re.search(rf"\b{re.escape(kw_norm)}\b", txt_norm, flags=re.IGNORECASE) is not None


def extract_adzuna_job_id(url: str) -> str:
    """Extract numeric job id from Adzuna details/land URLs."""
    if not url:
        return ""
    m = re.search(r"/(?:details|land/ad)/(\d+)", str(url))
    return m.group(1) if m else ""


def canonicalize_url(url: str) -> str:
    """
    Build a stable canonical URL for dedup/tracking.
    - Strip query params
    - Normalize Adzuna land/ad URLs to details/<id> when possible
    """
    base = (url or "").split("?", 1)[0].strip()
    if not base:
        return ""
    parsed = urlparse(base)
    netloc = (parsed.netloc or "").lower()
    if "adzuna." in netloc:
        job_id = extract_adzuna_job_id(base)
        if job_id and parsed.scheme:
            return f"{parsed.scheme}://{parsed.netloc}/details/{job_id}"
    return base


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
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=15)
            # Retry on transient 5xx (e.g., 502)
            if resp.status_code >= 500:
                raise requests.HTTPError(f"{resp.status_code} {resp.reason}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[WARN] Error on term='{term}' page={page} attempt {attempt + 1}/3: {e}")
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
            else:
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


REMOTE_TERMS = [
    "remote",
    "fully remote",
    "teletravail",
    "telework",
    "work from home",
    "home office",
    "wfh",
    "distributed",
]

HYBRID_TERMS = [
    "hybrid",
    "hybride",
    "2 days onsite",
    "3 days onsite",
]

ONSITE_TERMS = [
    "on site",
    "on-site",
    "onsite",
    "presentiel",
    "office based",
    "site based",
]


def detect_work_mode(title: str, desc: str, loc: str) -> str:
    """Return remote/hybrid/onsite/unknown from job text hints."""
    text = normalize_text(f"{title or ''} {desc or ''} {loc or ''}")
    has_hybrid = any(keyword_hit(text, term, boundary_only=True) for term in HYBRID_TERMS)
    has_remote = any(keyword_hit(text, term, boundary_only=True) for term in REMOTE_TERMS)
    has_onsite = any(keyword_hit(text, term, boundary_only=True) for term in ONSITE_TERMS)

    if has_hybrid:
        return "hybrid"
    if has_remote and has_onsite:
        return "hybrid"
    if has_remote:
        return "remote"
    if has_onsite:
        return "onsite"
    return "unknown"


def is_remote_job(title: str, desc: str, loc: str) -> bool:
    return detect_work_mode(title, desc, loc) in {"remote", "hybrid"}


def location_ok(loc: str, title: str = "", desc: str = "") -> bool:
    """Return True if location is acceptable for the active market."""
    if ACTIVE_MARKET == "ch" and is_remote_job(title, desc, loc):
        combined = normalize(f"{loc or ''} {title or ''} {desc or ''}")
        foreign_keywords = ACTIVE_MARKET_PROFILE.get("foreign_location_keywords", [])
        has_foreign = any(normalize(kw) in combined for kw in foreign_keywords)
        swiss_markers = ACTIVE_MARKET_PROFILE.get("allowed_location_keywords", [])
        has_swiss = any(normalize(marker) in combined for marker in swiss_markers)
        return not (has_foreign and not has_swiss)

    if not ACTIVE_MARKET_PROFILE.get("enforce_location_filter", True):
        # Relaxed mode for CH: don't care about canton/city, but avoid clearly foreign jobs.
        if ACTIVE_MARKET != "ch":
            return True

        combined = normalize(f"{loc or ''} {title or ''} {desc or ''}")
        foreign_keywords = ACTIVE_MARKET_PROFILE.get("foreign_location_keywords", [])
        has_foreign = any(normalize(kw) in combined for kw in foreign_keywords)

        swiss_markers = ACTIVE_MARKET_PROFILE.get("allowed_location_keywords", [])
        has_swiss = any(normalize(marker) in combined for marker in swiss_markers)

        if has_foreign and not has_swiss:
            return False
        return True

    if loc:
        norm_loc = normalize(loc)
        blocked_keywords = ACTIVE_MARKET_PROFILE.get("blocked_location_keywords", [])
        if any(normalize(kw) in norm_loc for kw in blocked_keywords):
            return False

    keywords = ACTIVE_MARKET_PROFILE.get("allowed_location_keywords", [])
    if not keywords:
        return True
    if not loc:
        # Keep unknown locations to avoid false negatives from sparse APIs.
        return True
    norm_loc = normalize(loc)
    return any(normalize(kw) in norm_loc for kw in keywords)


def _strip_exclude_exceptions(text: str) -> str:
    """Remove benign phrases before exclude-keyword matching."""
    norm = normalize_text(text or "")
    norm_padded = f" {norm} "
    for exc in EXCLUDE_EXCEPTIONS:
        exc_norm = normalize_text(exc)
        if not exc_norm:
            continue
        norm_padded = norm_padded.replace(f" {exc_norm} ", " ")
        norm_padded = norm_padded.replace(exc_norm, " ")
    return re.sub(r"\s+", " ", norm_padded).strip()


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    """Return all matching keywords (order preserved) after exception cleanup."""
    filtered_text = _strip_exclude_exceptions(text)
    hits = []
    for kw in keywords:
        if keyword_match(filtered_text, kw):
            hits.append(kw)
    return hits


def excluded_hits(text: str) -> list[str]:
    """Return list of excluded keywords, ignoring configured exception phrases."""
    return keyword_hits(text, EXCLUDE_KEYWORDS)


def no_excluded_keywords(text: str) -> bool:
    """Return False if any excluded keyword appears."""
    return not excluded_hits(text)


LEAD_TITLE_MARKERS = [
    "lead",
    "team lead",
    "tech lead",
    "technical lead",
    "chapter lead",
    "manager",
    "head of",
    "director",
]


def title_has_lead_or_manager(title: str) -> bool:
    title_norm = normalize_text(title or "")
    return any(keyword_hit(title_norm, marker, boundary_only=True) for marker in LEAD_TITLE_MARKERS)


def classify_excluded_hits(title: str, text: str) -> tuple[list[str], list[str]]:
    """
    Split exclude hits into hard vs soft.
    Lead mentions outside title are kept for manual review (soft).
    """
    hits = excluded_hits(text)
    if not hits:
        return [], []

    hard_hits: list[str] = []
    soft_hits: list[str] = []
    for hit in hits:
        if normalize_text(hit) in TITLE_ONLY_EXCLUDE and not keyword_match(title, hit):
            soft_hits.append(hit)
        else:
            hard_hits.append(hit)
    return hard_hits, soft_hits


def run_exclude_keyword_self_tests():
    """Quick local checks for exclude-keyword false-positive reductions."""
    print("[SELFTEST] Exclude keyword matching")

    title_1 = "Operations Graduate Program - Platform Trainee"
    desc_1 = "You will be supported by a manager during onboarding."
    hard_1, soft_1 = classify_excluded_hits(title_1, f"{title_1} {desc_1}")
    pass_1 = ("manager" not in [normalize_text(h) for h in hard_1]) and (
        "manager" in [normalize_text(s) for s in soft_1] or not keyword_match(desc_1, "manager")
    )
    print(
        f"[SELFTEST] manager in description only => hard={hard_1} soft={soft_1} "
        f"expected=no hard manager | {'PASS' if pass_1 else 'FAIL'}"
    )

    title_2 = "IT Manager"
    hard_2, soft_2 = classify_excluded_hits(title_2, title_2)
    pass_2 = "manager" in [normalize_text(h) for h in hard_2]
    print(
        f"[SELFTEST] manager in title => hard={hard_2} soft={soft_2} "
        f"expected=hard manager | {'PASS' if pass_2 else 'FAIL'}"
    )

    title_3 = "Cloud Architect"
    hard_3, soft_3 = classify_excluded_hits(title_3, title_3)
    pass_3 = "architect" in [normalize_text(h) for h in hard_3]
    print(
        f"[SELFTEST] architect in title => hard={hard_3} soft={soft_3} "
        f"expected=hard architect | {'PASS' if pass_3 else 'FAIL'}"
    )

    desc_4 = "You will own cloud architecture and platform patterns."
    hard_4, soft_4 = classify_excluded_hits("Cloud Engineer", desc_4)
    pass_4 = "architect" not in [normalize_text(x) for x in (hard_4 + soft_4)]
    print(
        f"[SELFTEST] architecture vs architect => hard={hard_4} soft={soft_4} "
        f"expected=no architect hit | {'PASS' if pass_4 else 'FAIL'}"
    )


def run_self_checks():
    """
    Minimal executable self-checks for language and experience policy.
    Designed for quick local validation without external test frameworks.
    """
    print("[SELFCHECK] Running language/experience checks...")
    passed = 0
    total = 0

    def check(label: str, condition: bool, details: str = ""):
        nonlocal passed, total
        total += 1
        ok = bool(condition)
        if ok:
            passed += 1
        suffix = f" | {details}" if details else ""
        print(f"[SELFCHECK] {label}: {'PASS' if ok else 'FAIL'}{suffix}")

    # 1) Dutch as plus/asset should NOT be mandatory.
    case_1 = "English required. Dutch is a plus."
    need_1 = classify_language_need(case_1)
    check(
        "Dutch plus => preferred not required",
        need_1["prefers_dutch"] and not need_1["requires_dutch"],
        f"signals={need_1.get('signals', [])}",
    )

    # 2) Dutch mandatory should stay blocked.
    case_2 = "Fluent Dutch required for this role."
    need_2 = classify_language_need(case_2)
    check(
        "Dutch mandatory => required",
        need_2["requires_dutch"] and blocked_language_requirement_reason(case_2, "strict") != "",
    )

    # 3) Dutch mandatory in Dutch.
    case_3 = "Nederlands verplicht. Frans is een plus."
    need_3 = classify_language_need(case_3)
    check(
        "Nederlands verplicht => required",
        need_3["requires_dutch"] and blocked_language_requirement_reason(case_3, "strict") != "",
    )

    # 4) FR or Dutch should be acceptable without Dutch.
    case_4 = "French or Dutch required. English is a plus."
    need_4 = classify_language_need(case_4)
    check(
        "French or Dutch => acceptable alternative",
        need_4["acceptable_without_dutch"] and blocked_language_requirement_reason(case_4, "strict") == "",
    )

    # 5) FR/NL short notation should be acceptable.
    case_5 = "Languages: FR/NL. English appreciated."
    need_5 = classify_language_need(case_5)
    check(
        "FR/NL => acceptable alternative",
        need_5["acceptable_without_dutch"] and not need_5["requires_dutch"],
    )

    # 6) Explicit bilingual requirement remains blocked.
    case_6 = "Fluent in French and Dutch required."
    need_6 = classify_language_need(case_6)
    check(
        "French and Dutch required => blocked",
        need_6["requires_dutch"] and blocked_language_requirement_reason(case_6, "strict") != "",
    )

    # 7) English-only remains acceptable.
    case_7 = "English only. Distributed team."
    need_7 = classify_language_need(case_7)
    check(
        "English only => not blocked",
        need_7["english_only"] and blocked_language_requirement_reason(case_7, "strict") == "",
    )

    # 8) 2-3 years + junior should not hard block.
    title_8 = "Junior Cloud Engineer"
    desc_8 = "2-3 years experience in Linux and cloud. Training provided."
    lvl_8, detail_8, years_8 = detect_experience_requirement_details(title_8, desc_8)
    check(
        "2-3 years + junior => manual/soft",
        lvl_8 in {"soft", "soft_junior_title"} and lvl_8 != "hard",
        f"level={lvl_8} detail={detail_8} years={years_8}",
    )

    # 9) 3+ years + trainee signals should not hard block.
    title_9 = "Platform Trainee"
    desc_9 = "3+ years experience preferred. We hire for potential and will be trained."
    lvl_9, detail_9, years_9 = detect_experience_requirement_details(title_9, desc_9)
    check(
        "3+ years + trainee signals => no hard block",
        lvl_9 in {"soft", "soft_junior_title"},
        f"level={lvl_9} detail={detail_9} years={years_9}",
    )
    check(
        "3+ years + trainee => conflict reason kept",
        "years_required_conflict_but_junior_signals" in normalize_text(detail_9),
        f"detail={detail_9}",
    )

    # 10) 5+ years stays hard block.
    title_10 = "Junior DevOps Engineer"
    desc_10 = "Minimum 5 years of experience required."
    lvl_10, detail_10, years_10 = detect_experience_requirement_details(title_10, desc_10)
    check(
        "5+ years => hard block",
        lvl_10 == "hard",
        f"level={lvl_10} detail={detail_10} years={years_10}",
    )

    # Keep previous keyword-specific checks.
    run_exclude_keyword_self_tests()
    print(f"[SELFCHECK] Summary: {passed}/{total} checks passed")


LANGUAGE_TERMS = {
    "fr": ["french", "francais", "francophone"],
    "en": ["english", "anglais", "anglophone"],
    "nl": ["dutch", "nederlands", "neerlandais"],
    "de": ["german", "deutsch", "allemand"],
}

LANGUAGE_REQUIRED_PATTERNS = {
    "nl": [
        r"\bdutch\s+(?:is\s+)?mandatory\b",
        r"\bmandatory\s+dutch\b",
        r"\bmust\s+speak\s+dutch\b",
        r"\bdutch\s+required\b",
        r"\bfluent\s+dutch\s+required\b",
        r"\bexcellent\s+command\s+of\s+dutch\b",
        r"\bnative\s+dutch\b",
        r"\bbilingual\s+dutch\b",
        r"\btweetalig(?:\s+\w+){0,3}\s+\bnl\b",
        r"\bc1\s+dutch\s+required\b",
        r"\bnederlands\s+vereist\b",
        r"\bnederlands\s+is\s+verplicht\b",
        r"\bnederlands\s+verplicht\b",
        r"\bmoet\s+nederlands\s+spreken\b",
        r"\bneerlandais\s+obligatoire\b",
        r"\bneerlandais\s+requis\b",
        r"\bgoede\s+kennis\s+(?:van\s+)?nederlands\s+is\s+vereist\b",
        r"\bbonne\s+maitrise\s+du\s+neerlandais\b",
        r"\bbonne\s+maitrise\s+du\s+francais\s+et\s+du\s+neerlandais\b",
    ],
    "de": [
        r"\bgerman\s+(?:is\s+)?mandatory\b",
        r"\bmandatory\s+german\b",
        r"\bmust\s+speak\s+german\b",
        r"\bgerman\s+required\b",
        r"\bfluent\s+german\s+required\b",
        r"\bexcellent\s+command\s+of\s+german\b",
        r"\bnative\s+german\b",
        r"\bdeutsch\s+erforderlich\b",
        r"\bdeutschkenntnisse\s+erforderlich\b",
        r"\ballemand\s+obligatoire\b",
        r"\ballemand\s+requis\b",
    ],
}

LANGUAGE_OPTIONAL_PATTERNS = {
    "nl": [
        r"\bdutch\s+is\s+a\s+plus\b",
        r"\bdutch\s+would\s+be\s+a\s+plus\b",
        r"\bnice\s+to\s+have\s+dutch\b",
        r"\bdutch\s+is\s+a\s+nice\s+to\s+have\b",
        r"\bdutch\s+is\s+an\s+asset\b",
        r"\bdutch\s+is\s+a\s+strong\s+asset\b",
        r"\bknowledge\s+of\s+dutch\s+is\s+a\s+plus\b",
        r"\bnederlands\s+is\s+een\s+plus\b",
        r"\bkennis\s+van\s+nederlands\s+is\s+een\s+plus\b",
        r"\bneerlandais\s+est\s+un\s+atout\b",
        r"\bneerlandais\s+(?:est|serait)\s+un\s+plus\b",
        r"\ble\s+neerlandais\s+est\s+un\s+plus\b",
        r"\ble\s+neerlandais\s+est\s+un\s+atout\b",
        r"\bneerlandais\s+souhaite\b",
        r"\bneerlandais\s+apprecie\b",
        r"\ble\s+neerlandais\s+serait\s+apprecie\b",
        r"\bdutch\s+is\s+a\s+bonus\b",
    ]
}

LANGUAGE_REQUIRED_CUE_RE = re.compile(
    r"\b(required|mandatory|must\s+speak|must\s+have|obligatoire|obligatoirement|requis|requise|"
    r"verplicht|vereist|necessary|necessaire|indispensable|exige|exigee|fluent|native|c1|c2|"
    r"excellent\s+command|strong\s+command|very\s+good\s+knowledge|bonne\s+maitrise|maitrise)\b"
)
LANGUAGE_OPTIONAL_CUE_RE = re.compile(
    r"\b(plus|nice\s+to\s+have|asset|atout|bonus|souhaite|apprecie|"
    r"serait\s+apprecie|serait\s+un\s+plus|est\s+un\s+plus|est\s+un\s+atout)\b"
)
LANGUAGE_ALTERNATIVE_RE = re.compile(r"\b(or|ou|of)\b")
LANGUAGE_TRILINGUAL_RE = re.compile(r"\b(trilingual|trilingue|drie(?:talig|talige))\b")
LANGUAGE_ALT_PAIR_RE = re.compile(
    r"\b(?:french|francais|fr|english|anglais|en|dutch|nederlands|neerlandais|nl|german|deutsch|allemand)\b\s*"
    r"(?:/|or|ou|of)\s*"
    r"\b(?:french|francais|fr|english|anglais|en|dutch|nederlands|neerlandais|nl|german|deutsch|allemand)\b"
)
ACCEPTABLE_FR_NL_ALTERNATIVE_PATTERNS = [
    r"\bdutch\s+or\s+french\b",
    r"\bfrench\s+or\s+dutch\b",
    r"\bdutch\s*/\s*french\b",
    r"\bfrench\s*/\s*dutch\b",
    r"\bfr\s*/\s*nl\b",
    r"\bnl\s*/\s*fr\b",
    r"\bfr\s+or\s+nl\b",
    r"\bnl\s+or\s+fr\b",
    r"\bat\s+least\s+one\s+of\s+(?:french|dutch)\s*(?:/|or)\s*(?:french|dutch)\b",
]

# Contextual mandatory matching: block only when language + mandatory cues co-occur
# within a short window. This avoids false positives from simple keyword presence.
BLOCKED_LANGUAGE_CONTEXT_PATTERNS = [
    re.compile(
        r"\b(?:dutch|nederlands|neerlandais|german|deutsch|allemand)\b(?:\W+\w+){0,5}\W+"
        r"\b(?:required|mandatory|must|obligatoire|verplicht|vereist|necessary|indispensable|"
        r"fluent|native|c1|c2|exige|exigee)\b"
    ),
    re.compile(
        r"\b(?:required|mandatory|must|obligatoire|verplicht|vereist|necessary|indispensable|"
        r"fluent|native|c1|c2|exige|exigee)\b(?:\W+\w+){0,5}\W+"
        r"\b(?:dutch|nederlands|neerlandais|german|deutsch|allemand)\b"
    ),
]

ENGLISH_ONLY_PATTERNS = [
    r"\benglish\s+only\b",
    r"\bonly\s+english\b",
    r"\benglish\s+required\b",
    r"\brequired\s+english\b",
]


def _extract_language_codes(text_norm: str) -> set[str]:
    found: set[str] = set()
    for code, terms in LANGUAGE_TERMS.items():
        for term in terms:
            if keyword_hit(text_norm, term, boundary_only=True):
                found.add(code)
                break
    return found


def _snippet(text_norm: str, max_len: int = 140) -> str:
    value = " ".join((text_norm or "").split())
    if len(value) <= max_len:
        return value
    return value[: max_len - 3].rstrip() + "..."


def _parse_language_signals(norm: str) -> dict:
    """
    Parse language requirements/preferences from normalized text.
    This parser is intentionally contextual:
    - optional wording (plus/asset/atout/bonus) overrides generic requirement cues
    - OR pairs (French or Dutch, FR/NL, ...) are treated as alternatives, not mandatory Dutch
    - explicit mandatory patterns still hard-mark requirements
    """
    required_langs: set[str] = set()
    optional_langs: set[str] = set()
    evidence: list[str] = []
    alternative_language_option = False
    alternative_langs: set[str] = set()

    if not norm:
        return {
            "required_langs": required_langs,
            "optional_langs": optional_langs,
            "evidence": evidence,
            "alternative_language_option": alternative_language_option,
            "alternative_langs": alternative_langs,
        }

    clauses = [chunk.strip() for chunk in re.split(r"[;,\n\.\|]+", norm) if chunk.strip()]
    for clause in clauses:
        langs = _extract_language_codes(clause)
        if not langs:
            continue

        explicit_optional_langs: set[str] = set()
        optional_hit = LANGUAGE_OPTIONAL_CUE_RE.search(clause) is not None
        for code, patterns in LANGUAGE_OPTIONAL_PATTERNS.items():
            if any(re.search(pat, clause) for pat in patterns):
                optional_hit = True
                if code in langs:
                    explicit_optional_langs.add(code)
        if explicit_optional_langs:
            optional_langs.update(explicit_optional_langs)

        explicit_required_langs: set[str] = set()
        for code, patterns in LANGUAGE_REQUIRED_PATTERNS.items():
            if any(re.search(pat, clause) for pat in patterns):
                if code in langs:
                    explicit_required_langs.add(code)

        # Generic cue can mark required only when we do not have a pure optional clause.
        required_hit = LANGUAGE_REQUIRED_CUE_RE.search(clause) is not None
        if optional_hit and not explicit_required_langs:
            required_hit = False

        # Context windows for blocked languages (Dutch/German) with mandatory wording.
        if any(pattern.search(clause) for pattern in BLOCKED_LANGUAGE_CONTEXT_PATTERNS):
            if any(code in langs for code in {"nl", "de"}):
                explicit_required_langs.update({code for code in langs if code in {"nl", "de"}})
                required_hit = True

        # Ex: "English and Dutch (mandatory speaking)" -> both required.
        and_combo = len(langs) >= 2 and re.search(r"\b(and|et|en|&)\b", clause)
        if and_combo and required_hit:
            required_langs.update(langs)

        trilingual = LANGUAGE_TRILINGUAL_RE.search(clause) is not None and len(langs) >= 2
        if trilingual:
            required_langs.update(langs)
            required_hit = True

        # Ex: "French or Dutch" / "FR/NL": alternative path (not hard Dutch requirement).
        alternative = len(langs) >= 2 and LANGUAGE_ALT_PAIR_RE.search(clause) is not None
        if alternative:
            alternative_language_option = True
            alternative_langs.update(langs)
            if _snippet(clause) not in evidence:
                evidence.append(_snippet(clause))
            continue

        if explicit_required_langs:
            required_langs.update(explicit_required_langs)
            if _snippet(clause) not in evidence:
                evidence.append(_snippet(clause))
            continue

        if optional_hit and not required_hit:
            optional_langs.update(langs)
            if _snippet(clause) not in evidence:
                evidence.append(_snippet(clause))
            continue

        if required_hit:
            required_langs.update(langs)
            if _snippet(clause) not in evidence:
                evidence.append(_snippet(clause))

    return {
        "required_langs": required_langs,
        "optional_langs": optional_langs,
        "evidence": evidence[:5],
        "alternative_language_option": alternative_language_option,
        "alternative_langs": alternative_langs,
    }


def language_requirements(text: str) -> dict:
    """
    Backward-compatible language parser used by enrichment/reporting.
    The richer policy (required vs preferred vs acceptable alternatives)
    is implemented in classify_language_need().
    Returns:
      {
        "required_langs": set[str],
        "optional_langs": set[str],
        "evidence": list[str],
        "alternative_language_option": bool,
      }
    """
    norm = normalize_text(text or "")
    return _parse_language_signals(norm)


def classify_language_need(text: str) -> dict:
    """
    Classify language need for job filtering/scoring.
    Returns:
      {
        "requires_dutch": bool,
        "prefers_dutch": bool,
        "acceptable_without_dutch": bool,
        "requires_blocked_language": bool,
        "blocked_required_langs": list[str],
        "required_langs": set[str],
        "optional_langs": set[str],
        "signals": list[str],
        "english_only": bool,
      }
    """
    norm = normalize_text(text or "")
    parsed = _parse_language_signals(norm)
    required = set(parsed.get("required_langs", set()))
    optional = set(parsed.get("optional_langs", set()))
    alternative_langs = set(parsed.get("alternative_langs", set()))
    blocked_codes = set(ACTIVE_MARKET_PROFILE.get("blocked_language_codes", []))

    requires_dutch = "nl" in required
    prefers_dutch = ("nl" in optional) and not requires_dutch

    # FR/NL alternatives are acceptable for this profile because French is available.
    acceptable_without_dutch = False
    if parsed.get("alternative_language_option") and {"fr", "nl"}.issubset(alternative_langs):
        acceptable_without_dutch = True
    if any(re.search(pattern, norm) for pattern in ACCEPTABLE_FR_NL_ALTERNATIVE_PATTERNS):
        acceptable_without_dutch = True

    # Explicit NL required overrides alternative wording.
    if requires_dutch:
        acceptable_without_dutch = False

    english_only = any(re.search(pattern, norm) for pattern in ENGLISH_ONLY_PATTERNS)
    blocked_required = sorted(required.intersection(blocked_codes))
    requires_blocked_language = len(blocked_required) > 0 and not acceptable_without_dutch

    signals = list(parsed.get("evidence", []))
    if prefers_dutch:
        signals.append("dutch_preferred_not_required")
    if acceptable_without_dutch:
        signals.append("fr_or_nl_alternative")
    if english_only and not requires_dutch:
        signals.append("english_only_or_english_required")
    if requires_dutch:
        signals.append("dutch_explicitly_required")

    return {
        "requires_dutch": requires_dutch,
        "prefers_dutch": prefers_dutch,
        "acceptable_without_dutch": acceptable_without_dutch,
        "requires_blocked_language": requires_blocked_language,
        "blocked_required_langs": blocked_required,
        "required_langs": required,
        "optional_langs": optional,
        "signals": signals[:8],
        "english_only": english_only,
        "alternative_language_option": bool(parsed.get("alternative_language_option")),
        "alternative_langs": alternative_langs,
    }


def blocked_language_requirement_reason(text: str, filter_mode: str = "strict") -> str:
    need = classify_language_need(text)

    # In broad mode we keep those rows and rely on downstream flags/manual checks.
    mode = resolve_filter_mode(filter_mode, allow_both=False) if filter_mode else "strict"
    if mode == "broad":
        return ""

    blocked_required = set(need.get("blocked_required_langs", []))
    if not blocked_required:
        return ""
    if "nl" in blocked_required:
        return "blocked_language_req:dutch_required"
    if "de" in blocked_required:
        return "blocked_language_req:german_required"
    blocked_label = sorted(blocked_required)[0]
    return f"blocked_language_req:{blocked_label}_required"


def language_manual_review_reason(text: str) -> str:
    need = classify_language_need(text)
    alt_langs = set(need.get("alternative_langs", set()))
    if need.get("alternative_language_option") and alt_langs.intersection({"nl", "de"}):
        if alt_langs.intersection({"fr"}):
            return ""
        return "language_alternative:blocked_language_option"
    return ""


def has_blocked_language_requirement(text: str) -> bool:
    """Return True when blocked language is explicitly required in text."""
    return bool(blocked_language_requirement_reason(text))


def has_acceptable_language_alternative(text: str) -> bool:
    """
    Return True when the ad offers an FR/NL alternative (acceptable for this profile),
    as long as Dutch/German is not explicitly marked mandatory elsewhere.
    """
    return bool(classify_language_need(text).get("acceptable_without_dutch", False))


INTERNSHIP_ALLOW_MARKERS = [
    "graduate program",
    "early careers",
    "new grad",
    "entry-level program",
    "entry level program",
    "no internship agreement required",
    "open to graduates",
    "open to graduate",
]

INTERNSHIP_AGREEMENT_MARKERS = [
    "internship agreement",
    "convention de stage",
    "stage agreement",
]

INTERNSHIP_STUDENT_ONLY_MARKERS = [
    "must be enrolled",
    "currently enrolled",
    "student",
    "etudiant",
    "universite",
    "campus",
]

INTERNSHIP_THESIS_MARKERS = [
    "master thesis",
    "thesis",
    "memoire",
]

INTERNSHIP_STAGE_MARKERS = [
    "stage",
    "stagiaire",
]

INTERNSHIP_INTERN_MARKERS = [
    "internship",
    "intern",
]

EXPERIENCE_JUNIOR_TITLE_MARKERS = [
    "junior",
    "graduate",
    "entry level",
    "entry-level",
    "trainee",
    "new grad",
    "early careers",
]

# Extra junior-like context markers from title OR description.
# These markers are used to de-risk strict "3+ years" parsing when the ad
# clearly positions itself as junior/graduate onboarding.
EXPERIENCE_JUNIOR_CONTEXT_MARKERS = [
    "junior",
    "graduate",
    "entry level",
    "entry-level",
    "trainee",
    "traineeship",
    "starter",
    "will be trained",
    "training provided",
    "we hire for potential",
    "hire for potential",
    "no prior experience required",
    "no experience required",
    "open to graduates",
    "young talent",
]


EXPERIENCE_SOFT_SIGNAL_PHRASES = [
    "experience confirmee",
    "experience significative",
    "experience solide",
    "profil confirme",
    "confirmed experience",
    "strong experience",
    "solid experience",
    "proven experience",
]

EXPERIENCE_YEARS_PATTERNS = [
    r"\b(?:at\s+least|min(?:imum)?\.?|minimum|required|requise|au\s+moins)\s*(?:de\s*)?(?P<years>\d{1,2})\+?\s*(?:years?|yrs?|ans?)\b",
    r"\b(?P<years>\d{1,2})\+?\s*(?:years?|yrs?|ans?)\s+(?:of\s+)?experience\b",
    r"\bexperience\s+(?:de|d['’]|minimum|minimale|minimal|required|requise|confirmee|significative|solide)?\s*(?:de\s*)?(?P<years>\d{1,2})\+?\s*(?:ans|years?)\b",
    r"\b(?P<years>\d{1,2})\+?\s*(?:ans|years?)\s+d['’]?\s*experience\b",
    r"\b(?P<years>\d{1,2})\+?\s*(?:years?|yrs?|ans?)\b",
]

EXPERIENCE_RANGE_PATTERNS = [
    r"\b(?P<start>\d{1,2})\s*(?:-|–|to|a|/)\s*(?P<end>\d{1,2})\s*(?:years?|ans?)\b",
]

def _near_experience_context(text_norm: str, start: int, end: int) -> bool:
    window = text_norm[max(0, start - 40) : min(len(text_norm), end + 40)]
    return "experience" in window


def _years_from_text(text: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\b", normalize_text(text or ""))
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _match_phrase_list(text_norm: str, phrases: list[str]) -> str:
    for phrase in phrases:
        phrase_norm = normalize_text(phrase or "").strip()
        if phrase_norm and keyword_hit(text_norm, phrase_norm, boundary_only=True):
            return phrase
    return ""


def _extract_years_required(text_norm: str) -> tuple[int | None, str, bool]:
    """
    Extract strongest explicit years requirement.
    Returns:
      (years_required, detail, is_range)
    """
    candidates: list[tuple[int, str, bool]] = []
    max_reasonable_years = 15

    for pattern in EXPERIENCE_RANGE_PATTERNS:
        for match in re.finditer(pattern, text_norm):
            start = int(match.group("start"))
            end = int(match.group("end"))
            if start > max_reasonable_years or end > max_reasonable_years:
                continue
            if end < start:
                continue
            if _near_experience_context(text_norm, match.start(), match.end()):
                token = re.sub(r"\s+", " ", match.group(0)).strip()
                candidates.append((end, token, True))

    for pattern in EXPERIENCE_YEARS_PATTERNS:
        for match in re.finditer(pattern, text_norm):
            years = int(match.group("years"))
            if years > max_reasonable_years:
                continue
            token = match.group(0)
            if "experience" in token or _near_experience_context(text_norm, match.start(), match.end()):
                token = re.sub(r"\s+", " ", token).strip()
                candidates.append((years, token, False))

    if not candidates:
        return None, "", False

    # Keep the strongest explicit requirement while preserving whether it was a range.
    best = sorted(candidates, key=lambda item: (item[0], item[2]), reverse=True)[0]
    years_required, detail, is_range = best
    return years_required, detail or f"{years_required}+ years", is_range


def internship_student_only_detail(title: str, desc: str) -> str:
    """
    Return blocking detail for student-only internships, else empty string.
    """
    text = normalize((title or "") + " " + (desc or ""))
    if not text:
        return ""

    if any(keyword_hit(text, marker, boundary_only=True) for marker in INTERNSHIP_ALLOW_MARKERS):
        return ""

    if any(keyword_hit(text, marker, boundary_only=True) for marker in INTERNSHIP_AGREEMENT_MARKERS):
        return "internship_agreement_required"

    if any(keyword_hit(text, marker, boundary_only=True) for marker in INTERNSHIP_STUDENT_ONLY_MARKERS):
        return "student_only_keyword"

    if any(keyword_hit(text, marker, boundary_only=True) for marker in INTERNSHIP_THESIS_MARKERS):
        return "thesis_keyword"

    return ""


def internship_generic_detail(title: str, desc: str) -> str:
    """
    Return manual-review detail for generic internship wording (not explicit student-only).
    """
    text = normalize((title or "") + " " + (desc or ""))
    if not text:
        return ""

    if any(keyword_hit(text, marker, boundary_only=True) for marker in INTERNSHIP_ALLOW_MARKERS):
        return ""

    if internship_student_only_detail(title, desc):
        return ""

    if any(keyword_hit(text, marker, boundary_only=True) for marker in INTERNSHIP_STAGE_MARKERS):
        return "stage_keyword"

    if any(keyword_hit(text, marker, boundary_only=True) for marker in INTERNSHIP_INTERN_MARKERS):
        return "internship_keyword"

    return ""


def is_internship_student_only(title: str, desc: str) -> bool:
    return bool(internship_student_only_detail(title, desc))


def detect_experience_requirement_details(title: str, desc: str) -> tuple[str, str, int | None]:
    """
    Detect explicit experience constraints.
    Returns (level, detail, years_required):
      - hard for 5+ years
      - soft / soft_junior_title for 3-4 years
      - none for 0-1 or no signal
    """
    title_norm = normalize_text(title or "")
    text_norm = normalize_text(f"{title or ''} {desc or ''}")
    if not text_norm:
        return "none", "", None

    has_junior_title = any(keyword_hit(title_norm, marker, boundary_only=True) for marker in EXPERIENCE_JUNIOR_TITLE_MARKERS)
    has_junior_context = any(
        keyword_hit(text_norm, marker, boundary_only=True) for marker in EXPERIENCE_JUNIOR_CONTEXT_MARKERS
    )

    years_required, detail, is_range = _extract_years_required(text_norm)
    if years_required is not None:
        # 5+ years remains a strict hard block even if "junior" appears in text.
        if years_required >= 5:
            return "hard", detail, years_required

        # "3+ years" with junior/graduate signals is likely inflated HR wording:
        # keep as manual-review signal, not hard block.
        if years_required >= 3:
            if has_junior_context or has_junior_title:
                return "soft_junior_title", "years_required_conflict_but_junior_signals", years_required
            return "soft", detail, years_required

        # 2-3 years ranges are accepted; no hard block.
        if is_range and years_required <= 3:
            if has_junior_context or has_junior_title:
                return "soft_junior_title", "years_required_conflict_but_junior_signals", years_required
            return "soft", detail, years_required

        return "none", "", years_required

    hard_phrase = _match_phrase_list(text_norm, EXPERIENCE_HARD_BLOCK_PHRASES)
    if hard_phrase:
        years_from_phrase = _years_from_text(hard_phrase)
        if years_from_phrase is not None and years_from_phrase >= 5:
            return "hard", hard_phrase, years_from_phrase
        if has_junior_context or has_junior_title:
            return "soft_junior_title", "years_required_conflict_but_junior_signals", years_from_phrase
        return "hard", hard_phrase, years_from_phrase

    soft_phrase = _match_phrase_list(text_norm, EXPERIENCE_SOFT_BLOCK_PHRASES)
    if soft_phrase:
        years_from_phrase = _years_from_text(soft_phrase)
        if years_from_phrase is not None and years_from_phrase <= 2:
            return "none", "", years_from_phrase
        if years_from_phrase is not None and years_from_phrase >= 5:
            return "hard", soft_phrase, years_from_phrase
        if has_junior_context or has_junior_title:
            return "soft_junior_title", "years_required_conflict_but_junior_signals", years_from_phrase
        return "soft", soft_phrase, years_from_phrase

    for marker in EXPERIENCE_SOFT_SIGNAL_PHRASES:
        if keyword_hit(text_norm, marker, boundary_only=True):
            if has_junior_context or has_junior_title:
                return "soft_junior_title", "years_required_conflict_but_junior_signals", None
            return "soft", marker, None

    return "none", "", None


def detect_experience_requirement(title: str, desc: str) -> tuple[str, str]:
    level, detail, _years_required = detect_experience_requirement_details(title, desc)
    return level, detail


def extract_years_required(title: str, desc: str) -> int | None:
    _level, _detail, years_required = detect_experience_requirement_details(title, desc)
    return years_required


def is_disallowed_language(text: str) -> bool:
    """Return True if detected dominant language is disallowed for the active market."""
    blocked_codes = set(ACTIVE_MARKET_PROFILE.get("blocked_language_codes", []))
    if not blocked_codes:
        return False

    try:
        snippet = (text or "")[:800]
        if not snippet.strip():
            return False

        lang = detect(snippet)
        return lang in blocked_codes
    except LangDetectException:
        return False
    except Exception:
        return False


def is_dutch(text: str) -> bool:
    """Backward-compatible alias for legacy imports."""
    return is_disallowed_language(text)


def training_program_relevant(title: str, desc: str) -> bool:
    """Allow trainee/graduate programs only when they look CS/IT-related."""
    text = normalize((title or "") + " " + (desc or ""))
    training_markers = [
        "graduate",
        "trainee",
        "intern",
        "internship",
        "stagiaire",
        "praktikant",
        "stage",
        "entry level",
        "formation",
    ]
    cs_markers = [
        "it",
        "ict",
        "computer",
        "informatique",
        "informaticien",
        "informatiker",
        "cloud",
        "system",
        "linux",
        "network",
        "application support",
        "helpdesk",
        "service desk",
        "support",
        "platform",
        "devops",
        "infrastructure",
    ]
    has_training_marker = any(keyword_hit(text, marker, boundary_only=True) for marker in training_markers)
    has_cs_marker = any(keyword_hit(text, marker, boundary_only=True) for marker in cs_markers)
    return has_training_marker and has_cs_marker


ROLE_TITLE_FALLBACK_KEYWORDS = [
    "it support",
    "support it",
    "support informatique",
    "helpdesk",
    "service desk",
    "servicedesk",
    "technicien support",
    "support n1",
    "support n2",
    "support n3",
    "technical support",
    "support technique",
    "it supporter",
    "ict supporter",
    "supporttechniker",
    "it-support",
    "it support specialist",
    "application support",
    "administrateur systeme",
    "administrateur systemes",
    "administratrice systeme",
    "administratrice systemes",
    "system administrator",
    "systems administrator",
    "network administrator",
    "administrateur reseau",
    "network engineer",
    "ingenieur reseau",
    "system admin",
    "systemadministrator",
    "it-systemadministrator",
    "it administrator",
    "it administratorin",
    "it-administrator",
    "ingenieur systeme",
    "ingenieur systemes",
    "ingenieur linux",
    "ict system engineer",
    "it infrastructure specialist",
    "test automation engineer",
    "qa automation engineer",
    "build engineer",
    "release engineer",
    "informaticien",
    "informatiker",
]

ROLE_TITLE_FALLBACK_PATTERNS = [
    r"\badministrat(?:eur|rice)(?:[-/\s]trice)?\b.{0,20}\bsystem",
    r"\badministrat(?:eur|rice)(?:[-/\s]trice)?\b.{0,20}\breseau",
    r"\b(system|network)\b.{0,25}\b(network|system)\b.{0,15}\badministrator\b",
    r"\bit[-\s]?administrator(?:in)?\b",
    r"\bit[-\s]?support\b",
    r"\bsupporttechniker\b",
    r"\btechnicien(?:ne)?\s+support\b",
    r"\bhelp\s*desk\b",
    r"\bservice\s*desk\b",
    r"\b(system|linux)\s+administrator\b",
]

# Optional, narrow role broadening for DevOps/Infra junior profiles.
# Guardrails:
# - must look infra/cloud-ish
# - explicitly reject industrial automation contexts (PLC/SCADA/HVAC/BMS)
ROLE_ALIAS_SAFE_KEYWORDS = [
    "platform engineer",
    "infra engineer",
    "infrastructure engineer",
    "linux engineer",
    "sysadmin",
    "system administrator",
    "cloud operations engineer",
    "cloud operations",
    "cloud infrastructure",
    "automation engineer",
]

ROLE_ALIAS_TECH_SIGNALS = [
    "ci/cd",
    "kubernetes",
    "docker",
    "terraform",
    "ansible",
    "linux",
    "devops",
    "sre",
    "platform",
    "infrastructure",
    "cloud",
    "aws",
    "azure",
    "gcp",
    "iac",
    "helm",
]

ROLE_ALIAS_INDUSTRIAL_BLOCKERS = [
    "plc",
    "scada",
    "hvac",
    "bms",
    "siemens s7",
    "process control",
    "electrical",
    "automation industrielle",
    "industrial automation",
]

# Strong role signals we trust when present in the title.
# We prefer title evidence over description evidence to reduce noisy matches
# coming from generic company text in long descriptions.
ROLE_TITLE_PRIMARY_SIGNALS = [
    "devops",
    "sre",
    "site reliability",
    "platform engineer",
    "cloud engineer",
    "cloud operations",
    "system administrator",
    "sysadmin",
    "linux administrator",
    "infrastructure engineer",
    "it support",
    "service desk",
    "helpdesk",
    "application support",
]

# Description-only matches must include concrete infra/tooling signals.
ROLE_DESC_INFRA_EVIDENCE = [
    "kubernetes",
    "docker",
    "terraform",
    "ansible",
    "ci/cd",
    "linux",
    "azure",
    "aws",
    "gcp",
    "observability",
    "incident management",
    "infrastructure as code",
    "iac",
    "helm",
    "prometheus",
]


def role_title_fallback_relevant(title: str) -> bool:
    """
    Recover obvious IT support/sysadmin titles that miss strict required-keyword patterns.
    """
    t = normalize(title or "")
    if any(keyword_hit(t, kw, boundary_only=True) for kw in ROLE_TITLE_FALLBACK_KEYWORDS):
        return True
    return any(re.search(pattern, t) is not None for pattern in ROLE_TITLE_FALLBACK_PATTERNS)


def role_alias_safe_relevant(title: str, desc: str) -> bool:
    """
    Recover safe infra aliases without opening non-target industrial automation noise.
    """
    title_norm = normalize_text(title or "")
    text_norm = normalize_text(f"{title or ''} {desc or ''}")
    if not text_norm:
        return False

    if any(keyword_hit(text_norm, bad, boundary_only=True) for bad in ROLE_ALIAS_INDUSTRIAL_BLOCKERS):
        return False

    alias_hits = [kw for kw in ROLE_ALIAS_SAFE_KEYWORDS if keyword_hit(title_norm, kw, boundary_only=True)]
    if not alias_hits:
        return False

    # "Automation Engineer" is broad; keep it only when explicit infra/tooling signals exist.
    if "automation engineer" in alias_hits:
        if not any(keyword_hit(text_norm, sig, boundary_only=True) for sig in ROLE_ALIAS_TECH_SIGNALS):
            return False

    return True


def _has_primary_role_title_signal(title: str) -> bool:
    title_norm = normalize_text(title or "")
    if not title_norm:
        return False
    return any(keyword_hit(title_norm, sig, boundary_only=True) for sig in ROLE_TITLE_PRIMARY_SIGNALS)


def _required_keywords_match_reliably(title: str, desc: str) -> bool:
    """
    Evaluate ROLE_REQUIRED_KEYWORDS with stricter evidence to avoid description-only noise.
    Rules:
    - title hit => accept (high confidence)
    - description-only hit => require concrete infra/tooling evidence
    """
    title_norm = normalize_text(title or "")
    desc_norm = normalize_text(desc or "")
    full_text = normalize_text(f"{title or ''} {desc or ''}")
    if not full_text:
        return False

    required_hits = [kw for kw in ROLE_REQUIRED_KEYWORDS if keyword_hit(full_text, kw, boundary_only=True)]
    if not required_hits:
        return False

    # Any required keyword explicitly in title is a strong positive signal.
    if any(keyword_hit(title_norm, kw, boundary_only=True) for kw in required_hits):
        return True

    # Description-only matches are accepted only when they look truly infra-focused.
    has_infra_evidence = any(keyword_hit(desc_norm, sig, boundary_only=True) for sig in ROLE_DESC_INFRA_EVIDENCE)
    has_industrial_noise = any(keyword_hit(desc_norm, bad, boundary_only=True) for bad in ROLE_ALIAS_INDUSTRIAL_BLOCKERS)
    return bool(has_infra_evidence and not has_industrial_noise)


ROLE_FORBIDDEN_CONTEXT_SKIP = {"keycloak", "commercial", "delivery"}
ROLE_DESC_SIGNAL_PREFIX_CHARS = 360
FORBIDDEN_ROLE_SECTION_PATTERNS = [
    r"\brole\b",
    r"\bposition\b",
    r"\bjob\s+title\b",
    r"\bwe\s+are\s+looking\s+for\b",
    r"\blooking\s+for\s+(?:a|an)\b",
    r"\byour\s+role\b",
    r"\bresponsibilities\b",
    r"\byour\s+mission\b",
    r"\bmission\b",
]
FORBIDDEN_STAKEHOLDER_PATTERNS = [
    r"\bcollaborat\w*\s+with\b",
    r"\bwork\w*\s+with\b",
    r"\bteam\s+includes?\b",
    r"\bteam\s+consists?\s+of\b",
    r"\bstakeholders?\s+include\b",
    r"\bin\s+collaboration\s+with\b",
    r"\balongside\b",
]
DELIVERY_ROLE_PATTERNS = [
    r"\bdelivery\s+(driver|courier|rider|agent)\b",
    r"\bwarehouse\s+delivery\b",
    r"\bcourier\b",
    r"\blivreur\b",
    r"\bchauffeur[-\s]?livreur\b",
]
COMMERCIAL_SALES_MARKERS = [
    "sales",
    "business development",
    "account executive",
    "account manager",
    "inside sales",
    "quota",
    "prospect",
    "pipeline",
    "lead generation",
    "cold call",
]
COMMERCIAL_FALSE_POSITIVE_MARKERS = [
    "commercial sector",
    "commercial vessels",
    "commercial operations",
]


def _is_delivery_role(text_norm: str) -> bool:
    return any(re.search(pattern, text_norm) for pattern in DELIVERY_ROLE_PATTERNS)


def _is_commercial_sales_role(title_norm: str, text_norm: str) -> bool:
    has_commercial = keyword_hit(title_norm, "commercial", boundary_only=True) or keyword_hit(
        text_norm, "commercial", boundary_only=True
    )
    if not has_commercial:
        return False
    if any(marker in text_norm for marker in COMMERCIAL_FALSE_POSITIVE_MARKERS):
        return False
    return any(keyword_hit(text_norm, marker, boundary_only=True) for marker in COMMERCIAL_SALES_MARKERS)


def forbidden_hit_in_desc(desc: str, bad: str) -> bool:
    """
    Return True only when a forbidden keyword appears in a high-signal role context in description:
    - very early in the text (summary zone), or
    - near role/position/responsibility cues.
    Stakeholder contexts ("team includes", "work with", ...) are ignored.
    """
    desc_norm = normalize_text(desc or "")
    bad_norm = normalize_text(bad or "").strip()
    if not desc_norm or not bad_norm:
        return False
    if not keyword_hit(desc_norm, bad_norm, boundary_only=True):
        return False

    bad_pattern = r"(?<![a-z0-9])" + re.escape(bad_norm).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    for match in re.finditer(bad_pattern, desc_norm):
        start = match.start()
        end = match.end()
        local_window = desc_norm[max(0, start - 90) : min(len(desc_norm), end + 120)]
        if any(re.search(pattern, local_window) for pattern in FORBIDDEN_STAKEHOLDER_PATTERNS):
            continue
        if start <= ROLE_DESC_SIGNAL_PREFIX_CHARS:
            return True
        left_context = desc_norm[max(0, start - 160) : start]
        if any(re.search(pattern, left_context) for pattern in FORBIDDEN_ROLE_SECTION_PATTERNS):
            return True
    return False


def role_forbidden_reason(title: str, desc: str) -> str:
    """
    Return forbidden-role detail when text clearly matches out-of-target role.
    Context-aware handling avoids tech false positives like Keycloak or service delivery wording.
    """
    text_norm = normalize_text(f"{title or ''} {desc or ''}")
    title_norm = normalize_text(title or "")

    for bad in ROLE_FORBIDDEN_KEYWORDS:
        bad_norm = normalize_text(bad or "").strip()
        if not bad_norm or bad_norm in ROLE_FORBIDDEN_CONTEXT_SKIP:
            continue
        # Title hit is a high-confidence signal: block directly.
        if keyword_hit(title_norm, bad_norm, boundary_only=True):
            return bad_norm
        # Description hit needs stronger contextual evidence to avoid stakeholder false positives.
        if forbidden_hit_in_desc(desc, bad_norm):
            return bad_norm

    if _is_delivery_role(text_norm):
        return "delivery_role"
    if _is_commercial_sales_role(title_norm, text_norm):
        return "commercial_sales"
    return ""


def role_relevant(title: str, desc: str) -> bool:
    """Keep infra / cloud / devops roles, drop forbidden ones."""
    text = normalize_text((title or "") + " " + (desc or ""))

    if role_forbidden_reason(title, desc):
        return False

    # Title-first positive signal for target roles.
    if _has_primary_role_title_signal(title):
        return True

    # Required keyword logic with extra description guardrails.
    if _required_keywords_match_reliably(title, desc):
        return True

    if ACTIVE_JOB_MODE == "speed":
        if any(keyword_hit(text, kw, boundary_only=True) for kw in SPEED_ROLE_TARGETS):
            return True

    if training_program_relevant(title, desc):
        return True

    if role_alias_safe_relevant(title, desc):
        return True

    return role_title_fallback_relevant(title)


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
        "manage stakeholders",
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


def compute_language_fit_score(title: str, desc: str) -> int:
    """
    Return language fit in [0..2]:
      - 2: FR/EN acceptable (including English-only acceptable)
      - 1: FR/EN acceptable but Dutch appears as preference (plus/asset)
      - 0: blocked language (NL/DE) explicitly required
    """
    text = f"{title or ''} {desc or ''}"
    need = classify_language_need(text)
    required = set(need.get("required_langs", set()))
    optional = set(need.get("optional_langs", set()))

    if need.get("requires_blocked_language", False):
        return 0
    if need.get("prefers_dutch", False):
        return 1

    # Clear FR/EN acceptance signals.
    if required.intersection({"fr", "en"}):
        return 2
    if need.get("english_only", False):
        return 2
    if need.get("acceptable_without_dutch", False):
        return 2

    norm = normalize_text(text)
    has_fr_or_en_signal = bool(_extract_language_codes(norm).intersection({"fr", "en"}))
    if has_fr_or_en_signal:
        return 2

    # Keep neutral fallback to avoid over-penalizing sparse descriptions.
    if optional.intersection({"fr", "en"}):
        return 2
    return 1 if bool(norm) else 0


def compute_priority_score(
    title: str,
    desc: str,
    loc: str,
    created: str,
    junior_score: int,
    language_fit_score: int,
) -> int:
    """
    Rank jobs by apply-first priority.
    Higher means better fit for quick-entry hiring strategy.
    """
    text = normalize((title or "") + " " + (desc or ""))
    loc_norm = normalize(loc or "")
    score = 50 + max(0, junior_score) * 2 + language_fit_score * 2

    for term, weight in ACTIVE_PRIORITY_TERMS.items():
        if normalize(term) in text:
            score += int(weight)

    training_patterns = [
        "junior",
        "trainee",
        "intern",
        "internship",
        "entry level",
        "training provided",
        "no experience required",
        "graduate",
    ]
    for pat in training_patterns:
        if pat in text:
            score += 2

    work_mode = detect_work_mode(title, desc, loc)
    if work_mode == "remote":
        score += 5
    elif work_mode == "hybrid":
        score += 3

    if ACTIVE_MARKET == "ch":
        romandie_terms = [
            "geneve",
            "geneva",
            "lausanne",
            "vaud",
            "neuchatel",
            "jura",
            "fribourg",
            "valais",
            "sion",
            "nyon",
            "montreux",
        ]
        if any(term in loc_norm for term in romandie_terms):
            score += 5

    # Prefer fresher offers when deciding what to apply first.
    try:
        dt = datetime.fromisoformat(str(created).replace("Z", "+00:00")).astimezone(timezone.utc)
        age_days = (datetime.now(timezone.utc) - dt).days
        if age_days <= 3:
            score += 8
        elif age_days <= 7:
            score += 6
        elif age_days <= 14:
            score += 4
        elif age_days <= 30:
            score += 2
    except Exception:
        pass

    return int(score)


def close_excel_for_locked_path(path: str) -> str:
    """
    Best-effort unlock for CSV writes on Windows.
    1) Close the workbook matching `path` if Excel is running.
    2) Optionally force-kill Excel as fallback.
    Returns a short action code for logging.
    """
    if os.name != "nt":
        return "unsupported_os"

    target = os.path.abspath(path).replace("'", "''")
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        f"$target=[System.IO.Path]::GetFullPath('{target}');"
        "$closed=$false;"
        "try {"
        "  $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application');"
        "  if($excel){"
        "    foreach($wb in @($excel.Workbooks)){"
        "      try {"
        "        $wbPath=[System.IO.Path]::GetFullPath($wb.FullName);"
        "        if($wbPath -ieq $target){$wb.Close($false);$closed=$true}"
        "      } catch {}"
        "    }"
        "    if($closed -and $excel.Workbooks.Count -eq 0){$excel.Quit()}"
        "  }"
        "} catch {};"
        "if($closed){'closed_target'} else {'not_closed'}"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=12,
        )
        out = (res.stdout or "").strip().lower()
        if "closed_target" in out:
            return "closed_target"
    except Exception:
        pass

    if not FORCE_KILL_EXCEL_ON_LOCK:
        return "not_closed"

    try:
        res = subprocess.run(
            ["taskkill", "/IM", "EXCEL.EXE", "/F"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if res.returncode == 0:
            return "killed_excel"
    except Exception:
        pass
    return "not_closed"


def safe_save_csv(df, path, retry_delay=3, max_retries=3):
    """Save CSV and retry if locked by Excel; fall back to .bak if still locked."""
    attempts = 0
    while attempts < max_retries:
        try:
            df.to_csv(path, index=False, encoding="utf-8-sig")
            print(f"[INFO] Saved file: {path}")
            return
        except PermissionError:
            attempts += 1
            unlocked = "disabled"
            if AUTO_CLOSE_EXCEL_ON_LOCK:
                unlocked = close_excel_for_locked_path(path)
                if unlocked in {"closed_target", "killed_excel"}:
                    print(f"[WARN] File {path} was locked. Auto-closed Excel ({unlocked}). Retrying write...")
                    time.sleep(1)
                    continue
            print(
                f"[WARN] File {path} is open (attempt {attempts}/{max_retries}, unlock={unlocked}). "
                f"Retrying in {retry_delay}s..."
            )
            time.sleep(retry_delay)
    # fallback
    backup = path + ".bak"
    df.to_csv(backup, index=False, encoding="utf-8-sig")
    print(f"[WARN] Could not write {path} after {max_retries} attempts. Saved to {backup} instead.")


def passes_filters(job: dict, source: str = "adzuna", filter_mode: str = "") -> dict | None:
    """Apply common filters and return normalized job if it passes."""
    mode = resolve_filter_mode(filter_mode or ACTIVE_FILTER_MODE, allow_both=False)
    created = job.get("created", "") or job.get("updated", "")

    loc = job.get("location", "")
    if isinstance(loc, dict):
        loc = loc.get("display_name", "")
    if not loc:
        loc = job.get("location.display_name", "")
    loc = rule_plain_text(loc)

    title = rule_plain_text(job.get("title", "") or "")
    desc = rule_plain_text(job.get("description", "") or "")
    url = job.get("redirect_url", "") or job.get("url", "") or job.get("link", "")
    canonical_url = canonicalize_url(url)

    company_val = job.get("company", "")
    if isinstance(company_val, dict):
        company = company_val.get("display_name", "") or company_val.get("name", "")
    else:
        company = company_val or job.get("company.display_name", "")
    company = rule_plain_text(company)

    if REQUIRE_DESCRIPTION and len(desc.strip()) < MIN_DESCRIPTION_CHARS:
        return None

    norm_title = normalize(title)
    if any(bt in norm_title for bt in BAD_TITLE_KEYWORDS):
        return None

    _rule_norm, full_text = job_text_for_rules({"title": title, "description": desc})
    work_mode = detect_work_mode(title, desc, loc)
    experience_level, experience_detail, years_required = detect_experience_requirement_details(title, desc)

    if not is_recent(created, MAX_DAYS_OLD):
        return None

    if not location_ok(loc, title, desc):
        return None

    if not role_relevant(title, desc):
        return None

    if is_internship_student_only(title, desc):
        return None

    exclude_hard_hits, _exclude_soft_hits = classify_excluded_hits(title, full_text)
    if exclude_hard_hits:
        return None

    if experience_level == "hard":
        return None

    # Keep two views:
    # - mode-aware reason for filtering decision
    # - strict reason for diagnostics/CSV transparency
    blocked_language_reason = blocked_language_requirement_reason(full_text, filter_mode=mode)
    blocked_language_reason_strict = blocked_language_requirement_reason(full_text, filter_mode="strict")
    language_need = classify_language_need(full_text)
    if blocked_language_reason:
        return None

    disallowed_language_detected = is_disallowed_language(full_text)
    if mode == "strict" and disallowed_language_detected:
        return None

    # Autoriser les offres neutres (score >= 0) pour ne pas filtrer trop agressivement
    junior_score = compute_junior_score(title, desc)
    # Exclure les annonces au score clairement nÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gatif, garder neutre ou positif
    min_junior_score = 0 if mode == "strict" else -1
    if junior_score < min_junior_score:
        return None
    language_fit_score = compute_language_fit_score(title, desc)

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
        "language_fit_score": language_fit_score,
        "priority_score": compute_priority_score(
            title,
            desc,
            loc,
            created,
            junior_score,
            language_fit_score,
        ),
        "is_remote": work_mode in {"remote", "hybrid"},
        "work_mode": work_mode,
        "years_required": years_required if years_required is not None else "",
        "experience_level": experience_level,
        "experience_detail": normalize_text(experience_detail) if experience_detail else "",
        "blocked_language_reason": blocked_language_reason_strict,
        "language_need_label": (
            "requires_blocked_language"
            if language_need.get("requires_blocked_language")
            else "prefers_dutch"
            if language_need.get("prefers_dutch")
            else "acceptable_without_dutch"
            if language_need.get("acceptable_without_dutch")
            else "fr_en_ok"
        ),
        "language_need_signals": " | ".join(language_need.get("signals", [])),
        "disallowed_language_detected": disallowed_language_detected,
        "filter_mode": mode,
        "source": source,
    }


def build_filtered_df(all_jobs: list[dict], filter_mode: str, source: str = "adzuna") -> pd.DataFrame:
    """Apply filtering + dedup + sorting for one filter mode."""
    filtered = []
    resolved_mode = resolve_filter_mode(filter_mode, allow_both=False)
    for job in all_jobs:
        parsed = passes_filters(job, source=source, filter_mode=resolved_mode)
        if parsed:
            filtered.append(parsed)

    df_f = pd.DataFrame(filtered)
    before = len(df_f)
    if "canonical_url" not in df_f.columns:
        if "url" in df_f.columns:
            df_f["canonical_url"] = df_f["url"].fillna("").astype(str).apply(canonicalize_url)
        else:
            df_f["canonical_url"] = ""
    if not df_f.empty:
        df_f = df_f.drop_duplicates(subset=["canonical_url", "title", "company"])
        sort_cols = [c for c in ["priority_score", "junior_score", "created"] if c in df_f.columns]
        if sort_cols:
            df_f = df_f.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
    after = len(df_f)
    print(f"[INFO] [{resolved_mode}] Duplicates removed: {before - after}")
    print(f"[INFO] [{resolved_mode}] Filtered kept: {len(df_f)}")
    return df_f


def near_miss_location_only(job: dict, min_priority: int = 68, source: str = "adzuna") -> dict | None:
    """
    Return job if it fails only location filter but is otherwise a strong candidate.
    Useful to manually review potentially relevant opportunities.
    """
    created = job.get("created", "") or job.get("updated", "")

    loc = job.get("location", "")
    if isinstance(loc, dict):
        loc = loc.get("display_name", "")
    if not loc:
        loc = job.get("location.display_name", "")
    loc = rule_plain_text(loc)

    title = rule_plain_text(job.get("title", "") or "")
    desc = rule_plain_text(job.get("description", "") or "")
    url = job.get("redirect_url", "") or job.get("url", "") or job.get("link", "")
    canonical_url = canonicalize_url(url)

    company_val = job.get("company", "")
    if isinstance(company_val, dict):
        company = company_val.get("display_name", "") or company_val.get("name", "")
    else:
        company = company_val or job.get("company.display_name", "")
    company = rule_plain_text(company)

    if REQUIRE_DESCRIPTION and len(desc.strip()) < MIN_DESCRIPTION_CHARS:
        return None

    norm_title = normalize(title)
    if any(bt in norm_title for bt in BAD_TITLE_KEYWORDS):
        return None

    _rule_norm, full_text = job_text_for_rules({"title": title, "description": desc})
    work_mode = detect_work_mode(title, desc, loc)
    experience_level, _experience_detail, years_required = detect_experience_requirement_details(title, desc)

    if not is_recent(created, MAX_DAYS_OLD):
        return None

    # Must fail location to be considered a location-only near miss.
    if location_ok(loc, title, desc):
        return None

    if not role_relevant(title, desc):
        return None

    if is_internship_student_only(title, desc):
        return None

    exclude_hard_hits, _exclude_soft_hits = classify_excluded_hits(title, full_text)
    if exclude_hard_hits:
        return None

    if experience_level == "hard":
        return None

    if blocked_language_requirement_reason(full_text):
        return None

    if is_disallowed_language(full_text):
        return None

    junior_score = compute_junior_score(title, desc)
    if junior_score < 0:
        return None

    language_fit_score = compute_language_fit_score(title, desc)
    priority_score = compute_priority_score(title, desc, loc, created, junior_score, language_fit_score)
    if priority_score < min_priority:
        return None

    return {
        "title": title,
        "company": company,
        "location": loc,
        "created": created,
        "url": url,
        "canonical_url": canonical_url,
        "description": desc[:400],
        "search_term": job.get("search_term", ""),
        "junior_score": junior_score,
        "language_fit_score": language_fit_score,
        "priority_score": priority_score,
        "is_remote": work_mode in {"remote", "hybrid"},
        "work_mode": work_mode,
        "years_required": years_required if years_required is not None else "",
        "near_miss_reason": "location_only",
        "source": source,
    }


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
    parser.add_argument(
        "--self-test-exclude-keywords",
        action="store_true",
        help="Run local exclude-keyword self-tests and exit.",
    )
    parser.add_argument(
        "--self-checks",
        action="store_true",
        help="Run local language/experience self-checks and exit.",
    )
    args = parser.parse_args()
    if args.self_test_exclude_keywords:
        run_exclude_keyword_self_tests()
        return
    if args.self_checks:
        run_self_checks()
        return

    # Optional non-breaking trigger for CI/local quick checks:
    # RUN_SELF_CHECKS=1 python adzuna_fetch.py --no-fetch --market be --filter-mode strict
    if os.getenv("RUN_SELF_CHECKS", "").strip().lower() in {"1", "true", "yes", "on"}:
        run_self_checks()

    global ACTIVE_FILTER_MODE
    configure_market(args.market, args.ch_focus)
    selected_filter_mode = resolve_filter_mode(args.filter_mode, allow_both=True)
    ACTIVE_FILTER_MODE = selected_filter_mode if selected_filter_mode != "both" else "strict"
    adzuna_raw_csv = ACTIVE_OUTPUT_PATHS["adzuna_raw_csv"]
    adzuna_filtered_csv = ACTIVE_OUTPUT_PATHS["adzuna_filtered_csv"]
    adzuna_filtered_strict_csv = ACTIVE_OUTPUT_PATHS["adzuna_filtered_strict_csv"]
    adzuna_filtered_broad_csv = ACTIVE_OUTPUT_PATHS["adzuna_filtered_broad_csv"]
    near_miss_csv = ACTIVE_OUTPUT_PATHS["near_miss_csv"]
    search_terms = list(SEARCH_TERMS)
    print(
        f"[INFO] Market={ACTIVE_MARKET} country={ACTIVE_MARKET_PROFILE['adzuna_country']} "
        f"ch_focus={ACTIVE_MARKET_PROFILE['ch_focus']} "
        f"langs={ACTIVE_MARKET_PROFILE['allowed_language_codes']} terms={len(search_terms)} "
        f"filter_mode={selected_filter_mode}"
    )

    all_jobs = []

    if args.no_fetch:
        if not os.path.exists(adzuna_raw_csv):
            print(f"[ERROR] Fichier brut introuvable: {adzuna_raw_csv}")
            return
        print("[INFO] Chargement du fichier brut existant...")
        df_raw = pd.read_csv(adzuna_raw_csv)
        all_jobs = df_raw.to_dict(orient="records")
    else:
        for term in search_terms:
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
        safe_save_csv(df_raw, adzuna_raw_csv)
        print(f"[INFO] Raw saved: {len(df_raw)}")

    if selected_filter_mode in ("strict", "both"):
        df_strict = build_filtered_df(all_jobs, filter_mode="strict", source="adzuna")
        safe_save_csv(df_strict, adzuna_filtered_strict_csv)
        safe_save_csv(df_strict, adzuna_filtered_csv)
        print(f"[INFO] Strict filtered saved: {len(df_strict)}")
    else:
        df_strict = None

    if selected_filter_mode in ("broad", "both"):
        df_broad = build_filtered_df(all_jobs, filter_mode="broad", source="adzuna")
        safe_save_csv(df_broad, adzuna_filtered_broad_csv)
        if selected_filter_mode == "broad":
            safe_save_csv(df_broad, adzuna_filtered_csv)
        print(f"[INFO] Broad filtered saved: {len(df_broad)}")
    else:
        df_broad = None

    # Near misses remain strict-only signal (best for manual review).
    if selected_filter_mode in ("strict", "both"):
        near_miss = []
        for job in all_jobs:
            parsed = near_miss_location_only(job, min_priority=68, source="adzuna")
            if parsed:
                near_miss.append(parsed)

        df_nm = pd.DataFrame(near_miss)
        if not df_nm.empty:
            if "canonical_url" not in df_nm.columns:
                df_nm["canonical_url"] = df_nm["url"].fillna("").astype(str).str.split("?", n=1).str[0]
            df_nm = df_nm.drop_duplicates(subset=["canonical_url", "title", "company"])
            sort_cols_nm = [c for c in ["priority_score", "language_fit_score", "junior_score", "created"] if c in df_nm.columns]
            if sort_cols_nm:
                df_nm = df_nm.sort_values(by=sort_cols_nm, ascending=[False] * len(sort_cols_nm))
        safe_save_csv(df_nm, near_miss_csv)
        print(f"[INFO] Near-miss (location-only) saved: {len(df_nm)} -> {near_miss_csv}")
    else:
        print("[INFO] Near-miss skipped in broad mode (strict-only signal).")


if __name__ == "__main__":
    main()


