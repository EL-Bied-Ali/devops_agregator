import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

for market, apply_f, hard_f in [
    ('GB', 'data/gb_apply_now_enriched.csv', 'data/gb_apply_now_hard.csv'),
    ('DE', 'data/de_apply_now_enriched.csv', 'data/de_apply_now_hard.csv'),
    ('FR', 'data/fr_apply_now_enriched.csv', 'data/fr_apply_now_hard.csv'),
    ('NL', 'data/nl_apply_now_enriched.csv', 'data/nl_apply_now_hard.csv'),
]:
    print(f"=== {market} APPLY-READY (avec descriptions complètes) ===")
    with open(apply_f, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: -float(r.get('priority_score', 0) or 0))
    for r in rows:
        ps = r.get('priority_score', '?')
        desc_len = len(r.get('description', '') or '')
        title = r.get('title', '?') or '?'
        company = r.get('company', '?') or '?'
        url = r.get('url', '') or r.get('redirect_url', '')
        print(f"  [{ps}] {desc_len:5}c | {title[:45]} | {company[:25]}")
        if url:
            print(f"         {url}")

    print(f"\n{market} HARD-EXCLUDED:")
    with open(hard_f, newline='', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            reason = r.get('recheck_failure_reason', '') or ''
            title = r.get('title', '?') or '?'
            company = r.get('company', '?') or '?'
            print(f"  HARD: {title[:45]} | {company[:20]} | {reason[:70]}")
    print()
