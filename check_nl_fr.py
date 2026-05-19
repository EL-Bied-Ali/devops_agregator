import csv

for market, fname in [('NL', 'data/nl_all_jobs_merged_filtered_strict.csv'), ('FR', 'data/fr_adzuna_jobs_filtered_strict.csv')]:
    with open(fname, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    print(f'\n{market}: {len(rows)} jobs')
    for r in rows:
        title = r.get('title', '') or ''
        company = r.get('company', '') or ''
        ps = r.get('adjusted_priority_score', '?')
        print(f'  [{ps}] {title[:50]} | {company[:25]}')
