"""Check description length and flag apply_now jobs with short (API-only) descriptions."""
import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sources = {
    'NL': ('data/nl_apply_queue.csv', 'data/nl_all_jobs_merged_filtered_strict.csv'),
    'DE': ('data/de_apply_queue.csv', 'data/de_all_jobs_merged_filtered_strict.csv'),
    'FR': ('data/fr_apply_queue.csv', 'data/fr_enriched_clean.csv'),
    'GB': ('data/gb_apply_queue.csv', 'data/gb_adzuna_jobs_filtered_strict.csv'),
}

SHORT_THRESHOLD = 500  # chars — below this = likely truncated API desc

for market, (queue_file, data_file) in sources.items():
    desc_map = {}
    with open(data_file, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            key = row.get('canonical_url') or row.get('url', '')
            desc_map[key] = row.get('description', '') or ''

    short_apply_now = []
    all_apply_now = []

    with open(queue_file, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row.get('recommended_action') != 'apply_now':
                continue
            url = row.get('canonical_url') or row.get('url', '')
            desc = desc_map.get(url, '')
            title = row.get('title', '?')
            company = row.get('company', '?')
            score = row.get('adjusted_priority_score', '?')
            all_apply_now.append((title, company, score, len(desc)))
            if len(desc) < SHORT_THRESHOLD:
                short_apply_now.append((title, company, score, len(desc), url))

    print(f"\n{market}: {len(all_apply_now)} apply_now — {len(short_apply_now)} with SHORT desc (<{SHORT_THRESHOLD} chars)")
    if short_apply_now:
        for title, company, score, dlen, url in sorted(short_apply_now, key=lambda x: -float(x[2] or 0)):
            print(f"  [{score}] {dlen:4}c | {title[:45]} | {company[:28]}")
            print(f"         {url}")
