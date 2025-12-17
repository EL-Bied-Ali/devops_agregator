"""
Quick probe script to experiment with Jooble API locations for Belgium.
Safe to delete after use.
"""

import requests
from collections import Counter

API_KEY = "8c2517d4-85cf-4b1e-9729-6823aef99b1c"
BASES = [
    f"https://jooble.org/api/{API_KEY}",
    f"http://jooble.org/api/{API_KEY}",
    f"https://be.jooble.org/api/{API_KEY}",  # returns 403 with current key
    f"http://be.jooble.org/api/{API_KEY}",   # returns 403 with current key
]

KEYWORDS = "devops"

LOCATION_CANDIDATES = [
    "",  # no location
    "Belgium",
    "Belgique",
    "Brussels",
    "Bruxelles",
    "Belgium, Brussels",
    "BE",
    "Belgium, BE",
    "Antwerp",
    "Gent",
    "Ghent",
    "Liege",
    "Namur",
    "Luxembourg",
    "Netherlands",
    "Europe",
]


def probe():
    for base in BASES:
        print(f"\n=== Base: {base} ===")
        for loc in LOCATION_CANDIDATES:
            payload = {
                "keywords": KEYWORDS,
                "page": 1,
                "searchParam": {"pageSize": 20},
            }
            if loc:
                payload["location"] = loc

            try:
                resp = requests.post(base, json=payload, timeout=10)
                status = resp.status_code
                if status != 200:
                    print(f"loc='{loc or 'none'}' -> HTTP {status}")
                    continue
                data = resp.json()
                total = data.get("totalCount", 0)
                locs = [
                    j.get("location", "")
                    for j in data.get("jobs", [])
                    if j.get("location")
                ]
                bel_hits = sum(
                    any(x in l for x in ["Belgium", "Brussels", "Bruxelles", "Belgique"])
                    for l in locs
                )
                top = locs[:5]
                print(
                    f"loc='{loc or 'none'}' -> total={total}, sample={top}, belgium_hits_in_sample={bel_hits}"
                )
            except Exception as e:
                print(f"loc='{loc or 'none'}' -> error {e}")


if __name__ == "__main__":
    probe()
