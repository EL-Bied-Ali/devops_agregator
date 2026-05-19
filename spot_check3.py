"""Re-check fixed false positives after location and filter fixes."""
from adzuna_fetch import configure_market, passes_filters, location_ok

def make_job(title, company, loc, desc, market):
    configure_market(market)
    return {"title": title, "company": {"display_name": company}, "location": {"display_name": loc}, "description": desc, "created": "2026-05-15T00:00:00Z", "salary_min": None, "salary_max": None, "redirect_url": "https://example.com/job/x", "id": "test"}

cases = [
    ('de', 'DevOps Engineer (m/f/d) – Cluj', 'Impower', 'Cluj', 'Cluj | Hybrid | DevOps Engineer. Impower is redefining property management. We are based in Cluj, Romania.', 'DROP'),
    ('gb', 'Graduate Solutions & Network Engineer', 'Veolia', 'Rugby, Warwickshire', 'Location: Ling Hall Landfill Site, Rugby. Veolia is a UK leader in environmental services, waste management, water, and energy services.', 'DROP'),
    ('de', 'Junior DevOps Engineer', 'Siemens', 'Munich', 'Join Siemens Munich as a Junior DevOps Engineer. Work with Kubernetes, Docker, Terraform in our cloud platform team. Junior level.', 'KEEP'),
    ('gb', 'Junior Cloud Engineer', 'Yapily', 'London', 'Junior Cloud Engineer at Yapily open banking platform. Work with AWS, Kubernetes, Terraform. No experience required, fresh graduates welcome.', 'KEEP'),
]

for market, title, company, loc, desc, expected in cases:
    configure_market(market)
    job = {"title": title, "company": {"display_name": company}, "location": {"display_name": loc}, "description": desc, "created": "2026-05-15T00:00:00Z", "salary_min": None, "salary_max": None, "redirect_url": "https://example.com/job/x", "id": "test"}
    result = passes_filters(job, filter_mode='strict')
    actual = 'KEEP' if result is not None else 'DROP'
    status = 'OK' if actual == expected else 'FAIL'
    print(f'{status} {actual} ({expected}) [{market.upper()}]: {title[:55]}')
