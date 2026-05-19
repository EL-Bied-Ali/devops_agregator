"""Check location_ok and description for specific problem jobs."""
import csv
from adzuna_fetch import configure_market, location_ok, passes_filters, role_relevant, TITLE_DOMAIN_BLOCKERS

# Check Impower DE Cluj
configure_market('de')
print("=== IMPOWER DE (Cluj) ===")
loc = "Cluj"
title = "DevOps Engineer (m/f/d) – Cluj"
desc = "Cluj | Hybrid | DevOps Engineer At Impower, we are redefining how property management works. Thousands of property managers still rely on outdated tools. We are based in Cluj, Romania but operate across Germany."
print(f"location_ok({loc!r}): {location_ok(loc, title, desc)}")
print(f"role_relevant: {role_relevant(title, desc)}")

# Full check with dummy job
job = {"title": title, "company": {"display_name": "Impower"}, "location": {"display_name": loc}, "description": desc, "created": "2026-05-15T00:00:00Z", "salary_min": None, "salary_max": None, "redirect_url": "https://example.com/job/99", "id": "test"}
result = passes_filters(job, filter_mode='strict')
print(f"passes_filters: {result is not None}")
print()

# Check Veolia GB (landfill)
configure_market('gb')
print("=== VEOLIA GB (landfill) ===")
loc = "Rugby, Warwickshire"
title = "Graduate Solutions & Network Engineer"
desc = "Do you see yourself in a graduate role? Salary: £30,000 Location: Ling Hall Landfill Site, Coalpit Lane, Rugby, Warwickshire Programme Duration: 2-year programme, starting September 2026. Veolia is a UK leader in environmental services, waste management, water, and energy services."
print(f"location_ok({loc!r}): {location_ok(loc, title, desc)}")
print(f"role_relevant: {role_relevant(title, desc)}")
for blocker in TITLE_DOMAIN_BLOCKERS:
    if blocker in title.lower():
        print(f"TITLE BLOCKER HIT: {blocker!r}")

job = {"title": title, "company": {"display_name": "Veolia"}, "location": {"display_name": loc}, "description": desc, "created": "2026-05-15T00:00:00Z", "salary_min": None, "salary_max": None, "redirect_url": "https://example.com/job/100", "id": "test2"}
result = passes_filters(job, filter_mode='strict')
print(f"passes_filters: {result is not None}")
print()

# Amazon GB - check if UK national required
print("=== AMAZON GB Graduate DevOps ===")
configure_market('gb')
