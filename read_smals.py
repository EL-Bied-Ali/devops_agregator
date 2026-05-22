import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('data/adzuna_jobs_filtered_strict_enriched.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if 'smals' in (r.get('company','') or '').lower():
            scraped = r.get('scraped_description','') or r.get('fetched_full_description','') or ''
            desc = r.get('description','') or ''
            full = scraped if len(scraped) > len(desc) else desc
            print(f"SMALS ({len(full)}c):\n")
            print(full)
            break

print("\n\n=== CONNECT PEOPLE RESEAU ===\n")
with open('data/adzuna_jobs_filtered_strict_enriched.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if 'connect people' in (r.get('company','') or '').lower() and r.get('apply_ready_after_recheck') == 'True':
            scraped = r.get('scraped_description','') or r.get('fetched_full_description','') or ''
            desc = r.get('description','') or ''
            full = scraped if len(scraped) > len(desc) else desc
            print(f"CONNECT PEOPLE RÉSEAU ({len(full)}c):\n")
            print(full)
            break
