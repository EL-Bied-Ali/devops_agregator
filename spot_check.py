"""Check specific jobs from the enriched CSV by company/title."""
import csv

checks = [
    ('Amazon', 'Graduate Devops', 'gb_adzuna_jobs_filtered_strict.csv'),
    ('Impower', 'DevOps', 'de_all_jobs_merged_filtered_strict.csv'),
    ('Albany Beck', 'DevOps', 'gb_adzuna_jobs_filtered_strict.csv'),
    ('Alteam', 'DevOps', 'gb_adzuna_jobs_filtered_strict.csv'),
    ('BMR', 'Cloud', 'gb_adzuna_jobs_filtered_strict.csv'),
    ('Yapily', 'Cloud', 'gb_adzuna_jobs_filtered_strict.csv'),
    ('Pertemps', 'SRE', 'gb_adzuna_jobs_filtered_strict.csv'),
    ('Veolia', 'Network', 'gb_adzuna_jobs_filtered_strict.csv'),
]

for company_q, title_q, fname in checks:
    path = f'data/{fname}'
    try:
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if company_q.lower() in (row.get('company', '') or '').lower() and \
                   title_q.lower() in (row.get('title', '') or '').lower():
                    print(f"=== {row.get('title', '?')} | {row.get('company','?')} ===")
                    print(f"URL: {row.get('url','?')}")
                    desc = row.get('description', '') or ''
                    print(f"Desc[:500]: {desc[:500]}")
                    print()
                    break
    except Exception as e:
        print(f"Error {path}: {e}")
