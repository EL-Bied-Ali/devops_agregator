import csv
from adzuna_fetch import configure_market, location_ok, passes_filters

with open('data/de_all_jobs_merged_filtered_strict.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if 'impower' in (row.get('company', '') or '').lower() or 'cluj' in (row.get('title', '') or '').lower():
            print(f"Title: {row.get('title','?')}")
            print(f"Company: {row.get('company','?')}")
            print(f"Location field: {row.get('location','?')!r}")
            print(f"Desc[:200]: {(row.get('description','') or '')[:200]}")

            configure_market('de')
            loc = row.get('location', '')
            title = row.get('title', '')
            desc = row.get('description', '') or ''
            print(f"location_ok({loc!r}): {location_ok(loc, title, desc)}")

            job = {"title": title, "company": {"display_name": row.get('company','')}, "location": {"display_name": loc}, "description": desc, "created": row.get('created', '2026-05-15T00:00:00Z'), "salary_min": None, "salary_max": None, "redirect_url": row.get('url', 'https://example.com'), "id": "test"}
            result = passes_filters(job, filter_mode='strict')
            print(f"passes_filters: {result is not None}")
            print()
