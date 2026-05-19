from adzuna_fetch import configure_market, detect_experience_requirement_details

configure_market('gb')

test_cases = [
    ("Site Reliability Engineer (SRE)", "We're looking for an SRE with 2-3 years of experience in DevOps, Platform Engineering, or SRE who can write production-quality code."),
    ("Junior Cloud Engineer", "Must ideally come with 1-2 years cloud engineering experience designing and building cloud infrastructure on Azure."),
    ("Junior DevOps Engineer", "No experience required. Fresh graduates welcome. We'll train you from day one."),
]

for title, desc in test_cases:
    level, detail, years = detect_experience_requirement_details(title, desc)
    print(f"Title: {title[:50]}")
    print(f"  -> level={level!r} detail={detail!r} years={years}")
    print()
