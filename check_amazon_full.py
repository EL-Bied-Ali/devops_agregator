import csv

with open('data/gb_adzuna_jobs_filtered_strict_enriched.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if 'amazon' in (row.get('company','') or '').lower() and 'devops' in (row.get('title','') or '').lower():
            print(f"=== {row.get('title','?')} | {row.get('company','?')} ===")
            print(f"URL: {row.get('url','?')}")
            desc = row.get('description','') or ''
            print(f"FULL Desc ({len(desc)} chars):")
            print(desc)
            break
