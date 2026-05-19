import csv

markets = {'NL': 'data/nl_apply_queue.csv', 'DE': 'data/de_apply_queue.csv', 'FR': 'data/fr_apply_queue.csv', 'GB': 'data/gb_apply_queue.csv'}
all_jobs = []
for market, path in markets.items():
    with open(path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            row['_market'] = market
            all_jobs.append(row)

def sort_key(r):
    try: ps = float(r.get('adjusted_priority_score', 0) or 0)
    except: ps = 0
    try: ss = float(r.get('sponsorship_score', 0) or 0)
    except: ss = 0
    return (-ps, -ss)

all_jobs.sort(key=sort_key)
apply_now = [j for j in all_jobs if j.get('recommended_action') == 'apply_now']
review = [j for j in all_jobs if j.get('recommended_action') == 'review']

print(f'Total: {len(all_jobs)} | APPLY NOW: {len(apply_now)} | REVIEW: {len(review)}')
by_market = {}
for j in all_jobs:
    m = j['_market']
    by_market.setdefault(m, {'apply_now': 0, 'review': 0})
    action = j.get('recommended_action', 'review')
    if action in ('apply_now', 'review'):
        by_market[m][action] += 1
for m, counts in sorted(by_market.items()):
    print(f"  {m}: apply_now={counts['apply_now']} review={counts['review']}")

print()
print("=== TOP 15 APPLY NOW ===")
for r in apply_now[:15]:
    mkt = r['_market']
    ps = r.get('adjusted_priority_score', '?')
    ss = r.get('sponsorship_score', '0')
    company = (r.get('company', '?') or '?')[:25]
    title = (r.get('title', '?') or '?')[:45]
    url = (r.get('url', '') or '')
    print(f"{mkt:<4} {ps:<6} spon={ss:<4} {company:<25} {title}")
    if url:
        print(f"     {url}")
