import csv

with open('data/nl_all_jobs_merged_filtered_strict.csv', newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

print(f'NL enriched clean: {len(rows)} jobs')
print()
for r in rows:
    title = r.get('title', '') or ''
    company = r.get('company', '') or ''
    ps = r.get('priority_score', r.get('adjusted_priority_score', '?'))
    ss = r.get('sponsorship_score', '0')
    desc_start = (r.get('description', '') or '')[:120]
    print(f"[{ps}] spon={ss} | {title[:45]} | {company[:25]}")
