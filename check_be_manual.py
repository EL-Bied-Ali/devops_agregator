import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== BE APPLY-READY (3 jobs from enrichment) ===")
with open('data/adzuna_jobs_apply_ready.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        desc = (r.get('description','') or '')[:300]
        print(f"Title: {r.get('title','?')} | {r.get('company','?')}")
        print(f"Desc: {desc}")
        print()

print("\n=== BE MANUAL-REVIEW (22 jobs) ===")
with open('data/adzuna_jobs_manual_review.csv', newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

rows.sort(key=lambda r: -float(r.get('priority_score', r.get('junior_score', 0)) or 0))
for r in rows:
    reason = r.get('manual_review_reason', '') or r.get('recheck_failure_reason', '') or ''
    desc = (r.get('description','') or '')[:200]
    print(f"[{r.get('priority_score','?')}] {r.get('title','?')[:45]} | {r.get('company','?')[:25]}")
    print(f"  Reason: {reason[:80]}")
    print(f"  Desc: {desc[:150]}")
    print()

print("\n=== BE HARD-EXCLUDED (12 jobs) ===")
with open('data/adzuna_jobs_hard_excluded.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        reason = r.get('recheck_failure_reason', '') or ''
        print(f"  HARD: {r.get('title','?')[:45]} | {r.get('company','?')[:25]} | {reason[:60]}")
