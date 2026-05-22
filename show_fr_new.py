import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# URLs déjà connues des 28 jobs précédents
known_from_fr_all = set()
try:
    with open('data/fr_all_apply_ready.csv', newline='', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            known_from_fr_all.add(r.get('url','') or r.get('canonical_url',''))
except:
    pass

new_jobs = []
known_jobs = []

with open('data/fr_penury_apply_ready.csv', newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
rows.sort(key=lambda r: -float(r.get('priority_score', 0) or 0))

for r in rows:
    url = r.get('url','') or r.get('canonical_url','') or ''
    if url in known_from_fr_all:
        known_jobs.append(r)
    else:
        new_jobs.append(r)

print(f"FR enrichissement pénurie: {len(rows)} apply-ready")
print(f"  Dont {len(new_jobs)} déjà connus + {len(new_jobs)} nouveaux\n")

print(f"=== {len(new_jobs)} NOUVEAUX jobs (via termes pénurie) ===\n")
for r in new_jobs:
    ps = r.get('priority_score','?')
    title = r.get('title','?') or '?'
    company = r.get('company','?') or '?'
    loc = r.get('location','?') or '?'
    url = r.get('url','') or ''
    desc = (r.get('description','') or '')[:250]
    desc_len = len(r.get('description','') or '')
    print(f"[{ps}] {desc_len}c | {title[:50]}")
    print(f"  {company} — {loc[:35]}")
    print(f"  {desc[:180]}")
    print(f"  {url}")
    print()
