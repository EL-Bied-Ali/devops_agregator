import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

targets = ['michael page', 'reisel', 'epoque', 'capgemini', 'alten', 'ekinox', 'studio rh', 'inforgeran']

with open('data/fr_penury_enriched_diag.csv', newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

cols = rows[0].keys() if rows else []
desc_cols = [c for c in cols if 'desc' in c.lower() or 'scraped' in c.lower() or 'fetched' in c.lower()]
print("Desc-related columns:", desc_cols)
print()

for r in rows:
    company = (r.get('company','') or '').lower()
    if not any(t in company for t in targets):
        continue

    apply_ready = r.get('apply_ready_after_recheck','')
    hard = r.get('hard_excluded_after_recheck','')
    fail = r.get('fail_reason_after_recheck','') or ''
    title = r.get('title','?') or '?'

    desc_api = r.get('description','') or ''
    desc_scraped = r.get('scraped_description','') or r.get('fetched_full_description','') or r.get('combined_description','') or ''

    print(f"=== {title[:50]} | {r.get('company','?')} ===")
    print(f"  apply_ready={apply_ready} | hard={hard}")
    if fail:
        print(f"  fail={fail[:80]}")
    print(f"  API desc: {len(desc_api)}c | Scraped: {len(desc_scraped)}c")
    if desc_scraped and len(desc_scraped) > len(desc_api):
        print(f"  FULL DESC (extra): {desc_scraped[len(desc_api):len(desc_api)+400]}")
    elif desc_scraped:
        print(f"  Scraped: {desc_scraped[:300]}")
    else:
        print(f"  API only: {desc_api[:300]}")
    print()
