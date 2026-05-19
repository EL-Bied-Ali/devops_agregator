"""Check descriptions of top questionable jobs."""
import csv

to_check = [
    ('gb_adzuna_jobs_filtered_strict.csv', 'Amazon', 'Graduate Devops'),
    ('gb_adzuna_jobs_filtered_strict.csv', 'Pertemps', 'SRE'),
    ('gb_adzuna_jobs_filtered_strict.csv', 'BMR', 'Cloud'),
    ('de_all_jobs_merged_filtered_strict.csv', 'Huawei', 'RAN'),
]

for fname, company_q, title_q in to_check:
    path = f'data/{fname}'
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if company_q.lower() in (row.get('company','') or '').lower() and title_q.lower() in (row.get('title','') or '').lower():
                print(f"=== {row.get('title','?')} | {row.get('company','?')} ===")
                desc = row.get('description', '') or ''
                # Print full description (truncated to 1000 chars)
                print(f"Desc:\n{desc[:1000]}")
                print()
                break
