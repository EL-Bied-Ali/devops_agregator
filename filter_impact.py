"""
Analyze the impact of each filtering step used in adzuna_fetch.py.

Loads the raw Adzuna CSV, replays filters in the same order as passes_filters,
and reports step-level removals with diagnostics.
"""

from collections import Counter
from typing import Dict, List, Tuple

import pandas as pd

import adzuna_fetch as af
from config import SUPPORTED_CH_FOCUS, SUPPORTED_FILTER_MODES, SUPPORTED_MARKETS, get_output_paths, resolve_filter_mode


def load_raw_jobs(path: str) -> List[Dict]:
    df = pd.read_csv(path)
    return df.to_dict(orient="records")


def extract_fields(job: Dict) -> Dict:
    """Flatten row fields using the same value precedence as passes_filters."""
    loc = job.get("location", "")
    if isinstance(loc, dict):
        loc = loc.get("display_name", "")
    if not loc:
        loc = job.get("location.display_name", "")

    title = af.clean_text(job.get("title", "") or "")
    desc = af.clean_text(job.get("description", "") or "")
    url = job.get("redirect_url", "") or job.get("url", "") or job.get("link", "")
    canonical_url = af.canonicalize_url(url)

    company_val = job.get("company", "")
    if isinstance(company_val, dict):
        company = company_val.get("display_name", "") or company_val.get("name", "")
    else:
        company = company_val or job.get("company.display_name", "")

    return {
        "created": job.get("created", "") or job.get("updated", ""),
        "location": af.clean_text(loc),
        "title": title,
        "description": desc,
        "url": url,
        "canonical_url": canonical_url,
        "company": af.clean_text(company),
        "search_term": job.get("search_term", "") or "",
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
    }


def check_description(desc: str) -> Tuple[bool, str]:
    if not af.REQUIRE_DESCRIPTION:
        return True, ""
    ok = len((desc or "").strip()) >= af.MIN_DESCRIPTION_CHARS
    return ok, "" if ok else "description_too_short"


def check_bad_title(title: str) -> Tuple[bool, str]:
    norm = af.normalize(title)
    for pat in af.BAD_TITLE_KEYWORDS:
        if pat in norm:
            return False, pat
    return True, ""


def check_recency(created: str) -> Tuple[bool, str]:
    ok = af.is_recent(created, af.MAX_DAYS_OLD)
    return ok, "" if ok else "too_old"


def check_location(loc: str, title: str = "", desc: str = "") -> Tuple[bool, str]:
    ok = af.location_ok(loc, title, desc)
    return ok, "" if ok else "location_blocked"


def check_role(title: str, desc: str) -> Tuple[bool, str]:
    text = af.normalize((title or "") + " " + (desc or ""))
    ok = af.role_relevant(title, desc)
    if ok:
        if any(good in text for good in af.ROLE_REQUIRED_KEYWORDS):
            return True, ""
        if af.training_program_relevant(title, desc):
            return True, "training_program_relevant"
        if af.role_title_fallback_relevant(title):
            return True, "title_fallback_relevant"
        return True, ""

    forbidden = af.role_forbidden_reason(title, desc)
    if forbidden:
        return False, f"forbidden:{forbidden}"
    return False, "missing_required"


def check_internship_student_only(title: str, desc: str) -> Tuple[bool, str]:
    detail = af.internship_student_only_detail(title, desc)
    return (not bool(detail)), (detail or "")


def check_excluded(title: str, text: str) -> Tuple[bool, str]:
    hard_hits, soft_hits = af.classify_excluded_hits(title, text)
    if hard_hits:
        return False, hard_hits[0]
    if soft_hits:
        return True, f"soft:{soft_hits[0]}"
    return True, ""


def check_blocked_language_requirement(text: str) -> Tuple[bool, str]:
    reason = af.blocked_language_requirement_reason(text)
    return (not bool(reason)), (reason if reason else "")


def check_disallowed_language(text: str, filter_mode: str) -> Tuple[bool, str]:
    if af.blocked_language_requirement_reason(text):
        return False, "blocked_language_req:explicit_required"
    blocked = af.is_disallowed_language(text)
    if filter_mode == "broad":
        # In broad mode we keep this as diagnostic only, not as a hard reject.
        return True, "would_block_in_strict" if blocked else ""
    return (not blocked), ("blocked_language_detected" if blocked else "")


def check_junior(title: str, desc: str, filter_mode: str) -> Tuple[bool, str, int]:
    score = af.compute_junior_score(title, desc)
    min_junior_score = 0 if filter_mode == "strict" else -1
    return score >= min_junior_score, "" if score >= min_junior_score else f"junior_score<{min_junior_score}", score


def summarize_counter(counter: Counter, top_n: int = 5, show_all: bool = False) -> str:
    if not counter:
        return "none"
    items = counter.most_common() if show_all else counter.most_common(top_n)
    return ", ".join(f"{k}:{v}" for k, v in items)


def compute_global_hits(jobs: List[Dict]) -> Tuple[Dict[str, Counter], Dict[str, int]]:
    """
    Count keyword/filter triggers on all rows without early-stop.
    """
    hits = {
        "bad_title": Counter(),
        "role_forbidden": Counter(),
        "role_required": Counter(),
        "exclude_keywords": Counter(),
    }
    misc = {
        "description_too_short": 0,
        "recency_fail": 0,
        "location_fail": 0,
        "internship_student_only": 0,
        "blocked_language_requirement": 0,
        "blocked_language_detected": 0,
        "junior_negative": 0,
    }

    for job in jobs:
        title = job.get("title", "") or ""
        desc = job.get("description", "") or ""
        loc = job.get("location", "") or ""
        created = job.get("created", "") or ""
        full_text = f"{title} {desc}"
        norm_title = af.normalize(title)
        norm_text = af.normalize(full_text)

        if af.REQUIRE_DESCRIPTION and len(desc.strip()) < af.MIN_DESCRIPTION_CHARS:
            misc["description_too_short"] += 1

        for pat in af.BAD_TITLE_KEYWORDS:
            if pat in norm_title:
                hits["bad_title"][pat] += 1

        forbidden = af.role_forbidden_reason(title, desc)
        if forbidden:
            hits["role_forbidden"][forbidden] += 1

        for good in af.ROLE_REQUIRED_KEYWORDS:
            if good in norm_text:
                hits["role_required"][good] += 1

        hard_hits, _soft_hits = af.classify_excluded_hits(title, full_text)
        for kw in hard_hits:
            hits["exclude_keywords"][kw] += 1

        if not af.is_recent(created, af.MAX_DAYS_OLD):
            misc["recency_fail"] += 1
        if not af.location_ok(loc, title, desc):
            misc["location_fail"] += 1
        if af.internship_student_only_detail(title, desc):
            misc["internship_student_only"] += 1
        if af.blocked_language_requirement_reason(full_text):
            misc["blocked_language_requirement"] += 1
            misc["blocked_language_detected"] += 1
        elif af.is_disallowed_language(full_text):
            misc["blocked_language_detected"] += 1
        if af.compute_junior_score(title, desc) < 0:
            misc["junior_negative"] += 1

    return hits, misc


def analyze(raw_jobs: List[Dict], report_csv: str = None, show_all: bool = False, filter_mode: str = "strict"):
    filter_mode = resolve_filter_mode(filter_mode, allow_both=False)
    step_summaries = []
    bad_title_hits = Counter()
    excluded_keyword_hits = Counter()
    forbidden_hits = Counter()
    blocked_language_requirement_hits = 0
    blocked_language_detected_hits = 0

    report_rows = []

    all_jobs = [extract_fields(j) for j in raw_jobs]
    for idx, job in enumerate(all_jobs):
        job["row_id"] = idx
    global_hits, global_misc = compute_global_hits(all_jobs)
    current = list(all_jobs)
    print(f"[IMPACT] Loaded raw rows: {len(current)} (filter_mode={filter_mode})")

    steps = [
        ("description_length", lambda job: check_description(job["description"])),
        ("bad_title", lambda job: check_bad_title(job["title"])),
        ("recency", lambda job: check_recency(job["created"])),
        ("location", lambda job: check_location(job["location"], job["title"], job["description"])),
        ("role_relevant", lambda job: check_role(job["title"], job["description"])),
        ("internship_student_only", lambda job: check_internship_student_only(job["title"], job["description"])),
        ("exclude_keywords", lambda job: check_excluded(job["title"], job["title"] + " " + job["description"])),
        (
            "blocked_language_requirement",
            lambda job: check_blocked_language_requirement(job["title"] + " " + job["description"]),
        ),
        (
            "blocked_language",
            lambda job: check_disallowed_language(job["title"] + " " + job["description"], filter_mode),
        ),
        ("junior_score", lambda job: check_junior(job["title"], job["description"], filter_mode)),
    ]

    if report_csv:
        for job in all_jobs:
            report_rows.append(
                {
                    "row_id": job["row_id"],
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", ""),
                    "url": job.get("url", ""),
                    "search_term": job.get("search_term", ""),
                    "created": job.get("created", ""),
                    "first_fail_step": "",
                    "first_fail_detail": "",
                    "junior_score": "",
                    "passes_filters": False,
                    "duplicate_removed": False,
                }
            )

    for step_name, func in steps:
        before = len(current)
        kept = []
        for job in current:
            ok_detail = func(job)
            ok = ok_detail[0]
            detail = ok_detail[1] if len(ok_detail) > 1 else ""

            if step_name == "junior_score":
                job["junior_score"] = ok_detail[2]

            if ok:
                if step_name == "blocked_language" and detail == "would_block_in_strict":
                    blocked_language_detected_hits += 1
                kept.append(job)
            else:
                if step_name == "bad_title":
                    bad_title_hits[detail] += 1
                elif step_name == "exclude_keywords":
                    excluded_keyword_hits[detail] += 1
                elif step_name == "role_relevant" and detail.startswith("forbidden:"):
                    forbidden_hits[detail.split(":", 1)[1]] += 1
                elif step_name == "blocked_language_requirement":
                    blocked_language_requirement_hits += 1
                elif step_name == "blocked_language":
                    blocked_language_detected_hits += 1

                if report_csv:
                    row = report_rows[job["row_id"]]
                    if not row["first_fail_step"]:
                        row["first_fail_step"] = step_name
                        row["first_fail_detail"] = detail
                        row["junior_score"] = job.get("junior_score", "")

        removed_count = before - len(kept)
        pct_removed = (removed_count / before * 100) if before else 0
        step_summaries.append(
            {
                "step": step_name,
                "before": before,
                "kept": len(kept),
                "removed": removed_count,
                "pct_removed": round(pct_removed, 1),
            }
        )
        current = kept

    passed_jobs = current

    if report_csv:
        for job in passed_jobs:
            row = report_rows[job["row_id"]]
            row["passes_filters"] = True
            row["junior_score"] = job.get("junior_score", "")
            if not row["first_fail_step"]:
                row["first_fail_step"] = "passed_all"

    df_passed = pd.DataFrame(passed_jobs)
    subset_keys = ["canonical_url", "title", "company"]
    duplicates_removed = 0
    df_unique = df_passed.copy()
    duplicates_mask = pd.Series([], dtype=bool)
    if not df_passed.empty:
        duplicates_mask = df_passed.duplicated(subset=subset_keys, keep="first")
        duplicates_removed = int(duplicates_mask.sum())
        df_unique = df_passed.loc[~duplicates_mask].copy()

    if report_csv and not df_passed.empty:
        for _, dup_job in df_passed.loc[duplicates_mask].iterrows():
            row = report_rows[int(dup_job["row_id"])]
            row["duplicate_removed"] = True

    # Safety check: compare with passes_filters to ensure analyzer parity.
    parity_mismatch = 0
    passed_row_ids = {job.get("row_id") for job in passed_jobs}
    for idx, raw in enumerate(raw_jobs):
        parsed = af.passes_filters(raw, source="adzuna", filter_mode=filter_mode)
        replay_ok = idx in passed_row_ids
        parsed_ok = parsed is not None
        if replay_ok != parsed_ok:
            parity_mismatch += 1

    print("\n[IMPACT] Step-by-step removals:")
    for s in step_summaries:
        print(
            f"- {s['step']}: before={s['before']} removed={s['removed']} "
            f"({s['pct_removed']}%) kept={s['kept']}"
        )

    print("\n[IMPACT] Diagnostics:")
    print(f"- Top bad title matches: {summarize_counter(bad_title_hits, show_all=show_all)}")
    print(f"- Top forbidden role hits: {summarize_counter(forbidden_hits, show_all=show_all)}")
    print(f"- Top excluded keywords: {summarize_counter(excluded_keyword_hits, show_all=show_all)}")
    print(f"- Blocked language requirement hits: {blocked_language_requirement_hits}")
    blocked_language_label = "Blocked language detected"
    if filter_mode == "broad":
        blocked_language_label = "Blocked language detected (would block in strict)"
    print(f"- {blocked_language_label}: {blocked_language_detected_hits}")
    print(f"- Duplicates removed: {duplicates_removed}")
    print(f"- Final kept after dedup: {len(df_unique)}")
    print(f"- Parity mismatch vs passes_filters: {parity_mismatch}")

    print("\n[IMPACT] Keyword hits across full dataset (no early-stop):")
    print(f"- Bad title matches: {summarize_counter(global_hits['bad_title'], show_all=show_all)}")
    print(f"- Forbidden role hits: {summarize_counter(global_hits['role_forbidden'], show_all=show_all)}")
    print(f"- Required keyword presence: {summarize_counter(global_hits['role_required'], show_all=show_all)}")
    print(f"- Exclude keyword matches: {summarize_counter(global_hits['exclude_keywords'], show_all=show_all)}")
    print(f"- Description too short: {global_misc['description_too_short']}")
    print(f"- Recency failures: {global_misc['recency_fail']}")
    print(f"- Location blocks: {global_misc['location_fail']}")
    print(f"- Internship student-only blocks: {global_misc['internship_student_only']}")
    print(f"- Blocked language requirement (all rows): {global_misc['blocked_language_requirement']}")
    print(f"- Blocked language detected (all rows): {global_misc['blocked_language_detected']}")
    print(f"- Junior score < 0: {global_misc['junior_negative']}")

    if report_csv:
        df_report = pd.DataFrame(report_rows)
        af.safe_save_csv(df_report, report_csv)
        print(f"[IMPACT] Detailed report written to {report_csv}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze filtering impact on Adzuna jobs.")
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
        help="Filtering strictness to replay (strict|broad). Defaults to JOB_FILTER_MODE env var or strict.",
    )
    parser.add_argument(
        "--raw-csv",
        default="",
        help="Path to raw Adzuna CSV. Defaults to the selected market raw file.",
    )
    parser.add_argument(
        "--report-csv",
        help="Optional path to write a per-job report (first failing step + duplicate info).",
    )
    parser.add_argument(
        "--all-keywords",
        action="store_true",
        help="Show full breakdown of keyword hits instead of top 5.",
    )
    args = parser.parse_args()

    market = af.configure_market(args.market, args.ch_focus)
    selected_filter_mode = resolve_filter_mode(args.filter_mode, allow_both=False)
    default_raw_csv = get_output_paths(market)["adzuna_raw_csv"]
    raw_csv = args.raw_csv or default_raw_csv

    raw_jobs = load_raw_jobs(raw_csv)
    analyze(raw_jobs, report_csv=args.report_csv, show_all=args.all_keywords, filter_mode=selected_filter_mode)


if __name__ == "__main__":
    main()
