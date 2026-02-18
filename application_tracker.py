"""
Track applications lifecycle per job (to_apply/applied/interview/...).

Commands:
- sync: refresh tracker from current filtered jobs while preserving statuses
- update: update status/notes/follow-up for one job_id
- show: quick summary and optional listing
"""

from __future__ import annotations

import argparse
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from adzuna_fetch import configure_market, safe_save_csv
from config import SUPPORTED_CH_FOCUS, SUPPORTED_MARKETS, get_market_profile, get_output_paths


VALID_STATUSES = [
    "to_apply",
    "saved",
    "applied",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
    "not_interested",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def make_job_id(canonical_url: str, title: str, company: str) -> str:
    raw = f"{canonical_url or ''}|{title or ''}|{company or ''}"
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:14]


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


def ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    defaults = {
        "job_id": "",
        "status": "to_apply",
        "applied_date": "",
        "follow_up_date": "",
        "notes": "",
        "first_seen": "",
        "last_seen": "",
        "last_updated": "",
    }
    for col, default in defaults.items():
        if col not in out.columns:
            out[col] = default
    # Normalize text-like columns to avoid pandas dtype warnings on updates.
    text_cols = ["job_id", "status", "applied_date", "follow_up_date", "notes", "first_seen", "last_seen", "last_updated"]
    for col in text_cols:
        out[col] = out[col].fillna("").astype(str)
    return out


def sync_tracker(market: str, ch_focus: str, input_csv: str = "", tracker_csv: str = ""):
    configure_market(market, ch_focus)
    profile = get_market_profile(market, ch_focus)
    paths = get_output_paths(market)
    input_path = input_csv or choose_input_csv(paths)
    tracker_path = tracker_csv or focused_path(paths["applications_tracker_csv"], market, profile["ch_focus"])

    jobs = safe_read_csv(input_path)
    if jobs.empty:
        print(f"[TRACKER] No jobs found in {input_path}")
        return

    for col in ["title", "company", "canonical_url", "url", "location", "created", "search_term", "source"]:
        if col not in jobs.columns:
            jobs[col] = ""
    if "priority_score" not in jobs.columns:
        jobs["priority_score"] = 0
    if "language_fit_score" not in jobs.columns:
        jobs["language_fit_score"] = 0
    if "junior_score" not in jobs.columns:
        jobs["junior_score"] = 0

    jobs["job_id"] = jobs.apply(
        lambda r: make_job_id(
            str(r.get("canonical_url", "") or r.get("url", "")),
            str(r.get("title", "")),
            str(r.get("company", "")),
        ),
        axis=1,
    )

    base_cols = [
        "job_id",
        "title",
        "company",
        "location",
        "created",
        "url",
        "canonical_url",
        "search_term",
        "source",
        "priority_score",
        "language_fit_score",
        "junior_score",
    ]
    base_cols = [c for c in base_cols if c in jobs.columns]
    tracker_new = jobs[base_cols].copy()

    tracker_old = ensure_cols(safe_read_csv(tracker_path))
    if not tracker_old.empty and "job_id" in tracker_old.columns:
        keep_old = [
            "job_id",
            "status",
            "applied_date",
            "follow_up_date",
            "notes",
            "first_seen",
            "last_seen",
            "last_updated",
        ]
        keep_old = [c for c in keep_old if c in tracker_old.columns]
        tracker_new = tracker_new.merge(tracker_old[keep_old], on="job_id", how="left")

    tracker_new = ensure_cols(tracker_new)

    now = now_iso()
    tracker_new["status"] = tracker_new["status"].fillna("").astype(str).str.strip().str.lower()
    tracker_new.loc[tracker_new["status"] == "", "status"] = "to_apply"
    tracker_new.loc[~tracker_new["status"].isin(VALID_STATUSES), "status"] = "to_apply"
    tracker_new.loc[tracker_new["first_seen"] == "", "first_seen"] = now
    tracker_new["last_seen"] = now
    tracker_new["last_updated"] = tracker_new["last_updated"].replace("", now)

    tracker_new = tracker_new.sort_values(
        by=[c for c in ["priority_score", "language_fit_score", "junior_score", "created"] if c in tracker_new.columns],
        ascending=False,
    )

    out_dir = os.path.dirname(tracker_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    safe_save_csv(tracker_new, tracker_path)
    print(
        f"[TRACKER] Synced market={market} ch_focus={profile['ch_focus']} "
        f"input={input_path} rows={len(tracker_new)} saved={tracker_path}"
    )


def update_tracker(
    market: str,
    ch_focus: str,
    job_id: str,
    status: str = "",
    note: str = "",
    follow_up_date: str = "",
    applied_date: str = "",
    tracker_csv: str = "",
):
    configure_market(market, ch_focus)
    paths = get_output_paths(market)
    profile = get_market_profile(market, ch_focus)
    tracker_path = tracker_csv or focused_path(paths["applications_tracker_csv"], market, profile["ch_focus"])
    tracker = ensure_cols(safe_read_csv(tracker_path))
    if tracker.empty:
        print(f"[TRACKER] Tracker is empty: {tracker_path}. Run sync first.")
        return

    mask = tracker["job_id"].astype(str) == str(job_id)
    if not mask.any():
        print(f"[TRACKER] job_id not found: {job_id}")
        return

    if status:
        status_norm = status.strip().lower()
        if status_norm not in VALID_STATUSES:
            print(f"[TRACKER] Invalid status '{status}'. Valid: {', '.join(VALID_STATUSES)}")
            return
        tracker.loc[mask, "status"] = status_norm
        if status_norm == "applied" and not applied_date:
            tracker.loc[mask, "applied_date"] = datetime.now(timezone.utc).date().isoformat()

    if note:
        old = tracker.loc[mask, "notes"].fillna("").astype(str)
        tracker.loc[mask, "notes"] = (old + " | " + note).str.strip(" |")

    if follow_up_date:
        tracker.loc[mask, "follow_up_date"] = follow_up_date

    if applied_date:
        tracker.loc[mask, "applied_date"] = applied_date

    tracker.loc[mask, "last_updated"] = now_iso()
    safe_save_csv(tracker, tracker_path)
    print(f"[TRACKER] Updated {job_id} in {tracker_path}")


def show_tracker(market: str, ch_focus: str, status: str = "", top_n: int = 20, tracker_csv: str = ""):
    configure_market(market, ch_focus)
    profile = get_market_profile(market, ch_focus)
    paths = get_output_paths(market)
    tracker_path = tracker_csv or focused_path(paths["applications_tracker_csv"], market, profile["ch_focus"])
    tracker = ensure_cols(safe_read_csv(tracker_path))
    if tracker.empty:
        print(f"[TRACKER] Tracker empty: {tracker_path}")
        return

    print(f"[TRACKER] market={market} ch_focus={profile['ch_focus']} rows={len(tracker)} file={tracker_path}")
    print("[TRACKER] status_counts:")
    counts = tracker["status"].fillna("to_apply").astype(str).str.lower().value_counts()
    for st, n in counts.items():
        print(f"- {st}: {n}")

    view = tracker.copy()
    if status:
        view = view[view["status"].astype(str).str.lower() == status.strip().lower()]
    view = view.sort_values(
        by=[c for c in ["priority_score", "language_fit_score", "junior_score", "created"] if c in view.columns],
        ascending=False,
    )

    cols = [c for c in ["job_id", "status", "priority_score", "title", "company", "location"] if c in view.columns]
    print("[TRACKER] top_rows:")
    for _, row in view.head(top_n)[cols].iterrows():
        print(" | ".join(str(row.get(c, "")) for c in cols))


def main():
    parser = argparse.ArgumentParser(description="Application tracker for job pipeline.")
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
    parser.add_argument("--tracker-csv", default="", help="Optional tracker CSV path override.")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sync = sub.add_parser("sync", help="Sync tracker from latest filtered jobs.")
    p_sync.add_argument("--input-csv", default="", help="Optional filtered jobs CSV path.")

    p_update = sub.add_parser("update", help="Update one application row by job_id.")
    p_update.add_argument("--job-id", required=True, help="Target job_id.")
    p_update.add_argument("--status", default="", help=f"New status: {', '.join(VALID_STATUSES)}")
    p_update.add_argument("--note", default="", help="Append note.")
    p_update.add_argument("--follow-up-date", default="", help="YYYY-MM-DD")
    p_update.add_argument("--applied-date", default="", help="YYYY-MM-DD")

    p_show = sub.add_parser("show", help="Show tracker summary and top rows.")
    p_show.add_argument("--status", default="", help="Filter by one status.")
    p_show.add_argument("--top-n", type=int, default=20, help="Max rows to display.")

    args = parser.parse_args()

    if args.cmd == "sync":
        sync_tracker(args.market, args.ch_focus, input_csv=args.input_csv, tracker_csv=args.tracker_csv)
    elif args.cmd == "update":
        update_tracker(
            args.market,
            args.ch_focus,
            job_id=args.job_id,
            status=args.status,
            note=args.note,
            follow_up_date=args.follow_up_date,
            applied_date=args.applied_date,
            tracker_csv=args.tracker_csv,
        )
    elif args.cmd == "show":
        show_tracker(
            args.market,
            args.ch_focus,
            status=args.status,
            top_n=args.top_n,
            tracker_csv=args.tracker_csv,
        )


if __name__ == "__main__":
    main()
