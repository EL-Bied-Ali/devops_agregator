"""Extract review jobs from a queue for enrichment."""
import csv, sys, argparse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

queues = {
    'FR': ('data/fr_apply_queue.csv', 'data/fr_enriched_clean.csv'),
    'DE': ('data/de_apply_queue.csv', 'data/de_all_jobs_merged_filtered_strict.csv'),
    'NL': ('data/nl_apply_queue.csv', 'data/nl_all_jobs_merged_filtered_strict.csv'),
    'GB': ('data/gb_apply_queue.csv', 'data/gb_adzuna_jobs_filtered_strict.csv'),
}

p = argparse.ArgumentParser()
p.add_argument('--market', default='FR')
p.add_argument('--max-jobs', type=int, default=30)
p.add_argument('--min-score', type=int, default=65)
args = p.parse_args()

queue_file, data_file = queues[args.market]

desc_map = {}
rows_map = {}
with open(data_file, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        key = row.get('canonical_url') or row.get('url', '')
        desc_map[key] = row.get('description', '') or ''
        rows_map[key] = row

review_jobs = []
with open(queue_file, newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if row.get('recommended_action') != 'review':
            continue
        score = float(row.get('adjusted_priority_score', 0) or 0)
        if score < args.min_score:
            continue
        url = row.get('canonical_url') or row.get('url', '')
        review_jobs.append((score, row.get('title','?'), row.get('company','?'), url))

review_jobs.sort(reverse=True)
print(f"{args.market}: {len(review_jobs)} review jobs with score>={args.min_score}")

tmp_input = f'data/_enrich_{args.market.lower()}_review_tmp.csv'
written = 0
with open(tmp_input, 'w', newline='', encoding='utf-8') as f:
    if fieldnames:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for score, title, company, url in review_jobs[:args.max_jobs]:
            data_row = rows_map.get(url)
            if data_row:
                writer.writerow(data_row)
                written += 1

print(f"Written {written} jobs to {tmp_input}")
