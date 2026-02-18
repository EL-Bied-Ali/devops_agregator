from __future__ import annotations

import argparse

import pandas as pd

import adzuna_fetch as af
from config import SUPPORTED_CH_FOCUS, SUPPORTED_FILTER_MODES, SUPPORTED_MARKETS, resolve_filter_mode


def as_text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def summarize_rows(rows: list[dict], header: str, limit: int = 20):
    print(f"\n{header} (showing {min(limit, len(rows))}/{len(rows)})")
    if not rows:
        print("- none")
        return
    for idx, row in enumerate(rows[:limit], start=1):
        print(
            f"{idx:02d}. [{row.get('reason', '')}] {row.get('title', '')} | {row.get('company', '')} | "
            f"{row.get('location', '')} | evidence={row.get('evidence', '')}"
        )


def main():
    parser = argparse.ArgumentParser(description="Debug language rules on an enriched CSV.")
    parser.add_argument("--input", default="data/adzuna_jobs_filtered_strict_enriched.csv")
    parser.add_argument("--market", choices=SUPPORTED_MARKETS, default="be")
    parser.add_argument("--ch-focus", choices=SUPPORTED_CH_FOCUS, default="")
    parser.add_argument("--filter-mode", choices=SUPPORTED_FILTER_MODES[:2], default="strict")
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    af.configure_market(args.market, args.ch_focus)
    _mode = resolve_filter_mode(args.filter_mode, allow_both=False)

    df = pd.read_csv(args.input)
    blocked_rows: list[dict] = []
    optional_nl_rows: list[dict] = []

    for _, row in df.iterrows():
        title = as_text(row.get("title", ""))
        company = as_text(row.get("company", ""))
        location = as_text(row.get("location", ""))
        desc = as_text(row.get("combined_description", "")) or as_text(row.get("description", ""))
        text = f"{title} {desc}"

        req = af.language_requirements(text)
        reason = af.blocked_language_requirement_reason(text)
        evidence = " | ".join(req.get("evidence", []))

        if reason:
            blocked_rows.append(
                {
                    "reason": reason,
                    "title": title,
                    "company": company,
                    "location": location,
                    "evidence": evidence,
                }
            )

        required = set(req.get("required_langs", set()))
        optional = set(req.get("optional_langs", set()))
        if "nl" in optional and "nl" not in required:
            optional_nl_rows.append(
                {
                    "reason": "optional_nl_only",
                    "title": title,
                    "company": company,
                    "location": location,
                    "evidence": evidence,
                }
            )

    summarize_rows(blocked_rows, "Top jobs blocked by explicit language requirement", limit=args.top)
    summarize_rows(optional_nl_rows, "Top jobs mentioning NL as optional (not required)", limit=args.top)


if __name__ == "__main__":
    main()
