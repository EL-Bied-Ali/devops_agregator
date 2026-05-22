import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# FR apply-ready + best review jobs
print("=== FRANCE — apply_now vérifiés ===\n")
with open('data/fr_apply_queue.csv', newline='', encoding='utf-8-sig') as f:
    rows = [r for r in csv.DictReader(f) if r.get('recommended_action') == 'apply_now']
rows.sort(key=lambda r: -float(r.get('adjusted_priority_score', 0) or 0))

for r in rows:
    score = r.get('adjusted_priority_score','?')
    title = r.get('title','?') or '?'
    company = r.get('company','?') or '?'
    loc = r.get('location','?') or '?'
    remote = r.get('is_remote','') or ''
    url = r.get('url','') or ''
    remote_tag = ' [REMOTE]' if str(remote).lower() not in ('false','0','') else ''
    print(f"[{score}]{remote_tag} {title[:50]}")
    print(f"  {company} — {loc[:40]}")
    print(f"  {url}")
    print()
