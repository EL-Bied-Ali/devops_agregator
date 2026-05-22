import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Check columns in diag CSV first
with open('data/gb_apply_now_enriched_diag.csv', newline='', encoding='utf-8-sig') as f:
    cols = csv.DictReader(f).fieldnames
print("Columns in diag CSV:", [c for c in (cols or []) if 'reason' in c.lower() or 'status' in c.lower() or 'hard' in c.lower() or 'recheck' in c.lower()])

# Check full descriptions of hard-excluded
checks = [
    ('GB', 'data/gb_apply_now_enriched_diag.csv', ['Amazon', 'Yapily']),
    ('FR', 'data/fr_apply_now_enriched_diag.csv', ['Pennylane', 'Sidetrade']),
]

for market, diag_file, targets in checks:
    print(f"\n=== {market} ===")
    with open(diag_file, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = row.get('company', '') or ''
            if any(t.lower() in company.lower() for t in targets):
                title = row.get('title', '?')
                desc = (row.get('description', '') or '')
                desc_len = len(desc)
                # Find all non-empty reason/status fields
                reason_fields = {k: v for k, v in row.items() if v and any(x in k.lower() for x in ['reason', 'status', 'exclude', 'hard', 'recheck', 'gate'])}
                print(f"  Company: {company} | Title: {title[:45]}")
                print(f"  Desc length: {desc_len}c")
                print(f"  Reason fields: {reason_fields}")
                if desc_len > 400:
                    # Show portion that might contain exclusion trigger
                    print(f"  Desc[400:800]: {desc[400:800]}")
                else:
                    print(f"  Full desc: {desc[:400]}")
                print()
