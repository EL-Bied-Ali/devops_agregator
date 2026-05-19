import csv
from adzuna_fetch import configure_market, role_relevant, training_program_relevant

configure_market('de')

with open('data/de_all_jobs_merged_filtered_strict_enriched.csv', newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if 'siemens' in (row.get('company','') or '').lower() and 'graduate' in (row.get('title','') or '').lower():
            title = row.get('title','') or ''
            desc = row.get('description','') or ''
            print(f"Title: {title}")
            print(f"role_relevant: {role_relevant(title, desc)}")
            print(f"training_program_relevant: {training_program_relevant(title, desc)}")
            print(f"Desc[:800]: {desc[:800]}")
            break
