import csv
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

checks = [
    ('nl_all_jobs_merged_filtered_strict.csv', 'Bosch', 'DevOps'),
    ('nl_all_jobs_merged_filtered_strict.csv', 'B&S', 'Cloud'),
    ('fr_enriched_clean.csv', 'Cherry Pick', 'SRE'),
    ('fr_enriched_clean.csv', 'Pennylane', 'DevOps'),
]

for fname, company_q, title_q in checks:
    path = f'data/{fname}'
    with open(path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if company_q.lower() in (row.get('company','') or '').lower() and title_q.lower() in (row.get('title','') or '').lower():
                desc = (row.get('description','') or '')[:600]
                print(f"=== {row.get('title','?')} | {row.get('company','?')} ===")
                print(f"URL: {row.get('url','?')}")
                print(f"Desc: {desc}")
                print()
                break
