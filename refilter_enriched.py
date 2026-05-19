"""Re-apply updated filter rules to enriched CSVs without re-fetching descriptions."""
import csv
import sys
from adzuna_fetch import passes_filters, configure_market

def refilter(market: str, input_csv: str, output_csv: str):
    configure_market(market)
    kept = []
    dropped = []
    with open(input_csv, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            job = {
                "title": row.get("title", ""),
                "company": {"display_name": row.get("company", "")},
                "location": {"display_name": row.get("location", "")},
                "description": row.get("description", ""),
                "created": row.get("created", "2026-05-01T00:00:00Z"),
                "salary_min": row.get("salary_min"),
                "salary_max": row.get("salary_max"),
                "redirect_url": row.get("url", "") or row.get("canonical_url", ""),
                "id": row.get("job_id", "refilter"),
            }
            result = passes_filters(job, filter_mode="strict")
            if result is not None:
                kept.append(row)
            else:
                dropped.append(row.get("title", "?") + " | " + row.get("company", "?"))

    with open(output_csv, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    print(f"[REFILTER] Market={market} input={input_csv}")
    print(f"[REFILTER] Kept={len(kept)} Dropped={len(dropped)}")
    for d in dropped:
        print(f"  DROPPED: {d}")
    print(f"[REFILTER] Output -> {output_csv}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--market", required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    refilter(args.market, args.input, args.output)
