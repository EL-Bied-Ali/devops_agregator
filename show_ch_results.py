import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== CH ROMANDIE APPLY-READY (11 jobs) ===\n")
with open('data/ch_romandie_apply_ready.csv', newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
rows.sort(key=lambda r: -float(r.get('priority_score', 0) or 0))
for r in rows:
    ps = r.get('priority_score', '?')
    title = r.get('title', '?') or '?'
    company = r.get('company', '?') or '?'
    loc = r.get('location', '?') or '?'
    url = r.get('url', '') or r.get('redirect_url', '')
    desc = (r.get('description', '') or '')[:300]
    desc_len = len(r.get('description', '') or '')
    remote = r.get('is_remote', '') or ''
    remote_tag = ' [REMOTE]' if str(remote).lower() not in ('false', '0', '') else ''
    print(f"[{ps}]{remote_tag} {title[:50]}")
    print(f"  {company} — {loc[:40]}")
    print(f"  Desc({desc_len}c): {desc[:200]}")
    print(f"  {url}")
    print()

print("\n=== CH HARD-EXCLUDED (13 jobs) ===")
with open('data/ch_romandie_hard.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        reason = r.get('recheck_failure_reason', '') or ''
        print(f"  HARD: {r.get('title','?')[:45]} | {r.get('company','?')[:25]} | {reason[:70]}")

print("\n=== CH MANUAL-REVIEW top 10 ===")
with open('data/ch_romandie_manual.csv', newline='', encoding='utf-8-sig') as f:
    rows2 = list(csv.DictReader(f))
rows2.sort(key=lambda r: -float(r.get('priority_score', 0) or 0))
for r in rows2[:10]:
    ps = r.get('priority_score', '?')
    reason = r.get('manual_review_reason', '') or ''
    url = r.get('url', '') or ''
    print(f"  [{ps}] {r.get('title','?')[:45]} | {r.get('company','?')[:25]} | {reason[:60]}")
    print(f"        {url}")
