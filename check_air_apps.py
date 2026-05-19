"""Check Air Apps and Booz Allen locations and descriptions."""
import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

checks = [
    ('data/de_all_jobs_merged_filtered_strict.csv', 'Air Apps', ''),
    ('data/de_all_jobs_merged_filtered_strict.csv', 'Booz Allen', ''),
    ('data/de_all_jobs_merged_filtered_strict.csv', 'Huawei', 'Site Design'),
    ('data/nl_all_jobs_merged_filtered_strict.csv', 'Air Apps', ''),
    ('data/fr_enriched_clean.csv', 'Air Apps', ''),
]

for fname, company_q, title_q in checks:
    with open(fname, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if company_q.lower() in (row.get('company','') or '').lower():
                if title_q and title_q.lower() not in (row.get('title','') or '').lower():
                    continue
                title = row.get('title','?') or '?'
                loc = row.get('location','?') or '?'
                desc = (row.get('description','') or '')[:500]
                print(f"=== {title} | {row.get('company','?')} | LOC={loc} | FILE={fname.split('/')[-1]} ===")
                print(f"Desc: {desc}")
                print()
                break
