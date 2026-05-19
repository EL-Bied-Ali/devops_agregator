import csv

targets = ['Civil', 'Warehouse', 'Trinseo', 'Albert Heijn', 'Analytics', 'EUROPEAN DYNAMICS', 'Databricks']

with open('data/nl_all_jobs_merged_filtered_strict.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        title = row.get('title', '') or ''
        company = row.get('company', '') or ''
        if any(t.lower() in title.lower() or t.lower() in company.lower() for t in targets):
            print(f"=== {title} | {company} ===")
            desc = row.get('description', '') or ''
            print(f"Desc[:400]: {desc[:400]}")
            print()
