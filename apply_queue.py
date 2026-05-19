"""
Build a ranked apply queue from filtered jobs.

Default behavior:
- Uses market/ch-focus aware paths
- Reads merged filtered CSV when available, otherwise Adzuna filtered CSV
- Merges application status from tracker
- Outputs top-N jobs to apply first
"""

from __future__ import annotations

import argparse
import hashlib
import os
import unicodedata
from pathlib import Path
from typing import Iterable

import pandas as pd
from pandas.errors import EmptyDataError

from adzuna_fetch import configure_market, safe_save_csv
from config import SUPPORTED_CH_FOCUS, SUPPORTED_MARKETS, get_market_profile, get_output_paths


CLOSED_STATUSES = {"applied", "interview", "offer", "rejected", "withdrawn", "not_interested"}
POSITIVE_FEEDBACK_STATUSES = {"interview", "offer"}
NEGATIVE_FEEDBACK_STATUSES = {"rejected", "not_interested", "withdrawn"}

MA_LOCATION_FOCUS_CLUSTERS = {
    "rabat": ["rabat", "sale", "sale ", "salé", "technopolis", "skhirat", "temara", "temara", "témara"],
    "casablanca": ["casablanca", "mohammedia", "bouskoura", "nouaceur", "sidi maarouf", "sidi maârouf"],
    "tanger": ["tanger", "tangier", "tetouan", "tetouan", "tétouan"],
    "rabat_or_remote": ["rabat", "sale", "sale ", "salé", "technopolis", "skhirat", "temara", "temara", "témara"],
}


def _normalize_text_key(value: str) -> str:
    return str(value or "").strip().lower()


def _normalize_match_text(*values: str) -> str:
    raw = " ".join(str(v or "") for v in values if str(v or ""))
    folded = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    return " ".join(folded.lower().split())


def resolve_location_focus_terms(location_focus: str, market: str) -> list[str]:
    focus = _normalize_match_text(location_focus)
    if not focus:
        return []
    if market == "ma" and focus in MA_LOCATION_FOCUS_CLUSTERS:
        return [_normalize_match_text(token) for token in MA_LOCATION_FOCUS_CLUSTERS[focus]]
    return [focus]


def location_matches_focus(location: str, location_focus: str, market: str, is_remote: bool = False) -> bool:
    terms = resolve_location_focus_terms(location_focus, market)
    if not terms:
        return True
    if market == "ma" and _normalize_match_text(location_focus) == "rabat_or_remote" and bool(is_remote):
        return True
    loc_norm = _normalize_match_text(location)
    return any(term in loc_norm for term in terms)


def location_focus_path(path: str, location_focus: str) -> str:
    focus = _normalize_match_text(location_focus)
    if not focus:
        return path
    safe_focus = focus.replace(" ", "_")
    p = Path(path)
    return str(p.with_name(f"{p.stem}_{safe_focus}{p.suffix}"))


MA_NON_TARGET_LANGUAGE_MARKERS = {
    "nl": ["neerlandais", "nederlands", "dutch", "dutch-speaking"],
    "de": ["germanophone", "german", "deutsch", "allemand"],
    "es": ["hispanophone", "hispano", "spanish", "espagnol"],
    "tr": ["turkish", "turc", "turcophone"],
    "it": ["italophone", "italien", "italiano"],
}

MA_FORCE_REVIEW_TITLE_MARKERS = {
    "product_owner": ["proxy product owner", "product owner"],
    "app_support": ["support applicatif", "application support"],
    "customer_service": ["conseiller de clientele", "customer care", "customer service"],
    "qa_testing": ["testeur", "qa", "quality assurance"],
    "internship": ["stagiaire", "stage ", " stage", "internship", "intern "],
}

MA_APPLY_NOW_TITLE_SIGNALS = [
    "junior infra",
    "technicien it",
    "technicien informatique",
    "technicien en informatique",
    "technicien support informatique",
    "technicien reseau",
    "technicien si",
    "technicien support",
    "help desk",
    "helpdesk",
    "service desk",
    "support it",
    "support technique",
    "administrateur systeme",
    "administrateur reseau",
    "system engineer",
    "systems engineer",
    "infrastructure engineer",
    "network engineer",
    "network administrator",
    "devops engineer",
    "cloud engineer",
    "platform engineer",
    "ingenieur reseaux",
    "ingenieur systeme",
    "ingenieur systemes d information",
    "ingenieur infrastructure",
]

MA_GENERIC_TITLE_MARKERS = [
    "ingenieur anglophone",
    "ingenieur francophone",
    "ingenieur germanophone",
    "ingenieur hispanophone",
    "ingenieur italophone",
    "ingenieur turcophone",
]


def compute_market_queue_adjustment(row: pd.Series, market_profile: dict) -> tuple[int, str, bool]:
    """
    Apply market-specific queue penalties without removing rows from the filtered CSV.
    For Morocco, this is where we demote obvious time-wasters:
    - extra-language specialist roles outside the target FR/EN/AR set
    - product/customer-service/test roles that slipped through relevance filters
    - internships that are not worth an "apply now" slot
    """
    market = str(market_profile.get("market", "") or "").strip().lower()
    if market != "ma":
        return 0, "", False

    allowed_languages = {str(code or "").strip().lower() for code in market_profile.get("allowed_language_codes", [])}
    title_norm = _normalize_match_text(row.get("title", ""))
    text_norm = _normalize_match_text(row.get("title", ""), row.get("description", ""), row.get("company", ""))
    if not text_norm:
        return 0, "", False

    penalty = 0
    reasons: list[str] = []
    force_review = False

    for code, markers in MA_NON_TARGET_LANGUAGE_MARKERS.items():
        if code in allowed_languages:
            continue
        if any(marker in text_norm for marker in markers):
            penalty -= 12
            reasons.append(f"language:{code}")
            force_review = True

    for reason, markers in MA_FORCE_REVIEW_TITLE_MARKERS.items():
        if any(marker in title_norm for marker in markers):
            penalty -= 10
            reasons.append(reason)
            force_review = True

    penalty = max(-30, penalty)
    return penalty, " | ".join(reasons[:4]), force_review


def market_apply_now_allowed(row: pd.Series, market_profile: dict) -> tuple[bool, str]:
    """
    Gate the small `apply_now` bucket with higher confidence rules.
    For Morocco, `apply_now` should mean the title itself is clearly on-target,
    not just that the blended score is high.
    """
    market = str(market_profile.get("market", "") or "").strip().lower()
    if market != "ma":
        return True, ""

    title_norm = _normalize_match_text(row.get("title", ""))
    if not title_norm:
        return False, "empty_title"

    if any(marker in title_norm for marker in MA_GENERIC_TITLE_MARKERS):
        return False, "generic_language_title"

    if any(signal in title_norm for signal in MA_APPLY_NOW_TITLE_SIGNALS):
        return True, ""

    if "junior" in title_norm:
        return True, ""

    return False, "title_not_specific_enough"


def _status_outcome_weight(status: str) -> int:
    """
    Lightweight outcome weighting from tracker statuses.
    Positive outcomes (interview/offer) should boost similar jobs.
    Negative outcomes should slightly demote similar jobs.
    """
    status_norm = _normalize_text_key(status)
    if status_norm == "offer":
        return 4
    if status_norm == "interview":
        return 3
    if status_norm == "applied":
        return 1
    if status_norm == "rejected":
        return -3
    if status_norm in {"not_interested", "withdrawn"}:
        return -2
    return 0


def build_feedback_maps(tracker_df: pd.DataFrame) -> tuple[dict[str, int], dict[str, int]]:
    """
    Build company/term feedback maps from historical outcomes.
    Scores are capped to keep ranking stable.
    """
    if tracker_df.empty:
        return {}, {}

    by_company: dict[str, list[int]] = {}
    by_term: dict[str, list[int]] = {}
    for _, row in tracker_df.iterrows():
        status = _normalize_text_key(row.get("status", ""))
        weight = _status_outcome_weight(status)
        if weight == 0:
            continue

        company_key = _normalize_text_key(row.get("company", ""))
        term_key = _normalize_text_key(row.get("search_term", ""))

        if company_key:
            by_company.setdefault(company_key, []).append(weight)
        if term_key:
            by_term.setdefault(term_key, []).append(weight)

    def aggregate(values: list[int]) -> int:
        if not values:
            return 0
        # Use mean-like score and cap to avoid overpowering current relevance.
        score = round(sum(values) / max(1, len(values)))
        return int(max(-4, min(4, score)))

    company_scores = {k: aggregate(v) for k, v in by_company.items() if v}
    term_scores = {k: aggregate(v) for k, v in by_term.items() if v}
    return company_scores, term_scores


def compute_feedback_score(
    row: pd.Series, company_scores: dict[str, int], term_scores: dict[str, int]
) -> tuple[int, str]:
    company_key = _normalize_text_key(row.get("company", ""))
    term_key = _normalize_text_key(row.get("search_term", ""))
    c_score = int(company_scores.get(company_key, 0))
    t_score = int(term_scores.get(term_key, 0))
    score = max(-6, min(6, c_score + t_score))
    notes: list[str] = []
    if c_score != 0 and company_key:
        notes.append(f"company:{c_score}")
    if t_score != 0 and term_key:
        notes.append(f"term:{t_score}")
    return score, " | ".join(notes)


def make_job_id(canonical_url: str, title: str, company: str) -> str:
    raw = f"{canonical_url or ''}|{title or ''}|{company or ''}"
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:14]


def safe_read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def choose_input_csv(paths: dict) -> str:
    candidates = [paths["merged_filtered_csv"], paths["adzuna_filtered_csv"]]
    existing: list[tuple[str, float]] = []
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            if os.path.getsize(path) <= 0:
                continue
            existing.append((path, os.path.getmtime(path)))
        except OSError:
            continue
    if not existing:
        return paths["adzuna_filtered_csv"]
    existing.sort(key=lambda x: x[1], reverse=True)
    return existing[0][0]


def focused_path(path: str, market: str, ch_focus: str) -> str:
    if market != "ch" or ch_focus in ("", "all"):
        return path
    p = Path(path)
    return str(p.with_name(f"{p.stem}_{ch_focus}{p.suffix}"))


def build_reason(row: pd.Series, market_profile: dict) -> str:
    reasons: list[str] = []
    if bool(row.get("is_remote", False)):
        reasons.append("remote/hybrid")

    sponsorship = int(float(row.get("sponsorship_score", 0) or 0))
    if sponsorship > 0:
        reasons.append("sponsors-visa")

    if int(row.get("language_fit_score", 0)) > 0:
        reasons.append("language-fit")

    if int(row.get("junior_score", 0)) >= 2:
        reasons.append("junior-friendly")

    search_term = str(row.get("search_term", "") or "").strip()
    if search_term:
        reasons.append(f"term:{search_term}")

    loc = str(row.get("location", "") or "").lower()
    romandie_markers = [
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
        "morges",
        "gland",
        "yverdon",
    ]
    if any(m in loc for m in romandie_markers):
        reasons.append("romandie")

    if market_profile.get("ch_focus") == "romandie" and "romandie" not in reasons:
        reasons.append("swiss-wide")

    feedback_score = int(float(row.get("feedback_score", 0) or 0))
    if feedback_score > 0:
        reasons.append("historical-fit+")
    elif feedback_score < 0:
        reasons.append("historical-fit-")

    return ", ".join(reasons[:4]) if reasons else "priority-ranked"


def normalize_status_col(status_values: Iterable) -> list[str]:
    out = []
    for s in status_values:
        txt = str(s or "").strip().lower()
        out.append(txt if txt else "to_apply")
    return out


def main():
    parser = argparse.ArgumentParser(description="Build top apply queue from filtered jobs.")
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
    parser.add_argument("--input-csv", default="", help="Optional override input CSV path.")
    parser.add_argument("--output-csv", default="", help="Optional override apply queue output CSV.")
    parser.add_argument(
        "--location-focus",
        default="",
        help="Optional location cluster filter (e.g. rabat, casablanca, tanger).",
    )
    parser.add_argument("--top-n", type=int, default=20, help="Max jobs to keep in apply queue.")
    parser.add_argument(
        "--min-priority",
        type=int,
        default=68,
        help="Minimum priority score for apply_now recommendation.",
    )
    parser.add_argument(
        "--include-closed",
        action="store_true",
        help="Include already closed statuses (applied/interview/rejected/etc.).",
    )
    args = parser.parse_args()

    market = configure_market(args.market, args.ch_focus)
    market_profile = get_market_profile(market, args.ch_focus)
    paths = get_output_paths(market)

    input_csv = args.input_csv or choose_input_csv(paths)
    base_output_csv = args.output_csv or focused_path(paths["apply_queue_csv"], market, market_profile["ch_focus"])
    output_csv = location_focus_path(base_output_csv, args.location_focus)
    tracker_csv = focused_path(paths["applications_tracker_csv"], market, market_profile["ch_focus"])

    jobs = safe_read_csv(input_csv)
    if jobs.empty:
        print(f"[QUEUE] No jobs found in {input_csv}")
        return

    for col in ["title", "company", "canonical_url", "url", "created"]:
        if col not in jobs.columns:
            jobs[col] = ""
    if "priority_score" not in jobs.columns:
        jobs["priority_score"] = 0
    if "language_fit_score" not in jobs.columns:
        jobs["language_fit_score"] = 0
    if "junior_score" not in jobs.columns:
        jobs["junior_score"] = 0
    if "is_remote" not in jobs.columns:
        jobs["is_remote"] = False
    if "search_term" not in jobs.columns:
        jobs["search_term"] = ""

    jobs["job_id"] = jobs.apply(
        lambda r: make_job_id(
            str(r.get("canonical_url", "") or r.get("url", "")),
            str(r.get("title", "")),
            str(r.get("company", "")),
        ),
        axis=1,
    )

    tracker = safe_read_csv(tracker_csv)
    company_feedback, term_feedback = build_feedback_maps(tracker)
    if not tracker.empty and "job_id" in tracker.columns:
        tracker = tracker.copy()
        if "status" not in tracker.columns:
            tracker["status"] = "to_apply"
        tracker["status"] = normalize_status_col(tracker["status"])
        keep_cols = [c for c in ["job_id", "status", "applied_date", "notes", "follow_up_date"] if c in tracker.columns]
        jobs = jobs.merge(tracker[keep_cols], on="job_id", how="left")
    else:
        jobs["status"] = "to_apply"
        jobs["applied_date"] = ""
        jobs["notes"] = ""
        jobs["follow_up_date"] = ""

    jobs["status"] = normalize_status_col(jobs["status"])
    if not args.include_closed:
        jobs = jobs[~jobs["status"].isin(CLOSED_STATUSES)].copy()
    if args.location_focus:
        before_focus = len(jobs)
        jobs = jobs[
            jobs.apply(
                lambda row: location_matches_focus(
                    row.get("location", ""),
                    args.location_focus,
                    market,
                    bool(row.get("is_remote", False)),
                ),
                axis=1,
            )
        ].copy()
        print(
            f"[QUEUE] Location focus={args.location_focus} matched {len(jobs)}/{before_focus} rows "
            f"(market={market})"
        )
        if jobs.empty:
            print(f"[QUEUE] No jobs found for location focus '{args.location_focus}' in {input_csv}")
            return

    # Apply a light feedback loop from historical outcomes.
    feedback_pairs = jobs.apply(
        lambda r: compute_feedback_score(r, company_feedback, term_feedback),
        axis=1,
    )
    jobs["feedback_score"] = feedback_pairs.map(lambda x: x[0])
    jobs["feedback_signals"] = feedback_pairs.map(lambda x: x[1])
    if "hiring_likelihood_score" not in jobs.columns:
        jobs["hiring_likelihood_score"] = 0
    if "sponsorship_score" not in jobs.columns:
        jobs["sponsorship_score"] = 0
    jobs["priority_score"] = pd.to_numeric(jobs["priority_score"], errors="coerce").fillna(0)
    jobs["hiring_likelihood_score"] = pd.to_numeric(jobs["hiring_likelihood_score"], errors="coerce").fillna(0)
    jobs["sponsorship_score"] = pd.to_numeric(jobs["sponsorship_score"], errors="coerce").fillna(0)
    jobs["feedback_score"] = pd.to_numeric(jobs["feedback_score"], errors="coerce").fillna(0)
    market_adjustments = jobs.apply(lambda r: compute_market_queue_adjustment(r, market_profile), axis=1)
    jobs["queue_adjustment"] = market_adjustments.map(lambda x: x[0])
    jobs["queue_adjustment_reasons"] = market_adjustments.map(lambda x: x[1])
    jobs["force_review"] = market_adjustments.map(lambda x: x[2])
    jobs["adjusted_priority_score"] = jobs["priority_score"] + jobs["feedback_score"] + jobs["queue_adjustment"]

    jobs["apply_reason"] = jobs.apply(lambda r: build_reason(r, market_profile), axis=1)
    apply_now_gates = jobs.apply(lambda r: market_apply_now_allowed(r, market_profile), axis=1)
    jobs["apply_now_gate_reason"] = apply_now_gates.map(lambda x: x[1])
    jobs["recommended_action"] = jobs.apply(
        lambda r: "review"
        if bool(r.get("force_review", False))
        or not (
            int(r.get("adjusted_priority_score", 0)) >= int(args.min_priority)
            and not str(r.get("apply_now_gate_reason", "") or "")
        )
        else "apply_now",
        axis=1,
    )

    sort_cols = [
        c
        for c in [
            "adjusted_priority_score",
            "sponsorship_score",
            "hiring_likelihood_score",
            "feedback_score",
            "priority_score",
            "language_fit_score",
            "junior_score",
            "created",
        ]
        if c in jobs.columns
    ]
    jobs = jobs.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))

    # Cap per-company listings to avoid recruiter spam (Extia x5, SQUAD x4, etc.)
    # Normalize company name before grouping: strip legal suffixes so that
    # "D4L data4life" and "D4L data4life gGmbH" count as the same company.
    MAX_PER_COMPANY = 3
    if "company" in jobs.columns:
        _legal_suffixes = (
            " gmbh", " ggmbh", " ag", " se", " kg", " ohg", " inc", " corp",
            " ltd", " llc", " plc", " bv", " nv", " sas", " sa", " spa",
            " sl", " oy", " ab", " as", " a/s", " limited", " group",
            " recruitment", " consulting", " conseil", " recrutement",
            " and consulting", " and cons", " solutions",
        )
        def _norm_company(name: str) -> str:
            n = str(name or "").lower().strip()
            for suffix in _legal_suffixes:
                if n.endswith(suffix):
                    n = n[: -len(suffix)].strip()
            return n

        company_key = jobs["company"].apply(_norm_company)
        # cumcount within each normalized company key (jobs already sorted by priority)
        rank_within_company = company_key.groupby(company_key).cumcount()
        jobs = jobs[rank_within_company < MAX_PER_COMPANY]

    keep_cols = [
        "job_id",
        "recommended_action",
        "adjusted_priority_score",
        "sponsorship_score",
        "feedback_score",
        "feedback_signals",
        "queue_adjustment",
        "queue_adjustment_reasons",
        "apply_now_gate_reason",
        "hiring_likelihood_score",
        "priority_score",
        "language_fit_score",
        "junior_score",
        "is_remote",
        "status",
        "title",
        "company",
        "location",
        "created",
        "search_term",
        "apply_reason",
        "url",
        "canonical_url",
        "applied_date",
        "follow_up_date",
        "notes",
        "source",
    ]
    keep_cols = [c for c in keep_cols if c in jobs.columns]
    queue = jobs[keep_cols].head(args.top_n).copy()

    out_dir = os.path.dirname(output_csv)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    safe_save_csv(queue, output_csv)

    print(
        f"[QUEUE] Market={market} ch_focus={market_profile['ch_focus']} "
        f"input={input_csv} rows={len(jobs)} -> queue={len(queue)} "
        f"feedback(company={len(company_feedback)}, term={len(term_feedback)}) saved={output_csv}"
    )


if __name__ == "__main__":
    main()

