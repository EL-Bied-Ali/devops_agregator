"""
Daily pipeline runner + new high-priority alert detection.

Flow:
1) Refresh filtered jobs (Adzuna, optional no-fetch mode)
2) Enrich full descriptions and re-check hidden constraints (optional)
3) Sync application tracker
4) Build apply queue
5) Detect newly surfaced high-priority jobs and optionally send webhook alert
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

import pandas as pd
import requests
from pandas.errors import EmptyDataError

from config import (
    SUPPORTED_CH_FOCUS,
    SUPPORTED_FILTER_MODES,
    SUPPORTED_MARKETS,
    get_market_profile,
    get_output_paths,
    resolve_filter_mode,
)


def safe_read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def run_cmd(cmd: list[str]):
    print(f"[DAILY] Run: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip())
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {"alerted_job_ids": [], "last_run": ""}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"alerted_job_ids": [], "last_run": ""}


def save_state(path: str, data: dict):
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def send_webhook(webhook_url: str, text: str):
    if not webhook_url:
        return
    try:
        # Generic payload for simple webhook endpoints.
        requests.post(webhook_url, json={"text": text, "message": text}, timeout=10)
        print("[DAILY] Webhook alert sent.")
    except Exception as e:
        print(f"[DAILY][WARN] Webhook failed: {e}")


def focused_path(path: str, market: str, ch_focus: str) -> str:
    if market != "ch" or ch_focus in ("", "all"):
        return path
    p = Path(path)
    return str(p.with_name(f"{p.stem}_{ch_focus}{p.suffix}"))


def preferred_existing_path(base_path: str, market: str, ch_focus: str) -> str:
    """Prefer focus-specific path when it exists, else fallback to base path."""
    focused = focused_path(base_path, market, ch_focus)
    if os.path.exists(focused):
        return focused
    return base_path


def main():
    parser = argparse.ArgumentParser(description="Run daily job pipeline and alert on new high-priority jobs.")
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
        help="Filtering strictness (strict|broad). Defaults to JOB_FILTER_MODE env var or strict.",
    )
    parser.add_argument("--top-n", type=int, default=20, help="Apply queue size.")
    parser.add_argument("--min-priority", type=int, default=68, help="Min score for apply_now.")
    parser.add_argument("--alert-top-k", type=int, default=8, help="Max new jobs in alert message.")
    parser.add_argument("--no-fetch", action="store_true", help="Use existing raw CSVs without API fetch.")
    parser.add_argument(
        "--skip-enrich",
        action="store_true",
        help="Skip full-description enrichment/recheck step.",
    )
    parser.add_argument("--enrich-sleep", type=float, default=1.0, help="Seconds to sleep between enriched page requests.")
    parser.add_argument("--enrich-max-retries", type=int, default=3, help="Max retries per enriched page request.")
    parser.add_argument("--enrich-timeout", type=int, default=15, help="Timeout seconds for enriched page request.")
    parser.add_argument(
        "--enrich-use-browser",
        action="store_true",
        help="Use Playwright browser fallback in enrichment for blocked pages.",
    )
    parser.add_argument("--enrich-browser-timeout", type=int, default=15, help="Playwright timeout seconds.")
    parser.add_argument("--enrich-max-jobs", type=int, default=0, help="Limit enriched rows (0 = all).")
    parser.add_argument(
        "--webhook-url",
        default="",
        help="Optional webhook URL. Defaults to JOB_ALERT_WEBHOOK_URL env var.",
    )
    args = parser.parse_args()

    market = (args.market or os.getenv("JOB_MARKET") or "be").strip().lower()
    ch_focus = (args.ch_focus or os.getenv("JOB_CH_FOCUS") or "all").strip().lower()
    filter_mode = resolve_filter_mode(args.filter_mode, allow_both=False)
    profile = get_market_profile(market, ch_focus)
    paths = get_output_paths(market)

    py = sys.executable
    root = os.path.dirname(os.path.abspath(__file__))
    if market == "ma":
        filtered_key = "merged_filtered_strict_csv" if filter_mode == "strict" else "merged_filtered_broad_csv"
    else:
        filtered_key = "adzuna_filtered_strict_csv" if filter_mode == "strict" else "adzuna_filtered_broad_csv"
    filtered_csv = preferred_existing_path(paths[filtered_key], market, profile["ch_focus"])
    p_filtered = Path(filtered_csv)
    enriched_csv = str(p_filtered.with_name(f"{p_filtered.stem}_enriched{p_filtered.suffix}"))

    if market == "ma":
        emploi_cmd = [
            py,
            os.path.join(root, "emploi_ma_fetch.py"),
            "--market",
            market,
            "--ch-focus",
            ch_focus,
            "--filter-mode",
            filter_mode,
        ]
        if args.no_fetch:
            emploi_cmd.append("--no-fetch")
        run_cmd(emploi_cmd)
        rekrute_cmd = [
            py,
            os.path.join(root, "rekrute_fetch.py"),
            "--market",
            market,
            "--ch-focus",
            ch_focus,
            "--filter-mode",
            filter_mode,
        ]
        if args.no_fetch:
            rekrute_cmd.append("--no-fetch")
        run_cmd(rekrute_cmd)
        marocannonces_cmd = [
            py,
            os.path.join(root, "marocannonces_fetch.py"),
            "--market",
            market,
            "--ch-focus",
            ch_focus,
            "--filter-mode",
            filter_mode,
        ]
        if args.no_fetch:
            marocannonces_cmd.append("--no-fetch")
        run_cmd(marocannonces_cmd)
        run_cmd(
            [
                py,
                os.path.join(root, "merge_jobs.py"),
                "--market",
                market,
                "--ch-focus",
                ch_focus,
                "--filter-mode",
                filter_mode,
            ]
        )
    else:
        adzuna_cmd = [
            py,
            os.path.join(root, "adzuna_fetch.py"),
            "--market",
            market,
            "--ch-focus",
            ch_focus,
            "--filter-mode",
            filter_mode,
        ]
        if args.no_fetch:
            adzuna_cmd.append("--no-fetch")
        run_cmd(adzuna_cmd)

    if market == "ma":
        print("[DAILY] Enrichment skipped for market=ma because Emploi.ma fetch already stores full detail pages.")
    elif not args.skip_enrich:
        enrich_cmd = [
            py,
            os.path.join(root, "enrich_full_descriptions.py"),
            "--market",
            market,
            "--ch-focus",
            ch_focus,
            "--filter-mode",
            filter_mode,
            "--input",
            filtered_csv,
            "--output",
            enriched_csv,
            "--filtered-output",
            filtered_csv,
            "--sleep",
            str(args.enrich_sleep),
            "--max-retries",
            str(args.enrich_max_retries),
            "--timeout",
            str(args.enrich_timeout),
            "--browser-timeout",
            str(args.enrich_browser_timeout),
        ]
        if args.enrich_use_browser:
            enrich_cmd.append("--use-browser")
        if args.enrich_max_jobs and args.enrich_max_jobs > 0:
            enrich_cmd.extend(["--max-jobs", str(args.enrich_max_jobs)])
        run_cmd(enrich_cmd)

    run_cmd(
        [
            py,
            os.path.join(root, "application_tracker.py"),
            "--market",
            market,
            "--ch-focus",
            ch_focus,
            "sync",
            "--input-csv",
            filtered_csv,
        ]
    )

    run_cmd(
        [
            py,
            os.path.join(root, "apply_queue.py"),
            "--market",
            market,
            "--ch-focus",
            ch_focus,
            "--input-csv",
            filtered_csv,
            "--top-n",
            str(args.top_n),
            "--min-priority",
            str(args.min_priority),
        ]
    )

    queue_csv = focused_path(paths["apply_queue_csv"], market, profile["ch_focus"])
    state_json = focused_path(paths["daily_alert_state_json"], market, profile["ch_focus"])
    queue = safe_read_csv(queue_csv)
    if queue.empty:
        print(f"[DAILY] Queue empty: {queue_csv}")
        return

    if "recommended_action" in queue.columns:
        queue = queue[queue["recommended_action"].astype(str) == "apply_now"].copy()
    if "status" in queue.columns:
        queue = queue[queue["status"].astype(str).str.lower().isin(["to_apply", "saved"])].copy()

    state = load_state(state_json)
    alerted = set(str(x) for x in state.get("alerted_job_ids", []))
    queue["job_id"] = queue.get("job_id", "").astype(str)
    new_jobs = queue[~queue["job_id"].isin(alerted)].copy()

    print(
        f"[DAILY] market={market} ch_focus={profile['ch_focus']} "
        f"apply_now={len(queue)} new_alerts={len(new_jobs)}"
    )

    webhook_url = args.webhook_url or os.getenv("JOB_ALERT_WEBHOOK_URL", "").strip()
    if len(new_jobs) > 0:
        cols = [c for c in ["priority_score", "title", "company", "location", "url", "job_id"] if c in new_jobs.columns]
        top_new = new_jobs.sort_values(
            by=[c for c in ["priority_score", "language_fit_score", "junior_score"] if c in new_jobs.columns],
            ascending=False,
        ).head(args.alert_top_k)[cols]

        lines = [
            f"New high-priority jobs: {len(new_jobs)} (market={market}, ch_focus={profile['ch_focus']})",
        ]
        for _, r in top_new.iterrows():
            lines.append(
                f"- [{int(r.get('priority_score', 0))}] {r.get('title', '')} | {r.get('company', '')} | "
                f"{r.get('location', '')} | {r.get('url', '')}"
            )
        message = "\n".join(lines)
        print(message)
        send_webhook(webhook_url, message)

    updated_ids = list(alerted.union(set(queue["job_id"].astype(str).tolist())))
    state["alerted_job_ids"] = updated_ids
    state["last_run"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    save_state(state_json, state)
    print(f"[DAILY] State saved: {state_json}")


if __name__ == "__main__":
    main()
