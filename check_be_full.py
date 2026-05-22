import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== BE APPLY-READY — descriptions complètes ===\n")
with open('data/adzuna_jobs_filtered_strict_enriched.csv', newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

rows.sort(key=lambda r: -float(r.get('priority_score', 0) or 0))

for r in rows:
    if r.get('apply_ready_after_recheck') != 'True':
        continue
    title = r.get('title','?') or '?'
    company = r.get('company','?') or '?'
    loc = r.get('location','?') or '?'
    url = r.get('url','') or ''
    desc_api = r.get('description','') or ''
    scraped = r.get('scraped_description','') or r.get('fetched_full_description','') or ''
    full = scraped if len(scraped) > len(desc_api) else desc_api
    print(f"[{r.get('priority_score','?')}] {title[:50]}")
    print(f"  {company} — {loc[:35]}")
    print(f"  Desc({len(full)}c): {full[:500]}")
    print(f"  {url}")
    print()

print("\n=== BE MANUAL-REVIEW top 5 — descriptions complètes ===\n")
manual = [r for r in rows if r.get('manual_review_after_recheck') == 'True']
manual.sort(key=lambda r: -float(r.get('priority_score', 0) or 0))
for r in manual[:5]:
    title = r.get('title','?') or '?'
    company = r.get('company','?') or '?'
    reason = r.get('manual_review_reason','') or ''
    desc_api = r.get('description','') or ''
    scraped = r.get('scraped_description','') or r.get('fetched_full_description','') or ''
    full = scraped if len(scraped) > len(desc_api) else desc_api
    url = r.get('url','') or ''
    print(f"[{r.get('priority_score','?')}] {title[:50]}")
    print(f"  {company} | Raison: {reason[:60]}")
    print(f"  Desc({len(full)}c): {full[:400]}")
    print(f"  {url}")
    print()
