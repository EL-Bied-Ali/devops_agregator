import csv
from adzuna_fetch import configure_market, passes_filters, role_relevant, training_program_relevant, normalize, BAD_TITLE_KEYWORDS

configure_market('nl')

with open('data/nl_all_jobs_merged_filtered_strict_enriched.csv', newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if 'picnic' in (row.get('company','') or '').lower() or 'analytics' in (row.get('title','') or '').lower():
            title = row.get('title', '') or ''
            desc = row.get('description', '') or ''
            created = row.get('created', '2026-05-15T00:00:00Z')
            print(f"Title: {title}")
            print(f"Company: {row.get('company','?')}")
            print(f"Created: {created}")
            print(f"Desc[:600]: {desc[:600]}")
            print()
            # Check why it passes
            norm_title = normalize(title)
            print(f"BAD_TITLE match: {[bt for bt in BAD_TITLE_KEYWORDS if bt in norm_title]}")
            print(f"role_relevant: {role_relevant(title, desc)}")
            print(f"training_program_relevant: {training_program_relevant(title, desc)}")

            job = {"title": title, "company": {"display_name": row.get('company','')}, "location": {"display_name": row.get('location','')}, "description": desc, "created": created, "salary_min": None, "salary_max": None, "redirect_url": row.get('url','https://x.com'), "id": "test"}
            result = passes_filters(job, filter_mode='strict')
            print(f"passes_filters: {result is not None}")
            break
