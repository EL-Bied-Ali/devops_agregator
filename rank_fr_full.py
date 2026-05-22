"""Read all FR enriched diagnostics and show full descriptions for apply-ready jobs."""
import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

diag_files = [
    'data/fr_apply_now_enriched_diag.csv',   # batch 1 (19 jobs)
    'data/fr_review_enriched_diag.csv',       # batch 2 (9 jobs from review)
    'data/fr_penury_enriched_diag.csv',       # batch 3 (26 jobs via penury terms)
]

seen_urls = set()
all_ready = []

for fname in diag_files:
    try:
        with open(fname, newline='', encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                if r.get('apply_ready_after_recheck') != 'True':
                    continue
                url = r.get('url','') or r.get('canonical_url','') or ''
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                desc_api = r.get('description','') or ''
                scraped = r.get('scraped_description','') or r.get('fetched_full_description','') or ''
                full = scraped if len(scraped) > len(desc_api) else desc_api
                r['_full_desc'] = full
                r['_desc_len'] = len(full)
                all_ready.append(r)
    except Exception as e:
        print(f"Error {fname}: {e}")

all_ready.sort(key=lambda r: -float(r.get('priority_score', 0) or 0))

print(f"FR apply-ready total unique: {len(all_ready)} jobs\n")

for r in all_ready:
    ps = r.get('priority_score','?')
    title = r.get('title','?') or '?'
    company = r.get('company','?') or '?'
    loc = r.get('location','?') or '?'
    url = r.get('url','') or ''
    full = r['_full_desc']
    dlen = r['_desc_len']
    print(f"[{ps}] {dlen}c | {title[:50]}")
    print(f"  {company} — {loc[:35]}")
    # Show the substantive part (skip company intro, show profile/missions)
    relevant = full[300:900] if dlen > 600 else full
    print(f"  {relevant[:400]}")
    print(f"  {url}")
    print()
