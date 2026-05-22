import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

targets = ['connect people', 'eumedica', 'smals']

with open('data/adzuna_jobs_filtered_strict_enriched.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        company = (r.get('company','') or '').lower()
        if not any(t in company for t in targets):
            continue
        title = r.get('title','?') or '?'
        hard = r.get('hard_excluded_after_recheck','')
        fail = r.get('fail_reason_after_recheck','') or ''
        hidden = r.get('hidden_exclude_hits','') or ''
        blocked = r.get('blocked_reason_detail','') or ''
        desc = (r.get('description','') or '')[:300]
        print(f"{title[:50]} | {r.get('company','?')}")
        print(f"  hard={hard} | fail={fail[:70]}")
        print(f"  blocked_detail={blocked[:50]} | hidden={hidden[:50]}")
        print(f"  desc: {desc[:200]}")
        print()
