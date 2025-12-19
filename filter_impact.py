"""
Analyze the impact of each filtering step used in adzuna_fetch.py.

Loads the raw Adzuna CSV, replays the filters in the same order, and
reports how many jobs each step removes plus a few diagnostics.
"""

from collections import Counter
from typing import Dict, List, Tuple

import pandas as pd

from config import ADZUNA_RAW_CSV
from adzuna_fetch import (
    MAX_DAYS_OLD,
    ROLE_FORBIDDEN_KEYWORDS,
    ROLE_REQUIRED_KEYWORDS,
    EXCLUDE_KEYWORDS,
    excluded_hits,
    normalize,
    is_recent,
    location_ok,
    role_relevant,
    is_dutch,
    compute_junior_score,
)


# Same quick title filter as in adzuna_fetch.main
BAD_TITLES = [
    "senior",
    "medior",
    "principal",
    "expert",
    " l3 ",
]


def load_raw_jobs(path: str) -> List[Dict]:
    df = pd.read_csv(path)
    return df.to_dict(orient="records")


def extract_fields(job: Dict) -> Dict:
    """Flatten the pieces we need from the normalized CSV row."""
    url = job.get("redirect_url", "") or job.get("url", "") or job.get("link", "")
    return {
        "created": job.get("created", ""),
        "location": job.get("location.display_name", ""),
        "title": job.get("title", "") or "",
        "description": job.get("description", "") or "",
        "url": url,
        "canonical_url": url.split("?", 1)[0] if url else "",
        "company": job.get("company.display_name", "") or "",
        "search_term": job.get("search_term", "") or "",
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
    }


def check_bad_title(title: str) -> Tuple[bool, str]:
    norm = normalize(title)
    for pat in BAD_TITLES:
        if pat in norm:
            return False, pat
    return True, ""


def check_recency(created: str) -> Tuple[bool, str]:
    ok = is_recent(created, MAX_DAYS_OLD)
    return ok, "" if ok else "too_old"


def check_location(loc: str) -> Tuple[bool, str]:
    ok = location_ok(loc)
    return ok, "" if ok else "location_blocked"


def check_role(title: str, desc: str) -> Tuple[bool, str]:
    text = normalize((title or "") + " " + (desc or ""))
    for bad in ROLE_FORBIDDEN_KEYWORDS:
        if bad in text:
            return False, f"forbidden:{bad}"
    if not any(good in text for good in ROLE_REQUIRED_KEYWORDS):
        return False, "missing_required"
    return True, ""


def check_excluded(text: str) -> Tuple[bool, str]:
    hits = excluded_hits(text)
    return (len(hits) == 0), (hits[0] if hits else "")


def check_dutch(text: str) -> Tuple[bool, str]:
    ok = not is_dutch(text)
    return ok, "" if ok else "dutch_detected"


def check_junior(title: str, desc: str) -> Tuple[bool, str, int]:
    score = compute_junior_score(title, desc)
    # Match the same threshold as passes_filters (score >= 0)
    return score >= 0, "" if score >= 0 else "junior_score<0", score


def summarize_counter(counter: Counter, top_n: int = 5, show_all: bool = False) -> str:
    if not counter:
        return "none"
    items = counter.most_common() if show_all else counter.most_common(top_n)
    return ", ".join(f"{k}:{v}" for k, v in items)


def compute_global_hits(jobs: List[Dict]) -> Tuple[Dict[str, Counter], Dict[str, int]]:
    """
    Count how often each keyword/filter would trigger when evaluated on all rows,
    without stopping early because a previous filter removed the job.
    """
    hits = {
        "bad_title": Counter(),
        "role_forbidden": Counter(),
        "role_required": Counter(),
        "exclude_keywords": Counter(),
    }
    misc = {
        "recency_fail": 0,
        "location_fail": 0,
        "dutch_detected": 0,
        "junior_negative": 0,
    }

    for job in jobs:
        title = job.get("title", "") or ""
        desc = job.get("description", "") or ""
        loc = job.get("location", "") or ""
        created = job.get("created", "") or ""
        norm_title = normalize(title)
        norm_text = normalize(title + " " + desc)

        for pat in BAD_TITLES:
            if pat in norm_title:
                hits["bad_title"][pat] += 1

        for bad in ROLE_FORBIDDEN_KEYWORDS:
            if bad in norm_text:
                hits["role_forbidden"][bad] += 1

        for good in ROLE_REQUIRED_KEYWORDS:
            if good in norm_text:
                hits["role_required"][good] += 1

        for kw in excluded_hits(norm_text):
            hits["exclude_keywords"][kw] += 1

        if not is_recent(created, MAX_DAYS_OLD):
            misc["recency_fail"] += 1
        if not location_ok(loc):
            misc["location_fail"] += 1
        if is_dutch(title + " " + desc):
            misc["dutch_detected"] += 1
        if compute_junior_score(title, desc) < 0:
            misc["junior_negative"] += 1

    return hits, misc


def analyze(raw_jobs: List[Dict], report_csv: str = None, show_all: bool = False):
    step_summaries = []
    bad_title_hits = Counter()
    excluded_hits = Counter()
    forbidden_hits = Counter()
    dutch_hits = 0

    report_rows = []

    # Start with all raw jobs
    all_jobs = [extract_fields(j) for j in raw_jobs]
    global_hits, global_misc = compute_global_hits(all_jobs)
    current = list(all_jobs)
    print(f"[IMPACT] Loaded raw rows: {len(current)}")

    steps = [
        ("bad_title", lambda job: check_bad_title(job["title"])),
        ("recency", lambda job: check_recency(job["created"])),
        ("location", lambda job: check_location(job["location"])),
        ("role_relevant", lambda job: check_role(job["title"], job["description"])),
        ("exclude_keywords", lambda job: check_excluded(job["title"] + " " + job["description"])),
        ("dutch", lambda job: check_dutch(job["title"] + " " + job["description"])),
        ("junior_score", lambda job: check_junior(job["title"], job["description"])),
    ]

    passed_jobs = []  # jobs that pass all filters (before dedup)
    passed_indices = []  # keep index to align report rows

    for step_name, func in steps:
        before = len(current)
        kept = []
        removed = []
        for job in current:
            ok_detail = func(job)
            ok = ok_detail[0]
            detail = ok_detail[1] if len(ok_detail) > 1 else ""

            if step_name == "junior_score":
                # ok_detail is (bool, detail, score)
                job["junior_score"] = ok_detail[2]

            if ok:
                kept.append(job)
            else:
                removed.append(job)
                if step_name == "bad_title":
                    bad_title_hits[detail] += 1
                elif step_name == "exclude_keywords":
                    excluded_hits[detail] += 1
                elif step_name == "role_relevant" and detail.startswith("forbidden:"):
                    forbidden_hits[detail.split(":", 1)[1]] += 1
                elif step_name == "dutch":
                    dutch_hits += 1

            if report_csv:
                report_rows.append(
                    {
                        "title": job["title"],
                        "company": job["company"],
                        "url": job["url"],
                        "search_term": job["search_term"],
                        "created": job["created"],
                        "fail_step": step_name if not ok else "pass_so_far",
                        "fail_detail": detail,
                        "junior_score": job.get("junior_score"),
                    }
                )

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

    # Jobs that fully passed all filters (before duplicate removal)
    passed_jobs = current

    # Duplicate removal (same criteria as adzuna_fetch)
    df_passed = pd.DataFrame(passed_jobs)
    # Align dedup with adzuna_fetch: use canonical_url + title + company
    subset_keys = ["canonical_url", "title", "company"]
    duplicates_mask = df_passed.duplicated(subset=subset_keys, keep="first")
    duplicates_removed = int(duplicates_mask.sum())
    df_unique = df_passed.loc[~duplicates_mask].copy()

    print("\n[IMPACT] Step-by-step removals:")
    for s in step_summaries:
        print(
            f"- {s['step']}: before={s['before']} removed={s['removed']} "
            f"({s['pct_removed']}%) kept={s['kept']}"
        )

    print("\n[IMPACT] Diagnostics:")
    print(f"- Top bad title matches: {summarize_counter(bad_title_hits, show_all=show_all)}")
    print(f"- Top forbidden role hits: {summarize_counter(forbidden_hits, show_all=show_all)}")
    print(f"- Top excluded keywords: {summarize_counter(excluded_hits, show_all=show_all)}")
    print(f"- Dutch detected: {dutch_hits}")
    print(f"- Duplicates removed: {duplicates_removed}")
    print(f"- Final kept after dedup: {len(df_unique)}")

    print("\n[IMPACT] Keyword hits across full dataset (no early-stop):")
    print(f"- Bad title matches: {summarize_counter(global_hits['bad_title'], show_all=show_all)}")
    print(f"- Forbidden role hits: {summarize_counter(global_hits['role_forbidden'], show_all=show_all)}")
    print(f"- Required keyword presence: {summarize_counter(global_hits['role_required'], show_all=show_all)}")
    print(f"- Exclude keyword matches: {summarize_counter(global_hits['exclude_keywords'], show_all=show_all)}")
    print(f"- Recency failures: {global_misc['recency_fail']}")
    print(f"- Location blocks: {global_misc['location_fail']}")
    print(f"- Dutch detected (all rows): {global_misc['dutch_detected']}")
    print(f"- Junior score < 0: {global_misc['junior_negative']}")

    if report_csv:
        # Mark duplicates in the report for the jobs that passed filters
        if report_rows and passed_jobs:
            # Update the rows corresponding to passed jobs with duplicate info
            # Find indices of rows marked as pass_so_far from the last step
            passed_report_indices = [
                idx for idx, row in enumerate(report_rows) if row["fail_step"] == "pass_so_far"
            ]
            for idx, is_dup in zip(passed_report_indices, duplicates_mask.tolist()):
                report_rows[idx]["duplicate_removed"] = bool(is_dup)
        df_report = pd.DataFrame(report_rows)
        df_report.to_csv(report_csv, index=False)
        print(f"[IMPACT] Detailed report written to {report_csv}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze filtering impact on Adzuna jobs.")
    parser.add_argument(
        "--raw-csv",
        default=ADZUNA_RAW_CSV,
        help=f"Path to raw Adzuna CSV (default: {ADZUNA_RAW_CSV})",
    )
    parser.add_argument(
        "--report-csv",
        help="Optional path to write a per-job report (includes first failing step and duplicates).",
    )
    parser.add_argument(
        "--all-keywords",
        action="store_true",
        help="Show full breakdown of keyword hits instead of top 5.",
    )
    args = parser.parse_args()

    raw_jobs = load_raw_jobs(args.raw_csv)
    analyze(raw_jobs, report_csv=args.report_csv, show_all=args.all_keywords)


if __name__ == "__main__":
    main()
