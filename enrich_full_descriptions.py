"""
Enrich filtered jobs with full descriptions from job URLs, then re-apply filters.

Typical use in pipeline:
1) Read already filtered CSV (strict or broad)
2) Scrape full description from each job page
3) Re-check filters on full text (to catch hidden constraints in truncated API text)
4) Write diagnostics CSV + refined filtered CSV
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter
from html import unescape
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import pandas as pd
import requests
try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright
except Exception:
    PlaywrightTimeout = Exception
    sync_playwright = None

import adzuna_fetch as af
from config import SUPPORTED_CH_FOCUS, SUPPORTED_FILTER_MODES, SUPPORTED_MARKETS, resolve_filter_mode

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

# In full-description recheck, only hard-exclude on high-confidence signals.
HARD_EXCLUDE_KEYWORDS = {
    "3+ years",
    "4+ years",
    "5+ years",
    "6+ years",
    "7+ years",
    "8+ years",
    "10+ years",
    "min 3 years",
    "minimum 3 years",
    "at least 3 years",
    "min 4 years",
    "minimum 4 years",
    "at least 4 years",
    "min 5 years",
    "minimum 5 years",
    "at least 5 years",
    "au moins 3 ans",
    "au moins 4 ans",
    "au moins 5 ans",
    "minimum 3 ans d'experience",
    "minimum 4 ans d'experience",
    "minimum 5 ans d'experience",
    "experience confirmee",
    "clearance",
    "security clearance",
    "secret clearance",
    "top secret",
    "defense",
    "defence",
    "military",
    "classified",
}

AMBIGUOUS_EXCLUDE_KEYWORDS = {
    "manager",
    "expert",
    "hardware",
    "principal",
    "architect",
    "lead",
    "ownership",
    "mentor",
}

AMBIGUOUS_ROLE_FORBIDDEN = {
    "coo",
    "delivery",
    "store",
    " l3 ",
    "software engineer",
    "artificial intelligence",
    "data engineer",
}

NOT_FOUND_PAGE_MARKERS = [
    "seite kann nicht gefunden werden",
    "wir konnen die von ihnen gesuchte seite nicht finden",
    "jobs seite kann nicht gefunden werden",
    "page cannot be found",
    "we cannot find the page you are looking for",
    "retour a la page d'accueil",
    "retour a la page daccueil",
    "zuruck zur startseite",
    "erweiterte suche",
    "all live ergebnisse in der ganzen schweiz durchsuchen",
]

SENIOR_TITLE_MARKERS = {
    "senior",
    "sr",
    "lead",
    "principal",
    "staff engineer",
    "architect",
    "head of",
    "manager",
    "director",
}

SENIOR_EXPERIENCE_PATTERNS = [
    r"\b(?:at\s+least|min(?:imum)?\.?)\s*(?:3|4|5|6|7|8|9|10)\+?\s*(?:years?|ans)\b",
    r"\b(?:au\s+moins|min(?:imum)?\.?)\s*(?:3|4|5|6|7|8|9|10)\+?\s*(?:ans|years?)\b",
    r"\b(?:3|4|5|6|7|8|9|10)\+?\s*(?:years?|ans)\s+(?:of\s+)?experience\b",
    r"\b(?:minimum|min\.?)\s*(?:de\s*)?(?:3|4|5|6|7|8|9|10)\s*ans\b",
    r"\b(?:3|4|5|6|7|8|9|10)\s*[-–]\s*(?:4|5|6|7|8|9|10)\s*(?:years?|ans)\b",
    r"\b(?:3|4|5|6|7|8|9|10)\s*(?:to|a)\s*(?:4|5|6|7|8|9|10)\s*(?:years?|ans)\b",
    r"\bexperience\s+(?:minimale|minimal|required|requise|minimum|minimale)\s*(?:de\s*)?(?:3|4|5|6|7|8|9|10)\s*(?:ans|years?)\b",
    r"\b(?:3|4|5|6|7|8|9|10)\s*(?:ans|years?)\s+d['’]?\s*experience\b",
    r"\bexperience\s+de\s+(?:3|4|5|6|7|8|9|10)\s*(?:ans|years?)\b",
]

MID_EXPERIENCE_PATTERNS = [
    r"\b(?:at\s+least|min(?:imum)?\.?)\s*2\+?\s*(?:years?|ans)\b",
    r"\b(?:au\s+moins|min(?:imum)?\.?)\s*2\+?\s*(?:ans|years?)\b",
    r"\b2\+?\s*(?:years?|ans)\s+(?:of\s+)?experience\b",
    r"\b(?:minimum|min\.?)\s*(?:de\s*)?2\s*ans\b",
    r"\b2\s*[-/]\s*3\s*(?:years?|ans)\b",
    r"\b2\s*(?:to|a)\s*3\s*(?:years?|ans)\b",
    r"\bexperience\s+(?:minimale|minimal|required|requise|minimum|minimale)\s*(?:de\s*)?2\s*(?:ans|years?)\b",
    r"\b2\s*(?:ans|years?)\s+d['’]?\s*experience\b",
]

NON_TARGET_APPRENTICESHIP_MARKERS = [
    "apprenticeship",
    "apprenti",
    "apprentissage",
    "cfc",
    "formation initiale",
]

NON_TARGET_TRAINER_MARKERS = [
    "formateur",
    "trainer",
    "instructor",
    "enseignant",
]

SUPPORT_ONLY_TITLE_PATTERNS = [
    r"\bhelp\s*desk\b",
    r"\bservice\s*desk\b",
    r"\bit\s+supporter\b",
    r"\bit\s+support\s+technician\b",
    r"\btechnicien(?:ne)?\s+support\b",
    r"\bsupport\s+technique\b",
    r"\bsupporttechniker\b",
]

INFRA_RELEVANT_MARKERS = [
    "devops",
    "cloud",
    "linux",
    "kubernetes",
    "terraform",
    "ansible",
    "sre",
    "platform",
    "infrastructure",
    "network",
    "system administrator",
    "systems administrator",
    "application support engineer",
    "application support",
]

INFRA_TITLE_MARKERS = [
    "devops",
    "cloud",
    "linux",
    "infrastructure",
    "platform",
    "network",
    "system administrator",
    "systems administrator",
    "application support engineer",
    "application support",
]

SENIOR_NETWORK_MARKERS = [
    "bgp",
    "ospf",
    "vxlan",
    "mpls",
    "ccnp",
    "ccie",
    "sdwan",
    "5000 users",
    "5 000 users",
    "5k users",
]

NON_TARGET_FINANCE_MARKERS = [
    "finance",
    "financial",
    "accounting",
    "comptabil",
    "trader",
    "trading",
    "credit",
]

NON_TARGET_BUSINESS_ANALYST_MARKERS = [
    "business analyst",
    "analyste fonctionnel",
    "functional analyst",
]

NON_TARGET_MANUAL_QA_MARKERS = [
    "test analyst",
    "manual tester",
    "manual testing",
]

NON_TARGET_INDUSTRIAL_MARKERS = [
    "electrical",
    "electric",
    "electrique",
    "process engineer",
    "production engineer",
    "plc",
    "scada",
    "instrumentation",
    "robotics",
    "mecanique",
    "mechanical",
]

QA_DEVOPS_BRIDGE_MARKERS = [
    "test automation",
    "qa automation",
    "cicd",
    "ci/cd",
    "devops",
    "pipeline",
    "build",
    "release",
]

CORE_IT_TITLE_MARKERS = [
    "devops",
    "cloud",
    "platform",
    "sre",
    "system administrator",
    "systems administrator",
    "linux",
    "test automation",
    "qa automation",
    "build engineer",
    "release engineer",
    "application support engineer",
]


def fetch_with_retries(
    url: str,
    session: requests.Session,
    max_retries: int = 3,
    timeout: int = 15,
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
            if resp.status_code >= 500 or resp.status_code == 429:
                raise requests.HTTPError(f"{resp.status_code} {resp.reason}")
            resp.raise_for_status()
            return resp.text, None
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            if attempt < max_retries - 1:
                # Light jitter helps reduce synchronized retries on rate-limited hosts.
                time.sleep(1.5 * (attempt + 1) + random.uniform(0.1, 0.6))
                continue
            return None, err
    return None, "unknown_error"


def extract_text(html: str, max_chars: int = 12000) -> str:
    """Best-effort text extraction from HTML."""
    structured = extract_structured_job_description(html)
    if structured:
        return structured[:max_chars]

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        text = " ".join(s.strip() for s in soup.stripped_strings)
    else:
        # Lightweight fallback if bs4 is unavailable.
        text = html
        for token in ("<script", "<style"):
            while True:
                start = text.lower().find(token)
                if start == -1:
                    break
                end = text.lower().find("</", start)
                if end == -1:
                    break
                close = text.find(">", end)
                if close == -1:
                    break
                text = text[:start] + " " + text[close + 1 :]
        text = text.replace("<", " ").replace(">", " ")
    text = " ".join(text.split())
    return text[:max_chars]


def is_not_found_page_text(text: str) -> bool:
    """Detect generic page-not-found templates returned instead of job content."""
    norm = af.normalize(text or "")
    if not norm:
        return False
    return any(marker in norm for marker in NOT_FOUND_PAGE_MARKERS)


def clean_html_fragment(text: str) -> str:
    if not text:
        return ""
    raw = unescape(str(text))
    if BeautifulSoup is not None:
        soup = BeautifulSoup(raw, "html.parser")
        cleaned = " ".join(s.strip() for s in soup.stripped_strings)
        return " ".join(cleaned.split())
    cleaned = re.sub(r"<[^>]+>", " ", raw)
    cleaned = " ".join(cleaned.split())
    return cleaned


def iter_dicts(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from iter_dicts(v)
    elif isinstance(value, list):
        for item in value:
            yield from iter_dicts(item)


def extract_adzuna_job_id(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"/(?:details|land/ad)/(\d+)", str(url))
    return m.group(1) if m else ""


def normalize_details_url(url: str) -> str:
    job_id = extract_adzuna_job_id(url)
    if not job_id:
        return ""
    return f"https://www.adzuna.ch/details/{job_id}"


def unique_urls(items: list[str]) -> list[str]:
    out = []
    seen = set()
    for raw in items:
        u = (raw or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def build_fetch_candidates(url: str, canonical_url: str = "") -> list[str]:
    """
    Build URL candidates ordered by probability of success.
    - Prefer stable details URL when we can derive a job id.
    - Keep provided URLs as fallback.
    """
    details_from_url = normalize_details_url(url)
    details_from_canonical = normalize_details_url(canonical_url)
    return unique_urls(
        [
            details_from_url,
            details_from_canonical,
            canonical_url,
            url,
            (url.split("?", 1)[0] if url else ""),
        ]
    )


def token_set(text: str) -> set[str]:
    norm = af.normalize(text or "")
    toks = [t for t in re.split(r"[^a-z0-9]+", norm) if len(t) >= 3]
    stop = {"and", "the", "for", "with", "des", "les", "une", "dans", "sur", "job", "jobs"}
    return {t for t in toks if t not in stop}


def absolutize_adzuna_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return "https://www.adzuna.ch" + href
    return "https://www.adzuna.ch/" + href


def find_adzuna_url_via_search(
    title: str,
    company: str,
    location: str,
    session: requests.Session,
    timeout: int = 12,
) -> str:
    """
    Search Adzuna website and pick the most likely matching details URL.
    Used only as fallback when direct candidates fail.
    """
    title = str(title or "").strip()
    company = str(company or "").strip()
    location = str(location or "").strip()
    if not title:
        return ""

    queries = unique_urls(
        [
            title,
            f"{title} {company}".strip(),
            f"{title} {location}".strip(),
        ]
    )
    title_tokens = token_set(title)
    company_tokens = token_set(company)
    location_tokens = token_set(location)
    best_score = -1
    best_url = ""

    for q in queries[:3]:
        try:
            resp = session.get(
                "https://www.adzuna.ch/search",
                params={"what": q},
                timeout=timeout,
                headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            if resp.status_code != 200:
                continue
            html = resp.text
            candidates: list[tuple[str, str, str]] = []

            if BeautifulSoup is not None:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = str(a.get("href", ""))
                    if "/details/" not in href and "/land/ad/" not in href:
                        continue
                    url = absolutize_adzuna_url(href)
                    anchor_text = " ".join(a.stripped_strings)
                    parent_text = " ".join(a.parent.stripped_strings) if a.parent else anchor_text
                    candidates.append((url, anchor_text, parent_text))
            else:
                for m in re.finditer(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", html, flags=re.I | re.S):
                    href = m.group(1)
                    if "/details/" not in href and "/land/ad/" not in href:
                        continue
                    url = absolutize_adzuna_url(href)
                    anchor_text = clean_html_fragment(m.group(2))
                    candidates.append((url, anchor_text, anchor_text))

            for url, anchor_text, surrounding_text in candidates:
                a_tokens = token_set(anchor_text)
                s_tokens = token_set(surrounding_text)
                score = 0
                if "/details/" in url:
                    score += 6
                score += 2 * len(title_tokens.intersection(a_tokens))
                score += 1 * len(company_tokens.intersection(s_tokens))
                score += 1 * len(location_tokens.intersection(s_tokens))

                if score > best_score:
                    best_score = score
                    best_url = url
        except Exception:
            continue

    return best_url if best_score >= 2 else ""


def load_cache(cache_path: str) -> dict:
    if not cache_path or not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_cache(cache_path: str, data: dict):
    if not cache_path:
        return
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, cache_path)


def refresh_viewer_html(input_csv: str, market: str, ch_focus: str, filter_mode: str):
    """
    Rebuild local HTML viewer from the latest CSV so browser refresh shows new data.
    """
    viewer_script = Path(__file__).with_name("jobs_viewer.py")
    if not viewer_script.exists():
        return
    src = Path(input_csv)
    if not src.exists():
        return
    out_html = src.with_name("job_viewer.html")
    cmd = [
        sys.executable,
        str(viewer_script),
        "--input",
        str(src),
        "--output",
        str(out_html),
        "--market",
        market,
        "--ch-focus",
        ch_focus,
        "--filter-mode",
        filter_mode,
        "--no-open",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[ENRICH] Viewer refreshed: {out_html}")
        else:
            err = (result.stderr or result.stdout or "").strip().splitlines()
            msg = err[-1] if err else "unknown error"
            print(f"[ENRICH][WARN] Viewer refresh failed: {msg}")
    except Exception as e:
        print(f"[ENRICH][WARN] Viewer refresh exception: {type(e).__name__}: {e}")


def extract_structured_job_description(html: str) -> str:
    """Prefer schema JobPosting description over full-page text."""
    ldjson_blocks: list[str] = []
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
            txt = node.string or node.get_text() or ""
            if txt.strip():
                ldjson_blocks.append(txt)
    else:
        for m in re.finditer(
            r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            txt = m.group(1).strip()
            if txt:
                ldjson_blocks.append(txt)

    for block in ldjson_blocks:
        try:
            data = json.loads(block)
        except Exception:
            continue
        for d in iter_dicts(data):
            d_type = str(d.get("@type", "")).lower()
            if "jobposting" in d_type and d.get("description"):
                cleaned = clean_html_fragment(d.get("description", ""))
                if len(cleaned) >= 60:
                    return cleaned

    # Adzuna page also embeds az_details with a description field.
    m = re.search(r'"description"\s*:\s*"(.*?)"\s*,\s*"id"\s*:', html, flags=re.DOTALL)
    if m:
        encoded = m.group(1)
        try:
            decoded = bytes(encoded, "utf-8").decode("unicode_escape")
        except Exception:
            decoded = encoded
        cleaned = clean_html_fragment(decoded)
        if len(cleaned) >= 60:
            return cleaned

    return ""


def playwright_fetch(url: str, timeout_ms: int = 15000) -> Tuple[Optional[str], Optional[str]]:
    """Try JS rendering for websites where requests() is blocked or incomplete."""
    if sync_playwright is None:
        return None, "playwright_not_installed"
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


def fetch_description_from_candidates(
    candidates: list[str],
    title: str,
    company: str,
    location: str,
    session: requests.Session,
    max_retries: int,
    timeout: int,
    use_browser: bool,
    browser_timeout: int,
) -> tuple[str, str, str]:
    """
    Try several URL candidates and return:
      (description_text, used_url, error_summary)
    """
    errors: list[str] = []

    for candidate in candidates:
        html, err = fetch_with_retries(candidate, session, max_retries=max_retries, timeout=timeout)
        if html:
            text = extract_text(html)
            if text and len(text.strip()) >= af.MIN_DESCRIPTION_CHARS:
                if is_not_found_page_text(text):
                    errors.append(f"{candidate}::not_found_template")
                    continue
                return text, candidate, ""
            errors.append(f"{candidate}::empty_or_short")
        else:
            errors.append(f"{candidate}::{err or 'fetch_failed'}")

        if use_browser and ("403" in (err or "") or "429" in (err or "") or "timeout" in (err or "").lower()):
            text, perr = playwright_fetch(candidate, timeout_ms=browser_timeout * 1000)
            if text:
                normalized = " ".join(text.split())[:12000]
                if normalized and len(normalized.strip()) >= af.MIN_DESCRIPTION_CHARS:
                    if is_not_found_page_text(normalized):
                        errors.append(f"{candidate}::browser::not_found_template")
                        continue
                    return normalized, candidate, ""
            errors.append(f"{candidate}::browser::{perr or 'browser_failed'}")

    search_url = find_adzuna_url_via_search(title, company, location, session=session, timeout=timeout)
    if search_url and search_url not in candidates:
        html, err = fetch_with_retries(search_url, session, max_retries=max_retries, timeout=timeout)
        if html:
            text = extract_text(html)
            if text and len(text.strip()) >= af.MIN_DESCRIPTION_CHARS:
                if is_not_found_page_text(text):
                    errors.append(f"{search_url}::search_fallback::not_found_template")
                else:
                    return text, search_url, ""
            errors.append(f"{search_url}::search_fallback::empty_or_short")
        else:
            errors.append(f"{search_url}::search_fallback::{err or 'fetch_failed'}")

        if use_browser and ("403" in (err or "") or "429" in (err or "") or "timeout" in (err or "").lower()):
            text, perr = playwright_fetch(search_url, timeout_ms=browser_timeout * 1000)
            if text:
                normalized = " ".join(text.split())[:12000]
                if normalized and len(normalized.strip()) >= af.MIN_DESCRIPTION_CHARS:
                    if is_not_found_page_text(normalized):
                        errors.append(f"{search_url}::search_fallback::browser::not_found_template")
                        return "", "", " | ".join(errors[:6])
                    return normalized, search_url, ""
            errors.append(f"{search_url}::search_fallback::browser::{perr or 'browser_failed'}")

    return "", "", " | ".join(errors[:6])


def first_fail_reason(job: dict, filter_mode: str) -> str:
    """Mirror passes_filters order to expose first failing step."""
    mode = resolve_filter_mode(filter_mode, allow_both=False)

    created = job.get("created", "") or job.get("updated", "")
    loc = job.get("location", "")
    if isinstance(loc, dict):
        loc = loc.get("display_name", "")
    if not loc:
        loc = job.get("location.display_name", "")
    loc = af.rule_plain_text(loc)

    title = af.rule_plain_text(job.get("title", "") or "")
    desc = af.rule_plain_text(job.get("description", "") or "")
    full_text = f"{title} {desc}"
    senior_reason = detect_explicit_senior_requirement(title, desc)
    if senior_reason:
        return senior_reason
    internship_detail = af.internship_student_only_detail(title, desc)
    if internship_detail:
        return f"non_target_role:student_internship_required:{internship_detail}"
    non_target_reason = detect_non_target_role(title, desc)
    if non_target_reason:
        return non_target_reason
    mid_exp_reason = detect_mid_experience_requirement(title, desc)
    if mid_exp_reason:
        return mid_exp_reason
    internship_manual_detail = af.internship_generic_detail(title, desc)
    if internship_manual_detail:
        return f"non_target_role:internship_generic:{internship_manual_detail}"

    if af.REQUIRE_DESCRIPTION and len(desc.strip()) < af.MIN_DESCRIPTION_CHARS:
        return "description_too_short"

    norm_title = af.normalize(title)
    for bad_title in af.BAD_TITLE_KEYWORDS:
        if bad_title in norm_title:
            return f"bad_title:{bad_title.strip()}"

    if not af.is_recent(created, af.MAX_DAYS_OLD):
        return "too_old"

    if not af.location_ok(loc, title, desc):
        return "location_blocked"

    if not af.role_relevant(title, desc):
        forbidden_detail = af.role_forbidden_reason(title, desc)
        if forbidden_detail:
            return f"role_forbidden:{forbidden_detail}"
        return "role_missing_required"

    hard_hits, soft_hits = af.classify_excluded_hits(title, full_text)
    if hard_hits:
        return f"exclude_keyword:{hard_hits[0]}"
    if soft_hits:
        return f"exclude_keyword:{soft_hits[0]}"

    blocked_language_reason = af.blocked_language_requirement_reason(full_text)
    if blocked_language_reason:
        return blocked_language_reason

    language_alternative_reason = af.language_manual_review_reason(full_text)
    if language_alternative_reason:
        return language_alternative_reason

    if mode == "strict" and af.is_disallowed_language(full_text):
        return "blocked_language_detected"

    junior_score = af.compute_junior_score(title, desc)
    min_junior_score = 0 if mode == "strict" else -1
    if junior_score < min_junior_score:
        return f"junior_score<{min_junior_score}"

    return ""


def classify_recheck_failure(
    keep_before: bool,
    keep_after_full: bool,
    fail_reason: str,
    title: str,
    filter_mode: str,
) -> tuple[bool, str]:
    """
    Decide whether a full-description failure is a hard exclusion or manual review.

    Returns:
      (hard_exclude, manual_review_reason)
    """
    if not keep_before or keep_after_full or not fail_reason:
        return False, ""

    reason = str(fail_reason)

    # High-confidence hidden constraints.
    if reason == "source_page_not_found":
        return True, ""
    if reason.startswith("non_target_role:student_internship_required:") or reason.startswith("internship_student_only:"):
        return True, ""
    if reason.startswith("non_target_role:"):
        if reason.startswith("non_target_role:internship_generic:"):
            return False, reason
        return True, ""
    if reason.startswith("explicit_senior_requirement:hard:") or reason.startswith("title_senior_marker:"):
        return True, ""
    if reason.startswith("explicit_experience_requirement:soft"):
        return False, reason
    if reason == "blocked_language_requirement" or reason.startswith("blocked_language_req:"):
        return True, ""
    if reason.startswith("language_alternative:"):
        return False, reason
    if reason.startswith("junior_score<"):
        return True, ""

    # Auto language detection is noisy on mixed-language CH postings.
    if reason == "blocked_language_detected":
        return False, reason

    if reason.startswith("exclude_keyword:"):
        kw = reason.split(":", 1)[1].strip().lower()
        if kw in {"lead", "lead_soft"}:
            if af.title_has_lead_or_manager(title):
                return True, ""
            return False, "exclude_keyword:lead_soft"
        if kw in {"senior", "principal", "staff engineer", "team lead", "tech lead", "director", "head of"}:
            return True, ""
        if kw in {k.lower() for k in HARD_EXCLUDE_KEYWORDS}:
            return True, ""
        if kw in {k.lower() for k in AMBIGUOUS_EXCLUDE_KEYWORDS}:
            return False, reason
        # Unknown exclude keywords become review-only by default in enrichment step.
        return False, reason

    if reason.startswith("role_forbidden:"):
        bad = reason.split(":", 1)[1].strip().lower()
        title_norm = af.normalize(title or "")
        if bad in {"commercial_sales", "delivery_role"}:
            return True, ""
        if bad in {k.lower() for k in AMBIGUOUS_ROLE_FORBIDDEN}:
            return False, reason
        # High confidence: forbidden marker appears in title itself.
        if bad and bad in title_norm:
            return True, ""
        # Otherwise review-only because it can be contextual in description.
        return False, reason

    # Role-missing from enriched text is often ambiguous/noisy for real jobs.
    if reason == "role_missing_required":
        return False, reason

    # Keep out of apply-ready when we could not enrich beyond likely preview text.
    if reason == "insufficient_full_description":
        return False, reason

    # Keep original hard behavior for non-textual constraints.
    if reason.startswith("bad_title:") or reason in {"description_too_short", "too_old", "location_blocked"}:
        return True, ""

    return False, reason


def keyword_hit(text_norm: str, keyword: str) -> bool:
    """Safer keyword match with boundaries to reduce accidental substrings."""
    kw = af.normalize(keyword or "").strip()
    txt = af.normalize(text_norm or "")
    if not kw or not txt:
        return False

    pattern = r"\b" + re.escape(kw).replace(r"\ ", r"\s+") + r"\b"
    return re.search(pattern, txt) is not None


def detect_explicit_senior_requirement(title: str, desc: str) -> str:
    """Return a reason id when text clearly signals non-junior seniority."""
    title_norm = af.normalize(title or "")
    for marker in SENIOR_TITLE_MARKERS:
        if keyword_hit(title_norm, marker):
            return f"title_senior_marker:{marker}"

    exp_level, exp_detail, _years_required = af.detect_experience_requirement_details(title, desc)
    if exp_level == "hard":
        return f"explicit_senior_requirement:hard:{af.normalize(exp_detail)}"

    return ""


def detect_mid_experience_requirement(title: str, desc: str) -> str:
    """
    Detect soft explicit experience requirements.
    Kept as manual-review (not hard exclude) because it can still be negotiable.
    """
    exp_level, exp_detail, _years_required = af.detect_experience_requirement_details(title, desc)
    if exp_level in {"soft", "soft_junior_title"}:
        return f"explicit_experience_requirement:{exp_level}:{af.normalize(exp_detail)}"
    return ""


def detect_non_target_role(title: str, desc: str) -> str:
    """
    Exclude clear non-target roles for this pipeline objective.
    """
    title_norm = af.normalize(title or "")
    text_norm = af.normalize(f"{title or ''} {desc or ''}")

    for marker in NON_TARGET_APPRENTICESHIP_MARKERS:
        if af.keyword_hit(text_norm, marker, boundary_only=True):
            return "non_target_role:apprenticeship"

    for marker in NON_TARGET_TRAINER_MARKERS:
        if af.keyword_hit(title_norm, marker, boundary_only=True):
            return "non_target_role:trainer"

    is_support_title = any(re.search(pat, title_norm) for pat in SUPPORT_ONLY_TITLE_PATTERNS)
    if is_support_title:
        has_infra_title_signal = any(
            af.keyword_hit(title_norm, marker, boundary_only=True) for marker in INFRA_TITLE_MARKERS
        )
        if not has_infra_title_signal:
            return "non_target_role:support_only"

    is_network_title = af.keyword_hit(title_norm, "network engineer", boundary_only=True) or af.keyword_hit(
        title_norm, "ingenieur reseau", boundary_only=True
    )
    if is_network_title and any(marker in text_norm for marker in SENIOR_NETWORK_MARKERS):
        return "non_target_role:senior_network"

    has_infra_signal = any(af.keyword_hit(text_norm, marker, boundary_only=True) for marker in INFRA_RELEVANT_MARKERS)
    has_bridge_signal = any(af.keyword_hit(text_norm, marker, boundary_only=True) for marker in QA_DEVOPS_BRIDGE_MARKERS)
    infra_or_bridge = has_infra_signal or has_bridge_signal
    has_core_it_title = any(af.keyword_hit(title_norm, marker, boundary_only=True) for marker in CORE_IT_TITLE_MARKERS)

    is_finance_title = any(af.keyword_hit(title_norm, marker, boundary_only=True) for marker in NON_TARGET_FINANCE_MARKERS)
    if is_finance_title and not has_core_it_title:
        return "non_target_role:finance"

    is_business_analyst_title = any(
        af.keyword_hit(title_norm, marker, boundary_only=True) for marker in NON_TARGET_BUSINESS_ANALYST_MARKERS
    )
    if is_business_analyst_title:
        return "non_target_role:business_analysis"

    if af.keyword_hit(title_norm, "manual", boundary_only=True) and af.keyword_hit(title_norm, "test", boundary_only=True):
        return "non_target_role:manual_qa"
    is_manual_qa_title = any(af.keyword_hit(title_norm, marker, boundary_only=True) for marker in NON_TARGET_MANUAL_QA_MARKERS)
    if is_manual_qa_title and not has_bridge_signal:
        return "non_target_role:manual_qa"

    is_industrial_title = any(
        af.keyword_hit(title_norm, marker, boundary_only=True) for marker in NON_TARGET_INDUSTRIAL_MARKERS
    )
    if is_industrial_title and not infra_or_bridge:
        return "non_target_role:industrial_automation"

    is_generic_automation_engineer = af.keyword_hit(title_norm, "automation engineer", boundary_only=True)
    is_qa_automation_title = af.keyword_hit(title_norm, "qa automation", boundary_only=True) or af.keyword_hit(
        title_norm, "test automation", boundary_only=True
    )
    if is_generic_automation_engineer and not is_qa_automation_title and not has_core_it_title:
        return "non_target_role:industrial_automation"

    return ""


def bool_to_int_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def blocked_reason_detail_from_reason(reason: str) -> str:
    text = str(reason or "").strip()
    if not text:
        return ""
    if ":" not in text:
        return text
    return text.split(":")[-1].strip()


def main():
    parser = argparse.ArgumentParser(description="Enrich filtered jobs with full descriptions + re-filter.")
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
        choices=SUPPORTED_FILTER_MODES[:2],
        default="",
        help="Filter strictness for re-check (strict|broad). Defaults to JOB_FILTER_MODE env var or strict.",
    )
    parser.add_argument("--input", required=True, help="Input filtered CSV.")
    parser.add_argument("--output", required=True, help="Output diagnostics CSV.")
    parser.add_argument(
        "--filtered-output",
        default="",
        help="Backward-compatible alias for --apply-ready-output.",
    )
    parser.add_argument(
        "--apply-ready-output",
        default="",
        help="Output CSV for apply-ready rows only (hard excludes and manual-review rows removed).",
    )
    parser.add_argument(
        "--manual-review-output",
        default="",
        help="Optional output CSV for manual-review rows only.",
    )
    parser.add_argument(
        "--hard-excluded-output",
        default="",
        help="Optional output CSV for hard-excluded rows only.",
    )
    parser.add_argument("--sleep", type=float, default=1.5, help="Seconds to sleep between requests.")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries per URL.")
    parser.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds.")
    parser.add_argument(
        "--use-browser",
        action="store_true",
        help="Use Playwright Chromium fallback for blocked/JS-heavy pages.",
    )
    parser.add_argument("--browser-timeout", type=int, default=15, help="Playwright timeout in seconds.")
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=0,
        help="Limit rows to enrich (0 = all). Useful for fast dry-runs.",
    )
    parser.add_argument(
        "--cache-path",
        default="",
        help="Optional JSON cache file for fetched descriptions.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable description cache reads/writes.",
    )
    args = parser.parse_args()

    market = af.configure_market(args.market, args.ch_focus)
    filter_mode = resolve_filter_mode(args.filter_mode, allow_both=False)
    apply_ready_output = args.apply_ready_output or args.filtered_output
    manual_review_output = args.manual_review_output
    hard_excluded_output = args.hard_excluded_output
    if apply_ready_output:
        p_apply = Path(apply_ready_output)
        if not manual_review_output:
            manual_review_output = str(p_apply.with_name(f"{p_apply.stem}_manual_review{p_apply.suffix}"))
        if not hard_excluded_output:
            hard_excluded_output = str(p_apply.with_name(f"{p_apply.stem}_hard_excluded{p_apply.suffix}"))
    print(
        f"[ENRICH] market={market} ch_focus={af.ACTIVE_MARKET_PROFILE['ch_focus']} "
        f"filter_mode={filter_mode}"
    )

    default_cache_path = str(Path(args.output).with_name("description_fetch_cache.json"))
    cache_path = "" if args.no_cache else (args.cache_path or default_cache_path)
    cache = load_cache(cache_path) if cache_path else {}

    df = pd.read_csv(args.input)
    if df.empty:
        print(f"[ENRICH] Empty input: {args.input}")
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        af.safe_save_csv(df, args.output)
        if apply_ready_output:
            Path(apply_ready_output).parent.mkdir(parents=True, exist_ok=True)
            af.safe_save_csv(df, apply_ready_output)
        if manual_review_output:
            Path(manual_review_output).parent.mkdir(parents=True, exist_ok=True)
            af.safe_save_csv(df, manual_review_output)
        if hard_excluded_output:
            Path(hard_excluded_output).parent.mkdir(parents=True, exist_ok=True)
            af.safe_save_csv(df, hard_excluded_output)
        return

    if args.max_jobs and args.max_jobs > 0:
        df = df.head(args.max_jobs).copy()
        print(f"[ENRICH] max_jobs={args.max_jobs}, working rows={len(df)}")

    rows = []
    apply_ready_rows = []
    manual_review_rows = []
    hard_excluded_rows = []
    hard_reason_counts: Counter[str] = Counter()
    review_reason_counts: Counter[str] = Counter()

    session = requests.Session()
    ok = 0
    fail = 0
    cache_hits = 0

    for _, row in df.iterrows():
        row_data = row.to_dict()
        url = row_data.get("url") or row_data.get("canonical_url") or ""
        canonical_url = row_data.get("canonical_url") or ""
        source = str(row_data.get("source", "adzuna") or "adzuna")
        original_desc = af.clean_text(row_data.get("description", "") or "")
        candidates = build_fetch_candidates(str(url), str(canonical_url))

        scraped = ""
        fetch_error = ""
        fetch_used_url = ""
        fetch_from_cache = False
        if candidates:
            # Cache hit: first candidate with cached non-empty description wins.
            if cache_path:
                for c in candidates:
                    cached = cache.get(c, {})
                    cached_text = str(cached.get("scraped", "") or "")
                    if is_not_found_page_text(cached_text):
                        # Purge stale cache entries containing generic "page not found" templates.
                        cache.pop(c, None)
                        continue
                    if cached_text and len(cached_text.strip()) >= af.MIN_DESCRIPTION_CHARS:
                        scraped = cached_text
                        fetch_used_url = c
                        fetch_from_cache = True
                        cache_hits += 1
                        break

            if not scraped:
                scraped, fetch_used_url, fetch_error = fetch_description_from_candidates(
                    candidates=candidates,
                    title=str(row_data.get("title", "")),
                    company=str(row_data.get("company", "")),
                    location=str(row_data.get("location", "")),
                    session=session,
                    max_retries=args.max_retries,
                    timeout=args.timeout,
                    use_browser=args.use_browser,
                    browser_timeout=args.browser_timeout,
                )
                if scraped:
                    if cache_path and fetch_used_url:
                        cache[fetch_used_url] = {"scraped": scraped}
                        # Keep aliases warm to improve future hit rates.
                        for c in candidates:
                            if c not in cache and c != fetch_used_url:
                                cache[c] = {"scraped": scraped}
                    ok += 1
                else:
                    fail += 1
            time.sleep(args.sleep)
        else:
            fetch_error = "missing_url"
            fail += 1

        combined_desc = scraped if scraped and len(scraped) > len(original_desc) else original_desc
        details_from_url = normalize_details_url(str(url))
        details_from_canonical = normalize_details_url(str(canonical_url))
        working_url = fetch_used_url or details_from_url or details_from_canonical or str(canonical_url or url or "")
        original_len = len((original_desc or "").strip())
        combined_len = len((combined_desc or "").strip())
        scraped_len = len((scraped or "").strip())
        preview_only = (
            original_len >= 390
            and combined_len <= 420
            and (not scraped or scraped_len <= original_len)
        )

        job_before = dict(row_data)
        job_before["description"] = original_desc
        keep_before = af.passes_filters(job_before, source=source, filter_mode=filter_mode) is not None

        job_after = dict(row_data)
        job_after["description"] = combined_desc
        title_text = str(row_data.get("title", "") or "")
        location_text = str(row_data.get("location", "") or "")
        experience_level, experience_detail, years_required = af.detect_experience_requirement_details(
            title_text, combined_desc
        )
        work_mode = af.detect_work_mode(title_text, combined_desc, location_text)
        explicit_senior_reason = detect_explicit_senior_requirement(title_text, combined_desc)
        internship_reason_detail = af.internship_student_only_detail(title_text, combined_desc)
        internship_manual_detail = af.internship_generic_detail(title_text, combined_desc)
        non_target_reason = detect_non_target_role(title_text, combined_desc)
        mid_experience_reason = detect_mid_experience_requirement(title_text, combined_desc)
        language_req = af.language_requirements(combined_desc)
        language_required_codes = sorted(language_req.get("required_langs", set()))
        language_optional_codes = sorted(language_req.get("optional_langs", set()))
        language_evidence = language_req.get("evidence", [])
        blocked_language_reason = af.blocked_language_requirement_reason(combined_desc)
        language_alternative_reason = af.language_manual_review_reason(combined_desc)
        page_not_found_detected = (not scraped) and ("not_found_template" in str(fetch_error or "").lower())
        keep_after_filters = af.passes_filters(job_after, source=source, filter_mode=filter_mode) is not None
        if page_not_found_detected:
            keep_after_full = False
            fail_reason = "source_page_not_found"
        elif keep_after_filters and preview_only:
            keep_after_full = False
            fail_reason = "insufficient_full_description"
        elif explicit_senior_reason:
            keep_after_full = False
            fail_reason = explicit_senior_reason
        elif internship_reason_detail:
            keep_after_full = False
            fail_reason = f"non_target_role:student_internship_required:{internship_reason_detail}"
        elif non_target_reason:
            keep_after_full = False
            fail_reason = non_target_reason
        elif blocked_language_reason:
            keep_after_full = False
            fail_reason = blocked_language_reason
        elif language_alternative_reason:
            keep_after_full = False
            fail_reason = language_alternative_reason
        elif mid_experience_reason:
            keep_after_full = False
            fail_reason = mid_experience_reason
        elif internship_manual_detail:
            keep_after_full = False
            fail_reason = f"non_target_role:internship_generic:{internship_manual_detail}"
        else:
            keep_after_full = bool(keep_after_filters)
            fail_reason = "" if keep_after_full else first_fail_reason(job_after, filter_mode)

        hard_exclude, manual_review_reason = classify_recheck_failure(
            keep_before=bool(keep_before),
            keep_after_full=bool(keep_after_full),
            fail_reason=fail_reason,
            title=str(row_data.get("title", "") or ""),
            filter_mode=filter_mode,
        )
        manual_review_flag = bool(keep_before and not keep_after_full and not hard_exclude and manual_review_reason)
        apply_ready_flag = bool(keep_after_full and not hard_exclude and not manual_review_flag)
        blocked_reason_detail = blocked_reason_detail_from_reason(manual_review_reason or fail_reason)
        seniority_flag = "none"
        if explicit_senior_reason:
            seniority_flag = "hard"
        elif mid_experience_reason:
            seniority_flag = "soft"
        effective_reason = manual_review_reason or fail_reason
        if seniority_flag == "none":
            if str(effective_reason).startswith("explicit_senior_requirement:") or str(effective_reason).startswith(
                "title_senior_marker:"
            ):
                seniority_flag = "hard"
            elif str(effective_reason).startswith("explicit_experience_requirement:"):
                seniority_flag = "soft"
            elif experience_level == "hard":
                seniority_flag = "hard"
            elif experience_level in {"soft", "soft_junior_title"}:
                seniority_flag = "soft"

        internship_flag = "none"
        if internship_reason_detail:
            internship_flag = "blocked_student"
        elif internship_manual_detail:
            internship_flag = "manual"
        if internship_flag == "none":
            if str(effective_reason).startswith("non_target_role:student_internship_required:"):
                internship_flag = "blocked_student"
            elif str(effective_reason).startswith("non_target_role:internship_generic:"):
                internship_flag = "manual"

        why_reasons = []
        for reason in [
            explicit_senior_reason,
            mid_experience_reason,
            (f"non_target_role:student_internship_required:{internship_reason_detail}" if internship_reason_detail else ""),
            (f"non_target_role:internship_generic:{internship_manual_detail}" if internship_manual_detail else ""),
            non_target_reason,
            blocked_language_reason,
            language_alternative_reason,
            fail_reason,
            manual_review_reason,
        ]:
            reason_str = str(reason or "").strip()
            if reason_str and reason_str not in why_reasons:
                why_reasons.append(reason_str)
        why_text = json.dumps(why_reasons, ensure_ascii=False)

        if keep_before and not keep_after_full:
            if hard_exclude:
                hard_reason_counts[fail_reason or "unknown"] += 1
            else:
                review_reason_counts[manual_review_reason or fail_reason or "unknown"] += 1

        original_hits = set(af.excluded_hits(original_desc))
        combined_hits = set(af.excluded_hits(combined_desc))
        hidden_hits = sorted(combined_hits - original_hits)

        blocked_req_reason_before = af.blocked_language_requirement_reason(original_desc)
        blocked_req_reason_after = af.blocked_language_requirement_reason(combined_desc)
        blocked_req_before = bool(blocked_req_reason_before)
        blocked_req_after = bool(blocked_req_reason_after)
        blocked_lang_before = af.is_disallowed_language(original_desc)
        blocked_lang_after = af.is_disallowed_language(combined_desc)

        rows.append(
            {
                **row_data,
                "scraped_description": scraped,
                "scraped_len": len(scraped),
                "original_len": len(original_desc),
                "combined_description": combined_desc,
                "combined_len": len(combined_desc),
                "fetched_full_description": bool(scraped),
                "fetch_from_cache": bool(fetch_from_cache),
                "fetch_used_url": fetch_used_url,
                "working_url": working_url,
                "fetch_candidates_count": len(candidates),
                "fetch_error": fetch_error,
                "preview_only_description": bool(preview_only),
                "not_found_template_detected": bool(page_not_found_detected),
                "keep_before_recheck": bool(keep_before),
                "keep_after_full_recheck": bool(keep_after_full),
                "keep_after_recheck": bool(apply_ready_flag),
                "apply_ready_after_recheck": bool(apply_ready_flag),
                "excluded_after_recheck": bool(keep_before and hard_exclude),
                "hard_excluded_after_recheck": bool(keep_before and hard_exclude),
                "manual_review_after_recheck": bool(manual_review_flag),
                "manual_review_reason": manual_review_reason if manual_review_flag else "",
                "blocked_reason_detail": blocked_reason_detail,
                "seniority_flag": seniority_flag,
                "years_required": years_required if years_required is not None else "",
                "experience_detail": af.normalize(experience_detail) if experience_detail else "",
                "internship_flag": internship_flag,
                "work_mode": work_mode,
                "why": why_text,
                "exclude_hits_combined": ", ".join(sorted(combined_hits)),
                "hidden_exclude_hits": ", ".join(hidden_hits),
                "blocked_lang_requirement_before": bool(blocked_req_before),
                "blocked_lang_requirement_after": bool(blocked_req_after),
                "blocked_lang_requirement_reason_before": blocked_req_reason_before,
                "blocked_lang_requirement_reason_after": blocked_req_reason_after,
                "disallowed_language_before": bool(blocked_lang_before),
                "disallowed_language_after": bool(blocked_lang_after),
                "language_required_langs": ",".join(language_required_codes),
                "language_optional_langs": ",".join(language_optional_codes),
                "language_requirement_evidence": " | ".join(language_evidence),
                "fail_reason_after_recheck": fail_reason,
            }
        )

        if apply_ready_flag:
            keep_row = dict(row_data)
            keep_row["description"] = combined_desc[:400] if combined_desc else original_desc
            keep_row["source_url"] = str(url or "")
            keep_row["source_canonical_url"] = str(canonical_url or "")
            keep_row["working_url"] = working_url
            if working_url:
                keep_row["url"] = working_url
                keep_row["canonical_url"] = working_url.split("?", 1)[0]
            keep_row["needs_manual_review"] = False
            keep_row["manual_review_reason"] = ""
            keep_row["fail_reason_after_recheck"] = ""
            keep_row["blocked_reason_detail"] = ""
            keep_row["seniority_flag"] = seniority_flag
            keep_row["years_required"] = years_required if years_required is not None else ""
            keep_row["internship_flag"] = internship_flag
            keep_row["work_mode"] = work_mode
            keep_row["why"] = why_text
            apply_ready_rows.append(keep_row)
        elif manual_review_flag:
            review_row = dict(row_data)
            review_row["description"] = combined_desc[:400] if combined_desc else original_desc
            review_row["source_url"] = str(url or "")
            review_row["source_canonical_url"] = str(canonical_url or "")
            review_row["working_url"] = working_url
            if working_url:
                review_row["url"] = working_url
                review_row["canonical_url"] = working_url.split("?", 1)[0]
            review_row["manual_review_reason"] = manual_review_reason
            review_row["fail_reason_after_recheck"] = fail_reason
            review_row["blocked_reason_detail"] = blocked_reason_detail_from_reason(manual_review_reason or fail_reason)
            review_row["seniority_flag"] = seniority_flag
            review_row["years_required"] = years_required if years_required is not None else ""
            review_row["internship_flag"] = internship_flag
            review_row["work_mode"] = work_mode
            review_row["why"] = why_text
            manual_review_rows.append(review_row)
        elif keep_before and hard_exclude:
            hard_row = dict(row_data)
            hard_row["description"] = combined_desc[:400] if combined_desc else original_desc
            hard_row["source_url"] = str(url or "")
            hard_row["source_canonical_url"] = str(canonical_url or "")
            hard_row["working_url"] = working_url
            if working_url:
                hard_row["url"] = working_url
                hard_row["canonical_url"] = working_url.split("?", 1)[0]
            hard_row["hard_exclude_reason"] = fail_reason
            hard_row["blocked_reason_detail"] = blocked_reason_detail_from_reason(fail_reason)
            hard_row["seniority_flag"] = seniority_flag
            hard_row["years_required"] = years_required if years_required is not None else ""
            hard_row["internship_flag"] = internship_flag
            hard_row["work_mode"] = work_mode
            hard_row["why"] = why_text
            hard_excluded_rows.append(hard_row)

    out_df = pd.DataFrame(rows)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    af.safe_save_csv(out_df, args.output)

    excluded_after = 0
    manual_review_after = 0
    if "excluded_after_recheck" in out_df.columns:
        excluded_after = int(bool_to_int_series(out_df["excluded_after_recheck"]).sum())
    if "manual_review_after_recheck" in out_df.columns:
        manual_review_after = int(bool_to_int_series(out_df["manual_review_after_recheck"]).sum())

    print(f"[ENRICH] Input rows: {len(df)}")
    print(f"[ENRICH] Fetched OK: {ok}, failed: {fail}, cache_hits: {cache_hits}")
    print(f"[ENRICH] Hard excluded after full-description recheck: {excluded_after}")
    print(f"[ENRICH] Marked manual-review after recheck: {manual_review_after}")
    print(f"[ENRICH] Apply-ready after recheck: {len(apply_ready_rows)}")
    if hard_reason_counts:
        top_reasons = ", ".join(f"{k}:{v}" for k, v in hard_reason_counts.most_common(8))
        print(f"[ENRICH] Top hard exclusion reasons: {top_reasons}")
    else:
        print("[ENRICH] Top hard exclusion reasons: none")
    if review_reason_counts:
        top_review = ", ".join(f"{k}:{v}" for k, v in review_reason_counts.most_common(8))
        print(f"[ENRICH] Top manual-review reasons: {top_review}")
    else:
        print("[ENRICH] Top manual-review reasons: none")
    print(f"[ENRICH] Diagnostics saved: {args.output}")

    if cache_path:
        save_cache(cache_path, cache)
        print(f"[ENRICH] Cache saved: {cache_path} (entries={len(cache)})")

    if apply_ready_output:
        refined_df = pd.DataFrame(apply_ready_rows)
        Path(apply_ready_output).parent.mkdir(parents=True, exist_ok=True)
        af.safe_save_csv(refined_df, apply_ready_output)
        print(
            f"[ENRICH] Apply-ready saved: {apply_ready_output} "
            f"(kept={len(refined_df)}, removed={len(df) - len(refined_df)})"
        )
    if manual_review_output:
        review_df = pd.DataFrame(manual_review_rows)
        Path(manual_review_output).parent.mkdir(parents=True, exist_ok=True)
        af.safe_save_csv(review_df, manual_review_output)
        print(f"[ENRICH] Manual-review saved: {manual_review_output} (rows={len(review_df)})")
    if hard_excluded_output:
        hard_df = pd.DataFrame(hard_excluded_rows)
        Path(hard_excluded_output).parent.mkdir(parents=True, exist_ok=True)
        af.safe_save_csv(hard_df, hard_excluded_output)
        print(f"[ENRICH] Hard-excluded saved: {hard_excluded_output} (rows={len(hard_df)})")

    # Keep the local viewer in sync with the enriched CSV output.
    refresh_viewer_html(
        input_csv=args.output,
        market=market,
        ch_focus=af.ACTIVE_MARKET_PROFILE.get("ch_focus", "all"),
        filter_mode=filter_mode,
    )


if __name__ == "__main__":
    main()
