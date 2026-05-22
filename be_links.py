import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

targets = {
    'APPLY-READY': ['data/adzuna_jobs_apply_ready.csv'],
    'MANUAL-REVIEW (vaut la peine)': ['data/adzuna_jobs_manual_review.csv'],
}

interesting_manual = ['sander', 'google', 'swift', 'approach cyber', 'vass', 'itproposal', 'cisco']

for label, files in targets.items():
    print(f"\n{'='*60}")
    print(f"{label}")
    print('='*60)
    for f in files:
        with open(f, newline='', encoding='utf-8-sig') as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            company = (r.get('company','') or '').lower()
            if label == 'MANUAL-REVIEW (vaut la peine)':
                if not any(t in company for t in interesting_manual):
                    continue
            title = r.get('title','?') or '?'
            company_orig = r.get('company','?') or '?'
            url = r.get('url', '') or r.get('redirect_url', '') or r.get('canonical_url', '')
            reason = r.get('manual_review_reason','') or ''
            desc = (r.get('description','') or '')[:200]
            print(f"\n{title}")
            print(f"Entreprise : {company_orig}")
            print(f"Lien : {url}")
            if reason:
                print(f"Note : {reason[:80]}")
            print(f"Aperçu : {desc[:150]}")
