"""Check full scraped descriptions for top ranking candidates."""
import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

checks = [
    # (market, file, company_q, title_q)
    ('FR', 'data/fr_all_apply_ready.csv', 'atlanse', 'junior'),
    ('FR', 'data/fr_all_apply_ready.csv', 'dassault', ''),
    ('FR', 'data/fr_all_apply_ready.csv', 'winamax', ''),
    ('FR', 'data/fr_all_apply_ready.csv', 'capgemini', 'cloud devops'),
    ('FR', 'data/fr_penury_enriched_diag.csv', 'michael page', 'junior'),
    ('DE', 'data/de_apply_now_enriched.csv', 'd4l', ''),
    ('GB', 'data/gb_apply_now_enriched.csv', 'iris audio', ''),
    ('GB', 'data/gb_apply_now_enriched.csv', 'granite', ''),
    ('GB', 'data/gb_apply_now_enriched.csv', 'sparta', ''),
    ('NL', 'data/nl_apply_now_enriched.csv', 'studocu', ''),
]

for market, fname, company_q, title_q in checks:
    try:
        with open(fname, newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                company = (row.get('company','') or '').lower()
                title = (row.get('title','') or '').lower()
                if company_q not in company:
                    continue
                if title_q and title_q not in title:
                    continue
                hard = row.get('hard_excluded_after_recheck','')
                if hard == 'True':
                    continue
                desc_api = row.get('description','') or ''
                scraped = row.get('scraped_description','') or row.get('fetched_full_description','') or ''
                full = scraped if len(scraped) > len(desc_api) else desc_api
                print(f"[{market}] {row.get('title','?')[:45]} | {row.get('company','?')}")
                print(f"  Desc: {full[200:600]}")
                print()
                break
    except Exception as e:
        print(f"Error {fname}: {e}")
