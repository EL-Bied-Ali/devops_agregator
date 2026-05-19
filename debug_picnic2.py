import adzuna_fetch
from adzuna_fetch import configure_market, role_relevant, training_program_relevant, SPEED_ROLE_TARGETS, ROLE_REQUIRED_KEYWORDS, keyword_hit, normalize_text

configure_market('nl')

title = "Analytics - Future Leaders Graduate Program"
desc = "Real ownership. Real impact. Build from day one. Are you an ambitious graduate ready to tackle complex, real-world challenges at the intersection of data, strategy and tech? The Future Leaders Graduate Program Business Analytics at Picnic is a two-year launchpad for exceptional talents. From day one, you join a business team, own a business topic, and become an expert in your field."

text = normalize_text(title + " " + desc)

print("Speed role targets HIT:")
for kw in SPEED_ROLE_TARGETS:
    if keyword_hit(text, kw, boundary_only=True):
        print(f"  HIT: {kw!r}")

print()
print("Required keywords HIT:")
for kw in ROLE_REQUIRED_KEYWORDS:
    if keyword_hit(text, kw, boundary_only=True):
        print(f"  HIT: {kw!r}")

print()
print("role_relevant:", role_relevant(title, desc))
print("training_program_relevant:", training_program_relevant(title, desc))
