import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== BE APPLY-READY (5 jobs vérifiés) ===\n")
with open('data/adzuna_jobs_apply_ready.csv', newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
rows.sort(key=lambda r: -float(r.get('priority_score', 0) or 0))
for r in rows:
    ps = r.get('priority_score', '?')
    title = r.get('title', '?') or '?'
    company = r.get('company', '?') or '?'
    loc = r.get('location', '?') or '?'
    url = r.get('url', '') or ''
    desc = (r.get('description', '') or '')[:350]
    desc_len = len(r.get('description', '') or '')
    print(f"[{ps}] {title[:50]}")
    print(f"  {company} — {loc[:35]}")
    print(f"  Desc({desc_len}c): {desc[:250]}")
    print(f"  {url}")
    print()

print("\n=== BE HARD-EXCLUDED — raisons ===")
with open('data/adzuna_jobs_hard_excluded.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        reason = r.get('recheck_failure_reason', '') or r.get('fail_reason_after_recheck', '') or ''
        print(f"  HARD: {r.get('title','?')[:42]} | {r.get('company','?')[:22]} | {reason[:65]}")

print("\n=== BE MANUAL-REVIEW top 8 (vaut la peine de vérifier) ===")
with open('data/adzuna_jobs_manual_review.csv', newline='', encoding='utf-8-sig') as f:
    rows2 = list(csv.DictReader(f))
rows2.sort(key=lambda r: -float(r.get('priority_score', 0) or 0))
for r in rows2[:8]:
    ps = r.get('priority_score', '?')
    reason = r.get('manual_review_reason', '') or ''
    url = r.get('url', '') or ''
    print(f"  [{ps}] {r.get('title','?')[:42]} | {r.get('company','?')[:22]} | {reason[:55]}")
    print(f"         {url}")
