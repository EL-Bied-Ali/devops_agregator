import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

targets = ['connect people', 'eumedica', 'smals', 'swift', 'google', 'cisco']

with open('data/adzuna_jobs_filtered_strict.csv', newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        company = (row.get('company','') or '').lower()
        if any(t in company for t in targets):
            title = row.get('title','?') or '?'
            loc = row.get('location','?') or '?'
            term = row.get('search_term','?') or '?'
            desc = (row.get('description','') or '')[:400]
            url = row.get('url','') or ''
            print(f"=== {title} | {row.get('company','?')} | {loc} ===")
            print(f"Via: {term} | URL: {url}")
            print(f"Desc: {desc}")
            print()
