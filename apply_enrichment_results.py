"""
Appliquer les résultats d'enrichissement aux apply_queues:
- Retirer les hard-excluded
- Mettre les apply-ready enrichis en apply_now
- Mettre les manual-review enrichis en review
"""
import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def load_csv(path):
    try:
        with open(path, newline='', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        return rows
    except Exception as e:
        print(f"[WARN] {e}")
        return []

def save_csv(rows, path, fieldnames=None):
    if not rows:
        return
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames or rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

markets = {
    'gb': {
        'queue': 'data/gb_apply_queue.csv',
        'hard': 'data/gb_apply_now_hard.csv',
        'manual': 'data/gb_apply_now_manual.csv',
    },
    'de': {
        'queue': 'data/de_apply_queue.csv',
        'hard': 'data/de_apply_now_hard.csv',
        'manual': 'data/de_apply_now_manual.csv',
    },
    'fr': {
        'queue': 'data/fr_apply_queue.csv',
        'hard': 'data/fr_apply_now_hard.csv',
        'manual': 'data/fr_apply_now_manual.csv',
    },
    'nl': {
        'queue': 'data/nl_apply_queue.csv',
        'hard': 'data/nl_apply_now_hard.csv',
        'manual': 'data/nl_apply_now_manual.csv',
    },
}

for market, paths in markets.items():
    queue = load_csv(paths['queue'])
    hard = load_csv(paths['hard'])
    manual = load_csv(paths['manual'])

    hard_urls = set()
    for r in hard:
        hard_urls.add(r.get('canonical_url') or r.get('url') or r.get('redirect_url', ''))
        hard_urls.add(r.get('url', ''))

    manual_urls = set()
    for r in manual:
        manual_urls.add(r.get('canonical_url') or r.get('url') or r.get('redirect_url', ''))
        manual_urls.add(r.get('url', ''))

    hard_urls.discard('')
    manual_urls.discard('')

    updated = []
    n_hard = 0
    n_demoted = 0
    for row in queue:
        url = row.get('url', '') or row.get('canonical_url', '')
        canon = row.get('canonical_url', '') or url
        # Check if hard excluded
        if url in hard_urls or canon in hard_urls:
            n_hard += 1
            continue  # drop completely
        # If it was apply_now but manual-review after enrichment → demote to review
        if row.get('recommended_action') == 'apply_now':
            if url in manual_urls or canon in manual_urls:
                row = dict(row)
                row['recommended_action'] = 'review'
                row['apply_now_gate_reason'] = 'enrichment:demoted_to_review'
                n_demoted += 1
        updated.append(row)

    fieldnames = queue[0].keys() if queue else []
    save_csv(updated, paths['queue'], fieldnames=fieldnames)

    apply_now_count = sum(1 for r in updated if r.get('recommended_action') == 'apply_now')
    review_count = sum(1 for r in updated if r.get('recommended_action') == 'review')
    print(f"{market.upper()}: {len(queue)} -> {len(updated)} (dropped {n_hard} hard, demoted {n_demoted}) | apply_now={apply_now_count} review={review_count}")
