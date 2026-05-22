"""Re-enrich apply_now jobs that still have short (API-only) descriptions."""
import csv, sys, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sources = {
    'NL': ('data/nl_apply_queue.csv', 'data/nl_all_jobs_merged_filtered_strict.csv'),
    'DE': ('data/de_apply_queue.csv', 'data/de_all_jobs_merged_filtered_strict.csv'),
    'FR': ('data/fr_apply_queue.csv', 'data/fr_enriched_clean.csv'),
    'GB': ('data/gb_apply_queue.csv', 'data/gb_adzuna_jobs_filtered_strict.csv'),
}

SHORT_THRESHOLD = 500

import argparse
p = argparse.ArgumentParser()
p.add_argument('--market', default='GB')
p.add_argument('--max-jobs', type=int, default=30)
args = p.parse_args()

queue_file, data_file = sources[args.market]

# Build desc map from data file
desc_map = {}
rows_map = {}
with open(data_file, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        key = row.get('canonical_url') or row.get('url', '')
        desc_map[key] = row.get('description', '') or ''
        rows_map[key] = row

# Get apply_now jobs with short descriptions
short_jobs = []
with open(queue_file, newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if row.get('recommended_action') != 'apply_now':
            continue
        url = row.get('canonical_url') or row.get('url', '')
        desc = desc_map.get(url, '')
        if len(desc) < SHORT_THRESHOLD:
            score = float(row.get('adjusted_priority_score', 0) or 0)
            short_jobs.append((score, row.get('title','?'), row.get('company','?'), url))

short_jobs.sort(reverse=True)
print(f"{args.market}: {len(short_jobs)} apply_now jobs need enrichment")

# Write a temp CSV with just these jobs for enrichment
tmp_input = f'data/_enrich_{args.market.lower()}_tmp.csv'
with open(tmp_input, 'w', newline='', encoding='utf-8') as f:
    if fieldnames:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for score, title, company, url in short_jobs[:args.max_jobs]:
            data_row = rows_map.get(url)
            if data_row:
                writer.writerow(data_row)

print(f"Written {min(len(short_jobs), args.max_jobs)} jobs to {tmp_input}")
print(f"\nNext step: run enrichment on this file")
print(f"  python enrich_full_descriptions.py --market {args.market.lower()} \\")
print(f"    --input {tmp_input} \\")
print(f"    --output data/{args.market.lower()}_enriched_apply_now.csv \\")
print(f"    --apply-ready-output data/{args.market.lower()}_all_jobs_merged_filtered_strict.csv \\")
print(f"    --cache-path data/description_fetch_cache.json --max-jobs {args.max_jobs}")
