"""Check descriptions of jobs by market and action."""
import csv, sys, argparse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

queues = {
    'NL': ('data/nl_apply_queue.csv', 'data/nl_all_jobs_merged_filtered_strict.csv'),
    'DE': ('data/de_apply_queue.csv', 'data/de_all_jobs_merged_filtered_strict.csv'),
    'FR': ('data/fr_apply_queue.csv', 'data/fr_enriched_clean.csv'),
    'GB': ('data/gb_apply_queue.csv', 'data/gb_adzuna_jobs_filtered_strict.csv'),
    'BE': ('data/be_apply_queue.csv', 'data/adzuna_jobs_apply_ready.csv'),
}

p = argparse.ArgumentParser()
p.add_argument('--market', default='DE')
p.add_argument('--action', default='review')
p.add_argument('--top', type=int, default=20)
p.add_argument('--min-score', type=int, default=0)
args = p.parse_args()

queue_file, data_file = queues.get(args.market, queues['DE'])

desc_map = {}
try:
    with open(data_file, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            key = row.get('canonical_url') or row.get('url', '')
            desc_map[key] = row.get('description', '') or ''
except Exception as e:
    print(f"[WARN] {e}")

with open(queue_file, newline='', encoding='utf-8-sig') as f:
    rows = [r for r in csv.DictReader(f)
            if r.get('recommended_action') == args.action
            and float(r.get('adjusted_priority_score', 0) or 0) >= args.min_score]

rows.sort(key=lambda r: -float(r.get('adjusted_priority_score', 0) or 0))
print(f"{args.market} {args.action} (score>={args.min_score}): {len(rows)} jobs — showing top {args.top}")
print()
for r in rows[:args.top]:
    title = r.get('title', '?') or '?'
    company = r.get('company', '?') or '?'
    ps = r.get('adjusted_priority_score', '?')
    ss = r.get('sponsorship_score', '0')
    url = r.get('url', '') or ''
    desc = desc_map.get(r.get('canonical_url') or url, '')[:300]
    print(f"[{ps}] spon={ss} | {title[:50]} | {company[:28]}")
    if url:
        print(f"  URL: {url}")
    if desc:
        print(f"  Desc: {desc[:200]}")
    print()
