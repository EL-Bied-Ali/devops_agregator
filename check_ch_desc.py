import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

targets = ['cern', 'evooq', 'nozomi', 'vitol', 'swisscom', 'infomaniak']

with open('data/ch_romandie_enriched_diag.csv', newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
    cols = rows[0].keys() if rows else []

print("Status columns:", [c for c in cols if any(x in c.lower() for x in ['recheck','hard','apply','manual','fail','reason','desc'])])
print()

for r in rows:
    company = (r.get('company','') or '').lower()
    if not any(t in company for t in targets):
        continue
    title = r.get('title','?') or '?'
    desc = r.get('description','') or ''
    apply_ready = r.get('apply_ready_after_recheck','?')
    hard = r.get('hard_excluded_after_recheck','?')
    fail = r.get('fail_reason_after_recheck','') or ''
    hidden = r.get('hidden_exclude_hits','') or ''
    desc_len = len(desc)
    print(f"=== {title[:50]} | {r.get('company','?')} ===")
    print(f"  apply_ready={apply_ready} | hard={hard} | desc={desc_len}c")
    print(f"  fail_reason: {fail[:80]}")
    print(f"  hidden_hits: {hidden[:60]}")
    if desc_len > 400:
        print(f"  FULL DESC (400-800): {desc[400:800]}")
    else:
        print(f"  DESC: {desc[:400]}")
    print()
