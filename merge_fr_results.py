"""Merge FR apply_now (19) + FR review apply-ready (9) into one clean FR queue."""
import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

files = [
    'data/fr_apply_now_enriched.csv',   # 19 from apply_now enrichment
    'data/fr_review_apply_ready.csv',   # 9 from review enrichment
]

all_rows = []
seen_urls = set()
fieldnames = None

for f in files:
    with open(f, newline='', encoding='utf-8-sig') as fh:
        reader = csv.DictReader(fh)
        if fieldnames is None:
            fieldnames = reader.fieldnames
        for row in reader:
            url = row.get('canonical_url') or row.get('url', '') or row.get('redirect_url', '')
            if url not in seen_urls:
                seen_urls.add(url)
                all_rows.append(row)

# Sort by priority_score
all_rows.sort(key=lambda r: -float(r.get('priority_score', 0) or 0))

print(f"FR combined apply-ready: {len(all_rows)} jobs")
for r in all_rows:
    ps = r.get('priority_score','?')
    title = r.get('title','?') or '?'
    company = r.get('company','?') or '?'
    url = r.get('url','') or ''
    print(f"  [{ps}] {title[:45]} | {company[:28]}")
    print(f"         {url}")

# Save combined
with open('data/fr_all_apply_ready.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"\nSaved to data/fr_all_apply_ready.csv")
