import csv

problem_companies = ['TJMaxx', 'Ubisoft', 'SECLOUS', 'Scalable', 'Edwards', 'Jobs for Humanity']
problem_title_keywords = ['HR Graduate', 'Clinical Graduate', 'Investments', 'Game Security', 'Build Engineer', 'IT Analyst Graduate']

files = [
    ('GB', 'data/gb_adzuna_jobs_filtered_strict.csv'),
    ('GB-enriched', 'data/gb_adzuna_jobs_filtered_strict_enriched.csv'),
    ('DE', 'data/de_all_jobs_merged_filtered_strict.csv'),
    ('DE-enriched', 'data/de_all_jobs_merged_filtered_strict_enriched.csv'),
]

for label, f in files:
    try:
        with open(f, newline='', encoding='utf-8-sig') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                title = row.get('title', '')
                company = row.get('company', '')
                is_problem = (
                    any(p.lower() in title.lower() for p in problem_title_keywords) or
                    any(p.lower() in company.lower() for p in problem_companies)
                )
                if is_problem:
                    print(f'[{label}] Title: {title} | Company: {company}')
                    desc = (row.get('description', '') or '')
                    print(f'  Desc[:400]: {desc[:400]}')
                    print()
    except Exception as e:
        print(f'Error {f}: {e}')
