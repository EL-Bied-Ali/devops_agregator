from adzuna_fetch import passes_filters, configure_market

configure_market('gb')

def make_job(title, company, loc, desc):
    return {"title": title, "company": {"display_name": company}, "location": {"display_name": loc}, "description": desc, "created": "2026-05-15T00:00:00Z", "salary_min": None, "salary_max": None, "redirect_url": "https://example.com/job/1", "id": "test123"}

test_cases = [
    # These should be DROPPED
    ('HR Graduate', 'Jobs for Humanity', 'london', 'We are looking for a HR Graduate to join our Transportation team. Kier Transportation builds and maintains infrastructure for the highways, rail, aviation and ports sectors.', 'DROP'),
    ('IT Analyst Graduate Programme', 'TJMaxx', 'london', 'At TJX Europe, every day brings new opportunities for growth. Distribution Centers, Corporate Offices, or Retail Stores. TK Maxx & Homesense.', 'DROP'),
    ('Clinical Graduate Program - Munich', 'Edwards Lifesciences', 'Munich', 'Make a meaningful difference to patients around the world. Our Clinical Graduate Program helps early-career professionals in the medical device industry.', 'DROP'),
    ('Graduate Program 2026 - Investments & Banking (m/f/x)', 'Scalable GmbH', 'Munich', 'Our Graduate Program - Investments & Banking is designed to provide graduates with comprehensive understanding of the financial services industry.', 'DROP'),
    ('Game Security Engineer (QA) (f/m/d)', 'Ubisoft', 'Berlin', 'Join our team as a Game Security Engineer QA where you will ensure quality of our game security and anti-cheat solutions.', 'DROP'),
    ('Build Engineer (C++ Ecosystem) | all gender | onsite Munich', 'SECLOUS', 'Munich', 'SECLOUS stands for innovation, trust and security. We deliver capabilities to build more secure C++ products using our NVD technology. Junior engineer welcome.', 'DROP'),
    # These should still PASS
    ('Junior DevOps Engineer', 'Granite', 'Bristol', 'Join our DevOps team working with Kubernetes, Terraform, AWS. Entry level position ideal for graduates with cloud infrastructure knowledge. We offer visa sponsorship and relocation support.', 'KEEP'),
    ('Graduate Cloud Engineer', 'KPMG', 'London', 'Join KPMG Technology as a Graduate Cloud Engineer working with Azure, Kubernetes, Terraform and CI/CD pipelines. Junior position. We are open to international candidates.', 'KEEP'),
]

ok = 0
fail = 0
for title, company, loc, desc, expected in test_cases:
    job = make_job(title, company, loc, desc)
    result = passes_filters(job)
    kept = result is not None
    actual = 'KEEP' if kept else 'DROP'
    status = 'OK' if actual == expected else 'FAIL'
    if status == 'OK':
        ok += 1
    else:
        fail += 1
    print(f'{status} {actual} (expected {expected}): {title[:60]}')

print(f'\n{ok}/{ok+fail} correct')
