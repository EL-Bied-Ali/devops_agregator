import csv

markets = {
    'BE': 'data/be_apply_queue.csv',
    'NL': 'data/nl_apply_queue.csv',
    'DE': 'data/de_apply_queue.csv',
    'FR': 'data/fr_apply_queue.csv',
    'GB': 'data/gb_apply_queue.csv',
}

all_jobs = []
for market, path in markets.items():
    try:
        with open(path, newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                row['_market'] = market
                all_jobs.append(row)
    except Exception as e:
        print(f"ERROR {market}: {e}")

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
    by_market.setdefault(m, {'apply_now': 0, 'review': 0, 'other': 0})
    action = j.get('recommended_action', 'review')
    if action in ('apply_now', 'review'):
        by_market[m][action] += 1
    else:
        by_market[m]['other'] += 1
print()
for m in ['BE', 'NL', 'DE', 'FR', 'GB']:
    if m in by_market:
        c = by_market[m]
        print(f"  {m}: apply_now={c['apply_now']} review={c['review']}")

print()
print("=== TOP 25 APPLY NOW (ranked by score) ===")
for r in apply_now[:25]:
    mkt = r['_market']
    ps = r.get('adjusted_priority_score', '?')
    ss = r.get('sponsorship_score', '0')
    company = (r.get('company', '?') or '?')[:25]
    title = (r.get('title', '?') or '?')[:45]
    url = (r.get('url', '') or '')
    print(f"{mkt:<4} {ps:<6} spon={ss:<4} {company:<25} {title}")
    if url:
        print(f"     {url}")

print()
print("=== ALL BE JOBS ===")
for r in [j for j in all_jobs if j['_market'] == 'BE']:
    print(f"  [{r.get('recommended_action','?')}] {r.get('adjusted_priority_score','?')} | {r.get('title','?')[:50]} | {r.get('company','?')}")
    print(f"    {r.get('url','')}")
