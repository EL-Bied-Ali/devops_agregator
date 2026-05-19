from adzuna_fetch import configure_market, role_relevant, training_program_relevant, passes_filters

configure_market('de')

# Siemens graduate program (should KEEP)
title = "Shape your future – Join the Siemens Graduate Program"
desc = "Join Siemens as a graduate. Work with cloud infrastructure, Kubernetes, Terraform, Azure. The Graduate Technology Program offers hands-on DevOps and platform engineering experience. Junior-friendly."
created = "2026-05-10T00:00:00Z"

job = {"title": title, "company": {"display_name": "Siemens AG"}, "location": {"display_name": "Munich"}, "description": desc, "created": created, "salary_min": None, "salary_max": None, "redirect_url": "https://adzuna.de/1", "id": "test"}

print(f"role_relevant: {role_relevant(title, desc)}")
print(f"training_program_relevant: {training_program_relevant(title, desc)}")
result = passes_filters(job, filter_mode='strict')
print(f"passes_filters: {result is not None} (expected KEEP)")

# Picnic analytics (should DROP)
configure_market('nl')
title2 = "Analytics - Future Leaders Graduate Program"
desc2 = "Real ownership. Build from day one. Business Analytics at Picnic is a two-year launchpad. Join a business team, own a topic, become an expert."
job2 = {"title": title2, "company": {"display_name": "Picnic"}, "location": {"display_name": "Amsterdam"}, "description": desc2, "created": created, "salary_min": None, "salary_max": None, "redirect_url": "https://adzuna.nl/2", "id": "test2"}
result2 = passes_filters(job2, filter_mode='strict')
print(f"Picnic Analytics passes_filters: {result2 is not None} (expected DROP)")
