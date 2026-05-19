import adzuna_fetch
from adzuna_fetch import configure_market, excluded_hits, job_text_for_rules, keyword_match, normalize_text

configure_market('gb')

# Check module-level EXCLUDE_KEYWORDS (updated by configure_market)
print("'landfill' in adzuna_fetch.EXCLUDE_KEYWORDS:", 'landfill' in adzuna_fetch.EXCLUDE_KEYWORDS)
print("Last 10 EXCLUDE_KEYWORDS:", adzuna_fetch.EXCLUDE_KEYWORDS[-10:])

title = "Graduate Solutions & Network Engineer"
desc = "Location: Ling Hall Landfill Site, Rugby. Veolia is a UK leader in environmental services, waste management, water, and energy services."

_rule_norm, full_text = job_text_for_rules({"title": title, "description": desc})
print("\nfull_text (first 300):", full_text[:300])
print("'landfill' in full_text:", 'landfill' in full_text)
print("'Landfill' in full_text:", 'Landfill' in full_text)

# Direct keyword match check
for kw in ['landfill', 'Landfill', 'waste management']:
    print(f"keyword_match(full_text, {kw!r}):", keyword_match(full_text, kw))

hits = excluded_hits(full_text)
print("\nexcluded_hits:", hits)
