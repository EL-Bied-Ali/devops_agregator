import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

queues = {
    'NL': 'data/nl_apply_queue.csv',
    'DE': 'data/de_apply_queue.csv',
    'FR': 'data/fr_apply_queue.csv',
    'GB': 'data/gb_apply_queue.csv',
}

# Jobs where a junior with Master + AZ-400 + 6 months has realistic chances
# Priority: explicitly junior, remote/hybrid, known sponsors, accessible description
best = [
    # (market, company_fragment, title_fragment)
    # REMOTE prioritaires
    ('DE', 'giant swarm', ''),
    ('DE', 'smartclip', ''),
    ('DE', 'voize', ''),
    # Junior explicit
    ('GB', 'iris audio', ''),
    ('GB', 'booksonix', ''),
    ('GB', 'granite', ''),
    ('GB', 'sparta global', ''),
    ('FR', 'atlanse', ''),
    ('FR', 'macompta', ''),
    ('FR', 'shape it', ''),
    ('FR', 'skynopy', ''),
    # Sponsor explicite / migration background welcome
    ('DE', 'd4l', ''),
    ('DE', 'lemon.markets', ''),
    ('DE', 'sopra steria', ''),
    ('DE', 'cardmarket', ''),
    ('DE', 'caspar', ''),
    # NL
    ('NL', 'studocu', ''),
    ('NL', 'xebia', ''),       # en review mais training program = meilleur option
    ('NL', 'bosch', ''),       # en review mais internship valide
    ('NL', 'ireckonu', ''),    # AZ-400 mentionné!
    # FR extras
    ('FR', 'winamax', ''),
    ('FR', 'cherry pick', ''),
    ('FR', 'extia', ''),
]

seen_urls = set()

for market, company_q, title_q in best:
    queue_file = queues[market]
    with open(queue_file, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            company = (row.get('company', '') or '').lower()
            title = (row.get('title', '') or '').lower()
            if company_q and company_q not in company:
                continue
            if title_q and title_q not in title:
                continue
            url = row.get('url', '') or ''
            if url in seen_urls:
                continue
            seen_urls.add(url)
            action = row.get('recommended_action', '?')
            score = row.get('adjusted_priority_score', '?')
            is_remote = row.get('is_remote', '') or ''
            print(f"[{market}][{action}][score={score}] {row.get('title','?')[:45]} — {row.get('company','?')[:25]}")
            if is_remote and str(is_remote).lower() not in ('false', '0', ''):
                print(f"  REMOTE ✓")
            print(f"  {url}")
            print()
            break
