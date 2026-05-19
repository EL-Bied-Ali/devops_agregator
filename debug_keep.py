from adzuna_fetch import passes_filters, configure_market, role_relevant, training_program_relevant, location_ok, normalize, BAD_TITLE_KEYWORDS

configure_market('gb')

def make_job(title, company, loc, desc):
    return {"title": title, "company": {"display_name": company}, "location": {"display_name": loc}, "description": desc, "created": "2026-01-01T00:00:00Z", "salary_min": None, "salary_max": None, "redirect_url": "https://example.com/job/1", "id": "test123"}

cases = [
    ('Junior DevOps Engineer', 'Granite', 'Bristol', 'Join our DevOps team working with Kubernetes, Terraform, AWS. Entry level position ideal for graduates with cloud infrastructure knowledge.'),
    ('Graduate Cloud Engineer', 'KPMG', 'London', 'Join KPMG Technology as a Graduate Cloud Engineer working with Azure, Kubernetes, Terraform and CI/CD pipelines. Junior position.'),
]

for title, company, loc, desc in cases:
    job = make_job(title, company, loc, desc)
    norm_title = normalize(title)
    print(f'\n=== {title} ===')
    print(f'  BAD TITLE MATCH: {[bt for bt in BAD_TITLE_KEYWORDS if bt in norm_title]}')
    print(f'  location_ok: {location_ok(loc, title, desc)}')
    print(f'  role_relevant: {role_relevant(title, desc)}')
    print(f'  training_program_relevant: {training_program_relevant(title, desc)}')
    result = passes_filters(job)
    print(f'  passes_filters: {result is not None}')
