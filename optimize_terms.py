"""
Analyze search-term yield from Adzuna raw vs filtered outputs.

Produces a CSV with per-term throughput and page tuning suggestions.
"""

import argparse
from pathlib import Path

import pandas as pd

import adzuna_fetch as af
from config import (
    DEFAULT_PAGES,
    PAGES_PER_TERM,
    SUPPORTED_CH_FOCUS,
    SUPPORTED_MARKETS,
    get_output_paths,
)


def choose_output_path(market: str, ch_focus: str) -> str:
    base = get_output_paths(market)["term_performance_csv"]
    if market == "ch" and ch_focus != "all":
        p = Path(base)
        return str(p.with_name(f"{p.stem}_{ch_focus}{p.suffix}"))
    return base


def recommendation(raw_count: int, kept_count: int, keep_rate: float, current_pages: int) -> tuple[str, int]:
    if raw_count < 8:
        return "insufficient_data", current_pages
    if kept_count == 0:
        return "drop_or_pause", 1
    if keep_rate < 0.05 and kept_count <= 1:
        return "reduce_pages", max(1, current_pages - 1)
    if keep_rate >= 0.22 and kept_count >= 6:
        return "increase_pages", min(current_pages + 1, 8)
    return "keep", current_pages


def run(raw_csv: str, filtered_csv: str, output_csv: str):
    raw_df = pd.read_csv(raw_csv)
    filtered_df = pd.read_csv(filtered_csv)

    if "search_term" not in raw_df.columns:
        raise ValueError(f"'search_term' missing in raw CSV: {raw_csv}")
    if "search_term" not in filtered_df.columns:
        raise ValueError(f"'search_term' missing in filtered CSV: {filtered_csv}")

    raw_df["search_term"] = raw_df["search_term"].fillna("").astype(str).str.strip()
    filtered_df["search_term"] = filtered_df["search_term"].fillna("").astype(str).str.strip()

    raw_counts = raw_df.groupby("search_term", dropna=False).size().rename("raw_count")
    kept_counts = filtered_df.groupby("search_term", dropna=False).size().rename("kept_count")
    joined = pd.concat([raw_counts, kept_counts], axis=1).fillna(0).reset_index()

    joined["raw_count"] = joined["raw_count"].astype(int)
    joined["kept_count"] = joined["kept_count"].astype(int)
    joined["filtered_out_count"] = joined["raw_count"] - joined["kept_count"]
    joined["keep_rate_pct"] = (
        (joined["kept_count"] / joined["raw_count"].replace(0, pd.NA)).fillna(0) * 100
    ).round(1)
    joined["drop_rate_pct"] = (100 - joined["keep_rate_pct"]).round(1)
    total_kept = int(joined["kept_count"].sum())
    joined["share_of_kept_pct"] = (
        (joined["kept_count"] / total_kept).fillna(0) * 100 if total_kept else 0
    )
    joined["share_of_kept_pct"] = joined["share_of_kept_pct"].round(1)
    joined["current_pages"] = joined["search_term"].map(lambda t: int(PAGES_PER_TERM.get(t, DEFAULT_PAGES)))

    if "priority_score" in filtered_df.columns:
        avg_priority = filtered_df.groupby("search_term")["priority_score"].mean().rename("avg_priority_score")
        joined = joined.merge(avg_priority.round(1), on="search_term", how="left")
    else:
        joined["avg_priority_score"] = pd.NA

    if "junior_score" in filtered_df.columns:
        avg_junior = filtered_df.groupby("search_term")["junior_score"].mean().rename("avg_junior_score")
        joined = joined.merge(avg_junior.round(2), on="search_term", how="left")
    else:
        joined["avg_junior_score"] = pd.NA

    actions = joined.apply(
        lambda r: recommendation(
            int(r["raw_count"]),
            int(r["kept_count"]),
            float(r["keep_rate_pct"]) / 100.0,
            int(r["current_pages"]),
        ),
        axis=1,
    )
    joined["recommendation"] = actions.map(lambda x: x[0])
    joined["suggested_pages"] = actions.map(lambda x: x[1])
    joined["search_term"] = joined["search_term"].replace("", "(missing_term)")

    joined = joined.sort_values(
        by=["filtered_out_count", "kept_count", "keep_rate_pct"],
        ascending=[False, False, False],
    )

    af.safe_save_csv(joined, output_csv)

    print(f"[TERMS] Raw rows: {len(raw_df)}")
    print(f"[TERMS] Kept rows: {len(filtered_df)}")
    print(f"[TERMS] Terms analyzed: {len(joined)}")
    print(f"[TERMS] Report written: {output_csv}")

    print("\n[TERMS] Top terms by filtered_out_count:")
    for _, row in joined.head(10).iterrows():
        print(
            f"- {row['search_term']}: raw={int(row['raw_count'])} kept={int(row['kept_count'])} "
            f"dropped={int(row['filtered_out_count'])} keep_rate={row['keep_rate_pct']}% "
            f"action={row['recommendation']} pages={int(row['current_pages'])}->{int(row['suggested_pages'])}"
        )


def main():
    parser = argparse.ArgumentParser(description="Analyze Adzuna term-level yield.")
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
    parser.add_argument("--raw-csv", default="", help="Path to raw Adzuna CSV.")
    parser.add_argument("--filtered-csv", default="", help="Path to filtered Adzuna CSV.")
    parser.add_argument("--output-csv", default="", help="Path for term performance report CSV.")
    args = parser.parse_args()

    market = af.configure_market(args.market, args.ch_focus)
    ch_focus = af.ACTIVE_MARKET_PROFILE.get("ch_focus", "all")
    output_paths = get_output_paths(market)

    raw_csv = args.raw_csv or output_paths["adzuna_raw_csv"]
    filtered_csv = args.filtered_csv or output_paths["adzuna_filtered_csv"]
    output_csv = args.output_csv or choose_output_path(market, ch_focus)

    run(raw_csv, filtered_csv, output_csv)


if __name__ == "__main__":
    main()
